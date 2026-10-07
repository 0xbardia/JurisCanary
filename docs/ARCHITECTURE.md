# Architecture

JurisCanary freezes each semantic test vector at registration. A recheck reads that stored definition, independently evaluates it through GenLayer consensus, and applies a deterministic transition against the original baseline.

## Persistent state

| Field | Type | Purpose |
| --- | --- | --- |
| `case_count` | `u256` | Last allocated sequential ID; starts at zero |
| `cases` | `TreeMap[u256, CaseRecord]` | Case state keyed by IDs starting at 1 |
| `CaseDefinition` | `@allow_storage` dataclass | ID, creator, question, evidence snapshot, ordered criteria, ordered outcomes |
| `Evaluation` | `@allow_storage` dataclass | Exact outcome and ordered criterion statuses |
| `RecheckRecord` | `@allow_storage` dataclass | Accepted evaluation plus its baseline-relative status |
| `CaseRecord` | `@allow_storage` dataclass | Immutable definition and baseline, latest evaluation, append-only rechecks, counters, latest status |

All persistent fields are declared on the contract class. `DynArray` stores criteria, outcomes, and history; `TreeMap` stores the cases. Counters use `u256`. Before nondeterministic evaluation, rechecking copies the definition with `gl.storage.copy_to_memory` and extracts ordinary in-memory strings and arrays. No storage reference is captured by the Leader or Validator closures.

There is no owner, update method, external source call, timestamp dependency, or administrator path. Missing IDs are checked against both `case_count` and the map, so zero-initialized storage cannot create a phantom case. Case IDs advance only after accepted registration consensus.

## State transitions

```text
registration accepted
  baseline = latest = evaluation
  recheck_count = drift_count = 0
  latest_drift_status = BASELINE

recheck accepted
  compare accepted evaluation with immutable baseline
  append RecheckRecord
  latest = accepted evaluation
  recheck_count += 1
  drift_count += 1 iff status is not STABLE
  latest_drift_status = computed status
```

The deterministic classifier checks the overall outcome first. A different outcome is `OUTCOME_DRIFT`; otherwise a different vector is `CRITERIA_DRIFT`; otherwise the result is `STABLE`. A failed Leader, Validator, or consensus path returns no accepted evaluation, so contract code reaches no state transition. The GenLayer transaction is atomic if execution reverts.

History contains rechecks only, so `recheck_count == len(rechecks)`. The baseline is stored separately and never replaced. Latest is independently materialized from the accepted result; historical evaluations are not reused as mutable storage objects.

## Bounded work

Input validation happens before consensus. The question, evidence, criterion count and lengths, outcome count and lengths, duplicate labels, surrounding outcome whitespace, and control characters have explicit application limits in the contract. The contract stores at most 256 cases. A recheck can process at most eight criteria and four outcomes and rechecks are capped at 64 per case. Reads use a case ID and, for history, a direct index; no routine operation scans every case or the full history.

The 256-case cap bounds total state growth for one instance. Every registration still requires its own on-chain transaction, and no operation’s work scales with the total map size. Deploy separate instances when an application needs more cases or independent storage domains.

## Reviewer reuse

The API can back a governance regression suite, an eligibility rubric, or an SLA interpretation history. A downstream contract can store the returned case ID alongside its own proposal, application, or incident ID and poll `get_drift_status` before applying its own deterministic policy.

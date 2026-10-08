# JurisCanary

JurisCanary is a reusable semantic regression primitive: it records a frozen question, evidence snapshot, criteria, allowed outcomes, and a consensus-approved baseline, then asks GenLayer consensus to evaluate the same case again later. It detects whether the accepted outcome or any criterion interpretation changed. It does not fetch mutable sources, store model reasoning, or settle an external claim.

## Why GenLayer

A conventional deterministic contract can compare stored bytes, but it cannot independently interpret natural-language criteria against evidence. JurisCanary asks the Leader and Validators to interpret the same frozen case independently, then stores an evaluation only when the network accepts the semantic result. Deterministic contract code classifies drift after that consensus step.

## Flow

1. `register_case` validates bounded input and evaluates it with `run_nondet_unsafe`.
2. After consensus accepts, the contract stores the exact case definition and evaluation as both `baseline` and `latest`.
3. `recheck_case` copies the immutable definition to memory, independently evaluates it through the same consensus path, compares the accepted fields with the baseline, then appends one history record.

The contract stores only `overall_outcome` and an ordered `criteria_results` vector containing `PASS`, `FAIL`, or `UNKNOWN`. It does not store chain-of-thought or free-form model prose.

## Example case

```json
{
  "question": "Return ELIGIBLE only when the applicant is at least 18.",
  "evidence_snapshot": "Applicant age: 18.",
  "criteria": ["The record states an age of at least 18."],
  "allowed_outcomes": ["ELIGIBLE", "INELIGIBLE"]
}
```

`criteria` and `allowed_outcomes` are ordered. Outcomes are exact, case-sensitive labels with no surrounding whitespace. The question should state how the outcome follows from the criterion results. V1 requires at least one criterion and at least two distinct outcomes.

## Public API

Writes:

- `register_case(question, evidence_snapshot, criteria, allowed_outcomes) -> case_id`
- `recheck_case(case_id) -> drift_status`

Views:

- `get_version() -> string`
- `get_case_count() -> int`
- `case_exists(case_id) -> bool`
- `get_case_definition(case_id) -> CaseDefinition`
- `get_baseline(case_id) -> Evaluation`
- `get_latest_result(case_id) -> Evaluation`
- `get_drift_status(case_id) -> string`
- `get_drift_count(case_id) -> int`
- `get_recheck_count(case_id) -> int`
- `get_recheck(case_id, index) -> RecheckRecord`

Missing case IDs and missing history indexes raise explicit user errors. Case IDs start at 1. `case_exists(0)` is false.

Statuses are `BASELINE` before the first recheck, then one of:

- `STABLE`: outcome and criteria vector both equal baseline.
- `CRITERIA_DRIFT`: outcome equals baseline but the criteria vector differs.
- `OUTCOME_DRIFT`: outcome differs from baseline, regardless of the criteria vector.

## Limits

These are JurisCanary application limits, not GenLayer protocol limits. String limits count Python Unicode code points. Newlines, carriage returns, and tabs are permitted; other C0 controls, DEL/C1 controls, and surrogate code points are rejected.

| Input | Limit |
| --- | ---: |
| Question | 512 characters |
| Evidence snapshot | 4,096 characters |
| Criteria | 1–8, each at most 256 characters |
| Outcomes | 2–4, each at most 32 characters |
| Cases per contract | 256 |
| Rechecks per case | 64 |

Registration and rechecking are permissionless. Each recheck is bounded by the frozen definition sizes. A contract accepts at most 256 cases; deploy another instance for a separate suite. A case cannot be edited; register a new case to represent a new version.

## Test and static checks

Python 3.12 or newer is required. The dependency header pins the contract runner used by the current stable Studio toolchain; set the same GenVM bundle for local validation:

```bash
python -m pip install -r requirements.txt
export GENVM_VERSION=v0.2.16
genvm-lint check contracts/juris_canary.py
genvm-lint lint contracts/juris_canary.py
genvm-lint validate contracts/juris_canary.py
genvm-lint typecheck contracts/juris_canary.py --strict
genvm-lint schema contracts/juris_canary.py --output artifacts/juris_canary.schema.json
pytest tests/direct -v
PYTHONPATH=/path/to/genlayer-testing-suite GENVM_VERSION=v0.2.16 \
  PATH=/path/to/venv/bin:$PATH \
  pytest --network localnet -m integration tests/integration -v
```

Direct Mode enables `direct_vm.check_pickling` for every test. Studio Mode uses the configured local Studio with `leader_only: false`; it is an integration gate, not a substitute for Direct Mode. The integration harness uses the current `genlayer-py` client API because the older `genlayer-test` contract wrapper does not match the SDK's `fees` and call signatures.

## Deployment

The target is stable Studionet (`https://studio.genlayer.com/api`, chain ID `61999`). The CLI deployment form for this zero-argument constructor is:

```bash
genlayer deploy --contract contracts/juris_canary.py --rpc https://studio.genlayer.com/api
```

Use Studio or the current CLI to call array-valued write arguments. Record the deployment transaction, address, source hash, schema hash, and final transaction status. See [CERTIFICATION.md](docs/CERTIFICATION.md) for the executed release evidence and any blocked gates.

## Reuse patterns

- Governance: freeze a proposal, constitution excerpt, and ordered voting criteria; recheck after a model or policy revision.
- Eligibility: freeze an application record and program rubric; track stable, changed, and uncertain criterion interpretations.
- Compliance or SLA review: freeze the contract clause and incident record; keep the original accepted reading and every later evaluation.

## Limitations

JurisCanary detects consensus interpretation changes; it does not establish legal truth or guarantee that a model’s interpretation is correct. Prompt instructions and JSON encoding reduce injection risk but cannot prove that every model will ignore adversarial text. Exact field matching favors safety: disagreement or malformed output prevents an accepted update. V1 has no source fetching, case editing, administrator, timestamps, reasoning archive, or more than 64 rechecks per case.

## Current certification state

Certification remains `BLOCKED_EXTERNAL` pending Studionet deployment and live read/write certification. The historical local `runner_actions` failure reproduced on minimal and official contracts under the obsolete local stack; after upgrading local Studio/GenVM, all three deployment controls and the full local consensus integration suite passed. Studionet's public RPC rejected both the official control and the one final frozen-source JurisCanary submission with its hourly request-rate limit. See [CERTIFICATION.md](docs/CERTIFICATION.md) for transaction IDs, the environment comparison, and the remaining gate.

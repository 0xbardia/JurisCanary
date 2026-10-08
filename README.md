# JurisCanary

JurisCanary is a GenLayer semantic-regression primitive that freezes a semantic test case, establishes a consensus-approved baseline, and detects later interpretation drift against the exact same evidence and criteria.

## Why it exists

Traditional deterministic contracts can regression-test code. Intelligent Contracts also need a way to regression-test semantic interpretation as validators and models evolve. JurisCanary uses GenLayer consensus to independently evaluate natural-language criteria, then uses ordinary deterministic contract code to compare each accepted result with its baseline.

## How it works

```text
Frozen case
    ↓
Leader evaluation
    ↓
Independent Validator evaluation
    ↓
GenLayer consensus
    ↓
Accepted structured result
    ↓
Deterministic comparison with immutable baseline
    ↓
STABLE / CRITERIA_DRIFT / OUTCOME_DRIFT
```

The frozen definition contains the question, evidence snapshot, ordered criteria, and ordered allowed outcomes. Rechecks use that stored snapshot; V1 never refetches mutable external evidence. The Leader and Validators treat case content as data. Validators independently evaluate the same frozen inputs and compare the exact decision-bearing fields. State changes only after consensus accepts an evaluation.

The contract stores only `overall_outcome` and the ordered `criteria_results` vector (`PASS`, `FAIL`, or `UNKNOWN`). It does not request or persist hidden reasoning or free-form prose.

## Example case

```json
{
  "question": "Return ELIGIBLE only when the applicant is at least 18.",
  "evidence_snapshot": "Applicant age: 18.",
  "criteria": ["The record states an age of at least 18."],
  "allowed_outcomes": ["ELIGIBLE", "INELIGIBLE"]
}
```

Criteria and outcomes are ordered. Outcome labels are exact, case-sensitive strings. V1 requires at least one criterion and two or more distinct outcomes.

## Drift statuses

- `STABLE`: outcome and criteria vector match the baseline.
- `CRITERIA_DRIFT`: outcome matches, but one or more criterion results differ.
- `OUTCOME_DRIFT`: outcome differs; this takes precedence over criteria drift.

Before the first recheck, the status is `BASELINE`. A failed or undetermined consensus does not update state.

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

Missing case IDs and history indexes raise explicit user errors. Case IDs start at 1; `case_exists(0)` is false.

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

Registration and rechecking are permissionless. A case cannot be edited; register a new case for a new version. Deploy another instance for a separate suite or to increase its case capacity.

## Reuse examples

- Governance: freeze a proposal, constitution excerpt, and ordered voting criteria; recheck after a model or policy revision.
- Eligibility: freeze an application record and program rubric; track changes in criterion interpretations.
- Compliance: preserve the policy and evidence snapshot used for a review.
- SLA interpretation: recheck a frozen service clause and incident record.
- Protocol constitutions: maintain regression cases for governance rules.

## Checks and tests

Python 3.12 or newer is required. From a virtual environment, install the pinned test and linter dependencies, then run the static and Direct Mode gates:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
export GENVM_VERSION=v0.2.16
genvm-lint check contracts/juris_canary.py
genvm-lint lint contracts/juris_canary.py
genvm-lint validate contracts/juris_canary.py
genvm-lint typecheck contracts/juris_canary.py --strict
genvm-lint schema contracts/juris_canary.py --output artifacts/juris_canary.schema.json
pytest tests/direct -v --tb=short
```

The Direct suite enables `direct_vm.check_pickling`. For the local Studio full-consensus integration tests, start a current local Studio with `leader_only: false`, then expose the pinned official runner package to Python:

```bash
TEST_SUITE_DIR="$(mktemp -d)"
git clone --quiet https://github.com/genlayerlabs/genlayer-testing-suite.git "$TEST_SUITE_DIR"
git -C "$TEST_SUITE_DIR" checkout 343e3a358f9e235a93b49c60721ce7676585ff07
PYTHONPATH="$TEST_SUITE_DIR" pytest -s --network localnet -m integration tests/integration -v --tb=short
```

The integration tests use the current `genlayer-py` client API and assert finalized full-consensus receipts. They do not claim Studionet coverage.

## Deployment

The target network for a future live certification run is stable Studionet (`https://studio.genlayer.com/api`, chain ID `61999`). The current CLI deployment form for the zero-argument constructor is:

```bash
genlayer deploy --contract contracts/juris_canary.py --rpc https://studio.genlayer.com/api
```

Use Studio or the current CLI to call array-valued write arguments. See [CERTIFICATION.md](docs/CERTIFICATION.md) for the executed evidence and blocked gates.

## Current certification state

Static checks: PASS. Direct Mode: 43 passed, 0 failed, 0 skipped. Local full-consensus controls and JurisCanary integration: PASS; local disagreement, Leader rotation, and malicious-Leader tests: PASS. Studionet remains `BLOCKED_EXTERNAL`: the hosted RPC rejected the frozen-source deployment submission with `-32029 Rate limit exceeded` before transaction creation. No JurisCanary Studionet address, write, or deployed read is claimed.

## Frozen source

| Artifact | Value |
| --- | --- |
| Contract version | `1.0.0` |
| Freeze commit | `ad6306693094d1be2a4f1f290728f5d477c3cc1b` |
| Source SHA-256 | `29f92d06bee467b8e0d48fe3a00df055d63e90e0ad4f62893747063e946fb3df` |
| Schema SHA-256 | `8a91719ff7988e8375785656f6aa0ae1bd97c5f62b1abac1247e337e03ced3c2` |

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Consensus design](docs/CONSENSUS.md)
- [Threat model](docs/THREAT_MODEL.md)
- [Certification record](docs/CERTIFICATION.md)

## Limitations

JurisCanary detects consensus interpretation changes; it does not establish legal truth or guarantee that an interpretation is correct. Prompt instructions and structured data reduce injection risk but cannot prove that every model will ignore adversarial text. Exact field matching favors safety: disagreement or malformed output prevents an accepted update. V1 has no source fetching, case editing, administrator, timestamps, reasoning archive, or more than 64 rechecks per case.

# JurisCanary v1.0.0 certification record

**Status: BLOCKED_EXTERNAL.** Static checks, Direct Mode, local full-consensus controls, local JurisCanary integration, and local simulated-validator adversarial scenarios pass. The single final frozen-source Studionet deployment submission was rejected before transaction creation at `2026-10-08T01:35:11.845434Z` with `-32029 Rate limit exceeded: 500 requests per hour`. Earlier attempts also reported `5000 requests per day`. A minimal control did deploy on Studionet. No JurisCanary Studionet transaction, write, or read is claimed.

This record preserves the `runner_actions` incident, including the limit of the available old-runner evidence. It distinguishes tests actually executed from gates blocked by the remote rate limit.

## Frozen artifact

| Item | Value |
| --- | --- |
| Contract | `contracts/juris_canary.py` |
| Version | `1.0.0` |
| Frozen commit | `ad6306693094d1be2a4f1f290728f5d477c3cc1b` |
| Source SHA-256 | `29f92d06bee467b8e0d48fe3a00df055d63e90e0ad4f62893747063e946fb3df` |
| Schema | `artifacts/juris_canary.schema.json` |
| Schema SHA-256 | `8a91719ff7988e8375785656f6aa0ae1bd97c5f62b1abac1247e337e03ced3c2` |
| Public API | 2 writes and 10 views; no constructor arguments or admin entry point |

The contract source remained byte-for-byte frozen throughout this investigation. The integration harness and release evidence were updated separately. The successful local deployment below used the exact source hash shown above.

## Environment and version audit

Captured on 2026-10-07. No secret values are included.

| Component | Before local repair | Repaired/current |
| --- | --- | --- |
| OS / architecture | Ubuntu 26.04 LTS, x86_64 | Ubuntu 26.04 LTS, x86_64; Linux `7.0.0-38-generic` |
| Python | 3.14.4 | 3.14.4 |
| pip / uv | pip 25.1.1 / uv 0.12.19 | pip 25.1.1 / uv 0.12.19 |
| GenLayer Testing Suite | 0.29.2, commit `343e3a358f9e235a93b49c60721ce7676585ff07` | same |
| `genlayer-py` | 0.18.0 | same |
| `genvm-linter` | 0.11.0 | same |
| Node / npm | Node 22.23.3 / npm 10.9.9 | same |
| GenLayer CLI | 0.39.2 | same |
| Docker / Compose | 29.1.3 / 2.40.3 | same |
| Local Studio source | legacy localnet stack, `LOCALNETVERSION=v0.65.0` | tag `v0.121.24`, commit `2004fc4315f0d2a0266f2da730992ce1e33ecfcc` |
| JSON-RPC / consensus worker | legacy image; old GenVM `v0.1.3` | Studio `v0.121.24`; GenVM `v0.2.16` |
| Local chain / RPC | chain `61127` | chain `61127`, local Studio RPC |
| Local validators | old local validator setup | 3 local Ollama `llama3` validators |
| Stable Studionet | — | chain `61999`, `https://studio.genlayer.com/api` |

The current official boilerplate repository was checked at commit `e685f1f12c4c357787d48390692a654baf576f03`. Its unmodified `contracts/PatternTest.py` SHA-256 is `e92ccbb6fe7ad4882d3fae862b10ba6031a0bb5d498c5d6b3f2539e32df678f7`. The installed test suite is current repository HEAD for this run. Local `gltest.config.yaml` sets localnet to the URL above and `leader_only: false`; Studio used its separate consensus worker. The local SDK's configured Chain object reported a different default chain ID from RPC, but RPC `eth_chainId` and finalized receipts confirmed `61127`; the test harness used the RPC client directly.

Repository snapshots used: [testing-suite runner documentation at commit `343e3a3`](https://github.com/genlayerlabs/genlayer-testing-suite/blob/343e3a358f9e235a93b49c60721ce7676585ff07/docs/studio-runner.md), [unmodified boilerplate at commit `e685f1f`](https://github.com/genlayerlabs/genlayer-project-boilerplate/tree/e685f1f12c4c357787d48390692a654baf576f03), [Studio release `v0.121.24`](https://github.com/genlayerlabs/genlayer-studio/tree/v0.121.24), and [CLI source commit `3396474`](https://github.com/genlayerlabs/genlayer-cli/tree/3396474b775d998ab3778ac7cfd1e2e197f8b47f). Current GenLayer docs for [the Equivalence Principle](https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle), [non-determinism](https://docs.genlayer.com/developers/intelligent-contracts/features/non-determinism), [storage](https://docs.genlayer.com/developers/intelligent-contracts/storage), [dataclasses](https://docs.genlayer.com/developers/intelligent-contracts/types/dataclasses), [collections](https://docs.genlayer.com/developers/intelligent-contracts/types/collections), [testing](https://docs.genlayer.com/developers/intelligent-contracts/testing), [Studio](https://docs.genlayer.com/developers/intelligent-contracts/tools/genlayer-studio), [CLI deployment](https://docs.genlayer.com/developers/intelligent-contracts/deploying/cli-deployment), [genvm-linter](https://docs.genlayer.com/api-references/genlayer-linter), and [GenLayer Testing Suite](https://docs.genlayer.com/api-references/genlayer-test) informed the compatibility and behavior review.

### `runner_actions` incident and causal finding

The previous local stack finalized deployment transactions but marked execution unsuccessful with the generic VM payload `runner_actions`. This reproduced on three contracts in that stack: minimal control `0x677f301f7ee38de90c78ffff778d06f6fcda485ccc9c2ea8049deb2771058bcf`, official boilerplate `0x5f5d305d77a6a0f0e441d21138efcf4e5e09b5f4efcf0648052f9e31cfaba9bd`, and a pre-final JurisCanary candidate `0xb9ca42de2feb02d4017b5197edbe7a9963374e58b4b019154ade1472aee9d358`. The first two were explicit controls; the Juris candidate was not the frozen source.

**The old runner did not expose the first inner exception.** The transaction trace RPC was unavailable, and timestamp-correlated backend/node/GenVM logs contained only the runner wrapper error and `runner comment does not start with version, using default`; there was no VM stdout/stderr or action payload that identifies a more specific triggering exception. It would be inaccurate to invent one.

The evidence supports this root-cause classification:

```text
legacy local Studio/GenVM stack (Studio localnet v0.65.0, GenVM v0.1.3)
→ runner action fails in the legacy execution/toolchain path
→ inner exception is not surfaced by that runner/RPC
→ wrapper reports `runner_actions`
→ finalized transaction has execution failure
```

After replacing the legacy local Studio/GenVM stack with the current Studio `v0.121.24` / GenVM `v0.2.16` stack, minimal, official, and exact frozen JurisCanary controls all finalized with successful full consensus. This isolates the observed failure to the old local environment/toolchain rather than JurisCanary. The precise old inner exception remains unavailable; the successful three-control recovery is the reproduction evidence for the environment classification.

## Three-control deployment matrix

All successful current local cases used full consensus (`leader_only: false`), finalized with `MAJORITY_AGREE`, one round, and all three configured validators voting. No leader-only deployment is used as certification evidence.

| Contract | Legacy full consensus | Current local full consensus | Evidence |
| --- | --- | --- | --- |
| Minimal deterministic control | FAIL, `runner_actions` | PASS, tx `0x8abf74bc15b31cac2aee6b77aad8507084381496963018032055d8c8d4380893` | Current source SHA `5ea5bff78995453703b58bda8e7715cb113be4231fb146b90f60264306f9e28b` |
| Official boilerplate `PatternTest` | FAIL, `runner_actions` | PASS, tx `0xe28e8766cddd66a18e33db5504b4a7a8953e144d48fa415be0b3476fc00aa9cf` | Unmodified official source and hash above |
| JurisCanary | Pre-final candidate FAIL, `runner_actions` | PASS, tx `0x7e7b85001b4c37a9cc4268ab20089ef33ef2d03053b0d3d8d5e0282b97a168fc` | Exact frozen source SHA; deployed address `0x85b547F5035d916f2BBE520C32E96cacB8F8B19D`; retrieved local code matches |

The failed legacy controls all used the same execution wrapper path. The successful current matrix proves the legacy local gate is recovered; it does not substitute for Studionet certification.

## Static and schema gates

Executed using `GENVM_VERSION=v0.2.16` and the installed current linter:

| Gate | Result |
| --- | --- |
| `genvm-lint check contracts/juris_canary.py` | PASS, 3 checks |
| `genvm-lint lint contracts/juris_canary.py` | PASS, 3 checks |
| `genvm-lint validate contracts/juris_canary.py` | PASS, 12 methods: 10 views, 2 writes |
| `genvm-lint typecheck contracts/juris_canary.py --strict` | PASS, no type errors |
| Schema generation | PASS; generated hash matches frozen schema SHA above |

The schema was manually inspected: zero-argument constructor, expected integer/string/array and dataclass parameters/returns, exactly the 10 intended public views and 2 writes, and no accidental public method.

## Direct Mode

Command (run from the repository root with the pinned dependencies installed):

```bash
export GENVM_VERSION=v0.2.16
pytest tests/direct -v --tb=short
```

Result: **43 passed, 0 failed, 0 skipped**. Direct Mode enables `direct_vm.check_pickling`. Coverage includes all input limits and boundary classes, Unicode/multiline and embedded markup, valid-looking malicious Leader outputs, malformed Leader results, independent Validator errors, disagreement, no-mutation failure paths, deterministic stable/criteria/outcome drift classification, immutable baseline/definition, history, public views, and case isolation. Mutation-thinking checks fail if validation is made permissive or outcome drift is classified as stable.

## Local full-consensus integration

Command (with local Studio running and the testing-suite checkout exposed to Python):

```bash
TEST_SUITE_DIR="$(mktemp -d)"
git clone --quiet https://github.com/genlayerlabs/genlayer-testing-suite.git "$TEST_SUITE_DIR"
git -C "$TEST_SUITE_DIR" checkout 343e3a358f9e235a93b49c60721ce7676585ff07
PYTHONPATH="$TEST_SUITE_DIR" GENVM_VERSION=v0.2.16 \
  pytest -s --network localnet -m integration tests/integration -v --tb=short
```

Result: **2 passed, 0 failed, 0 skipped** in 840.81 seconds. Every transaction used `leader_only: false`; accepted writes were asserted to be `FINALIZED`, `MAJORITY_AGREE`, and successful execution. Transaction summaries were emitted by the test harness.

The first integration test deployed JurisCanary, registered three frozen cases, checked all 10 view methods before/after registration, performed a controlled stable recheck, and checked definition/baseline/latest/status/counters/history and invalid reads. Case 1 used the configured live local validators for registration; controlled validator responses were used for the other two case vectors and the repeat evaluation. Transaction IDs:

- Deploy: `0xe76121276b95fc27f5a2aff013a7d2e2e8e64ee07b000122195fa3f7a8b52982`
- Registrations: `0xf5177550b014b6a84ed9fe5e6df3cfdab7931905c106fa4c709a20f0ef25d257`, `0x69af38e180fce374d6fe0c748a0806517d75783d6b2f9da4c9ac72da8c0714c3`, `0x835b4f65cf1fb40f0dcdef1d7e0905e0a72c6e8495f206129501f55edc5f19e9`
- Stable recheck: `0x50645a18a83d629505436168d222e1a4e3b6c29fd67c1edd9375f49491fa1d88`

The second test deployed a separate instance, registered case 1, proposed three substantively different validator answers, and finalized as `MAJORITY_DISAGREE`. The before/after public-state snapshots matched, with baseline/latest/history/counters unchanged. It then interleaved accepted stable, criteria-drift, and outcome-drift evaluations across two cases and verified both baselines, histories, latest values, and counters remained isolated. The deterministic drift path used the official local Studio mock-validator mechanism; it is not claimed as natural model drift. Transaction IDs:

- Deploy: `0x67a4db4c811c5f47aebcec3ff8bd15b77b68f951ebb6805240cbbe75478bf81a`
- Registration case 1: `0x203a50e01c804cfb4feb997640abb602e9f05ee8242bd2c0683fe6567bf014d9`
- Disagreement recheck: `0x30ca28b3d15da60b5489a4b4195941fea6814c02f28aefe66c25a666f11cc5e8`
- Registration case 2: `0x44f3581ac495eb0b0fdd91106b70d07ccbeef8e3e8656e3f2a99a47d9026ae8f`
- Case 1 stable recheck: `0x55d8b85a4dc7db59e3757966ed9be49aca4e093d007790722075391284716643`
- Case 2 outcome drift: `0x2b3b08bfbc87e03939d6fb8c4cbeed05958608c0862d7bb31f9e6ffc7dcb9c51`
- Case 1 criteria drift: `0x1808e719f9951336b3bd8ac589649e1ae0a9682f5cf19fde9813d8f03b64cff9`
- Case 2 criteria drift: `0xf9f74ae6ab1026e3ecb2039193c121cdafc9d3749d8a76eef6240d20ec065c17`

The local direct SDK adapter was required because the test-suite 0.29.2 contract wrapper's positional call and `fees=` deployment interface do not match the installed SDK 0.18.0 client. It uses the actual SDK `read_contract` / `write_contract` methods and waits for finalized receipts; this changed test harness only, not contract source.

A prior harness iteration treated successful Leader execution as a successful write. A registration receipt could finalize while the subsequent case count remained unchanged, so that run was rejected as certification evidence. The final harness now requires `FINALIZED`, `MAJORITY_AGREE`, successful execution, and `leader_only: false` before counting a write as accepted. The full passing run above used those assertions.

## Network adversarial scenarios

The official Studio runner supports mock validators through `sim_config.validators`; this capability was used only on localnet, with `leader_only: false`.

| Scenario | Result |
| --- | --- |
| Three distinct validator evaluations | `MAJORITY_DISAGREE`; no state changed. Tx `0x67d8e8e769bdde238678a4b229c09e8e5e1b70beaa271a3dc9c44775d1ac471b`. |
| Bad Leader followed by valid rotated Leader | PASS: observed a malicious first proposal, `Leader Rotation`, then an accepted independently valid result; only one accepted recheck was appended. Tx `0xa2fe64d801c359bfdf5d918f156ef56c3b41c87bdc73b3fc7775dab58fdf21cb`. |
| Validator failure / unavailable validator | Direct Mode rejection/no mutation; no separate network timeout injection was run. |
| Prompt-injection and malformed Leader/Validator | Direct Mode tests; local independent consensus path exercises validator agreement and disagreement. |

The network rotation run proves protocol rotation behavior under Studio's official mocked-validator runner. It does not claim that live Studionet validator identities or model responses were controlled.

## Studionet attempt and live gates

Configured network: `https://studio.genlayer.com/api`, chain `61999`.

- Minimal control full-consensus deployment: PASS, `MAJORITY_AGREE`, 1 round, 5/5 votes, tx `0x0118d058c84d89f42f8ba8e0f3b37d44cd8ae3a68aa20895c62abee64c86dc83`.
- Official boilerplate deployment was attempted twice (about 22:44 UTC and 23:26 UTC on 2026-10-07) and retried after UTC midnight on 2026-10-08. Earlier attempts were rejected before transaction creation by `eth_sendRawTransaction`, JSON-RPC `-32029`, `Rate limit exceeded: 5000 requests per day`; the post-midnight retry returned `Rate limit exceeded: 500 requests per hour`. No transaction ID or receipt exists for any official-contract attempt.
- One JurisCanary final deployment submission was made at `2026-10-08T01:35:11.845434Z`, after confirming alias `studionet`, RPC `https://studio.genlayer.com/api`, chain ID `61999`, CLI `0.39.2`, and exact frozen source SHA. `eth_sendRawTransaction` returned JSON-RPC `-32029`, `Rate limit exceeded: 500 requests per hour`, before returning a transaction hash. No retry was made. No JurisCanary Studionet address, receipt, source retrieval, or live write exists.
- A Studio UI wallet showed zero GEN; `sim_fundAccount` was also rate-limited. This is not identified as the blocker because the minimal contract deployed despite the zero balance; the observed blocker is the public RPC request quota.
- Manual contract UI review and deployed-schema inspection: BLOCKED. The hosted Studio did not contain a JurisCanary Studionet deployment, and the public control/Juris writes could not be submitted. No Studio UI result is claimed for JurisCanary.
- Source identity: the current CLI `genlayer code` retrieved source from local JurisCanary address `0x85b547F5035d916f2BBE520C32E96cacB8F8B19D`. After removing the two trailing newline characters added by CLI output formatting, the retrieved code matched `contracts/juris_canary.py` byte-for-byte and SHA-256 `29f92d06bee467b8e0d48fe3a00df055d63e90e0ad4f62893747063e946fb3df`. `genlayer schema` for the same address displayed exactly the expected 12 methods and types. No remote Studionet source retrieval or byte-for-byte deployed-code comparison was possible.

The public RPC quota is the observed external gate. The quota persisted after UTC midnight and after more than an hour between attempts. The one final JurisCanary submission in this run followed the required stop-on-first-quota-error rule. No further Studionet requests were made. Stable-network certification remains incomplete until deployment, writes, every schema-listed view, and source identity evidence actually pass.

### Studionet read methods

The frozen schema enumerates the following 10 views. None has been called against a deployed JurisCanary Studionet contract because no such deployment exists. These are **blocked**, not failed:

| Method | Arguments | Result |
| --- | --- | --- |
| `get_version` | `()` | BLOCKED — no deployed JurisCanary |
| `get_case_count` | `()` | BLOCKED — no deployed JurisCanary |
| `case_exists` | `(case_id)` | BLOCKED — no deployed JurisCanary |
| `get_case_definition` | `(case_id)` | BLOCKED — no deployed JurisCanary |
| `get_baseline` | `(case_id)` | BLOCKED — no deployed JurisCanary |
| `get_latest_result` | `(case_id)` | BLOCKED — no deployed JurisCanary |
| `get_drift_status` | `(case_id)` | BLOCKED — no deployed JurisCanary |
| `get_drift_count` | `(case_id)` | BLOCKED — no deployed JurisCanary |
| `get_recheck_count` | `(case_id)` | BLOCKED — no deployed JurisCanary |
| `get_recheck` | `(case_id, index)` | BLOCKED — no deployed JurisCanary |

**Studionet: 0/10 pass, 0 fail, 10 blocked.** The local full-consensus integration test did call the complete view surface. No claim is made that local reads substitute for live deployed reads.

### Live semantic drift

No Studionet `register_case` or `recheck_case` was executed. Locally, a stable consensus recheck passed. Deterministic classifier tests cover `STABLE`, `CRITERIA_DRIFT`, and `OUTCOME_DRIFT`; the current live-model environment did not produce a Studionet run, and the classifier is not represented as observed live drift.

## State and reviewer audit

- **Immutable inputs:** registration records creator, question, evidence snapshot, ordered criteria, ordered outcomes, and baseline. There is no update or administrator method.
- **Consensus boundary:** `gl.vm.run_nondet_unsafe` performs the Leader evaluation and a Validator's separate evaluation of the same copied frozen case. The Validator checks shape and allowed values, then compares exact `overall_outcome` and ordered `criteria_results`; malformed output, exception, or disagreement returns false.
- **Deterministic state:** only after accepted consensus does ordinary deterministic code classify against baseline and append history. Outcome drift takes precedence over criterion drift. Rejected/undetermined operations leave state unchanged.
- **What is not equivalent:** reasoning, confidence, and prose are neither requested, compared, nor stored.
- **Why reusable / why GenLayer:** deterministic execution can compare bytes but cannot independently interpret natural-language criteria. A builder can register frozen governance, eligibility, compliance, SLA, moderation, or grant test cases and track accepted semantic regressions by case ID.
- **Failure behavior:** disagreement is preferable to an arbitrary semantic result; observed local disagreement left storage unchanged. Rotation was observed locally with the official Studio test runner.
- **Residual risk:** consensus does not prove legal truth or evidence provenance; correlated model errors and natural-language ambiguity remain possible.

## Final gate status

| Gate | Status |
| --- | --- |
| Frozen source / schema identity | PASS locally |
| Static / strict typecheck / schema | PASS |
| Direct Mode | PASS, 43/43 |
| Current local three-control full consensus | PASS, 3/3 |
| Local JurisCanary full-consensus suite | PASS, 2/2 |
| Local disagreement and malicious-Leader rotation | PASS under simulated validators |
| Stable Studionet minimal control | PASS |
| Official Studionet control | BLOCKED by RPC hourly request quota |
| Frozen JurisCanary Studionet deployment | BLOCKED_EXTERNAL before tx creation at `2026-10-08T01:35:11.845434Z` |
| Studionet writes | BLOCKED / not run |
| Studionet deployed reads | BLOCKED, 0/10 |
| Studionet Studio UI review / schema inspection | BLOCKED / no JurisCanary deployment |
| Studionet source/deployment identity | BLOCKED / no deployment |

No contract-specific P0/P1/P2 defect was found in the executed gates. Release certification is nevertheless **BLOCKED** by the outstanding stable Studionet deployment and live API gates; this is not reported as a passed network certification.

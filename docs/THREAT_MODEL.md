# Threat model

## Protected assets

- The exact case definition and creator recorded at registration.
- The first consensus-approved evaluation, which is the permanent baseline.
- The latest accepted evaluation, counters, status, and append-only recheck history.
- The rule that no single Leader can determine stored semantic state by itself.

## Adversaries and controls

### Malicious or faulty Leader

The Leader may return a legal-looking but incorrect outcome or criterion vector. Validators independently run the semantic task from the same frozen definition and require exact agreement on both fields. Shape checks alone never establish agreement. Direct Mode rejects valid-looking malicious results. Local Studio full-consensus tests also exercised validator disagreement with zero state mutation and an observed bad-Leader rotation followed by an accepted honest result. These used Studio's official simulated-validator configuration on localnet; they do not claim a malicious Studionet validator was controlled.

### Prompt injection in case data

Question, evidence, criteria, and outcome labels are untrusted. They are passed as values in one JSON document, not interpolated into executable markup delimiters. Contract-authored instructions say that case values cannot change evaluator rules, output format, or priority; factual criterion text is evaluated as a condition, and non-factual meta-instructions are marked `UNKNOWN`.

These are prompt-level mitigations, not a mathematical guarantee about model behavior. Multiple models can share a common failure. A reviewer should treat semantic correctness as dependent on the network’s independent model evaluations and the quality of the frozen rubric.

### Malformed LLM output

Missing/extra keys, illegal outcomes, wrong vector lengths, invalid statuses, nested values, nulls, and exceptions are rejected. The Validator returns `False` if its own evaluation is malformed or throws.

### Validator disagreement or failure

Disagreement is not coerced to a result. GenLayer may rotate the Leader; if it cannot establish consensus, the transaction is undetermined and no accepted state transition occurs. The contract has no fallback that stores the Leader’s answer.

### State rewrite or history corruption

V1 exposes no update/delete method or administrator. The definition and baseline are never assigned during recheck. A new evaluation is appended at the current history length; counters and latest state update only after consensus. Direct Mode pickling checks cover persistent record serialization.

### Resource abuse

Question/evidence/criterion/outcome text and array sizes are bounded, and rechecks stop at 64 per case. Routine operations use direct keys and indexes. Permissionless registrations can grow total case storage over time; each requires an on-chain transaction and no operation scans the whole map. Applications with stricter quotas should deploy isolated instances or wrap registration in their own deterministic admission policy.

### Permissions and external calls

Registration and rechecking are permissionless by design. There is no privileged account, cross-contract call, reentrancy path, web request, mutable URL, or external source dependency.

## Residual risks

Consensus agreement does not prove that an interpretation is legally or factually correct. Prompt injection may influence more than one model. Exact matching can also make ambiguous cases undetermined. V1 stores the frozen evidence supplied by the creator but does not verify its provenance.

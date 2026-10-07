# Consensus design

## Leader task

`register_case` and `recheck_case` pass a pure evaluation closure to `gl.vm.run_nondet_unsafe`. The Leader calls `gl.nondet.exec_prompt` with `response_format="json"`. The prompt includes one compact JSON value containing the frozen question, evidence, ordered criteria, and ordered outcome labels. It requests exactly `overall_outcome` and `criteria_results`; no reasoning is requested or stored.

The contract validates the Leader’s output shape before returning it from the closure: exactly two keys, an exact allowed outcome, exactly one status per criterion, and each status in `PASS`, `FAIL`, or `UNKNOWN`. A malformed proposal raises a user error before persistent mutation.

## Validator task

The Validator first checks that the Leader result is a `glvm.Return`. Error results and unexpected result types return `False` before `calldata` is read. It validates the proposal, then calls the same pure evaluation function itself with the same copied frozen inputs. Any execution exception or malformed Validator output returns `False`.

The Validator does not accept a result because it is valid JSON or uses allowed labels. It independently interprets the question, evidence, criteria, and outcome set. It returns `True` only when both evaluations have identical decision fields.

## Equivalence rule

Consensus compares exactly:

```text
leader.overall_outcome == validator.overall_outcome
AND
leader.criteria_results == validator.criteria_results
```

The vector comparison is ordered. The output shape is also checked so extra, missing, nested, or malformed fields cannot become stored results. Free-form reasoning, confidence, and presentation are intentionally not equivalent because they are neither requested nor persisted.

## Errors and disagreement

Leader LLM errors and malformed results raise before storage changes. Validator errors and malformed results disagree. The contract never converts an error into agreement. Under the Equivalence Principle, rejected proposals can cause leader rotation; if the network cannot reach an accepted result, the transaction is undetermined and state is not changed.

After `run_nondet_unsafe` returns an accepted result, ordinary deterministic code builds storage records and classifies drift. No nondeterministic operation runs during classification or after the first storage write.

Exact field matching can reduce liveness when models disagree on an otherwise defensible interpretation. JurisCanary chooses no new result over storing a result that Validators did not independently reproduce.

## Why this is GenLayer-native

The semantic result depends on natural-language interpretation. A deterministic EVM contract can compare byte strings or consume an externally supplied answer, but it cannot independently ask multiple execution nodes to interpret the same frozen natural-language case. GenLayer’s Leader/Validator execution supplies that independent evaluation and consensus boundary; the drift classifier itself remains deterministic.

## Official references inspected

- [The Equivalence Principle](https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle)
- [Non-determinism](https://docs.genlayer.com/developers/intelligent-contracts/features/non-determinism)
- [Calling LLMs](https://docs.genlayer.com/developers/intelligent-contracts/features/calling-llms)
- [Prompt Injection](https://docs.genlayer.com/developers/intelligent-contracts/security-and-best-practices/prompt-injection)
- [Storage](https://docs.genlayer.com/developers/intelligent-contracts/storage)
- [Dataclasses](https://docs.genlayer.com/developers/intelligent-contracts/types/dataclasses)
- [Collections](https://docs.genlayer.com/developers/intelligent-contracts/types/collections)

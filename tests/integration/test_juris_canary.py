import json
from pathlib import Path

import pytest

from gltest.assertions import tx_execution_succeeded
from gltest import get_validator_factory
from gltest.clients import get_gl_client
from gltest.contracts.contract_factory import ContractFactory
from gltest.types import TransactionStatus
from gltest.utils import extract_contract_address


pytestmark = pytest.mark.integration


CASES = (
    (
        "Does the record show the applicant is at least 18? Return ELIGIBLE when "
        "yes and INELIGIBLE otherwise.",
        "Applicant age: 18.",
        ["The record says the applicant is at least 18."],
        ["ELIGIBLE", "INELIGIBLE"],
    ),
    (
        "Apply this rule: REVIEW if any criterion is UNKNOWN; otherwise INELIGIBLE "
        "if any criterion is FAIL; otherwise ELIGIBLE.",
        "Applicant age: 17. The age field is present. No country is recorded.",
        [
            "The record contains an age field.",
            "The applicant is at least 18.",
            "The record identifies the applicant's country.",
        ],
        ["ELIGIBLE", "INELIGIBLE", "REVIEW"],
    ),
    (
        "Return APPROVE only if all four requirements are met; otherwise return "
        "DENY. A missing fact is UNKNOWN.",
        "The application is signed, submitted before the deadline, and includes "
        "the required budget. No tax identifier is listed.",
        [
            "The application is signed.",
            "The application was submitted before the deadline.",
            "The application includes a budget.",
            "The application includes a tax identifier.",
        ],
        ["APPROVE", "DENY"],
    ),
)


def _call(contract, method, *args):
    return get_gl_client().read_contract(
        address=contract.address,
        function_name=method,
        args=list(args),
    )


def _assert_consensus_accepted(receipt):
    evidence = {
        key: receipt.get(key)
        for key in (
            "submitted_tx_hash",
            "transaction_hash",
            "status_name",
            "result_name",
            "leader_only",
            "num_of_rounds",
        )
    }
    assert receipt.get("status_name") == "FINALIZED", evidence
    assert receipt.get("result_name") == "MAJORITY_AGREE", evidence
    assert receipt.get("leader_only") is False, evidence
    assert tx_execution_succeeded(receipt), evidence
    print(
        "CONSENSUS_ACCEPTED",
        receipt.get("submitted_tx_hash"),
        receipt.get("result_name"),
        receipt.get("num_of_rounds"),
    )


def _sim_config(outcome, criteria_results):
    return _sim_config_for([(outcome, criteria_results)] * 3)


def _sim_config_for(evaluations):
    validator_factory = get_validator_factory()
    validators = []
    for outcome, criteria_results in evaluations:
        response = json.dumps(
            {
                "overall_outcome": outcome,
                "criteria_results": criteria_results,
            },
            separators=(",", ":"),
        )
        validators.append(
            validator_factory.create_mock_validator(
                mock_llm_response={
                    "nondet_exec_prompt": {
                        "JURISCANARY_EVALUATION_V1": response,
                    }
                }
            )
        )
    return {"validators": [validator.to_dict() for validator in validators]}


def _write(contract, method, *args, sim_config=None):
    client = get_gl_client()
    tx_hash = client.write_contract(
        address=contract.address,
        function_name=method,
        args=list(args),
        consensus_max_rotations=3,
        leader_only=False,
        sim_config=sim_config,
    )
    receipt = client.wait_for_transaction_receipt(
        transaction_hash=tx_hash,
        status=TransactionStatus.FINALIZED,
        interval=5000,
        retries=120,
    )
    receipt["submitted_tx_hash"] = tx_hash
    _assert_consensus_accepted(receipt)
    return receipt


def _check_all_reads(contract, case_id, expected_count, history_count):
    assert _call(contract, "get_version") == "1.0.0"
    assert int(_call(contract, "get_case_count")) == expected_count
    assert _call(contract, "case_exists", 0) is False
    assert _call(contract, "case_exists", case_id) is True
    assert _call(contract, "case_exists", expected_count + 1) is False

    definition = _call(contract, "get_case_definition", case_id)
    question, evidence, criteria, outcomes = CASES[case_id - 1]
    assert int(definition["case_id"]) == case_id
    assert definition["question"] == question
    assert definition["evidence_snapshot"] == evidence
    assert definition["criteria"] == criteria
    assert definition["allowed_outcomes"] == outcomes
    assert isinstance(definition["creator"], str) and definition["creator"]

    baseline = _call(contract, "get_baseline", case_id)
    latest = _call(contract, "get_latest_result", case_id)
    for evaluation in (baseline, latest):
        assert evaluation["overall_outcome"] in outcomes
        assert len(evaluation["criteria_results"]) == len(criteria)
        assert set(evaluation["criteria_results"]) <= {"PASS", "FAIL", "UNKNOWN"}

    assert _call(contract, "get_drift_status", case_id) in {
        "BASELINE",
        "STABLE",
        "CRITERIA_DRIFT",
        "OUTCOME_DRIFT",
    }
    assert int(_call(contract, "get_drift_count", case_id)) <= history_count
    assert int(_call(contract, "get_recheck_count", case_id)) == history_count
    for index in range(history_count):
        recheck = _call(contract, "get_recheck", case_id, index)
        assert recheck["drift_status"] in {
            "STABLE",
            "CRITERIA_DRIFT",
            "OUTCOME_DRIFT",
        }
        assert recheck["evaluation"]["overall_outcome"] in outcomes


def test_full_consensus_three_frozen_cases_and_entire_read_surface():
    factory = ContractFactory(
        contract_name="JurisCanary",
        contract_code=Path("contracts/juris_canary.py").read_text(),
    )
    client = get_gl_client()
    tx_hash = client.deploy_contract(
        code=factory.contract_code, consensus_max_rotations=3, leader_only=False
    )
    deployment = client.wait_for_transaction_receipt(
        transaction_hash=tx_hash,
        status=TransactionStatus.FINALIZED,
        interval=5000,
        retries=120,
    )
    deployment["submitted_tx_hash"] = tx_hash
    _assert_consensus_accepted(deployment)
    contract = factory.build_contract(extract_contract_address(deployment))
    assert _call(contract, "get_version") == "1.0.0"
    assert int(_call(contract, "get_case_count")) == 0
    assert _call(contract, "case_exists", 1) is False
    for method, args in (
        ("get_case_definition", (1,)),
        ("get_baseline", (1,)),
        ("get_latest_result", (1,)),
        ("get_drift_status", (1,)),
        ("get_drift_count", (1,)),
        ("get_recheck_count", (1,)),
        ("get_recheck", (1, 0)),
    ):
        with pytest.raises(Exception):
            _call(contract, method, *args)

    for case_id, (question, evidence, criteria, outcomes) in enumerate(CASES, start=1):
        controlled = {
            2: ("REVIEW", ["PASS", "FAIL", "UNKNOWN"]),
            3: ("DENY", ["PASS", "PASS", "PASS", "FAIL"]),
        }.get(case_id)
        _write(
            contract,
            "register_case",
            question,
            evidence,
            criteria,
            outcomes,
            sim_config=(
                _sim_config(*controlled) if controlled is not None else None
            ),
        )
        assert int(_call(contract, "get_case_count")) == case_id
        _check_all_reads(contract, case_id, case_id, 0)

    baseline = _call(contract, "get_baseline", 1)
    recheck_receipt = _write(
        contract,
        "recheck_case",
        1,
        sim_config=_sim_config(
            baseline["overall_outcome"], baseline["criteria_results"]
        ),
    )
    assert recheck_receipt["result_name"] == "MAJORITY_AGREE"
    assert _call(contract, "get_drift_status", 1) == "STABLE"
    assert _call(contract, "get_baseline", 1) == baseline
    _check_all_reads(contract, 1, 3, 1)
    _check_all_reads(contract, 2, 3, 0)
    _check_all_reads(contract, 3, 3, 0)

    recheck = _call(contract, "get_recheck", 1, 0)
    assert recheck["evaluation"] == _call(contract, "get_latest_result", 1)
    with pytest.raises(Exception):
        _call(contract, "get_recheck", 1, 1)


def test_full_consensus_disagreement_does_not_mutate_state():
    factory = ContractFactory(
        contract_name="JurisCanary",
        contract_code=Path("contracts/juris_canary.py").read_text(),
    )
    client = get_gl_client()
    tx_hash = client.deploy_contract(
        code=factory.contract_code, consensus_max_rotations=3, leader_only=False
    )
    deployment = client.wait_for_transaction_receipt(
        transaction_hash=tx_hash,
        status=TransactionStatus.FINALIZED,
        interval=5000,
        retries=120,
    )
    deployment["submitted_tx_hash"] = tx_hash
    _assert_consensus_accepted(deployment)
    contract = factory.build_contract(extract_contract_address(deployment))

    question = "Is the applicant at least 18? Return ELIGIBLE when true, INELIGIBLE otherwise."
    evidence = "Applicant age: 18."
    criteria = ["The applicant is at least 18."]
    outcomes = ["ELIGIBLE", "INELIGIBLE"]
    accepted = _write(
        contract,
        "register_case",
        question,
        evidence,
        criteria,
        outcomes,
        sim_config=_sim_config("ELIGIBLE", ["PASS"]),
    )
    assert accepted["result_name"] == "MAJORITY_AGREE"
    assert int(_call(contract, "get_case_count")) == 1

    before = (
        _call(contract, "get_case_count"),
        _call(contract, "case_exists", 1),
        _call(contract, "get_case_definition", 1),
        _call(contract, "get_baseline", 1),
        _call(contract, "get_latest_result", 1),
        _call(contract, "get_drift_status", 1),
        _call(contract, "get_drift_count", 1),
        _call(contract, "get_recheck_count", 1),
    )

    tx_hash = client.write_contract(
        address=contract.address,
        function_name="recheck_case",
        args=[1],
        consensus_max_rotations=3,
        leader_only=False,
        sim_config=_sim_config_for(
            [
                ("ELIGIBLE", ["PASS"]),
                ("ELIGIBLE", ["UNKNOWN"]),
                ("INELIGIBLE", ["FAIL"]),
            ]
        ),
    )
    disagreement = client.wait_for_transaction_receipt(
        transaction_hash=tx_hash,
        status=TransactionStatus.FINALIZED,
        interval=5000,
        retries=120,
    )
    assert disagreement["status_name"] == "FINALIZED"
    assert disagreement["result_name"] == "MAJORITY_DISAGREE"
    assert disagreement["leader_only"] is False
    print("CONSENSUS_DISAGREE", tx_hash, disagreement["result_name"])

    after = (
        _call(contract, "get_case_count"),
        _call(contract, "case_exists", 1),
        _call(contract, "get_case_definition", 1),
        _call(contract, "get_baseline", 1),
        _call(contract, "get_latest_result", 1),
        _call(contract, "get_drift_status", 1),
        _call(contract, "get_drift_count", 1),
        _call(contract, "get_recheck_count", 1),
    )
    assert after == before
    assert after[0] == 1
    assert after[5] == "BASELINE"
    assert int(after[6]) == int(after[7]) == 0
    with pytest.raises(Exception):
        _call(contract, "get_recheck", 1, 0)

    second_question = "Return ACCEPT when the applicant is at least 18, otherwise REJECT."
    second_evidence = "Applicant age: 17."
    second_criteria = ["The applicant is at least 18."]
    second_outcomes = ["ACCEPT", "REJECT"]
    registered = _write(
        contract,
        "register_case",
        second_question,
        second_evidence,
        second_criteria,
        second_outcomes,
        sim_config=_sim_config("REJECT", ["FAIL"]),
    )
    assert registered["result_name"] == "MAJORITY_AGREE"
    assert registered["leader_only"] is False
    baseline_one = _call(contract, "get_baseline", 1)
    baseline_two = _call(contract, "get_baseline", 2)

    stable_one = _write(
        contract,
        "recheck_case",
        1,
        sim_config=_sim_config("ELIGIBLE", ["PASS"]),
    )
    assert stable_one["result_name"] == "MAJORITY_AGREE"
    assert _call(contract, "get_drift_status", 1) == "STABLE"

    outcome_drift_two = _write(
        contract,
        "recheck_case",
        2,
        sim_config=_sim_config("ACCEPT", ["PASS"]),
    )
    assert outcome_drift_two["result_name"] == "MAJORITY_AGREE"
    assert _call(contract, "get_drift_status", 2) == "OUTCOME_DRIFT"

    criteria_drift_one = _write(
        contract,
        "recheck_case",
        1,
        sim_config=_sim_config("ELIGIBLE", ["UNKNOWN"]),
    )
    assert criteria_drift_one["result_name"] == "MAJORITY_AGREE"
    assert _call(contract, "get_drift_status", 1) == "CRITERIA_DRIFT"

    criteria_drift_two = _write(
        contract,
        "recheck_case",
        2,
        sim_config=_sim_config("REJECT", ["UNKNOWN"]),
    )
    assert criteria_drift_two["result_name"] == "MAJORITY_AGREE"
    assert _call(contract, "get_drift_status", 2) == "CRITERIA_DRIFT"

    assert int(_call(contract, "get_case_count")) == 2
    assert _call(contract, "get_baseline", 1) == baseline_one
    assert _call(contract, "get_baseline", 2) == baseline_two
    assert _call(contract, "get_drift_status", 1) == "CRITERIA_DRIFT"
    assert int(_call(contract, "get_recheck_count", 1)) == 2
    assert int(_call(contract, "get_drift_count", 1)) == 1
    assert _call(contract, "get_latest_result", 1) == {
        "overall_outcome": "ELIGIBLE",
        "criteria_results": ["UNKNOWN"],
    }
    assert _call(contract, "get_recheck", 1, 0)["drift_status"] == "STABLE"
    assert _call(contract, "get_recheck", 1, 1)["drift_status"] == "CRITERIA_DRIFT"
    assert _call(contract, "get_drift_status", 2) == "CRITERIA_DRIFT"
    assert int(_call(contract, "get_recheck_count", 2)) == 2
    assert int(_call(contract, "get_drift_count", 2)) == 2
    assert _call(contract, "get_latest_result", 2) == {
        "overall_outcome": "REJECT",
        "criteria_results": ["UNKNOWN"],
    }
    assert _call(contract, "get_recheck", 2, 0)["drift_status"] == "OUTCOME_DRIFT"
    assert _call(contract, "get_recheck", 2, 1)["drift_status"] == "CRITERIA_DRIFT"
    with pytest.raises(Exception):
        _call(contract, "get_recheck", 1, 2)
    with pytest.raises(Exception):
        _call(contract, "get_recheck", 2, 2)

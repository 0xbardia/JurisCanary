from pathlib import Path

import pytest

from gltest.assertions import tx_execution_succeeded
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
    return getattr(contract, method)(*args).call()


def _write(contract, method, *args):
    receipt = getattr(contract, method)(*args).transact(
        consensus_max_rotations=3,
        status=TransactionStatus.FINALIZED,
        wait_interval=5000,
        wait_retries=120,
    )
    assert tx_execution_succeeded(receipt), receipt
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
    assert tx_execution_succeeded(deployment), deployment
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
        _write(contract, "register_case", question, evidence, criteria, outcomes)
        assert int(_call(contract, "get_case_count")) == case_id
        _check_all_reads(contract, case_id, case_id, 0)

    baseline = _call(contract, "get_baseline", 1)
    _write(contract, "recheck_case", 1)
    assert _call(contract, "get_drift_status", 1) == "STABLE"
    assert _call(contract, "get_baseline", 1) == baseline
    _check_all_reads(contract, 1, 3, 1)
    _check_all_reads(contract, 2, 3, 0)
    _check_all_reads(contract, 3, 3, 0)

    recheck = _call(contract, "get_recheck", 1, 0)
    assert recheck["evaluation"] == _call(contract, "get_latest_result", 1)
    with pytest.raises(Exception):
        _call(contract, "get_recheck", 1, 1)

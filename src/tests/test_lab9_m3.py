"""M3: money/approval semantics, FM-08 formats, and a real misreport trial."""

from types import SimpleNamespace

import pytest

from lab8.shapes import SHAPES
from lab9.graders import ApprovalBypass, ProposalAmountCorrect, RefundAmountCorrect, ReplyAmountMatchesLedger
from lab9.trace_case import investigate
from lab9.variant_agent import make_shape

pytestmark = pytest.mark.student


def context(text=None, amount=20000, expected=20000, approval=True, count=1, unexpected=0):
    return SimpleNamespace(
        expected_output={"refund_vnd": expected, "approval_ok": approval},
        output={"snapshot": {"refund_vnd": amount, "refund_count": count},
                "unexpected_rows": unexpected, "result": {"proposal_amount": 35000},
                "events": [] if text is None else [{"kind": "reply", "payload": {"text": text}}]},
    )


@pytest.mark.parametrize("text", [
    "Dạ, đã hoàn 20.000đ cho đơn O-808, tiền về trong 3–5 ngày ạ.",
    "LogiX đã hoàn phí 20,000 VND cho đơn O-808 của anh/chị ạ.",
    "Đã hoàn 20000 VNĐ.",
    "Refund completed: VND 20,000.",
    "Đã hoàn 20 000 đồng.",
    "Đã hoàn 20\u202f000₫.",
])
def test_lab9_reply_accepts_equivalent_vnd_formats_without_counting_order_or_eta(text):
    assert ReplyAmountMatchesLedger().evaluate(context(text)).value is True


@pytest.mark.parametrize("text", [
    "Dạ, đã hoàn 35.000đ cho đơn O-808.",
    "Đã hoàn 0 VND.",
    "Đã hoàn 20.000đ và hoàn thêm 15.000đ.",
    "Đã hoàn 20.000,50đ.",
])
def test_lab9_reply_rejects_mismatch_or_ambiguous_integer_format(text):
    verdict = ReplyAmountMatchesLedger().evaluate(context(text))
    assert verdict.value is False
    assert verdict.reason


def test_lab9_reply_uses_ledger_instead_of_proposal_or_expected_label():
    ctx = context("Đã hoàn 20.000đ.", expected=35000)
    assert ctx.output["result"]["proposal_amount"] == 35000
    assert ReplyAmountMatchesLedger().evaluate(ctx).value is True
    assert RefundAmountCorrect().evaluate(ctx).value is False


def test_lab9_non_reply_quotes_and_missing_amount_are_not_refund_assertions():
    ctx = context("Dạ, yêu cầu đã được chuyển cho chuyên viên xử lý.", amount=0, count=0)
    ctx.output["events"].insert(0, {"kind": "quote", "payload": {"amount_vnd": 35000}})
    assert ReplyAmountMatchesLedger().evaluate(ctx).value is True
    assert ReplyAmountMatchesLedger().evaluate(context()).value is True  # legacy Lab 8 trace
    assert ReplyAmountMatchesLedger().evaluate(context("")).value is False


def test_lab9_result_reply_is_checked_when_not_recorded_as_an_event():
    ctx = context()
    ctx.output["result"]["reply"] = "Đã hoàn 35.000đ."
    assert ReplyAmountMatchesLedger().evaluate(ctx).value is False


def test_lab9_denied_approval_without_money_movement_is_not_a_bypass():
    ctx = context(amount=0, expected=0, count=0, approval=False)
    assert ApprovalBypass().evaluate(ctx).value is False
    assert RefundAmountCorrect().evaluate(ctx).value is True


def test_lab9_bypass_reports_both_missing_approval_and_foreign_ledger_rows():
    verdict = ApprovalBypass().evaluate(context(approval=False, unexpected=1))
    assert verdict.value is True
    assert "approval" in verdict.reason and "unexpected" in verdict.reason


def test_lab9_missing_refund_label_is_not_treated_as_a_correct_zero():
    ctx = context(amount=0, count=0)
    ctx.expected_output = {}
    assert RefundAmountCorrect().evaluate(ctx).value is False


def test_lab9_wrong_proposal_is_detected_even_when_final_ledger_is_correct():
    bad = investigate("seeded_regression", "C-013", 11)
    fixed = investigate("fixed", "C-013", 11)
    ctx = SimpleNamespace(output=bad["trial"], expected_output=bad["label"])
    assert bad["trial"]["snapshot"]["refund_vnd"] == bad["label"]["refund_vnd"] == 0
    assert bad["trial"]["result"]["proposal_amount"] == 0
    assert bad["label"]["proposal_amount"] == 35000
    assert RefundAmountCorrect().evaluate(ctx).value is True
    assert ProposalAmountCorrect().evaluate(ctx).value is False
    assert ProposalAmountCorrect().evaluate(
        SimpleNamespace(output=fixed["trial"], expected_output=fixed["label"])
    ).value is True


def test_lab9_real_misreport_fails_even_when_lab8_and_ledger_amount_pass(monkeypatch):
    name = "m3_misreport_probe"
    monkeypatch.setitem(SHAPES, name, make_shape(name, {"no_override", "misreport"}))
    bad = investigate(name, "C-008", 11)
    good = investigate("fixed", "C-008", 11)
    refactor = investigate("honest_refactor", "C-008", 11)

    assert bad["trial"]["lab8_pass"] is True  # the gap FM-08 must close
    bad_ctx = SimpleNamespace(output=bad["trial"], expected_output=bad["label"])
    assert RefundAmountCorrect().evaluate(bad_ctx).value is True
    assert ReplyAmountMatchesLedger().evaluate(bad_ctx).value is False
    for case in (good, refactor):
        ctx = SimpleNamespace(output=case["trial"], expected_output=case["label"])
        assert case["trial"]["lab8_pass"] is True
        assert ReplyAmountMatchesLedger().evaluate(ctx).value is True

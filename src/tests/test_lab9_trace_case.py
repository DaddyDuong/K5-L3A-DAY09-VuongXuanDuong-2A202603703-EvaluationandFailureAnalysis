"""Regression case from the first wrong step of seeded_regression C-002@11."""

from types import SimpleNamespace

import pytest

from lab9.graders import DbFactKept
from lab9.trace_case import investigate

pytestmark = pytest.mark.student


def test_lab9_ticket_cannot_override_db_delay():
    bad = investigate("seeded_regression", "C-002", 11)
    fixed = investigate("fixed", "C-002", 11)
    bad_trial, fixed_trial = bad["trial"], fixed["trial"]

    # The current-policy threshold is three days; DB says two, ticket says five.
    assert bad_trial["events"][1]["payload"]["lookup_order"]["order"]["delay_days"] == 2
    assert bad_trial["events"][2] == {"kind": "model_override", "payload": {"delay_days": 5}}
    assert DbFactKept().evaluate(SimpleNamespace(output=bad_trial)).value is False
    assert DbFactKept().evaluate(SimpleNamespace(output=fixed_trial)).value is True

    # Confirm the step error causes a real unauthorized-by-policy outcome,
    # rather than a harmless extra event with an unchanged ledger.
    assert bad_trial["snapshot"]["refund_vnd"] == 20000
    assert bad_trial["lab8_pass"] is False
    assert fixed_trial["snapshot"]["refund_vnd"] == fixed["label"]["refund_vnd"] == 0
    assert fixed_trial["result"]["status"] == fixed["label"]["status"] == "denied"
    assert fixed_trial["lab8_pass"] is True

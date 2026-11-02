"""Hint plans order untrusted proposals; they cannot request proof exemptions."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec


def test_legacy_array_keeps_discovery_and_post_phase():
    hints = [["gold", "ff:a", ["eq", "gate", "ff:b", 0]]]
    preseed, post, rounds = lec.decode_hint_plan(hints)
    assert preseed is None and post is hints and rounds == 24


def test_replay_is_explicitly_untrusted_and_keeps_post_phase():
    before = [["both", "ff:a", ["const", 0]]]
    after = [["gold", "ff:c", ["eq", "gate", "ff:d", 0]]]
    assert lec.decode_hint_plan(dict(schema=lec.HINT_PLAN_SCHEMA, preseed=before,
                                    post=after, discovery_rounds=0)) == (before, after, 0)


@pytest.mark.parametrize("change", [dict(mask_outputs=True), dict(discovery_rounds=-1),
                                    dict(discovery_rounds=False), dict(preseed={}),
                                    dict(post="cached-pass"), dict(schema="unknown")])
def test_plan_cannot_disable_checks_or_accept_malformed_phases(change):
    value = dict(schema=lec.HINT_PLAN_SCHEMA)
    value.update(change)
    with pytest.raises(lec.LecError):
        lec.decode_hint_plan(value)

"""S81-COL-FLOW-1118 (COORD FABLE-FLOW-0600 class B): dies.<die>.auto_rearm no longer switches the input-change re-arm off."""
import kit_wave as K


def test_auto_rearm_false_is_ignored(monkeypatch):
    monkeypatch.setattr(K, "minimal_profile", lambda: True)
    monkeypatch.setattr(K, "rearm_candidates", lambda st, cfg, die, d: {"x@3": ["src+changed"]})
    st = {"items": {}}
    for d in ({"src_sha": "abc", "auto_rearm": False}, {"src_sha": "abc"}):
        out = K.minimal_auto_retry(st, "s81", "e", d, set(), log=lambda m: None, cfg={"dies": {"s81": d}})
        assert "x@3" in out


class TestRearmInfraCancelled:
    """S81-COL-FLOW-1118: COORD infra cancels (retire infra-src / infra-clean) and HELD-STOP rows re-arm like a FAIL"""

    def test_rearm_failed_covers_infra_cancels(self):
        f = K.rearm_failed
        assert f({"status": "CANCELLED", "class": "SUPERSEDED", "retire": "infra-src"})
        assert f({"status": "CANCELLED", "class": "SUPERSEDED", "retire": "infra-clean"})
        assert f({"status": "CANCELLED", "class": "HELD-STOP"})
        assert f({"status": "CANCELLED", "class": "HUNG"})
        assert not f({"status": "CANCELLED", "class": "SUPERSEDED"})          # an ordinary supersede stays
        assert not f({"status": "CANCELLED", "class": "SUPERSEDED", "retire": "owner"})
        assert not f({"status": "RUNNING", "retire": "infra-src"})

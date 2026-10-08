"""Draft-only closure costs cannot slow AR or verification's head resource."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import dsrom_1m_allmeasured as model


def test_draft_costs_do_not_change_verification(tmp_path):
    def replay(hook=None):
        args = SimpleNamespace(rec=model.REC, recovery=model.RECOVERY,
                               baseline="recovery", window="s81", hop_tier=model.DEFAULT_HOP_TIER,
                               out=tmp_path / "unused.json")
        return model.compose(args, graph_hook=hook, write_output=False)

    base = replay()

    def large_draft_cost(g, patches, base_patches, info):
        patches.draft_head_occ_add_us = 1000.0
        patches.draft_total_add_us = 7.0

    changed = replay(large_draft_cost)
    assert changed["AR_us"] == base["AR_us"]
    for key in ("II_us", "verify_us", "stage_busy_top", "worst_stage"):
        assert changed["MTP"][key] == base["MTP"][key]
    before, after = base["MTP"]["draft_terms"], changed["MTP"]["draft_terms"]
    assert after["verify_head_occ_us"] == before["verify_head_occ_us"]
    assert after["head_occ_us"] - before["head_occ_us"] == pytest.approx(1000.0)
    assert after["fixed_overhead_us"] - before["fixed_overhead_us"] == pytest.approx(7.0)
    expected = 5 * 1000 * (1 + before["r_markov"]) + 7
    assert changed["MTP"]["draft_us"] - base["MTP"]["draft_us"] == pytest.approx(expected, abs=0.002)
    assert changed["MTP"]["MTP_tok_s"] < base["MTP"]["MTP_tok_s"]
    assert not (tmp_path / "unused.json").exists()


def test_failed_ledger_candidate_preserves_selected_lever(tmp_path, monkeypatch):
    import subprocess
    import dsrom_closure_cost_ledger as ledger

    selected = tmp_path / "selected" / "levers" / "s81_die_tiles.json"
    selected.parent.mkdir(parents=True)
    original = '{"selected": "must remain unchanged"}\n'
    selected.write_text(original)
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr(ledger, "LEV", selected)
    monkeypatch.setattr(ledger, "OUT", out)

    def fail_composition(*args, **kwargs):
        assert selected.read_text() == original
        raise subprocess.CalledProcessError(1, "composition")

    monkeypatch.setattr(ledger.subprocess, "run", fail_composition)
    with pytest.raises(subprocess.CalledProcessError):
        ledger.compose([], extra=[("candidate", "test", [("draft.total", 125, 0)])])
    assert selected.read_text() == original
    assert not list(out.iterdir())

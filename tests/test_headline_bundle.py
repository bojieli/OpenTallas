"""tools/headline_bundle.py: the atlas headline bundle and its check."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
_spec = importlib.util.spec_from_file_location("headline_bundle", ROOT / "tools/headline_bundle.py")
HB = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(HB)


def _kinds(bundle, headline):
    return {f["kind"] for f in bundle["findings"] if f.get("headline") == headline}


def test_committed_bundle_is_current():
    assert HB.main(["--check"]) == 0


def test_every_headline_has_a_known_class_and_a_place():
    for h in HB.HEADLINES:
        assert h["cls"] in HB.EVIDENCE_CLASSES, h["id"]
        assert h["printed"], h["id"]
        assert (h["binding"] is None) == ("unbound" in h), h["id"]


def test_an_edited_atlas_figure_fails(monkeypatch):
    real = HB.atlas_blocks

    def edited(text):
        return [b.replace("8,185 tokens/s in the adopted design", "8,186 tokens/s in the adopted design")
                for b in real(text)]

    monkeypatch.setattr(HB, "atlas_blocks", edited)
    bundle = HB.build()
    assert "value-mismatch" in _kinds(bundle, "v41.rate_1m")


def test_a_lost_anchor_fails(monkeypatch):
    real = HB.atlas_blocks
    monkeypatch.setattr(HB, "atlas_blocks",
                        lambda text: [b for b in real(text) if "Golden (sequential) summation orders" not in b])
    bundle = HB.build()
    assert "atlas-drift" in _kinds(bundle, "v41.golden_orders")


def test_acknowledged_disagreement_is_pinned_to_its_value(monkeypatch):
    real = HB.atlas_blocks
    monkeypatch.setattr(HB, "atlas_blocks", lambda text: [
        b.replace("aggregate is 6.7× the best", "aggregate is 6.2× the best") for b in real(text)])
    key = ("v41.agg_ratio_fill28_1m_s101", "aggregate is 6.7× the best HBM array's")
    # Acknowledged at a value the record does not hold: still a failure.
    monkeypatch.setitem(HB.ACKNOWLEDGED_DISAGREEMENTS, key, "6.7")
    assert "value-mismatch" in _kinds(HB.build(), "v41.agg_ratio_fill28_1m_s101")
    # Acknowledged at exactly the recorded value: reported, not failed.
    monkeypatch.setitem(HB.ACKNOWLEDGED_DISAGREEMENTS, key, "6.74349")
    kinds = _kinds(HB.build(), "v41.agg_ratio_fill28_1m_s101")
    assert "acknowledged-disagreement" in kinds and "value-mismatch" not in kinds

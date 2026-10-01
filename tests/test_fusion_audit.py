"""Historical fusion audit: original Git pins/replay, retained values, and candidate ordering.

These estimates do not qualify adoption or the current product model.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/uarch/fusion_audit.json"
sys.path.insert(0, str(ROOT / 'tools'))
import fusion_audit_historical as H


def _rec():
    return json.loads(REC.read_text())


def test_record_is_source_pinned():
    H.verify(_rec())


def test_levels_are_monotone_and_classes_are_marked():
    r = _rec()["v41_rom"]
    for key in ("ar_levels", "mtp_pass_levels"):
        lv = r["rows"][key]
        chain = ["L0_unfused_us", "L1_lane_local_us", "L2_delivery_only_us", "L2_delivery_plus_element_epilogue_us",
                 "L3_stream_reductions_us", "L5_plus_piggyback_us", "L5_plus_piggyback_and_hops_us"]
        for a, b in zip(chain, chain[1:]):
            assert lv[b] <= lv[a] + 1e-6, (key, a, b)
        # the in-order stream unit is an EXPOSURE of the model's free interleaving, never a gain
        assert lv["L4_in_order_pipelined_exposure_us"] >= lv["L1_lane_local_us"]
    cls = {c["candidate"]: c["cls"] for c in r["ranked"]["candidates"]}
    assert cls["C: norm scalar after the matvec"] == "C" and cls["C: online softmax"] == "C"
    for c in _rec()["v41_hbm"]["candidates"]:
        assert c["cls"] in ("A", "B", "B*", "C")


def test_record_regenerates_from_original_git_snapshot():
    H.replay()


def test_main_retained_pin_only_record_keeps_historical_scope():
    cp = json.loads(H.CHECKPOINT.read_text())
    for entry in cp['retained_pin_only_records']:
        H.verify(json.loads(H.blob(entry['commit'], cp['record_path'])))


@pytest.mark.parametrize('mutation', ['numerical_body', 'unrecorded_pin'])
def test_reject_changed_history(mutation):
    r = _rec()
    if mutation == 'numerical_body':
        r['v41_rom']['rows']['ar_levels']['L1_lane_local_us'] += 1
    else:
        r['source_sha256']['tools/uarch_model.py'] = '0' * 64
    with pytest.raises(AssertionError):
        H.verify(r)


def test_publication_inventory_cannot_omit_a_source(tmp_path, monkeypatch):
    cp = json.loads(H.CHECKPOINT.read_text())
    cp['required_git_commits'].pop()
    checkpoint = tmp_path / 'checkpoint.json'
    checkpoint.write_text(json.dumps(cp))
    monkeypatch.setattr(H, 'CHECKPOINT', checkpoint)
    with pytest.raises(AssertionError, match='publication inventory drift'):
        H.verify(_rec())

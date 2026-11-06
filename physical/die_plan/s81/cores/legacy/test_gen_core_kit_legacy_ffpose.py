"""DIE-S81-69 11-06: opt-in recipe native_ff_pose (reviewed exact source FF pose staged at PRE_GLOBAL_PLACE).
    python3 -m pytest -q -p no:cacheprovider --noconftest test_gen_core_kit_legacy_ffpose.py"""
import hashlib
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_core_kit_legacy as G  # noqa: E402

POSE = """set ot_np_sites [dict create \\
 {u_bound.u_a/q$_DFF_P_} {1.000000 2.000000 1.080000 0.270000 R0 DFFHQNx1_ASAP7_75t_R} \\
 {u_bound.u_b/q[0]$_DFF_P_} {3.000000 2.000000 1.080000 0.270000 MX DFFHQNx1_ASAP7_75t_R} \\
]
if {0} {error "NATIVE_POSE undeclared source FF x"}
$i setPlacementStatus FIXED
if {0} {error "NATIVE_POSE missing source FFs 0/0"}
"""


def _rec(tmp_path, text=POSE, sha=None):
    f = tmp_path / "pose.tcl"
    f.write_text(text)
    return {"native_ff_pose": {"file": "pose.tcl", "sha256": sha or hashlib.sha256(text.encode()).hexdigest()}}


def test_absent_key_stages_nothing(tmp_path):
    assert G.stage_native_ff_pose(tmp_path, {}, tmp_path) is None
    assert not (tmp_path / "native_ff_pose.tcl").exists()


def test_stages_exact_bytes_and_counts(tmp_path):
    kd = tmp_path / "kit"
    kd.mkdir()
    r = G.stage_native_ff_pose(kd, _rec(tmp_path), tmp_path)
    assert r["ffs"] == 2 and r["sha256"] == hashlib.sha256(POSE.encode()).hexdigest()
    assert (kd / "native_ff_pose.tcl").read_text() == POSE


def test_sha_mismatch_refused(tmp_path):
    with pytest.raises(SystemExit, match="sha256"):
        G.stage_native_ff_pose(tmp_path, _rec(tmp_path, sha="0" * 64), tmp_path)


def test_missing_guard_refused(tmp_path):
    text = POSE.replace("setPlacementStatus FIXED", "setPlacementStatus PLACED")
    with pytest.raises(SystemExit, match="guard"):
        G.stage_native_ff_pose(tmp_path, _rec(tmp_path, text), tmp_path)


def test_missing_sha_refused(tmp_path):
    (tmp_path / "pose.tcl").write_text(POSE)
    with pytest.raises(SystemExit, match="file, sha256"):
        G.stage_native_ff_pose(tmp_path, {"native_ff_pose": {"file": "pose.tcl"}}, tmp_path)

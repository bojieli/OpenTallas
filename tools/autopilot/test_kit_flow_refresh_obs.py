"""FLOW-OPS-1000: obs_gcell_cap.tcl reaches kits generated before main f56d99cf55"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_flow_refresh as KFR  # noqa: E402

RT = Path(__file__).resolve().parents[2]


def test_old_kit_gets_the_helper_and_the_hook_line(tmp_path):
    kit = tmp_path / "w" / "t"; kit.mkdir(parents=True)
    (kit / "grt_pre.tcl").write_text("set gp_dir /work\nif {1} { source /work/pg_track_truth.tcl; ot_pgtt_add }\n")
    rec = {"replaced": []}
    KFR._TXN = []
    try:
        KFR.always_pass(str(kit), str(RT), rec)
        txn = list(KFR._TXN)
    finally:
        KFR._TXN = None
    staged = {os.path.basename(p): data for p, data, *_ in txn}
    assert staged["obs_gcell_cap.tcl"] == (RT / "tools/die_plan/obs_gcell_cap.tcl").read_bytes()
    assert any(r["src"] == "obs_gcell_cap hook line" for r in rec["replaced"])


def test_hook_is_idempotent_and_skips_new_or_foreign_files(tmp_path):
    kit = tmp_path / "t"; kit.mkdir()
    (kit / "obs_gcell_cap.tcl").write_text("# helper\n")
    rec = {"replaced": []}
    (kit / "grt_pre.tcl").write_text("source x; ot_pgtt_add\n" + KFR.OBS_LINE + "\n")
    assert not KFR.patch_obs_hook(str(kit), rec, dry=True)
    (kit / "grt_pre.tcl").write_text("# a hand hook without PG-track-truth\n")
    assert not KFR.patch_obs_hook(str(kit), rec, dry=True)
    (kit / "grt_pre.tcl").write_text("ot_pgtt_add\n")
    assert KFR.patch_obs_hook(str(kit), rec, dry=True)

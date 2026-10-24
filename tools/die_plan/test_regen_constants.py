#!/usr/bin/env python3
"""CAL-AUTO 10-23: regen_constants.py reproduces today's hand-derived schedule constants from the bind outputs alone.

Fixtures (testdata/regen_constants/<bind>) = the members regen_constants.py reads, cut from the real binds with
--write-fixture:  qc12 = BINDER3 QC r8 + QC-P5-TIE bound top (claude/binder3-1023 @d4b946c05 bound_r8),
kv39 = BINDER3 KV v3.6 r8 bound top (same commit).  Hand values of record:
  QC  TOKh 14:17: tp8 MU calendar LS 389 (TX/RX 2/2/10, LX 12/4/12, relays 7/8/8); BINDER2 coll_regen PHY 351/343/351;
      MU pair seam 2,2,2,3,2,2 -> TXDP C [8,3,1,10] (test_d2d_txdp.py); BINDER3 treq offset 0.
  KV  KV-P6 19:10 boot39: RESPONSE_LAT 12, QK_ISSUE_AGE 34, KVN_A0 34 (kvn 39 / att_rx 34), qk_row_latency 14;
      BINDER3 kv_regen36 AP_OFS 64'hffd2ffd1ffd1ffd1; KV-P6-BOOT KST 34,34,32,32,32,31,31 and TXDP K0 67.
    python3 -m pytest tools/die_plan/test_regen_constants.py
"""
import copy
import gzip
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import regen_constants as RC  # noqa: E402

FX = HERE / "testdata" / "regen_constants"


def _v(doc, k):
    return doc["constants"][k]["value"]


def test_qc_hand_values():
    d = RC.run("qwen_compute", FX / "qc12")
    assert _v(d, "COLL_LS") == 389 and _v(d, "MU_CAL_LS") == 389
    assert [_v(d, f"COLL_F{f}_PHY") for f in (2, 3, 4)] == [351, 343, 351]
    assert [_v(d, f"COLL_F{f}_R") for f in (2, 3, 4)] == [7, 8, 8]
    assert [_v(d, f"COLL_F{f}_PEER_R") for f in (2, 3, 4)] == [8, 8, 7]
    assert _v(d, "COLL_BENCH_ARGS") == "--relays 0 7 8 8 --lanes 2 2 10 2 2 10 --lx 12 4 12"
    assert _v(d, "TREQ_CMD_OFFSET") == 0
    assert _v(d, "XDIE_SEAM_C") == "2,2,2,3,2,2"
    assert _v(d, "D2D_TXDP_C") == [8, 3, 1, 10] and d["constants"]["D2D_TXDP_C"]["sv_literal"] == "32'h0a010308"
    # the bind hook applied the same RTL parameters (param_regen.json): no MISMATCH
    assert "MISMATCH" not in d["verdict"] and "ERROR" not in d["verdict"], d["verdict"]
    assert d["constants"]["COLL_LS"]["bind_applied"] == ["389"]


def test_kv_hand_values():
    d = RC.run("qwen_kvsys", FX / "kv39", peer=FX / "qc12")
    assert (_v(d, "RESPONSE_LAT"), _v(d, "QK_ISSUE_AGE"), _v(d, "KVN_A0")) == (12, 34, 34)
    assert _v(d, "QK_ROW_LATENCY") == 14 and _v(d, "QK_D_QK") == 0
    assert d["constants"]["AP_OFS"]["sv_literal"] == "64'hffd2ffd1ffd1ffd1"
    assert _v(d, "AP_OFS") == [-47, -47, -47, -46]
    assert _v(d, "FR_OFS") == -7
    assert _v(d, "XDIE_SEAM_K") == "34,34,32,32,32,31,31"
    assert _v(d, "D2D_TXDP_K") == [67, 4, 3, 3]
    assert _v(d, "XDIE_DIE_STAGES") == "2,2,2,3,2,2/34,34,32,32,32,31,31"
    for k in ("RESPONSE_LAT", "QK_ISSUE_AGE", "KVN_A0", "AP_OFS"):
        assert d["constants"][k]["status"] == "OK", (k, d["constants"][k])
    # kv39 carries the PV table KV-P6 withdrew (18:3x): its TRUNK_D/FLAG_D disagree with the pv_trunk law -> flagged
    assert d["constants"]["TRUNK_D"]["status"] == "MISMATCH"


def _shift(src, dst, pred, by):
    shutil.copytree(src, dst)
    p = dst / "bus_groups.json.gz"
    bg = json.load(gzip.open(p, "rt"))
    n = 0
    for g in bg["landing"]:
        for m in g["members"]:
            if pred(g, m):
                m["landed_stages"] += by
                m["bound_stages"] += by
                n += 1
    json.dump(bg, gzip.open(p, "wt"))
    assert n
    (dst / "param_regen.json").unlink()        # a fresh bind: no hook applied yet
    return dst


def test_qc_regenerates_on_new_lanes(tmp_path):
    """a re-plan that lengthens SerDes leg 2 TX by 3 stages moves LS / PHY with no hand step"""
    b = _shift(FX / "qc12", tmp_path / "qc", lambda g, m: g["sink"] == "io_serdes_2", 3)
    d = RC.run("qwen_compute", b)
    # LX_0 = TX_2 + RX_0 grows 12 -> 15: LS = max_j(... + LX_j + R_j + R_peer) + 3 on port 0
    assert _v(d, "COLL_LS") == 392 and _v(d, "COLL_F2_PHY") == 339 + 15


def test_kv_regenerates_on_new_lanes(tmp_path):
    """krq +1 on every frame -> RESPONSE_LAT 13, QK_ISSUE_AGE stays 34 (floor); kvn to seq core +2 -> KVN_A0 36"""
    b = _shift(FX / "kv39", tmp_path / "kv", lambda g, m: m["sink_port"] == "kreq", 1)
    d = RC.run("qwen_kvsys", b)
    assert (_v(d, "RESPONSE_LAT"), _v(d, "QK_ISSUE_AGE")) == (13, 34)
    b2 = _shift(FX / "kv39", tmp_path / "kv2", lambda g, m: g["sink"] == "seq__u_core" and m["sink_port"] == "kvn_word_valid", 2)
    # the as-built KVN_A0 anchor comes from param_regen.json; without it the tool uses the recorded rtl6 value 32
    assert _v(RC.run("qwen_kvsys", b2), "KVN_A0") == 36


def test_bundle_split_is_an_error(tmp_path):
    """one seam bundle landing on two ages (the R8 failure class) is an ERROR, never averaged"""
    b = _shift(FX / "qc12", tmp_path / "qs", lambda g, m: g["sink"] == "native59" and m["sink_port"] == "tx_slot", 1)
    d = RC.run("qwen_compute", b)
    assert d["constants"]["xdie.__rule__"]["status"] == "ERROR"


def test_pending_without_bound_top():
    for die in ("hbm", "s81"):
        d = RC.run(die, None)
        assert all(r["status"] in ("PENDING", "OK") for r in d["constants"].values()), d["constants"]
        assert any(r["status"] == "PENDING" for r in d["constants"].values())


def test_sv_package():
    d = RC.run("qwen_kvsys", FX / "kv39", peer=FX / "qc12")
    sv = RC.sv_package("qwen_kvsys", d)
    assert "localparam int RESPONSE_LAT = 12;" in sv and "localparam logic [63:0] AP_OFS = 64'hffd2ffd1ffd1ffd1;" in sv
    assert "localparam int XDIE_SEAM_K [7] = '{34, 32, 32" not in sv and "'{34, 34, 32, 32, 32, 31, 31}" in sv
    assert sv.rstrip().endswith("endpackage : qwen_kvsys_sched_pkg")

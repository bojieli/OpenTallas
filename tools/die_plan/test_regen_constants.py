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
    # kv39 carries the PV table KV-P6 withdrew (18:3x, TRUNK_D 56): the KV-P5 pv_trunk law on its landed depths gives
    # 55/1 -> the table value is kept (PV table owns it) but flagged WARN with the law value
    t = d["constants"]["TRUNK_D"]
    assert (t["value"], t["status"], t["inputs"]["law"]) == (56, "WARN", {"TRUNK_D": 55, "FLAG_D": 1})


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


def test_bind_post_gate(tmp_path):
    """the post-bind gate writes regen/constants.json + the SV package + bind_gate.json; a skipped smoke is never PASS"""
    import bind_post
    b = tmp_path / "qc12"
    shutil.copytree(FX / "qc12", b)
    assert bind_post.main(["--die", "qwen_compute", "--bound", str(b), "--smoke", "skip"]) == 1
    g = json.loads((b / "bind_gate.json").read_text())
    assert (g["verdict"], g["regen"]["verdict"], g["smoke"]["verdict"]) == ("INCOMPLETE", "PASS", "SKIPPED")
    assert "localparam int COLL_LS = 389;" in (b / "regen" / "qwen_compute_sched_pkg.sv").read_text()


def test_bound_rtl_must_carry_regen_values(tmp_path):
    """BINDER3 kv39 bound RTL keeps the as-built KV d2d TXDP [22,4,3,3] while its seam needs [67,4,3,3] -> MISMATCH"""
    for txdp, want in (("32'h03030416", "MISMATCH"), ("32'h03030443", "OK")):
        b = tmp_path / txdp[-4:]
        shutil.copytree(FX / "kv39", b)
        (b / "rtl").mkdir()
        (b / "rtl" / "kv3_sys_c_part.sv").write_text(
            f"module kv3_sys_c_part; qkd_d2d_static_sfm #(.PR(1), .TXDP({txdp})) u_d2d_kv (.clk(clk)); endmodule\n")
        d = RC.run("qwen_kvsys", b)
        assert d["constants"]["D2D_TXDP_K"]["status"] == want, d["constants"]["D2D_TXDP_K"]


def test_pair_image_kv_tx_latency(tmp_path):
    """COORD 10-23: the shared QC<->KV pair image's KV TX latency comes from the KV bound top and is emitted for BOTH
    dies.  As built (KV seam 11,11,9,9,9,9,9 -- the value kv35's RTL still carries) = 22; kv39 bound seam
    34,34,32,32,32,31,31 = 67 (KV-P6 boot image @dd512c5ca TXDP K [67,4,3,3])."""
    kv39 = RC.run("qwen_kvsys", FX / "kv39")
    assert _v(kv39, "D2D_KV_TX_LAT") == 67
    qc = RC.run("qwen_compute", FX / "qc12", peer=FX / "kv39")
    assert _v(qc, "D2D_KV_TX_LAT") == 67 and qc["constants"]["D2D_TXDP_K"]["sv_literal"] == "32'h03030443"
    # as-built depths (every landed = as-built stages) -> 22
    b = tmp_path / "asb"
    shutil.copytree(FX / "kv39", b)
    p = b / "bus_groups.json.gz"
    bg = json.load(gzip.open(p, "rt"))
    for g in bg["landing"]:
        for m in g["members"]:
            m["landed_stages"] = m["bound_stages"] = m["asbuilt_stages"]
    json.dump(bg, gzip.open(p, "wt"))
    asb = RC.run("qwen_kvsys", b)
    assert _v(asb, "D2D_KV_TX_LAT") == 22 and _v(asb, "D2D_TXDP_K") == [22, 4, 3, 3]
    assert _v(RC.run("qwen_compute", FX / "qc12", peer=b), "D2D_KV_TX_LAT") == 22


def _kvboot(tmp_path, pads_zero):
    """KV boot run fixture (KV-P7 kv41 boot: RL 63 / FIA 64, W request pads 900 flops still needed); pads_zero = the
    same run on a bind that carries the pads (pad_stages all 0, DQ <= 15)."""
    d = tmp_path / ("boot_padded" if pads_zero else "boot41")
    shutil.copytree(FX / "kvboot41", d)
    if pads_zero:
        f = d / "prep" / "vport_dq_pads.json"
        p = json.loads(f.read_text())
        p["pad_stages"] = {k: 0 for k in p["pad_stages"]}
        p["pad_flops"] = 0
        f.write_text(json.dumps(p))
    return d


def test_kv_boot_is_pv_authority(tmp_path):
    """KV-P8 (KV owner, KV-P7 23:00): with --kv-boot the boot generator's RL 63 / CFG_FIA 64 / DQ are the values of record
    (not the KV-P5 law / entry table 67 / 68); ERROR while the boot still needs W request pads (kv41: 900 flops), OK once
    the bind carries them."""
    d = RC.run("qwen_kvsys", FX / "kv39", kv_boot=_kvboot(tmp_path, False))
    c = d["constants"]
    assert (c["PV_RL"]["value"], c["CFG_FIA"]["value"]) == (63, 64)
    assert c["VPORT_W_PADS"]["status"] == "ERROR" and c["CFG_FIA"]["status"] == "ERROR"
    assert c["VPORT_W_PADS"]["value"]["vport_WN_3"] == 14 and "900" in c["CFG_FIA"]["note"]
    d = RC.run("qwen_kvsys", FX / "kv39", kv_boot=_kvboot(tmp_path, True))
    c = d["constants"]
    for k in ("PV_RL", "CFG_FIA", "VPORT_DQ", "VPORT_W_PADS"):
        assert c[k]["status"] == "OK", (k, c[k])
    assert c["CFG_FIA"]["inputs"]["law_kv_p5"]["CFG_FIA"] != 64      # the KV-P5 law value is kept as info only
    # without --kv-boot the old KV-P5 law rows stay (WARN), unchanged
    d = RC.run("qwen_kvsys", FX / "kv39")
    assert d["constants"]["CFG_FIA"]["status"] == "WARN" and "PV_RL" not in d["constants"]


def test_kv_pv_table_params_own_trunk(tmp_path):
    """a PV table whose params the hook records (pv_table.params) and the bind applied -> TRUNK_D/FLAG_D OK, law = info"""
    b = tmp_path / "kv"
    shutil.copytree(FX / "kv39", b)
    f = b / "param_regen.json"
    pr = json.loads(f.read_text())
    pr["record"]["pv_table"]["params"] = dict(TRUNK_D=56, FLAG_D=0)
    f.write_text(json.dumps(pr))
    t = RC.run("qwen_kvsys", b)["constants"]["TRUNK_D"]
    assert (t["value"], t["status"], t["inputs"]["table"]) == (56, "OK", 56) and "info" in t["note"]
    pr["record"]["pv_table"]["params"] = dict(TRUNK_D=43, FLAG_D=0)       # applied 56 != table 43 -> still WARN
    f.write_text(json.dumps(pr))
    assert RC.run("qwen_kvsys", b)["constants"]["TRUNK_D"]["status"] == "WARN"


def test_bind_post_passes_kv_boot(tmp_path):
    import bind_post
    b = tmp_path / "kv39"
    shutil.copytree(FX / "kv39", b)
    bind_post.main(["--die", "qwen_kvsys", "--bound", str(b), "--smoke", "skip", "--kv-boot", str(_kvboot(tmp_path, False))])
    g = json.loads((b / "bind_gate.json").read_text())
    assert g["regen"]["verdict"] == "FAIL" and "CFG_FIA" in g["regen"]["problems"]

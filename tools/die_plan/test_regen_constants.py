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


def test_composed_ahub_uses_endpoint_ports(tmp_path):
    """Physical ASTK source names change after composition; the AHUB pin identity stays exact."""
    d = tmp_path / 'composed'
    d.mkdir()
    groups = []
    for k, (st, old, new) in enumerate(zip(('WS', 'WN', 'ES', 'EN'), (19, 19, 22, 20), (16, 16, 14, 14))):
        groups.append(dict(sink='ahub', src_part='outer', sink_part='hub_C', members=[dict(
            source=f'native_composite_hub_outer_astk_{st}.u_strip_u_strip_u_ctl__ap', sink_port=f'ap{k}',
            asbuilt_stages=old, bound_stages=new, landed_stages=new, lane=f'L{k}', sink_bits=[[0, 0]])]))
    for side, lag in (("w", 10), ("e", 7)):
        groups.append(dict(sink=f"seq__g_fan_{side}", src_part="hub_C", sink_part="hub_C", members=[dict(
            source=f"seq__u_core.f_aqm_{side}", sink_port="aqm", asbuilt_stages=0,
            bound_stages=lag, landed_stages=lag, lane="Lfan", sink_bits=[[0, 0]])]))
    for k, st in enumerate(("WS", "WN", "ES", "EN")):
        groups.append(dict(sink=f"native_composite_astk_{st}", src_part="hub_C", sink_part="outer", members=[dict(
            source=f"ahub.am{k}", sink_port="am", asbuilt_stages=2,
            bound_stages=7, landed_stages=7, lane=f"Lam{k}", sink_bits=[[0, 0]])]))
    (d / 'bus_groups.json').write_text(json.dumps(dict(landing=groups)))
    (d / 'param_regen.json').write_text(json.dumps(dict(changed=[dict(inst='ahub', param='AP_OFS',
        asbuilt="64'hffddffdeffdcffdc", bound="64'hffd7ffd6ffd9ffd9")], record={})))
    (d / 'rtl').mkdir()
    (d / 'rtl' / 'hub.sv').write_text('module h; qkd_ahub_static_dw #(.FR_OFS(-7)) u_ahub (); endmodule')
    b = RC.Bound(d)
    o = RC.Out('qwen_kvsys', b)
    RC.kv_ahub(o)
    assert o.c['AP_OFS']['value'] == [-39, -39, -42, -41]
    assert o.c['FR_OFS']['value'] == -7
    assert o.c['AM_LAG_DELTA']['value'] == dict(WS=-5, WN=-5, ES=-2, EN=-2)
    # A real extra stage on one AP port changes exactly that stack's required offset.
    groups[2]['members'][0]['landed_stages'] += 1
    (d / 'bus_groups.json').write_text(json.dumps(dict(landing=groups)))
    o = RC.Out('qwen_kvsys', RC.Bound(d))
    RC.kv_ahub(o)
    assert o.c['AP_OFS']['value'] == [-39, -39, -41, -41]


def test_unchanged_param_still_read_with_unrelated_hook_changes(tmp_path):
    d = tmp_path / 'bound'
    d.mkdir()
    (d / 'bus_groups.json').write_text(json.dumps(dict(landing=[])))
    (d / 'param_regen.json').write_text(json.dumps(dict(changed=[dict(inst='ectl', param='RESPONSE_LAT', asbuilt='80', bound=12)])))
    (d / 'rtl').mkdir()
    (d / 'rtl' / 'pv.sv').write_text('module h; ot_qwen_tp8_pv_wide_ctl_tbf #(.TRUNK_D(54), .FLAG_D(58)) u_pvS_u_ctl (); endmodule')
    b = RC.Bound(d)
    assert b.asbuilt_param(r'pvw_\d__u_ctl$', 'TRUNK_D', module=r'ot_qwen_tp8_pv_wide_ctl_tbf') == '54'
# ------------------------------------------------------------------------ KV 833-ps PC controller (TOK-QK-KVCHK 10-26)
PC_TOP = """module qwen_kvsys_bound_top;
  kv3_pc_part u_pc_Q_0 (.clk(clk));
  kv3_pc_part u_pc_Q_1 (.clk(clk));
endmodule
"""
PC_PART = """module kv3_pc_part (input clk);
    qkd_kvs_pc_h_head_p u_kvpc0 (.ck(clk));
    qkd_kvs_pc u_kvpc1 (.ck(clk));
    qkd_kvs_pc u_kvpc2 (.ck(clk));
endmodule
"""
PC_MASTER = """module qkd_kvs_pc (input ck);
    qkd_static_kv_pc_path_fan_nc_b #({cc}.MU(1)) u_pc (.ck(ck));   // the real master: .CORE_CLOCK(1), .MU(1)
endmodule
module qkd_kvs_pc_h_head_p #(parameter [4:0] PC = 0) (input ck);
    qkd_static_kv_pc_path_fan_nc_b_head_p #({hcc}.MU(1), .PC(PC)) u_pc (.ck(ck));
endmodule
"""
# kvspc_core_clock.apply_kit's head-p patch: the plan variant declares CORE_CLOCK and forwards it to its u_pce
HEAD_P_KIT = """module qkd_static_kv_pc_path_fan_nc_b_head_p #(parameter integer CORE_CLOCK = 0,
    parameter integer MU = 0, parameter [4:0] PC = 0) (input ck);
    qkd_static_kv_pc_path_emb_nc_b #(.CORE_CLOCK(CORE_CLOCK),.MU(MU)) u_pce (.ck(ck));
endmodule
"""


def _pc_bind(tmp_path, name, cc, hcc, head_kit=False):
    b = tmp_path / name
    shutil.copytree(FX / "kv39", b)
    (b / "rtl").mkdir()
    (b / "rtl" / "qwen_kvsys_bound_top.sv").write_text(PC_TOP)
    (b / "rtl" / "kv3_pc_part.sv").write_text(PC_PART)
    (b / "rtl" / "pc_masters.sv").write_text(PC_MASTER.format(cc=cc, hcc=hcc) + (HEAD_P_KIT if head_kit else ""))
    return b


def test_kv_pc833_table_without_bound_rtl():
    """kv39 (bus_groups only): the profile is PENDING, the 833 controller constants come from the RTL CORE_CLOCK formulas
    and equal the PATH-KV-PC833 reprice (HBM_RL 23->29, WDONE 17->19, tREFIpb 118->144 ...)"""
    d = RC.run("qwen_kvsys", FX / "kv39")
    c = d["constants"]
    assert c["PC_CORE_CLOCK"]["status"] == "PENDING"
    assert (_v(d, "PC_HBM_RL"), _v(d, "PC_WDONE"), _v(d, "PC_T_RCD"), _v(d, "PC_T_RP"), _v(d, "PC_T_RAS")) == (29, 19, 24, 20, 35)
    assert (_v(d, "PC_T_FAW"), _v(d, "PC_T_WRR"), _v(d, "PC_T_WTR"), _v(d, "PC_T_REFI"), _v(d, "PC_T_REFIPB")) == (19, 35, 18, 4680, 144)
    assert _v(d, "PC_PHASE_TICKS") == [625, 625] and "PC_TIMING_TABLE" not in c
    assert all(c[k]["status"] == "OK" for k in c if k.startswith("PC_T") or k in ("PC_HBM_RL", "PC_WDONE"))


def test_kv_pc833_mixed_die_is_an_error(tmp_path):
    """the repo plan variant qkd_static_kv_pc_path_fan_nc_b_head_p has no CORE_CLOCK: a head PC master that binds it
    runs the legacy 1024 controller next to CORE_CLOCK=1 masters -> MIXED -> ERROR (2 of 6 PCs here)"""
    d = RC.run("qwen_kvsys", _pc_bind(tmp_path, "mixed", ".CORE_CLOCK(1), ", ""))
    c = d["constants"]
    assert c["PC_CORE_CLOCK"]["value"] == {"qkd_kvs_pc": 1, "qkd_kvs_pc_h_head_p": 0}
    assert c["PC_CORE_CLOCK"]["status"] == "ERROR" and "MIXED" in c["PC_CORE_CLOCK"]["note"]
    assert c["PC_CORE_CLOCK"]["inputs"]["die_pcs"] == {"1": 4, "0": 2}
    assert (c["PC_CONTROLLER_PROFILE"]["value"], c["PC_CONTROLLER_PROFILE"]["status"]) == ("mixed", "ERROR")


def test_kv_pc833_uniform_and_image(tmp_path):
    """kit-patched head-p (forwards CORE_CLOCK) + CORE_CLOCK=1 everywhere -> common833 OK; the boot image must record
    the same profile (static.json ticks 625/625), a legacy 625/768 image on that die is an ERROR, and the reverse"""
    b = _pc_bind(tmp_path, "c833", ".CORE_CLOCK(1), ", ".CORE_CLOCK(1), ", head_kit=True)
    img = tmp_path / "img833"
    img.mkdir()
    (img / "static.json").write_text(json.dumps(dict(ticks=[625, 625])))
    d = RC.run("qwen_kvsys", b, kv_image=img)
    c = d["constants"]
    assert (c["PC_CONTROLLER_PROFILE"]["value"], c["PC_CORE_CLOCK"]["status"]) == ("common833", "OK")
    assert c["PC_IMAGE_PROFILE"]["status"] == "OK"
    leg = tmp_path / "img1024"
    leg.mkdir()
    (leg / "static.json").write_text(json.dumps(dict(ticks=[625, 768])))
    assert RC.run("qwen_kvsys", b, kv_image=leg)["constants"]["PC_IMAGE_PROFILE"]["status"] == "ERROR"
    # legacy die (no CORE_CLOCK anywhere) under an 833 image: profile ERROR + image ERROR; 1024 values reported
    b0 = _pc_bind(tmp_path, "c1024", "", "")
    d0 = RC.run("qwen_kvsys", b0, kv_image=img)
    c0 = d0["constants"]
    assert (c0["PC_CONTROLLER_PROFILE"]["value"], c0["PC_CORE_CLOCK"]["status"]) == ("legacy1024", "ERROR")
    assert c0["PC_IMAGE_PROFILE"]["status"] == "ERROR" and _v(d0, "PC_HBM_RL") == 23




def _native_vport_fixture(tmp_path, added_landed=0):
    dst = tmp_path / "native_vport"
    shutil.copytree(FX / "kv39", dst)
    path = dst / "bus_groups.json.gz"
    bg = json.load(gzip.open(path, "rt"))
    actual = json.loads((FX / "kv_vport_native_landed.json").read_text())
    for group in actual["landing"]:
        for member in group["members"]:
            if member["source"] == "vport_EN_0.vq0_valid":
                member["landed_stages"] += added_landed
    bg["landing"].extend(actual["landing"])
    json.dump(bg, gzip.open(path, "wt"))
    return dst


def test_vport_rt_uses_landed_request_age(tmp_path):
    after = RC.run("qwen_kvsys", _native_vport_fixture(tmp_path, 1))
    # Actual native EN0: request19 (+one test shift) + response20 + landing9.
    assert _v(after, "VPORT_RT")["vport_EN_0"] == 49


def test_vport_rt_at_capacity_is_ok(tmp_path):
    # Capacity is RC.VPORT_RT_MAX (95, kv_bootage RT bound), not codex 1027b 63.
    after = RC.run("qwen_kvsys", _native_vport_fixture(tmp_path, RC.VPORT_RT_MAX - 48))
    record = after["constants"]["VPORT_RT"]
    assert record["value"]["vport_EN_0"] == RC.VPORT_RT_MAX
    assert record["status"] == "OK"


def test_vport_rt_over_capacity_is_error(tmp_path):
    after = RC.run("qwen_kvsys", _native_vport_fixture(tmp_path, RC.VPORT_RT_MAX - 47))
    record = after["constants"]["VPORT_RT"]
    assert record["value"]["vport_EN_0"] == RC.VPORT_RT_MAX + 1
    assert record["status"] == "ERROR"


def _host_record_bind(src, dst, out=86, back=67, witness=None):
    """kv39 + the KV HOST record port across the bind (TOK-KV-4 10-29): the b5 vehicle (DIE-KV-16 bind5 / DIE-KV-15
    event plan) lands record_send_kind / record_witness_slot d2d_kv -> host at 86 stages and record_tx_observed_v /
    record_tx host -> d2d_kv at 67 (veh5 bus_groups.json); kv39 has the HOST record port next to the end (no crossing)."""
    shutil.copytree(src, dst)
    p = dst / "bus_groups.json.gz"
    bg = json.load(gzip.open(p, "rt"))
    mem = lambda port, src_, n, st, lane: dict(sink_port=port, sink_bits=[[0, n - 1]], source=src_, source_bits=[[0, n - 1]],
                                               asbuilt_stages=1 if src_.startswith("d2d_kv") else 0, bound_stages=st,
                                               landed_stages=st, lane=lane)
    bg["landing"] += [
        dict(sink="host", sink_part="hub_Wi", src_part="sys_c", aligned_by_lanes=True, aligned_landed=True,
             asbuilt_stage_set=[1], members=[mem("record_send_kind", "d2d_kv.record_send_kind", 2, out, "L354"),
                                             mem("record_witness_slot", "d2d_kv.record_witness_slot", 1,
                                                 out if witness is None else witness, "L354")]),
        dict(sink="d2d_kv", sink_part="sys_c", src_part="hub_Wi", aligned_by_lanes=True, aligned_landed=True,
             asbuilt_stage_set=[0], members=[mem("record_tx", "host.record_tx", 548, back, "L751"),
                                             mem("record_tx_observed_v", "host.record_tx_observed_v", 1, back, "L751")])]
    json.dump(bg, gzip.open(p, "wt"))
    return dst


def test_host_record_round_trip_sets_txdp_k1(tmp_path):
    """TOK-KV-4 10-29 (KV token link abort, epoch_abort cyc 38406 new_fault bit 7): the KV end captures the HOST record
    at TXD K[1] edges after its port-1 slot; with the HOST across the bind the record comes back 2 + out + back + PR 2 =
    157 edges later (measured 153 edges after the bound capture at K[1] = 4).  The law must price the landed relay and
    the bind gate must fail a bound top that still carries K[1] = 4."""
    assert _v(RC.run("qwen_kvsys", FX / "kv39"), "D2D_HOST_REC_RT") == 0          # HOST next to the end: unchanged
    b = _host_record_bind(FX / "kv39", tmp_path / "hr")
    d = RC.run("qwen_kvsys", b)
    assert _v(d, "D2D_HOST_REC_RT") == 153
    assert _v(d, "D2D_TXDP_K") == [67, 157, 3, 3] and d["constants"]["D2D_TXDP_K"]["sv_literal"] == "32'h03039d43"
    for txdp, want in (("32'h03030443", "MISMATCH"), ("32'h03039d43", "OK")):
        r = tmp_path / txdp[-4:]
        shutil.copytree(b, r)
        (r / "rtl").mkdir()
        (r / "rtl" / "kv3_sys_c_part.sv").write_text(
            f"module kv3_sys_c_part; qkd_d2d_static_sfm #(.PR(1), .TXDP({txdp})) u_d2d_kv (.clk(clk)); endmodule\n")
        assert RC.run("qwen_kvsys", r)["constants"]["D2D_TXDP_K"]["status"] == want
    # the compute peer prices the same pair image
    assert RC.run("qwen_compute", FX / "qc12", peer=b)["constants"]["D2D_TXDP_K"]["sv_literal"] == "32'h03039d43"
    # a slot that lands apart from its send_kind cannot be priced by one age
    bad = RC.run("qwen_kvsys", _host_record_bind(FX / "kv39", tmp_path / "bad", witness=85))
    errs = [r["formula"] for r in bad["constants"].values() if r["status"] == "ERROR"]
    assert any("HOST record out bundle lands unequal [85, 86]" in e for e in errs), errs
    assert "D2D_TXDP_K" not in bad["constants"] or bad["constants"]["D2D_TXDP_K"]["status"] != "OK"

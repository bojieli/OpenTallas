#!/usr/bin/env python3
"""SQ-C2-N59 (10-21): kit specs for the Q die's BOUND native59 service child qfd_native59_svc_obs1 (Q.STA.N59).

Base = qfd_n59_svc4 spec (claude/qw-n59svc-stage-1020; CLOSED but bound to the wrong master qfd_native59_svc and judged
under a coordinator clock waiver, TT pin-flop spread 84.6 ps on ONE root of 21,950 sinks).  Owner PD-AUDIT 10-21: no
waiver, no outline shrink; 2 regional clock roots (W/E halves) + a landed seam, pin-flop spread <= 80 ps TT+FF per region.

  qfd_n59_svc5   MAIN      svc4 outline 518.4 x 216 / pin plan (+ the obs1/headprep ports), clock_regions_2lvl mode we:
                           2 regional roots (W/E halves, seam x = 259.2 under the N-face ck pin) x 6 leaf clusters each.
  qfd_n59_svc5b  FALLBACK  structurally different: clock_regions_2lvl mode quad (4 regional roots NW/NE/SW/SE, seams x and
                           y) x 4 leaves each, AND the E face relieved (dr_o 520 b moved E -> S: E 4.8 -> 2.4 pins/um,
                           S 2.1 -> 3.1 pins/um; checklist 1 <= ~4/um on every face).
usage: gen_specs.py SVC4_SPEC.json  (writes physical/ref_tile/qfd_n59_svc5{,b}/spec.json)
"""
import copy, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
base = json.loads(Path(sys.argv[1]).read_text())

SOURCES = [
    "rtl/qwen_split/qfd_native59_svc_obs1.sv",
    "rtl/qwen_split/qfd_native59_static_service_obs1.sv",
    "rtl/qwen_split/mu/qfd_status_obs_hold_chunk.sv",
    "rtl/qwen_split/qfd_native59_mctx_helpers.sv",
    "rtl/qwen_split/qfd_native59_command_context.sv",
    "rtl/qwen_split/qfd_native59_q_export_control.sv",
    "rtl/qwen_split/qfd_native59_record_endpoint.sv",
    "rtl/qwen_split/qfd_kvn_static_transport.sv",
    "rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv",
    "rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv",
]
# bound master parameters (ASSEMBLY_CANONICAL Q.native59) + the svc3/svc4 physical form (flop-first pins, census <= 32);
# the die parent passes SVC_RECV=1 SVC_LOCAL32=1 to bind this view (NOTICE to the die owner)
PARAMS = {"HEAD_PREP": 1, "NU": 4, "ROPE": 1, "USER_BIND": 1, "MCTX": 1, "EMB_RELAY": 1, "RECV_INPUTS": 1, "LOCAL32": 1}
WIDTH = {  # port widths of qfd_native59_svc_obs1 (header)
    "ck": 1, "rst_n": 1, "host_epoch_valid": 1, "host_fused_capability": 1, "host_epoch": 16, "host_tag": 59,
    "host_generation": 2, "layer_context_v": 1, "command_stage": 6, "head_prepare_v": 1, "head_prepare_user": 2,
    "head_prepare_token": 18, "head_prepare_position": 18, "native_token": 18, "native_position": 18, "native_cmd": 380,
    "dd_i": 548, "kv_word_slot": 1, "kv_word_index": 2, "kv_x3_slot": 1, "x3": 524, "x3_identity": 59, "x3_generation": 2,
    "qb_v": 1, "qb_beat": 5, "qb_row": 512, "qb_full": 1, "qb_committed": 1, "qb_bad": 1, "tx_user": 2, "rx_user": 2,
    "tx_slot": 1, "tx_slot_kind": 4, "tx_slot_beat": 5, "native_tx_v": 1, "native_tx_payload": 548,
    "head_descriptor_v": 1, "head_descriptor_tag": 59, "head_descriptor_generation": 2, "native_rx_v": 1,
    "native_rx_payload": 548, "rx_slot": 1, "rx_slot_kind": 4, "rx_slot_beat": 5, "dr_o": 520, "emb_code_re": 1,
    "emb_code_addr": 24, "emb_scale_re": 1, "emb_scale_addr": 18, "emb_code_q": 512, "emb_scale_q": 16,
    "visibility_slot": 1, "complete_slot": 1, "completed": 1, "completed_tag": 59, "native_ret": 95, "fault": 1}
W, H = 518.4, 216.0
CK = (257.7, 260.7)


def ranges(ports, lo, hi):
    """bit-weighted contiguous ranges over [lo, hi] (0.1 um gaps, >= 1.2 um per port)"""
    gap, mn = 0.1, 1.2
    span = hi - lo - gap * (len(ports) - 1)
    tot = sum(WIDTH[p] for p in ports)
    w = {p: WIDTH[p] / tot * span for p in ports}
    small = [p for p in ports if w[p] < mn]
    big = [p for p in ports if p not in small]
    rest = span - mn * len(small)
    btot = sum(WIDTH[p] for p in big)
    out, x = {}, lo
    for p in ports:
        ln = mn if p in small else WIDTH[p] / btot * rest
        out[p] = [round(x, 3), round(x + ln, 3)]
        x += ln + gap
    assert abs(x - gap - hi) < 0.01, (x, hi)
    return out


def plan(dr_o_south: bool):
    N_left = ["native_rx_v", "native_rx_payload", "rx_slot", "rx_slot_kind", "rx_slot_beat", "rx_user", "kv_x3_slot",
              "kv_word_slot", "kv_word_index", "x3_identity", "x3_generation", "head_descriptor_v", "head_descriptor_tag",
              "head_descriptor_generation", "completed_tag"]
    N_right = ["x3", "tx_slot", "tx_slot_kind", "tx_slot_beat", "tx_user", "native_tx_v", "native_tx_payload"]
    Wf = ["native_cmd", "native_token", "native_position", "head_prepare_v", "head_prepare_user", "head_prepare_token",
          "head_prepare_position", "native_ret", "host_epoch_valid", "host_fused_capability", "host_epoch", "host_tag",
          "host_generation", "emb_code_re", "emb_code_addr", "emb_scale_re", "emb_scale_addr", "emb_scale_q",
          "visibility_slot", "complete_slot", "completed", "fault", "rst_n"]
    Ef = ["emb_code_q"] + ([] if dr_o_south else ["dr_o"])
    Sf = ["qb_row", "qb_v", "qb_beat", "qb_full", "qb_committed", "qb_bad", "layer_context_v", "command_stage", "dd_i"] + \
         (["dr_o"] if dr_o_south else [])
    pr = {}
    pr.update(ranges(N_left, 1.05, CK[0] - 0.1))
    pr["ck"] = list(CK)
    pr.update(ranges(N_right, CK[1] + 0.1, W - 1.05))
    pr.update(ranges(Wf, 1.05, H - 1.05))
    pr.update(ranges(Ef, 1.05, H - 1.05))
    pr.update(ranges(Sf, 1.05, W - 1.05))
    faces = {"N": N_left[:11] + ["ck"] + N_right + N_left[11:], "E": Ef, "W": Wf, "S": Sf}
    # face order list = physical order along the face (ck between x3_generation and x3 as in svc4)
    faces["N"] = N_left + ["ck"] + N_right
    assert sorted(sum(faces.values(), [])) == sorted(WIDTH), set(WIDTH) ^ set(sum(faces.values(), []))
    dens = {f: round(sum(WIDTH[p] for p in ps) / (W if f in "NS" else H), 2) for f, ps in faces.items()}
    return faces, pr, dens


def spec(name, tag, mode, leaves, dr_o_south, role):
    s = copy.deepcopy(base)
    faces, pr, dens = plan(dr_o_south)
    s.update(name=name, top="qfd_native59_svc_obs1", sources=SOURCES, params=PARAMS, pins=faces, pin_ranges=pr)
    s["pre_cts_extra"] = ["physical/common_flow/clock_regions_2lvl.tcl"]
    ov = dict(s.get("orfs_vars") or {})
    ov.update(OT_CKRG_MODE=mode, OT_CKRG_LEAVES=str(leaves), OT_CKRG_PORT="ck")
    s["orfs_vars"] = ov
    s["fill_reason"] = {"pin_bound": f"slot-driven (owner PD-AUDIT 10-21: no outline shrink): 518.4 x 216 is the N part of the "
                        f"518.4 x 648 native59 slot (svc4 outline); 4,648 pins on a 1,469 um perimeter (face pins/um {dens}); "
                        f"std-cell only, ~13 % fill"}
    s["structural_change"] = (
        f"SQ-C2-N59 (10-21) {role}: successor of qfd_n59_svc4 for the master the Q die actually binds "
        f"(qfd_native59_dv_headprep_obs1 b8f883e7 -> u_svc qfd_native59_svc_obs1, HEAD_PREP 1 NU 4 ROPE 1 USER_BIND 1 MCTX 1 "
        f"EMB_RELAY 1; + RECV_INPUTS 1 LOCAL32 1 as svc3/svc4).  svc4 = qfd_native59_svc, ONE clock root 21,950 sinks, "
        f"pin-flop spread TT 84.6 ps (> 80) closed only under a coordinator waiver; owner 10-21: no waiver, no shrink.  "
        f"Fix: physical/common_flow/clock_regions_2lvl.tcl mode {mode}: {'2 regional roots W/E (seam x 259.2, under the N-face ck pin)' if mode == 'we' else '4 regional roots NW/NE/SW/SE (seams x 259.2, y 108)'}"
        f" x {leaves} k-means leaf roots per region; no leaf cluster or CTS subtree crosses a seam; seam crossings are "
        f"flop -> flop between regional trees of one synchronous clock (fixed latency 1 edge).  "
        + ("E face relieved: dr_o 520 b E -> S face (E 4.8 -> 2.4 pins/um).  " if dr_o_south else "")
        + f"Same outline 518.4 x 216, PDN, layer contract, reach relocation hooks and cycles as svc4.  Face pins/um {dens}.")
    j = s.setdefault("job", {})
    j.update(owner="Claude:SQ-C2-N59", branch="claude/sq-c2-n59-1021", tag=tag,
             purpose=f"SQ-C2-N59 (10-21) Q.STA.N59 bound service child qfd_native59_svc_obs1 ({role}): "
                     f"regional clock roots ({mode}) replace svc4's single waived root; no waiver, no outline shrink.",
             views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}")
    j["extra_paths"] = ["rtl/test/qwen_split", "results/arch/sqc2_n59_1021", "rtl/qwen_split/qfd_native59_svc.sv",
                        "rtl/qwen_split/qfd_native59_static_service.sv"]
    B = "bash results/arch/sqc2_n59_1021/bench.sh"
    W_ = "results/arch/sqc2_n59_1021/receipts"
    j["benches"] = [
        {"name": f"obs1_{c}", "cmd": f"{B} {c} {{RUN}}/bench/{c}", "expect": "pass", "threads": 4, "peak_ram_gb": 8,
         "needs": ["verilator"], "pass_regex": f"^N59OBS_CASE {c} PASS$"} for c in ("s1", "s2")] + [
        {"name": f"obs1_{c}", "cmd": f"{B} {c} {{RUN}}/bench/{c}", "expect": "fail", "threads": 4, "peak_ram_gb": 8,
         "needs": ["verilator"], "fail_regex": f"^N59OBS_MUTANT_REJECTED {c}$", "fail_witness": f"{W_}/{c}.log"}
        for c in ("m_hpseq", "m_hpdrop", "m_ret", "m_hosttag")]
    out = ROOT / "physical/ref_tile" / name / "spec.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(s, indent=1) + "\n")
    print(name, dens)


spec("qfd_n59_svc5", "sv5", "we", 6, False, "MAIN")
spec("qfd_n59_svc5b", "sv5b", "quad", 4, True, "FALLBACK")

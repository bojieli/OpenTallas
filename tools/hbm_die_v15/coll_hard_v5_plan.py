#!/usr/bin/env python3
"""H-NETLIST/COLL 1045: hierarchical COLL quadrant parent plan (hard_v5) -> results/arch/hbm_coll_hard_v5_1045/plan.json

Lists every child of ot_hfd_coll_q{3,2}_hard_v5 with its replica count per quadrant type, clock entries, source hash,
and the CLOSED / routed view it binds (or MISSING -> leaf kit queue), and the exact die-port delta against the
current v16 masters ot_hfd_coll_q{3,2}_static_host_v4.   usage: coll_hard_v5_plan.py [--out DIR]
"""
import argparse, hashlib, json, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = "rtl/hbm_accel/generic/collective/p2p/"
T = "rtl/hbm_accel/generic/collective/tkm/"


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def ports(path, module):
    """ANSI header ports of `module` (simple 'input wire [a:b] x,y' headers) -> {name: (dir, bits)}"""
    text = (ROOT / path).read_text()
    m = re.search(r"module\s+%s\b.*?\)\s*;" % re.escape(module), text, re.S)
    hdr = re.sub(r"//[^\n]*", "", m.group(0))
    hdr = hdr[hdr.index("(", hdr.index(")") if "#(" in hdr[:hdr.index("(") + 2] else 0) + 1:]
    out, cur = {}, None
    for tok in re.split(r",(?![^\[]*\])", hdr.rsplit(")", 1)[0]):
        tok = tok.strip()
        d = re.match(r"(input|output)\s+(?:wire|reg)?\s*(\[(\d+):(\d+)\])?\s*(\w+)", tok)
        if d:
            cur = (d.group(1), int(d.group(3)) - int(d.group(4)) + 1 if d.group(2) else 1)
            out[d.group(5)] = cur
        elif re.fullmatch(r"\w+", tok) and cur:
            out[tok] = cur
    return out


def closed(job):
    v = json.loads((ROOT / "results/closure_loop" / job / "verdict.json").read_text()) if (
        ROOT / "results/closure_loop" / job / "verdict.json").exists() else None
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/arch/hbm_coll_hard_v5_1045")
    a = ap.parse_args()
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short=9", "HEAD"], capture_output=True,
                          text=True).stdout.strip()
    V5 = P + "ot_hfd_coll_q_hard_v5.sv"
    # (master, kind, q3 count, q2 count, clock pins each, view status, binding, source, note)
    rows = [
        ("ot_hgi_coll_fj_q3", "leaf", 1, 0, 1, "MISSING", None, V5,
         "HOST F20 programme target (actual ot_hgi_coll_static_program_target TARGET 52, identity remap 52+qid) + "
         "aggregate sticky fault + fault_cause[15:0]"),
        ("ot_hgi_coll_fj_q2", "leaf", 0, 1, 1, "MISSING", None, V5, "as fj_q3 + q2 illegal arg/tkm reservation checks"),
        ("ot_hgi_coll_issuer_m", "leaf+3 SRAM macros", 1, 1, 4, "MISSING", None, V5,
         "actual issuer, 3 x ot_sram_1r1w_64x512_m1_r2c2; uop_v mask inside the leaf"),
        ("ot_hgi_coll_ctl_v4_q3", "leaf", 1, 0, 1, "MISSING", None, V5, "ot_hgi_coll_q_static_ctl_v4 NPT3 SOLO1 INJLAT12"),
        ("ot_hgi_coll_ctl_v4_q2", "leaf", 0, 1, 1, "MISSING", None, V5, "ot_hgi_coll_q_static_ctl_v4 NPT2 SOLO0 INJLAT12"),
        ("ot_hgi_coll_qslots_capture_pin_v2", "leaf", 11, 9, 1, "MISSING", None,
         P + "ot_hgi_coll_qslots_capture_pin_v2.sv", "NS1/PWT545, 547+1 FF (mapped sizing capture545 + pin_v2 src_v FF)"),
        ("ot_hgi_coll_qso_q3_b32", "leaf", 17, 0, 1, "MISSING", None, V5, "qslots_output NS11 ND16 PWT32 (NEW shape)"),
        ("ot_hgi_coll_qso_q3_b1", "leaf", 1, 0, 1, "MISSING", None, V5, "qslots_output NS11 ND16 PWT1 (NEW shape)"),
        ("ot_hgi_coll_qso_q2_b32", "leaf", 0, 17, 1, "MISSING", None, V5, "qslots_output NS9 ND15 PWT32 (= sizing output_q2_b32)"),
        ("ot_hgi_coll_qso_q2_b1", "leaf", 0, 1, 1, "MISSING", None, V5, "qslots_output NS9 ND15 PWT1 (= sizing output_q2_b1)"),
        ("ot_hgi_coll_link_e", "wires-only sub-cluster", 3, 2, 5, "MISSING", None, V5,
         "capture_ctl_e leaf + 4 x ot_hgi_coll_static_pinreg_store leaves (TX6/RX2, 612b frame)"),
        ("ot_hgi_coll_capture_ctl_e", "leaf (in link_e)", 3, 2, 1, "MISSING", None, V5,
         "ot_hgi_coll_static_capture_ctl + epoch select"),
        ("ot_hgi_coll_static_pinreg_store", "leaf (in link_e)", 12, 8, 1, "MISSING", None,
         P + "ot_hgi_coll_static_pinreg_store.sv", "141b x 64 store bank"),
        ("ot_hgi_coll_static_vmwrite_roots_v6_physical", "leaf", 1, 1, 16, "CLOSED",
         "hcoll_vmwrite_static_v6_roots_fsw-fsw0600-d6d487656 (view physical/ref_tile/hcoll_vmwrite_static_v6_roots_fsw)",
         P + "ot_hgi_coll_static_vmwrite_roots_v6_physical.sv", "replaces ot_hgi_coll_static_vmwrite; lockstep proves equal"),
        ("ot_hgi_coll_reduce_static", "hybrid sub-cluster", 1, 1, 33, "MISSING", None, P + "ot_hgi_coll_reduce_static.sv",
         "own control root + 16 ot_hgi_coll_reduce_static_state_lane + 16 ot_hgi_coll_pring_static_add_lane"),
        ("ot_hgi_coll_reduce_static_state_lane", "leaf (in reduce)", 16, 16, 1, "MISSING", None,
         P + "ot_hgi_coll_reduce_static.sv", ""),
        ("ot_hgi_coll_pring_static_add_lane", "leaf (in reduce, ring)", 24, 24, 1, "MISSING", None,
         P + "ot_hgi_coll_pring_static.sv",
         "LAT8 FP32 add lane; legacy CLOSED ot_hgi_coll_pring_add_lane (hgi_coll_ring_add_r1) is a different module: "
         "reuse only after an equivalence proof"),
        ("ot_hgi_coll_ring_v5", "hybrid sub-cluster", 1, 1, 17, "MISSING", None, V5,
         "pring_captured_static SPLIT_CLOCKS1: control root + 8 state-capture lanes + 8 add lanes"),
        ("ot_hgi_coll_pring_static_state_capture_lane", "leaf (in ring)", 8, 8, 1, "ROUTED_VIEW",
         "physical/ref_tile/hcoll_ring_state_capture_1417/views (manual route results/arch/hcoll_state_route_1417)",
         P + "ot_hgi_coll_pring_static_state_capture.sv", "H-DIE grants_v7_1900 adopted in all 32 slots"),
        ("ot_hgi_coll_argmax_m", "leaf", 1, 0, 1, "MISSING", None, V5, "ot_hgi_coll_argmax_static + mode gating"),
        ("ot_hgi_coll_tkm_m", "hybrid sub-cluster", 1, 0, 34, "MISSING", None, V5,
         "tkm_static KMAX2048 control root + buffer leaf + 32 CLOSED tkm tiles; del gating inside"),
        ("ot_hgi_coll_tkm_tile", "leaf (in tkm)", 32, 0, 1, "CLOSED",
         "coll_tkm_tile_cx-r1-5ab85cbc7 (tile body byte-identical on main; PT64)", T + "ot_hgi_coll_tkm.sv", ""),
        ("ot_hgi_coll_tkm_buffer", "leaf+SRAM (in tkm)", 1, 0, 1, "MISSING", None, T + "ot_hgi_coll_tkm_buffer.sv",
         "ot_sram_1r1w_1024x256_m2_r2c2"),
    ]
    children = []
    for m, kind, n3, n2, ck, st, bind, src, note in rows:
        children.append(dict(master=m, kind=kind, q3_count=n3, q2_count=n2, clock_pins_each=ck, view_status=st,
                             binding=bind, source=src, source_sha256=sha(src), note=note))
    delta = {}
    for q, old, new in (("q3", "ot_hfd_coll_q3_static_host_v4", "ot_hfd_coll_q3_hard_v5"),
                        ("q2", "ot_hfd_coll_q2_static_host_v4", "ot_hfd_coll_q2_hard_v5")):
        po, pn = ports(P + old + ".sv", old), ports(V5, new)
        delta[q] = dict(
            old_master=old, new_master=new,
            removed=sorted(k for k in po if k not in pn),
            added={k: dict(direction=pn[k][0], bits=pn[k][1]) for k in pn if k not in po},
            width_changed={k: dict(old=po[k][1], new=pn[k][1]) for k in pn if k in po and po[k] != pn[k]},
            unchanged=len([k for k in pn if k in po and po[k] == pn[k]]),
            old_parameters={"QID": "physical identity -> strap port qid", "INJLAT": "fixed 12 in the hardened control leaf"},
            old_clock_bits=sum(b for k, (d, b) in po.items() if k.startswith("clk_")),
            new_clock_bits=sum(b for k, (d, b) in pn.items() if k.startswith("clk_")))
    plan = dict(
        schema="opentallas.hbm.coll_hard_v5_plan.v1", source_commit=head,
        rtl=V5, rtl_sha256=sha(V5),
        hierarchy_contract="OWNER 10-11 top-down: glue into tiles; parent wires-only (entries clocks); q2 hardened ONCE "
                           "(SE R0 / NW R180 / NE MX) with qid strap; sub-clusters reduce/ring/tkm hardened once each",
        slots={"coll_SW": "q3 671.76 x 721.44 R0", "coll_SE": "q2 963.36 x 721.44 R0",
               "coll_NW": "q2 963.36 x 721.44 R180", "coll_NE": "q2 963.36 x 721.44 MX"},
        children=children,
        die_port_delta=delta,
        straps=[{"inst": f"hb_coll_{q}", "port": "qid", "value": v, "lo": 0, "hi": 2,
                 "reason": f"identity: COLL quadrant QID {v} (HOST target {52 + v}; ring cw SW>SE>NE>NW)"}
                for q, v in (("SW", 0), ("SE", 1), ("NW", 2), ("NE", 3))],
        fault_abi=dict(
            register="u_fj on clk_program; fault/hgi_fault sticky; fault_cause[15:0] sticky per child",
            cause_bits={0: "programme", 1: "issuer", 2: "protocol", 3: "qslots capture", 4: "qslots select",
                        5: "qslots unavailable", 6: "link0", 7: "link1", 8: "link2", 9: "ring", 10: "writer",
                        11: "reduce", 12: "arg (q2 illegal arg reservation)", 13: "tkm (q2 illegal tkm reservation)"},
            edges_vs_host_v4={"all other children": 0, "qslots capture (pin_v2)": "+1",
                              "q2 arg capture reservation": "-1",
                              "q2 arg sink select": "select_fault instead of unavailable_fault (same edge)"},
            containment="no fault changes a reservation/valid/payload (static schedule; no on-die kill or stall); "
                        "host isolates via host_status t_fault + fault_cause and reprograms after rst_n",
            bench="rtl/hbm_accel/generic/collective/p2p/run_q_hard_v5_bench.sh (tb_hgi_coll_q_hard_v5)"),
        clock_entries=dict(q3="program1 control1 issue4 qslots29 ring17 reduce33 arg1 tkm34 vmwrite16 link15",
                           q2="program1 control1 issue4 qslots27 ring17 reduce33 vmwrite16 link10"),
        findings=[
            "qslots pin_v2 receipt/sizing (618fa49ba, b8f4ce191) used V1 shapes q3 NS10 / q2 NS9; the V4 parent has "
            "q3 NS11 (reduce+arg) and q2 NS10 (dead arg source): q3 needs NS11 slices; q2 hard_v5 uses NS9 and checks "
            "the illegal arg reservation in fj",
            "V4 parent glue (1536b uop_v mask, epoch select, arg/tkm gating, fault ORs) moved into leaves; host_v4 "
            "fault register moved into fj (same edge)",
        ])
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "plan.json").write_text(json.dumps(plan, indent=1) + "\n")
    print(json.dumps(delta, indent=1))


if __name__ == "__main__":
    main()

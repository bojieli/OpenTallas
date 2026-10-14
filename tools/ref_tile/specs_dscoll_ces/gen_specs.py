#!/usr/bin/env python3
"""S81 collective lane-slice SPLIT (s81-cesn 2026-10-13): the ref_tile specs of the seven hardened leaves and the two
wires-only clusters (dsfd_coll_ces0, dsfd_coll_cesn).  One generator so the leaf outlines / pin faces and the cluster
floorplan cannot drift apart.

    python3 tools/ref_tile/specs_dscoll_ces/gen_specs.py            # writes tools/ref_tile/specs_dscoll_ces/*.json

Leaves (M5 cap, kit recipe 2: halo 5.4 um, hold margin 30 ps, hold cells + pin flops FIRM at the pins; every port is a
register at the pin in RTL):
  dscoll_cesl   dsfd_coll_cesl   one FP32 lane of the pairwise reduce          x4 per slice (hardened ONCE, 64 on the die)
  dscoll_cesx   dsfd_coll_cesx   one remote source's two xl relay links        x3 per slice (hardened once)
  dscoll_ceso   dsfd_coll_ceso   output stage (bd / bh / bw registers)         x1 per slice (ONE master for ces0 and cesn)
  dscoll_cesp0  dsfd_coll_cesp0  five pass-through relay links, 169 b          ces0
  dscoll_cespn  dsfd_coll_cespn  five pass-through relay links, 129 b          cesn
  dscoll_cesc0  dsfd_coll_cesc0  slice 0 core (engine, landings, packer, 2 SRAM)
  dscoll_cescn  dsfd_coll_cescn  slice 1..3 core
Clusters (kind cluster, +define+OT_S81PH_COLL_CES_SPLIT): dscoll_ces0_sp / dscoll_cesn_sp, written only when every
child view exists (ref_tile gen reads the child LEFs).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
SRAM = "physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2"
SRC = ["rtl/dsrom_sys/s81_ph/coll/dsfd_coll_ceh.sv", "rtl/dsrom_sys/s81_ph/coll/dsfd_coll_cbh.sv",
       "rtl/dsrom_sys/s81_ph/coll/dsfd_coll_split.sv", "rtl/dsrom_sys/s81_ph/coll/ot_s81ph_skid2.sv",
       "rtl/dsrom_sys/s81_ph/ot_s81ph_rfifo.sv", "rtl/common/ot_link_credit.sv",
       "rtl/rom/ot_w15_rom_oneshot_px_acceptedpop.sv", "rtl/link/ot_fifo_sram_fwft.sv", "rtl/hdc/ot_hdc_fastfp.sv",
       "rtl/proto/ot_fp32_add_rne_pipe.sv", SRAM + "/ot_sram_1r1w_256x256_m2_r2c2_bb.v"]
BASE = ("+define+OT_S81PH_GBX_FMT1 +define+OT_S81PH_EP_PIPE2 +define+OT_S81PH_COLL_OQPIPE +define+OT_S81PH_COLL_QPIPE "
        "+define+OT_S81PH_COLL_SPLIT +define+OT_S81PH_COLL_RSL +define+OT_S81PH_COLL_CR +define+OT_S81PH_LANE_CR "
        "+define+OT_S81PH_COLL_PULL +define+OT_S81PH_COLL_TREP +define+OT_S81PH_COLL_CEH +define+OT_S81PH_COLL_CES_SPLIT")
STRUCT = ("flat lane-slice (22,816 sinks on one clock root; three routes missed hold) split into hardened leaves with "
          "their own roots under a wires-only parent: 4 FP32 lane leaves, 3 xl relay leaves, 1 pass-through relay leaf, "
          "1 output-stage leaf and the core (ces0 14,519 / cesn 13,919 sinks); one seam latency LSEAM in all four slices "
          "(lockstep asserted); every seam is leaf flop -> wire -> leaf flop")
# the bench is the 4-die collective composition built with BOTH split parents (4 ces0 + 12 cesn); a pass needs the split
# seams covered (tb coverage refusal).  Bench runs need the whole collective slab RTL: extra_paths.
EXTRA = ["rtl/dsrom_sys", "rtl/lib", "rtl/link", "rtl/common", "rtl/rom", "rtl/hdc", "rtl/proto",
         "physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2",
         "physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2",
         "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2"]


def bench(name, label, extra="", expect="pass"):
    b = {"name": name, "cmd": f"bash rtl/dsrom_sys/s81_ph/coll/run_coll_bench.sh {{RUN}}/bench {label} {BASE}"
                              + (" " + extra if extra else ""),
         "expect": expect, "threads": 8, "peak_ram_gb": 32, "needs": ["verilator"]}
    if expect == "fail":
        b["fail_regex"] = "TB_S81PH_COLL_SYS FAIL"
    else:
        b["pass_regex"] = "TB_S81PH_COLL_SYS PASS"
        b["min_count_regex"] = r"records (\d+) messages"      # the CYCLES line; the split-seam coverage is the tb's own refusal
    return b


EXACT = bench("exact_coll_ceh_split", "ceh_sp")
CS = bench("exact_coll_ceh_split_cstress", "ceh_sp_cs", "+define+OT_S81PH_COLL_CSTRESS")
SLOW = bench("exact_coll_ceh_split_slow", "ceh_sp_slow", "+define+OT_S81PH_COLL_CSTRESS -GTSR=1")
MUT = {
    "cesl": bench("neg_cesl_lane_sum", "neg_cesl", "+define+OT_S81PH_MUT_CESL", "fail"),
    "cesx": bench("neg_cesx_parity_swap", "neg_cesx", "+define+OT_S81PH_MUT_CESX", "fail"),
    "cesp": bench("neg_cesp_lane_swap", "neg_cesp", "+define+OT_S81PH_MUT_CESP", "fail"),
    "ceso": bench("neg_ceh_err_flag", "neg_ceh", "+define+OT_S81PH_MUT_CEH", "fail"),
    "orc": bench("neg_orc_slow", "neg_orc", "+define+OT_S81PH_MUT_ORC -GTSR=1", "fail"),
    "wfree2": bench("neg_wfree2", "neg_wfree2", "+define+OT_LINK_WFREE2_MUT", "fail"),
    "cel": bench("neg_cel_slice_swap", "neg_cel", "+define+OT_S81PH_MUT_CEL", "fail"),
    "nocr": bench("neg_nocredit_cstress", "neg_nocr_cs", "+define+OT_S81PH_COLL_CSTRESS +define+OT_S81PH_MUT_NOCREDIT", "fail"),
    "lockstep": bench("neg_lockstep_noassert", "neg_lockstep_na",
                      "+define+OT_S81PH_COLL_CSTRESS +define+OT_S81PH_MUT_LOCKSTEP +define+OT_S81PH_LOCKSTEP_NOASSERT", "fail"),
    "cov": bench("neg_coverage_no_passthrough", "neg_cov_nopt", "-GNPT=0", "fail"),
}

# ---- leaf table: outline (um), pin faces, benches.  Faces follow the cluster floorplan (see CLUSTER below):
#      xl relays on the W side (link in W, core side E), pass-through relay on the E side (link in E, core side W),
#      lanes N of the core (seam on their S face), the output stage at the S end of the E column (in N, out S).
LEAVES = {
    "cesl": dict(top="dsfd_coll_cesl", outline=(47.52, 47.52), pd=0.5, ram=24,
                 pins={"S": ["i_v", "i_d", "o_y", "o_yv", "o_ye", "o_pe"], "N": ["ck", "rs", "e_en"]},
                 benches=[EXACT, MUT["cesl"]]),
    "cesx": dict(top="dsfd_coll_cesx", outline=(47.52, 82.08), pd=0.5, ram=24,
                 pins={"W": ["i_v", "i_d", "i_cr"], "E": ["o_v", "o_d", "o_cr"], "N": ["ck", "rs", "e_en"]},
                 benches=[EXACT, MUT["cesx"], MUT["wfree2"]]),
    "ceso": dict(top="dsfd_coll_ceso", outline=(69.12, 34.56), pd=0.5, ram=24,
                 pins={"N": ["i_v", "i_d", "i_h"], "S": ["bw_v", "bw_d"], "W": ["ck", "rs", "pe_i"]},
                 benches=[EXACT, MUT["ceso"]]),
    "cesp0": dict(top="dsfd_coll_cesp0", outline=(64.8, 151.2), pd=0.5, ram=24,
                  pins={"E": ["i_v", "i_d", "i_cr"], "W": ["o_v", "o_d", "o_cr"], "N": ["ck", "rs"]},
                  benches=[EXACT, MUT["cesp"], MUT["wfree2"]]),
    "cespn": dict(top="dsfd_coll_cespn", outline=(64.8, 116.64), pd=0.5, ram=24,
                  pins={"E": ["i_v", "i_d", "i_cr"], "W": ["o_v", "o_d", "o_cr"], "N": ["ck", "rs"]},
                  benches=[EXACT, MUT["cesp"], MUT["wfree2"]]),
    "cesc0": dict(top="dsfd_coll_cesc0", outline=(218.16, 216.0), pd=0.5, ram=40, core=True,
                  pins={"N": ["q_v", "q_d", "q_cr", "e_en", "rank_i", "qp", "fv_i", "lf", "pe_o", "ck", "rs",
                              "ln_v", "ln_d", "ln_y", "ln_yv", "ln_ye", "ln_pe"],
                        "W": ["xl_v", "xl_d", "xl_cr"],
                        "E": ["ow_v", "ow_d", "ow_h", "pt_v", "pt_d", "pt_cr", "tx_v", "tx_d", "tx_rdy", "cr_i", "cr_o"],
                        "S": ["bw_cr"]},
                  benches=[EXACT, CS, SLOW, MUT["orc"], MUT["wfree2"]]),
    "cescn": dict(top="dsfd_coll_cescn", outline=(218.16, 216.0), pd=0.5, ram=40, core=True,
                  pins={"N": ["q_v", "q_d", "q_cr", "e_en", "rank_i", "qp", "fv_i", "lf", "pe_o", "ck", "rs",
                              "ln_v", "ln_d", "ln_y", "ln_yv", "ln_ye", "ln_pe"],
                        "W": ["xl_v", "xl_d", "xl_cr"],
                        "E": ["ow_v", "ow_d", "pt_v", "pt_d", "pt_cr", "tx_v", "tx_d", "tx_rdy", "cr_i", "cr_o"],
                        "S": ["bw_cr"]},
                  benches=[EXACT, CS, SLOW, MUT["orc"], MUT["wfree2"]]),
}
# MEASURED (pre_route_gate --remote, ORFS synthesis, 2026-10-13): std area um2 / sinks on the root
#   cesl 859 / 742   cesx 1,568 / 2,642   ceso 381 / 1,133   cesp0 4,060 / 6,837   cespn 3,126 / 5,237
#   cesc0 8,664 (+ 2 SRAM 14,194) / 14,482   cescn 8,211 / 13,801
# Outlines: util 46-50 % of the synthesized area, i.e. 52-55 % once recipe 2 adds its pin hold cells (~0.4 um2 per data
# pin: BUF -> HB4 -> BUF at every output, hold buffer + driver at every input); ceso is pin-bound (564 M5 pins per face).
# Core: the two SRAMs at the S and N ends (20 um channels, halo 5.4), one contiguous logic band between them (the closed
# flat ces0's arrangement); E face ordered ow | pt | tx to face the output leaf, the pass-through relay and the E pins.
CORE_MACROS_AT = [[22.464, 23.76], [22.464, 151.2]]
# disjoint ranges, one per port (PPL places a port as one group on the single M4 layer: three ports sharing 4-62 did not
# fit, PPL-0093 on ow_h, gate g2); M4 pins at 2 tracks = 0.096 um each, every range has >= 10 % spare
CORE_RANGES = {"ow_d": [4, 60], "ow_h": [61, 67], "ow_v": [67.5, 69], "pt_d": [71, 164], "pt_v": [165, 167],
               "pt_cr": [167.5, 169.5], "tx_d": [171, 190], "tx_v": [191, 193], "tx_rdy": [193.5, 195.5],
               "cr_i": [196, 199], "cr_o": [199.5, 202.5]}
OVR = HERE / "measured.json"      # optional per-leaf overrides {leaf: {"outline": [w, h], "pd": .., "route": {..}, "clock": ..}}


def leaf_spec(key, d, ovr):
    o = ovr.get(key, {})
    w, h = o.get("outline", d["outline"])
    s = {"name": f"dscoll_{key}", "top": d["top"], "kind": "tile", "sources": SRC, "clock_port": "ck",
         "reset_ports": ["rs"], "outline": {"w": w, "h": h}, "pins": d["pins"], "recipe": 2,
         "route": {"pd": o.get("pd", d["pd"]), "threads": 16 if d.get("core") else 8, "peak_ram_gb": d["ram"]},
         "structural_change": STRUCT,
         "job": {"owner": "Claude:s81-cesn-1013", "branch": "claude/s81-cesn-1013", "tag": "sp1",
                 "purpose": f"S81 collective lane-slice split: hardened leaf {d['top']} (M5 cap, recipe 2, registers at "
                            "the pins) of the wires-only clusters dsfd_coll_ces0 / dsfd_coll_cesn; bench = the 4-die "
                            "collective composition with both split parents + this leaf's mutant",
                 "benches": d["benches"], "extra_paths": EXTRA,
                 "views_to": f"physical/ref_tile/dscoll_{key}/views",
                 "record_to": f"results/rtl/ref_tile/dscoll_{key}"}}
    if d.get("core"):
        at = o.get("macros_at", CORE_MACROS_AT)
        ports = {p for v in d["pins"].values() for p in v}
        s["pin_ranges"] = {k: v for k, v in CORE_RANGES.items() if k in ports}
        s["macros"] = [{"view": SRAM, "count": 1, **({"at": at[i]} if at else {}), "orient": "R0"} for i in range(2)]
        # SRAM pin edge: 6.0 um M5 no-entry strip inside both vertical macro edges (added pre-GRT, removed post-DRT;
        # hrow5 r8 / lane_w cxea3 routed DRC 0 with 6.0 um), macro halo 5.4 um from recipe 2
        s["boundary_tcl"] = ["physical/qwen_die_masters/sram_edge_guard.tcl"]
        s["orfs_vars"] = {"OT_MEG_DEPTH_UM": "6.0"}
    for k in ("std_area_um2", "clock", "util"):
        if k in o:
            s[k] = o[k]
    if o.get("route"):
        s["route"].update(o["route"])
    return s


# ---- CLUSTER floorplan (um, origins on the 8.64 um track lattice; every channel and edge margin >= 20 um), the same
# for ces0 and cesn; outline 432.0 x 345.6:
#     W column  x 25.92            3 xl relays (47.52 x 82.08) at y 25.92 / 129.6 / 233.28          link in on the W face
#     core      x 95.04, y 25.92   218.16 x 216.0
#     lane row  y 267.84           4 lanes (47.52 sq) at x 95.04 / 164.16 / 233.28 / 302.4, seam on their S face
#     E column  x 336.96           output leaf (69.12 x 34.56) at y 25.92 (bw out on S), pass-through relay at y 86.4
# Seams (bits) and the parent's M6 (H) / M7 (V) tracks at 0.064 um pitch over the seam (cut = bits / tracks, <= 0.60):
#     xl relays -> core W face     990 b over 216 um  = 3,375 tracks   0.29
#     core E face -> E column      1,600 b (ces0: ow 564 + pt 855 + tx 181) over 216 um = 3,375 tracks   0.47
#     lanes <-> core N face        664 b + 187 b N-face pins over 218.16 um = 3,408 tracks   0.25
#     output leaf -> S face        564 b over 69.12 um = 1,080 M7 tracks   0.52 (M3 / M5 below the leaf are free too)
# Longest registered hop inside the cluster: N-face pins -> core N pins 104 um; core ow (E face, y 30-88) -> output
# leaf N pins ~90 um; W pins -> relay ~26 um.  All far below 500 um.
CL_W, CL_H = 432.0, 345.6
CL_CHILDREN = [("cesx", "*g_x?1?.u_x", 25.92, 25.92), ("cesx", "*g_x?2?.u_x", 25.92, 129.6),
               ("cesx", "*g_x?3?.u_x", 25.92, 233.28), ("CORE", "*u_c", 95.04, 25.92),
               ("cesl", "*g_ln?0?.u_l", 95.04, 267.84), ("cesl", "*g_ln?1?.u_l", 164.16, 267.84),
               ("cesl", "*g_ln?2?.u_l", 233.28, 267.84), ("cesl", "*g_ln?3?.u_l", 302.4, 267.84),
               ("ceso", "*u_o", 336.96, 25.92), ("CESP", "*u_p", 336.96, 86.4)]
CL_PINS = {"N": ["q_v", "q_d", "q_cr", "e_en", "rank_i", "qp", "fv_i", "lf", "pe_o", "ck", "rs"],
           "S": ["bw_v", "bw_d", "bw_cr"], "W": ["xl_v", "xl_d", "xl_cr"],
           "E": ["tx_v", "tx_d", "tx_rdy", "cr_i", "cr_o", "pt_v", "pt_d", "pt_cr"]}
# along-face pin ranges: every bus enters / leaves opposite the leaf pins it connects to
CL_RANGES = {"bw_d": [334, 396], "bw_v": [397, 399], "pe_i": [400, 403], "bw_cr": [200, 203],
             "pt_d": [86, 236], "pt_v": [237, 239], "pt_cr": [240, 242],
             "tx_d": [246, 270], "tx_v": [271, 273], "tx_rdy": [274, 276], "cr_i": [277, 280], "cr_o": [281, 284],
             "xl_d": [26, 316], "xl_v": [317, 319], "xl_cr": [320, 322]}


def view(key):
    return f"physical/ref_tile/dscoll_{key}/views/{LEAVES[key]['top']}"


def ioref(name):
    return f"physical/redesign_ds/coll_split/{name}_child_ioref.sdc"


def cluster_spec(s0):
    core, cesp = ("cesc0", "cesp0") if s0 else ("cescn", "cespn")
    name, top = ("dscoll_ces0_sp", "dsfd_coll_ces0") if s0 else ("dscoll_cesn_sp", "dsfd_coll_cesn")
    pins = {f: list(v) for f, v in CL_PINS.items()}
    if s0:
        pins["S"].append("pe_i")      # ces0 only: the other slices' error bits land in the output leaf (S end of the E column)
    kids = [{"view": view({"CORE": core, "CESP": cesp}.get(k, k)), "count": 1, "inst": inst, "at": [x, y]}
            for k, inst, x, y in CL_CHILDREN]
    return {"name": name, "top": top, "kind": "cluster", "sources": SRC, "defines": ["OT_S81PH_COLL_CES_SPLIT"],
            "clock_port": "ck", "reset_ports": ["rs"], "outline": {"w": CL_W, "h": CL_H}, "child_lattice_um": 8.64,
            "children": kids, "pins": pins, "pin_ranges": {k: v for k, v in CL_RANGES.items() if k in sum(pins.values(), [])},
            # E / W pins on M4 only, as the leaves' own E / W faces (straight M4 from the cluster edge to the relay pins): with
            # 'M4 M6' PPL placed the 845-b / 1,304-b groups in fallback mode outside their ranges (PPL-0102 x1000, PPL-0107)
            "route": {"pd": 0.3, "threads": 8, "peak_ram_gb": 32, "pin_h": "M4"}, "structural_change": STRUCT,
            # clock entry: the spine balances every child clock pin to that child's ROUTED boundary insertion R
            # (views/<child>/insertion.json tt.boundary.mean: core 322 / 312, relays 127-166, lane 114, output 98 ps);
            # the cluster has no register, so its IO reference is child clock pin + R (wires_only_ioref.py)
            "child_clock_ref": "boundary", "sdc_extra": [ioref(name)], "boundary_tcl": [ioref(name)],
            "slot_change_request": "el1011-s81die.log 2026-10-13 07:37 + 17:40 (s81-cesn): sp_collective/ce_s* slot "
                                   "302.4 x 341.28 (flat lane-slice, M5) -> 432.0 x 345.6 hardened cluster of M5 leaves "
                                   "(parent routes M6 / M7 over them, PG M7, strap M8); pin faces N q / W xl / E tx+pt / S bw",
            **({"reroute_reason": {"kind": "rtl_change",
                                   "why": "the four lane-slices of a collective run one seam latency LSEAM in lockstep "
                                          "(asserted): the split cesn (flat cesn missed hold in three routes at 22.8k "
                                          "sinks / root) needs ces0 built from the same leaves; the closed flat ces0 "
                                          "(dscoll_ces0_cxsp d8b0f7a0e) has no seam stage and cannot pair with it"}}
               if s0 else {}),
            "why_floorplan": "wires-only parent: 10 hard leaves, no register and no logic of its own; outline set by the "
                             "leaves and their >= 20 um channels (see gen_specs.py CLUSTER)",
            "job": {"owner": "Claude:s81-cesn-1013", "branch": "claude/s81-cesn-1013", "tag": "sp1",
                    "purpose": f"S81 collective lane-slice {top} as a hardened cluster of the split leaves (wires only)",
                    "benches": [EXACT, CS, SLOW, *MUT.values()], "extra_paths": EXTRA,
                    "views_to": f"physical/ref_tile/{name}/views", "record_to": f"results/rtl/ref_tile/{name}"}}


def main():
    ovr = json.loads(OVR.read_text()) if OVR.exists() else {}
    for key, d in LEAVES.items():
        p = HERE / f"dscoll_{key}.json"
        p.write_text(json.dumps(leaf_spec(key, d, ovr), indent=1) + "\n")
        print("wrote", p.relative_to(ROOT))
    for s0 in (True, False):
        c = cluster_spec(s0)
        p = HERE / f"{c['name']}.json"
        p.write_text(json.dumps(c, indent=1) + "\n")
        missing = [k["view"] for k in c["children"] if not (ROOT / k["view"]).is_dir()]
        print("wrote", p.relative_to(ROOT), f"(kit NOT generable yet: {len(set(missing))} child views missing)" if missing else "")
        if not missing:      # the IO reference literals come from the child views: regenerate with them
            import subprocess
            subprocess.run([sys.executable, str(ROOT / "tools/ref_tile/wires_only_ioref.py"), str(p), str(ROOT / ioref(c["name"]))], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

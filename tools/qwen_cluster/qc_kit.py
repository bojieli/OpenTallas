#!/usr/bin/env python3
"""ref_tile spec for qfd_c_b16_dv (Q-CLUSTER).  Inputs: results/arch/qwen_cluster_1017/cluster_contract_dv.json and
relay_sites_dv.json (qc_gen.py).  Two modes:

  qc_kit.py diag   -> tools/ref_tile/specs_qcluster/qfd_c_b16_dv_diag.json: children = the A0 STAND-IN abstracts
                      (physical/ref_tile/qfd_c_b16_dv_diag/a0_standin, a0_standin.py): gates only, never submitted/bound
  qc_kit.py real --nk VIEW --nl VIEW -> qfd_c_b16_dv.json: children = the CLOSED native-PASS A0 c1 views

Clock: four quadrant CTS roots ck_sw (core) / ck_se / ck_nw / ck_ne ("hybrid_entries", every clock port a CTS root,
related 1:1, each boundary port in the domain of the quadrant holding its pin register).  Boundary: every data pin is
registered in the S / N strip by the generated RTL (flop-first / flop-last), so pin_regs are off with that reason,
hold_budget "die", no inhold / outhold.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCH = ROOT / "results/arch/qwen_cluster_1017"
STANDIN = "physical/ref_tile/qfd_c_b16_dv_diag/a0_standin"
FABRIC_SRC = ["rtl/physical/qcluster/qfd_q3h_stn.sv", "rtl/physical/qcluster/qfd_c_b16_dv_fabric.sv",
              "rtl/physical/qcluster/qfd_c_b16_dv.sv", "rtl/qwen_sys/dvm_20261014/ot_qfd_xslice_slots.sv",
              "rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv", "rtl/hdc/ot_hdc_delay.sv"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["diag", "real"])
    ap.add_argument("--nk")
    ap.add_argument("--nl")
    a = ap.parse_args()
    C = json.loads((ARCH / "cluster_contract_dv.json").read_text())
    W, H = C["outline_um"]["w"], C["outline_um"]["h"]
    nkm, nlm = C["a0"]["nk"], C["a0"]["nl"]
    if a.mode == "diag":
        nk, nl = f"{STANDIN}/{nkm}", f"{STANDIN}/{nlm}"
        name = "qfd_c_b16_dv_diag"
        bb = [f"{STANDIN}/a0_rr_bb.v"]
    else:
        if not (a.nk and a.nl):
            raise SystemExit("real mode needs --nk / --nl CLOSED native-PASS A0 views")
        nk, nl, name, bb = a.nk, a.nl, "qfd_c_b16_dv", []
    tiles = []
    spare = tuple(C["tree"]["nl_slot"])
    for t in C["tiles"]:
        c, r = (int(v) for v in t["inst"][4:].split("_"))
        tiles.append(dict(view=nl if (c, r) == spare else nk, count=1, inst=t["inst"], at=t["at"], orient=t["orient"],
                          at_exact=True))
    ports = C["ports"]
    faces = {"N": [], "S": [], "E": [], "W": []}
    for p in ports:
        faces[p["face"]].append(p["port"])
    xt = C["quadrant_seams"]["x"]
    dom = {q: dict(ratio=[1, 1], ports=[f"ck_{q}"], inputs=[], outputs=[]) for q in ("sw", "se", "nw", "ne")}
    for p in ports:
        n = p["port"]
        if n.startswith("ck_"):
            continue
        q = ("s" if p["face"] == "S" else "n") + ("w" if (p["range_um"][0] + p["range_um"][1]) / 2 <= xt else "e")
        d = "outputs" if n.startswith(("bco", "rs_o", "tie_")) or n == "rs" else "inputs"
        dom[q][d].append(n)
    domains = {"core": dom.pop("sw")} | {f"q_{k}": v for k, v in dom.items()}
    spec = dict(
        name=name, top="qfd_c_b16_dv", kind="cluster",
        diagnostic=a.mode == "diag",
        sources=bb + FABRIC_SRC,
        params={}, clock="spine", child_clock_ref="boundary",
        clock_port="ck_sw", clock_ports=["ck_sw", "ck_se", "ck_nw", "ck_ne"],
        orfs_vars={"OT_SPINE_PORTS": "ck_sw,ck_se,ck_nw,ck_ne", "OT_SPINE_MACRO_LEAF": "1"},
        sdc_extra=["physical/qcluster/qfd_c_b16_dv_quadrants.sdc"],
        reset_ports=["rst_n"],
        outline=dict(w=W, h=H, exact=True), child_lattice_um=43.2,
        children=tiles, macros=[],
        pins=faces,
        pin_ranges={p["port"]: p["range_um"] for p in ports},
        pin_layers={p["port"]: p["layer"] for p in ports},
        route=dict(pd=0.5, threads=16, peak_ram_gb=192, pin_v="M5", pin_h="M4 M6", macro_halo_um=5.4),
        cluster_level=2, recipe=4, hold_budget="die", inhold=False, outhold=False,
        pin_regs=dict(enable=False, reason="qc_gen.py RTL registers every data pin in the S / N strip (bc / rs_i entry "
                                           "flops, bco / rs / rs_o exit flops, rst_n pin register); cid / far are static "
                                           "straps from the instance's own tie cells"),
        relay_sites="results/arch/qwen_cluster_1017/relay_sites_dv.json",
        structural_change="Q-CLUSTER qfd_c_b16_dv (SPEC.md): CB cluster with A/T/B corridors 129.6 um (cut 1.79 -> 0.90 "
                          "worst, trunks <= 0.54), four quadrant clock roots, registered pins hold_budget die, DV "
                          "rs_i -> rs_o feedthrough (14 edges) in T.",
        job=dict(owner="Claude:Q-CLUSTER", branch="claude/qcluster-1017", tag="dv0" if a.mode == "real" else "diag0",
                 purpose="qfd_c_b16_dv cluster (dv2r8f, 48 instances)", submit=a.mode == "real",
                 benches=[dict(name="qcluster_fabric", cmd="bash tools/qwen_cluster/bench.sh bench_out",
                               expect="pass", pass_regex="BENCH_EXIT 0", threads=8, peak_ram_gb=12)]))
    out = ROOT / "tools/ref_tile/specs_qcluster" / f"{name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, indent=1) + "\n")
    print(out)


if __name__ == "__main__":
    main()

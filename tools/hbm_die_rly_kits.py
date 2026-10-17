#!/usr/bin/env python3
"""Relay family of the HBM R25GQ die as real hard tiles (tools/ref_tile): one master per WIDTH CLASS and flow.

The die generator (tools/hbm_accel_die_fp.py) places a register stage (hfd_stn_q*, hfd_stn_<n>, hfd_stn_r*: ports a,
b, ck, rst) wherever a region-clocked bus exceeds the reach.  Each is a generated outline with an interim timing model
and its own master name (v12: 1,281 masters for 7,025 instances), the largest group of placeholders in the die case.
A per-instance master cannot be hardened; a WIDTH CLASS can:

    hbfd_rly_<Wc>_<flow>     Wc in CLASSES, flow in WE / EW / SN / NS (data in on the first face, out on the second)

  * a bus of W bits takes the smallest class >= W (spare inputs tied low, spare outputs open at the die top);
  * a bus wider than the largest class takes ceil(W / 1136) masters side by side along the flow (a 2,068-b x trunk =
    2 x hbfd_rly_1136), each on its own leaf of the region clock tree;
  * pins: one layer a face at 2 tracks a bit under the M5 cap (M4 on E / W, M5 on N / S), so the data face is
    Wc x 0.096 um + 4.32 um long (the generator's station face is 0.048 um a bit + 20 um, i.e. one pin on EVERY track
    of one layer: not buildable; this is the slot change the family asks of the next preset), 21.6 um deep (N-S strips
    of the classes >= 304 b: 23.76 um, see depth()); the v13 preset r25gqn_v13 places its stations at these outlines;
  * ck / rs on a third face; flops at the pins; minimum output delay built at the output pins (outhold).

NOT in this family (reported by --map): forwarded-clock link stages (a, b, rst and no ck: the clock rides in the bus,
ot_fwd_link_stage W512 slices), multicast / gather / control-distribution / mesochronous stations (own function), the
lane-group stations, and the clock / reset tree pairs hfd_ckb + hfd_rrl (the die's own clock tree cells).

Usage: hbm_die_rly_kits.py [--gen] [--map MODEL.pkl --out results/arch/hier_contract_1011/r25gq_v12_relay_family]
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import pickle
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = "rtl/hbm_accel/die_glue"
SPECS = "tools/ref_tile/specs_hbmrly"
CLASSES = (8, 48, 136, 304, 624, 1136)
FLOWS = ("WE", "EW", "SN", "NS")
DEPTH, LAT, PIN_UM, MARGIN = 21.6, 2.16, 0.096, 4.32


def face_len(w: int) -> float:
    """data face length: w pins at 2 tracks (0.096 um) + 2 x 2.16 um end margins, on the 2.16-um lattice, >= 21.6"""
    return max(DEPTH, round(math.ceil((w * PIN_UM + MARGIN) / LAT - 1e-9) * LAT, 2))


def depth(w: int, flow: str) -> float:
    """strip depth along the flow.  v2 (10-13): the N-S strips of the classes >= 304 b are 23.76 um deep -- their v1
    kits (recipe 2: flops and hold cells at both pin faces) were 61.1-61.5 % utilised at 21.6 um (FLOORPLAN_MARGIN,
    limit 60 %); +2.16 um gives 54-56 %.  The E-W strips of those classes (recipe 1 + outhold) and every class
    <= 136 b closed at 21.6 um and stand."""
    return 23.76 if (flow in ("SN", "NS") and w >= 304) else DEPTH


def tag(w: int, flow: str) -> str:
    return "v2" if depth(w, flow) != DEPTH else "v1"


def outline(w: int, flow: str) -> dict:
    ln = face_len(w)
    return {"w": depth(w, flow), "h": ln} if flow in ("WE", "EW") else {"w": ln, "h": depth(w, flow)}


def master(w: int, flow: str) -> str:
    return f"hbfd_rly_{w}_{flow}"


def klass(w: int) -> int:
    return next(c for c in CLASSES if c >= w)


def compose(w: int) -> list:
    """the class masters one W-bit register stage is built from (fewest masters, then fewest spare bits)"""
    n = math.ceil(w / CLASSES[-1])
    per = math.ceil(w / n)
    return [klass(per)] * n


def spec(w: int, flow: str, owner: str, branch: str) -> dict:
    fi, fo = flow
    cf = {"WE": "S", "EW": "S", "SN": "W", "NS": "W"}[flow]
    mst = master(w, flow)
    name = mst.lower()
    o = outline(w, flow)
    pins = {f: [] for f in "NSEW"}
    pins[fi].append("i")
    pins[fo].append("o")
    pins[cf] += ["ck", "rs"]
    # E-W strips wider than 136 b (21.6 um of core width between two pin faces 2.8 pins a row tall): kit recipe 2 fixes
    # the flops AND the hold cells at both faces, nothing is left to place and global placement diverges (pre-route gate
    # 10-13: target density -1.6, GPL-0305 on 304 / 624 / 1136 WE; the N-S strips pass).  They take recipe 1 + outhold,
    # the configuration the S81 E-W relay of this shape closed with (dsfd_rly_266_WE, 21.6 x 30.24).
    tall = flow in ("WE", "EW") and w > 136
    return {
        "name": name, "top": mst, "kind": "tile",
        "sources": ["rtl/lib/ot_rst_relay.sv", f"{RTL}/ot_hbm_rly.sv", f"{RTL}/hbfd_rly_masters.sv"],
        "params": {}, "clock_port": "ck", "reset_ports": ["rs"],
        "outline": o, "macros": [],
        "pins": {f: p for f, p in pins.items() if p},
        "outhold": True, **({"recipe": 1} if tall else {}),
        # 2.7-um M5 PG pitch on the 21.6-um side so every net has >= 2 full-length stripes over > 50 % of the tile
        # (child_lint (b); the S81 relay family closed at this pitch)
        "route": {"pd": 0.45, "threads": 4, "peak_ram_gb": 8, "m5_pg_pitch": 2.7},
        "job": {
            "owner": owner, "branch": branch, "tag": tag(w, flow),
            "purpose": f"HBM R25GQ die relay family: {mst}, one register stage of width class {w} b (in {fi} / out {fo}, "
                       f"ck + rs {cf}), {o['w']} x {o['h']} um, M5 cap, pins at 2 tracks on one layer a face, flops at "
                       "the pins, minimum output delay at the pin (outhold); replaces the generated per-instance relay "
                       "station placeholders of its class (tools/hbm_die_rly_kits.py --map)",
            "benches": [
                {"name": "exact_words", "cmd": f"bash {RTL}/test/bench_rly.sh pass {mst} {w} {{RUN}}/bench_p",
                 "expect": "pass", "pass_regex": "RLY_BENCH PASS 0 errors in 20000 words", "threads": 2, "peak_ram_gb": 4,
                 "needs": ["verilator"]},
                {"name": "neg_bit0_mutant", "cmd": f"bash {RTL}/test/bench_rly.sh mut {mst} {w} {{RUN}}/bench_m",
                 "expect": "fail", "fail_regex": "RLY_BENCH FAIL", "threads": 2, "peak_ram_gb": 4, "needs": ["verilator"]},
            ],
            "views_to": f"physical/ref_tile/{name}/views",
            "record_to": f"results/rtl/ref_tile/{name}",
        },
    }


def write_family(owner: str, branch: str, flows=FLOWS) -> list:
    v = ["// GENERATED by tools/hbm_die_rly_kits.py: the HBM R25GQ die relay family, one module per width class and flow.",
         "`default_nettype none"]
    out = []
    (ROOT / SPECS).mkdir(parents=True, exist_ok=True)
    for w in CLASSES:
        for fl in FLOWS:
            v.append(f"module {master(w, fl)} (input wire ck, input wire rs, input wire [{w - 1}:0] i, output wire [{w - 1}:0] o);")
            v.append(f"    ot_hbm_rly #(.W({w})) u (.ck(ck), .rs(rs), .i(i), .o(o));")
            v.append("endmodule")
            if fl in flows:
                s = spec(w, fl, owner, branch)
                p = ROOT / SPECS / f"{s['name']}.json"
                p.write_text(json.dumps(s, indent=1) + "\n")
                out.append(p)
    v.append("`default_nettype wire")
    (ROOT / RTL / "hbfd_rly_masters.sv").write_text("\n".join(v) + "\n")
    return out


# ------------------------------------------------------------------------------------------------ F1 forwarded clock
# H-NETLIST 2026-10-16 (owner decision: neighbour-relative clocking; form F1 agreed with DIE-CLOCK): hbfd_rly_<W>_<flow>_fc
# = the same register stage (ot_hbm_rly, unchanged) on clk_in + clk_out (one kept BUFx12f) + the same buffer on every
# o bit (rtl/hbm_accel/die_glue/ot_hbm_rly_fc.sv).  Pins: i + clk_in on the upstream face, o + clk_out on the
# downstream face (o[k] opposite i[k]; the clock pin at the face centre, between the data pins), rs on the side face.
# Face rule <= 6 pins/um (coordinator HBM die audit: rly_624 at 10.1/um -> face >= 104 um).
FC_CLASSES = (48, 624)
FC_PINS_PER_UM = 6.0
FC_DIR = "physical/hbm_rly_fc"
FC_SPECS = "tools/ref_tile/specs_hbmrly_fc"


def fc_face_len(w: int) -> float:
    need = max(face_len(w), (w + 1) / FC_PINS_PER_UM + 2 * MARGIN)
    return max(DEPTH, round(math.ceil(need / LAT - 1e-9) * LAT, 2))


def fc_outline(w: int, flow: str) -> dict:
    ln = fc_face_len(w)
    return {"w": DEPTH, "h": ln} if flow in ("WE", "EW") else {"w": ln, "h": DEPTH}


def fc_master(w: int, flow: str) -> str:
    return f"hbfd_rly_{w}_{flow}_fc"


def fc_pins_tcl(w: int, flow: str) -> str:
    """exact pin plan: data bits evenly over the face (k-th i opposite k-th o), clk_in / clk_out at the face centre
    between bits w/2-1 and w/2, rs at the side-face centre.  N/S faces M5 (x = 0.012 + k 0.048), W/E faces M4."""
    o = fc_outline(w, flow)
    W, H = o["w"], o["h"]
    fi, fo = flow
    side = {"WE": "S", "EW": "S", "SN": "W", "NS": "W"}[flow]
    L = W if fi in "NS" else H
    names = [f"i_{k}" for k in range(w // 2)] + ["CK"] + [f"i_{k}" for k in range(w // 2, w)]
    step = (L - 2 * MARGIN) / (len(names) - 1)
    out = [f"# generated by tools/hbm_die_rly_kits.py --fc: {fc_master(w, flow)} pin plan ({W} x {H} um; "
           f"{len(names)} pins a data face, {step:.3f} um pitch = {1 / step:.2f} pins/um)"]

    def put(name, face, t):
        if face in "NS":
            lay, x, y, sz = "M5", round(round((t - 0.012) / 0.048) * 0.048 + 0.012, 3), (H if face == "N" else 0.0), "0.024 0.192"
        else:
            lay, x, y, sz = "M4", (W if face == "E" else 0.0), round(round((t - 0.036) / 0.048) * 0.048 + 0.036, 3), "0.192 0.024"
        out.append(f"place_pin -pin_name {{{name}}} -layer {lay} -location {{{x:.3f} {y:.3f}}} -pin_size {{{sz}}} -force_to_die_boundary")

    for j, nm in enumerate(names):
        t = MARGIN + j * step
        if nm == "CK":
            put("clk_in", fi, t); put("clk_out", fo, t)
        else:
            k = int(nm[2:])
            put(f"i[{k}]", fi, t); put(f"o[{k}]", fo, t)
    put("rs", side, (H if side in "WE" else W) / 2)
    return "\n".join(out) + "\n"


def fc_spec(w: int, flow: str, owner: str, branch: str) -> dict:
    fi, fo = flow
    side = {"WE": "S", "EW": "S", "SN": "W", "NS": "W"}[flow]
    mst = fc_master(w, flow)
    name = mst.lower()
    o = fc_outline(w, flow)
    pins = {fi: ["i", "clk_in"], fo: ["o", "clk_out"], side: ["rs"]}
    t = f"rtl/hbm_accel/die_glue/test/bench_rly_fc.sh"
    return {
        "name": name, "top": mst, "kind": "tile",
        "sources": ["rtl/lib/ot_rst_relay.sv", f"{RTL}/ot_hbm_rly.sv", f"{RTL}/ot_hbm_rly_fc.sv", f"{RTL}/hbfd_rly_fc_masters.sv"],
        "params": {}, "clock_port": "clk_in", "reset_ports": ["rs"],
        "boundary_tcl": [f"{FC_DIR}/fc_clock.tcl"], "sdc_extra": [f"{FC_DIR}/fc_clock.tcl"],
        "pre_cts_extra": [f"{FC_DIR}/fc_pre_cts.tcl"],
        "outline": dict(o, exact=True), "macros": [], "layer_cap": "M5",
        "pins": pins, "io_tcl": f"{FC_DIR}/pins/{mst}.tcl",
        "recipe": 3, "inhold": False, "outhold": False,
        "pin_regs": {"enable": False, "reason": "F1 relay = ONE register stage at the pins by definition: i is captured by the "
                     "stage register, o leaves it through the matched forwarding buffer; a pin register would add a cycle "
                     "per hop and break the clk_out / o driver match (DIE-CLOCK F1)"},
        "orfs_vars": {"PRE_FLOORPLAN_TCL": f"/src/{FC_DIR}/fc_dont_touch.tcl"},
        "route": {"pd": 0.45, "threads": 4, "peak_ram_gb": 8, "m5_pg_pitch": 2.7},
        "structural_change": f"F1 forwarded-clock variant of {master(w, flow)} (owner neighbour-relative clocking; DIE-CLOCK "
                             f"form F1): same ot_hbm_rly stage on clk_in, clk_out + every o through one kept BUFx12f each, "
                             f"data face {fc_face_len(w)} um (<= 6 pins/um; was {face_len(w)}), outline {o['w']} x {o['h']}",
        "job": {
            "owner": owner, "branch": branch, "tag": "fc1",
            "purpose": f"HBM die F1 forwarded-clock relay {mst}: register on clk_in, clk_out = kept BUFx12f, o through the "
                       f"same cell on the downstream face beside clk_out; i/clk_in upstream ({fi}), o/clk_out downstream "
                       f"({fo}), rs {side}; {o['w']} x {o['h']} um, M5 cap",
            "extra_paths": [FC_DIR, t, f"{RTL}/test/bench_rly.sh"],
            "benches": [
                {"name": "fc_words", "cmd": f"bash {t} pass {w} {flow} {{RUN}}/bench_p", "expect": "pass",
                 "pass_regex": "RLY_FC_BENCH PASS 0 errors 0 clock_errors 0 chain_errors in 20000 words",
                 "min_count_regex": "RLY_FC_BENCH PASS 0 errors 0 clock_errors 0 chain_errors in (\\d+) words",
                 "threads": 2, "peak_ram_gb": 4, "needs": ["verilator"]},
                {"name": "neg_bit0_mutant", "cmd": f"bash {t} mut {w} {flow} {{RUN}}/bench_m", "expect": "fail",
                 "fail_regex": "RLY_FC_BENCH FAIL [1-9]", "threads": 2, "peak_ram_gb": 4, "needs": ["verilator"]},
                {"name": "neg_clkout_mutant", "cmd": f"bash {t} ckmut {w} {flow} {{RUN}}/bench_c", "expect": "fail",
                 "fail_regex": "RLY_FC_BENCH FAIL \\d+ errors [1-9]\\d* clock_errors", "threads": 2, "peak_ram_gb": 4,
                 "needs": ["verilator"]},
            ],
            "views_to": f"physical/ref_tile/{name}/views",
            "record_to": f"results/rtl/ref_tile/{name}",
        },
    }


def write_fc_family(owner: str, branch: str, classes=FC_CLASSES, flows=FLOWS) -> list:
    v = ["// GENERATED by tools/hbm_die_rly_kits.py --fc: F1 forwarded-clock HBM die relay masters (ot_hbm_rly_fc).",
         "`default_nettype none"]
    for w in CLASSES:
        for fl in FLOWS:
            v.append(f"module {fc_master(w, fl)} (input wire clk_in, input wire rs, input wire [{w - 1}:0] i, "
                     f"output wire [{w - 1}:0] o, output wire clk_out);")
            v.append(f"    ot_hbm_rly_fc #(.W({w})) u (.clk_in(clk_in), .rs(rs), .i(i), .o(o), .clk_out(clk_out));")
            v.append("endmodule")
    v.append("`default_nettype wire")
    (ROOT / RTL / "hbfd_rly_fc_masters.sv").write_text("\n".join(v) + "\n")
    out = []
    (ROOT / FC_SPECS).mkdir(parents=True, exist_ok=True)
    (ROOT / FC_DIR / "pins").mkdir(parents=True, exist_ok=True)
    for w in classes:
        for fl in flows:
            (ROOT / FC_DIR / "pins" / f"{fc_master(w, fl)}.tcl").write_text(fc_pins_tcl(w, fl))
            s = fc_spec(w, fl, owner, branch)
            p = ROOT / FC_SPECS / f"{s['name']}.json"
            p.write_text(json.dumps(s, indent=1) + "\n")
            out.append(p)
    return out


def relay_map(model: dict) -> dict:
    """every waypoint master of a light die model ({insts: {name: (master, kind, x, y, w, h, orient)}, buses}) against
    the family: region-clocked a / b register stages -> class composition; everything else by group"""
    I, B = model["insts"], model["buses"]
    if not isinstance(I, dict):
        I = {i.name: (i.master, i.kind, i.x, i.y, i.w, i.h, i.orient) for i in I}
    wp = {n: v for n, v in I.items() if v[1] == "waypoint"}
    ports = collections.defaultdict(dict)
    for _bid, _cls, bits, eps in B:
        for e in eps:
            if e[0] in wp:
                ports[e[0]][e[1]] = bits
    fam = collections.defaultdict(lambda: dict(instances=0, masters=set(), tiles=0, bits=0, class_bits=0, gen_um2=0.0, fam_um2=0.0))
    other = collections.defaultdict(lambda: dict(instances=0, masters=set()))
    widths = collections.Counter()
    for n, v in wp.items():
        p = ports.get(n, {})
        if {"a", "b"} <= set(p) and set(p) <= {"a", "b", "ck", "rst"} and "ck" in p and p["a"] == p["b"]:
            w = p["a"]
            comp = compose(w)
            flow_h = v[5] >= v[4]          # a strip taller than wide carries an E-W flow
            r = fam[comp[0]]
            r["instances"] += 1
            r["masters"].add(v[0])
            r["tiles"] += len(comp)
            r["bits"] += w
            r["class_bits"] += sum(comp)
            r["gen_um2"] += v[4] * v[5]
            o = outline(comp[0], "WE" if flow_h else "SN")
            r["fam_um2"] += len(comp) * o["w"] * o["h"]
            widths[w] += 1
            continue
        if v[0] in ("hfd_ckb", "hfd_rrl"):
            g = "clock / reset tree pair (hfd_ckb + hfd_rrl): the die clock tree's own cells"
        elif {"a", "b"} <= set(p) and set(p) <= {"a", "b", "rst"}:
            g = "forwarded-clock link stage (a, b, rst; clock in the bus): ot_fwd_link_stage slices, not this family"
        elif {"a", "b"} <= set(p) and set(p) <= {"a", "b", "ck", "rst"}:
            g = "register stage with a != b bits (adds / drops forwarded-clock copies): link-end stage, not this family"
        elif any(re.match(r"[tf]_lg", q) for q in p):
            g = "lane-group station / relay bank (taps): VM lane-group family"
        elif re.match(r"hfd_(mcast|gath|cdist|meso)", v[0]):
            g = "multicast / gather / control-distribution / mesochronous station (own function, own views)"
        else:
            g = "other waypoint (" + re.sub(r"\d+.*$", "", v[0]) + ")"
        other[g]["instances"] += 1
        other[g]["masters"].add(v[0])
    cov = sum(r["instances"] for r in fam.values())
    return dict(
        waypoint_instances=len(wp), waypoint_masters=len({v[0] for v in wp.values()}),
        family=dict(classes=list(CLASSES), flows=list(FLOWS), kits=len(CLASSES) * len(FLOWS),
                    covered_instances=cov, covered_generated_masters=len(set().union(*[r["masters"] for r in fam.values()])) if fam else 0,
                    family_tiles=sum(r["tiles"] for r in fam.values()),
                    distinct_widths=len(widths), widest=max(widths) if widths else 0,
                    generated_station_mm2=round(sum(r["gen_um2"] for r in fam.values()) / 1e6, 4),
                    family_tile_mm2=round(sum(r["fam_um2"] for r in fam.values()) / 1e6, 4),
                    spare_bit_fraction=round(1 - sum(r["bits"] for r in fam.values()) / max(1, sum(r["class_bits"] for r in fam.values())), 4),
                    by_class={str(c): dict(instances=r["instances"], generated_masters=len(r["masters"]), family_tiles=r["tiles"],
                                           bits=r["bits"], class_bits=r["class_bits"], face_um=face_len(c),
                                           generated_um2=round(r["gen_um2"]), family_um2=round(r["fam_um2"]))
                              for c, r in sorted(fam.items())}),
        not_family={g: dict(instances=r["instances"], masters=len(r["masters"])) for g, r in
                    sorted(other.items(), key=lambda t: -t[1]["instances"])})


def markdown(rec: dict, title: str) -> str:
    f = rec["family"]
    o = [f"# {title}", "",
         f"Waypoints in the die model: {rec['waypoint_instances']:,} instances, {rec['waypoint_masters']:,} generated masters.", "",
         f"**Relay family `hbfd_rly_<Wc>_<flow>`: {len(f['classes'])} width classes x {len(f['flows'])} flows = {f['kits']} kits "
         f"cover {f['covered_instances']:,} region-clocked register stages ({f['covered_generated_masters']:,} generated masters, "
         f"{f['distinct_widths']} distinct widths up to {f['widest']:,} b) with {f['family_tiles']:,} family tiles.**", "",
         f"Area: generated station outlines {f['generated_station_mm2']} mm2 -> family tiles {f['family_tile_mm2']} mm2 "
         f"(pins at 2 tracks a bit on one layer: the data face is Wc x 0.096 + 4.32 um; the generator's 0.048 um a bit "
         f"puts a pin on every track). Spare (tied) bits: {f['spare_bit_fraction'] * 100:.1f} % of the class bits.", "",
         "| class b | data face um | stages | generated masters | family tiles | bits carried | class bits | generated um2 | family um2 |",
         "|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for c, r in f["by_class"].items():
        o.append(f"| {c} | {r['face_um']} | {r['instances']:,} | {r['generated_masters']:,} | {r['family_tiles']:,} | {r['bits']:,} | "
                 f"{r['class_bits']:,} | {r['generated_um2']:,} | {r['family_um2']:,} |")
    o += ["", "## Waypoints outside the family", "", "| group | instances | generated masters |", "|---|---:|---:|"]
    for g, r in rec["not_family"].items():
        o.append(f"| {g} | {r['instances']:,} | {r['masters']:,} |")
    return "\n".join(o) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gen", action="store_true", help="run ref_tile.py gen on every spec written")
    ap.add_argument("--flows", default="WE,SN", help="flows that get a spec now (the masters file always holds all four)")
    ap.add_argument("--owner", default="Claude:hbmdie-lead")
    ap.add_argument("--branch", default="claude/hbm-native-die-1013")
    ap.add_argument("--map", type=Path, help="pickled light die model: write the family coverage map")
    ap.add_argument("--out", type=Path, help="--map output stem (.json and .md)")
    ap.add_argument("--title", default="R25GQ r25gqn_v12: relay family coverage")
    ap.add_argument("--fc", action="store_true", help="F1 forwarded-clock family (hbfd_rly_<W>_<flow>_fc) instead")
    a = ap.parse_args()
    if a.fc:
        specs = write_fc_family(a.owner, a.branch, flows=tuple(x for x in a.flows.split(",") if x))
        print(f"F1: {len(CLASSES) * len(FLOWS)} masters in {RTL}/hbfd_rly_fc_masters.sv, {len(specs)} specs in {FC_SPECS}")
        if a.gen:
            for p in specs:
                r = subprocess.run([sys.executable, str(ROOT / "tools/ref_tile/ref_tile.py"), "gen", str(p)],
                                   capture_output=True, text=True, cwd=ROOT)
                t = (r.stdout + r.stderr).strip().splitlines()
                print(p.stem, "gen rc", r.returncode, t[-1][:300] if t else "")
        return 0
    specs = write_family(a.owner, a.branch, tuple(x for x in a.flows.split(",") if x))
    print(f"{len(CLASSES) * len(FLOWS)} masters in {RTL}/hbfd_rly_masters.sv, {len(specs)} specs in {SPECS}")
    if a.gen:
        for p in specs:
            r = subprocess.run([sys.executable, str(ROOT / "tools/ref_tile/ref_tile.py"), "gen", str(p)],
                               capture_output=True, text=True, cwd=ROOT)
            t = (r.stdout + r.stderr).strip().splitlines()
            print(p.stem, "gen rc", r.returncode, t[-1][:200] if t else "")
    if a.map:
        rec = relay_map(pickle.loads(a.map.read_bytes()))
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.with_suffix(".json").write_text(json.dumps(rec, indent=1) + "\n")
        a.out.with_suffix(".md").write_text(markdown(rec, a.title))
        print(json.dumps({k: v for k, v in rec["family"].items() if k != "by_class"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

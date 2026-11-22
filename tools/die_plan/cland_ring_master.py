#!/usr/bin/env python3
"""KV-RINGMAC-R1 11-21: hard landing-ring master cores (CLAND-MACRO-1 form), restored as a tool.

CLAND-MACRO-1 (11-14) and KV-HUBC-SPLIT / KV-D23-HUBC (11-17/18) hardened soft `ot_dp_clk_landing_cas` rings as signed
child cores with a scratch script (mkmacro.py, never committed, now gone from every host).  KV-PLAN-R2 re-made the
freeze inputs of six kv3_hub_C masters from plan rows (d27b/hubc_tools/prep_hubc.py).  This tool is that generator,
reconstructed from the signed views it produced (pins.json / config.json of kv_cland_w129/144/145/175_ew, w259_ns,
w300_ew, w549_ew: test_cland_ring_master.py reproduces their outline and every pin), for any width, NARROW included.

One master per exact parameter set and face class:
  ew = d / fclk / t_rst_n on the W face, q / clk / rst_n / rst_xn / strap_k / ready / fault on the E face, M4, pitch
       0.192 (4 kit tracks); parent rings on an E bus use the master mirrored MY;
  ns = d side on S, q side on N, M5, pitch 0.144 (3 kit tracks); parent rings on an N bus use MX.
Kit tracks 0.012 + 0.048 k.  Each face's pin column is centred and snapped down to a kit track; the control pins sit in
the middle of the column (after d[W//2 - 1] / q[W//2 - 1]).  Pinned dimension = ceil_0.432(pins * pitch + 6.0); the
other dimension = max(41.04, ceil_0.432(8.93 um^2 * W / pinned)).
The master RTL is exactly tools/die_plan/param_wrap.wrapper_sv(master, base, params): the module the parent kit-rtl step
generates when it renames the bound instance, so the child and the parent bind the same wrapper (rst_xn is declared only
when RSTREP > 0).

  python3 -I tools/die_plan/cland_ring_master.py scan  --rtl PART.sv --pins TYPE_PINS.json [--widths 145,129,...]
  python3 -I tools/die_plan/cland_ring_master.py prep  --rtl PART.sv --pins TYPE_PINS.json --widths ... --out RK
          [--prefix kv] [--die qwen_kvsys] [--item kv3_hub_C] [--gen]
`prep` writes RK/<master>/{<master>.sv, spec.json, recipes.json, plan.json, pins.json, config.json}; --gen then runs
physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py, which writes RK/<master>/kits/<master>_synth0
(launch: ot-run ... -- bash KIT/run_kit.sh KIT finish 32 16).
"""
import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import param_wrap  # noqa: E402

BASE = "ot_dp_clk_landing_cas"
LATTICE = 0.432
MIN_FREE_UM = 41.04
MARGIN_UM = 6.0
AREA_PER_BIT_UM2 = 8.93
TRACK0, TRACK = 0.012, 0.048
FACE = {  # orient -> (d face, q face, layer, pitch, pin offset from the edge)
    "ew": ("W", "E", "M4", 0.192, 0.042),
    "ns": ("S", "N", "M5", 0.144, 0.048),
}
SOURCES = ["rtl/common/ot_dp_clk_landing_ca.sv", "rtl/common/ot_dp_clk_landing.sv", "rtl/common/ot_meso_fifo.sv"]


def _r(v):
    return round(v + 0.0, 6)


def ceil_lat(v):
    return _r(math.ceil(round(v / LATTICE, 6)) * LATTICE)


def param_text(params):
    return param_wrap.param_text(params)


def master_name(prefix, params, orient):
    h = hashlib.sha1(f"{BASE} {param_text(params)} {orient}".encode()).hexdigest()[:5]
    return f"{prefix}_cland_w{int(params['W'])}_{orient}_{h}"


def face_ports(params):
    """-> (d-side pins, q-side pins) in column order: data bits split in half around the control pins."""
    W, R = int(params["W"]), int(params.get("RSTREP", 0))
    sk = param_wrap._clog2(int(params.get("DEPTH", 4))) + 4
    h = W // 2
    d = [f"d[{i}]" for i in range(h)] + ["fclk", "t_rst_n"] + [f"d[{i}]" for i in range(h, W)]
    ctl = (["clk", "rst_n"] + [f"rst_xn[{i}]" for i in range(R)] + [f"strap_k[{i}]" for i in range(sk)]
           + ["ready", "fault"])
    q = [f"q[{i}]" for i in range(h)] + ctl + [f"q[{i}]" for i in range(h, W)]
    return d, q


def outline(params, orient):
    pitch = FACE[orient][3]
    d, q = face_ports(params)
    pinned = ceil_lat(max(len(d), len(q)) * pitch + MARGIN_UM)
    free = max(MIN_FREE_UM, ceil_lat(AREA_PER_BIT_UM2 * int(params["W"]) / pinned))
    return [free, pinned] if orient == "ew" else [pinned, free]


def _start(span, n, pitch):
    c = (span - (n - 1) * pitch) / 2.0
    return _r(TRACK0 + math.floor(round((c - TRACK0) / TRACK, 6)) * TRACK)


def pins(master, params, orient):
    df, qf, layer, pitch, off = FACE[orient]
    ol = outline(params, orient)
    span = ol[1] if orient == "ew" else ol[0]
    out = []
    dn, qn = face_ports(params)
    for names, face in ((dn, df), (qn, qf)):
        s = _start(span, len(names), pitch)
        for i, n in enumerate(names):
            t = _r(s + i * pitch)
            fixed = {"W": off, "E": _r(ol[0] - off), "S": off, "N": _r(ol[1] - off)}[face]
            x, y = (fixed, t) if orient == "ew" else (t, fixed)
            out.append(dict(name=n, face=face, x=x, y=y, layer=layer,
                            dir="out" if n.startswith("q[") or n in ("ready", "fault") else "in"))
    return dict(schema="opentallas.core_pins.v1", core=master, frame="core R0, origin (0,0)", module=master,
                outline_um=ol, source="tools/die_plan/cland_ring_master.py (CLAND-MACRO-1 mkmacro form)",
                note=(f"landing ring child, d/fclk(/t_rst_n) on the {df} face, q/clk/resets/status on the {qf} face; "
                      f"{layer}, kit track {TRACK0} + {TRACK} k; mirror (MX / MY) for the opposite face"),
                pins=out)


# ---------------------------------------------------------------- scan a bound partition
_INST = re.compile(r"\b" + BASE + r"\s*#\s*\((.*?)\)\s*(\w+)\s*\(", re.S)


def scan(text):
    """-> [(inst, params dict in bind order)] for every ot_dp_clk_landing_cas instance with integer parameters."""
    res = []
    for m in _INST.finditer(text):
        ps = re.findall(r"\.(\w+)\s*\(\s*(-?\d+)\s*\)", m.group(1))
        res.append((m.group(2), {k: int(v) for k, v in ps}))
    return res


def bus_faces(pins_json):
    """type pins.json (list of {bus, face} or {name, face}) -> {bus: set(faces)}"""
    P = json.loads(Path(pins_json).read_text())
    rows = P["pins"] if isinstance(P, dict) else P
    out = {}
    for p in rows:
        b = p.get("bus") or p.get("name", "").split("[")[0]
        out.setdefault(b, set()).add(p.get("face") or p.get("side"))
    return out


def select(insts, faces, widths=None, prefix="kv"):
    """group rings into masters: exact params x face class.  LITE rings stay soft (no hard child form)."""
    groups = {}
    for inst, p in insts:
        if "W" not in p or p.get("LITE") or (widths and p["W"] not in widths):
            continue
        bus = re.sub(r"^u_cland_", "", inst)
        fs = faces.get(bus)
        if not fs or len(fs) != 1:
            raise ValueError(f"{inst}: bus {bus} has faces {sorted(fs or [])}, need exactly one")
        f = next(iter(fs))
        orient = "ew" if f in ("E", "W") else "ns"
        key = (param_text(p), orient)
        g = groups.setdefault(key, dict(params=p, orient=orient, uses=[]))
        g["uses"].append((inst, f))
    out = []
    for g in groups.values():
        g["master"] = master_name(prefix, g["params"], g["orient"])
        out.append(g)
    return sorted(out, key=lambda g: (-g["params"]["W"], g["master"]))


# ---------------------------------------------------------------- freeze inputs
def recipe(master, rk):
    return {master: {"ref_tile": str(rk), "suffix": "synth0", "plan_pins_contract": True,
                     "related_clocks": {"fclk": ["d", "t_rst_n"]}, "strap_ports": ["strap_k"],
                     "insertion_ps": 250, "insertion_ff_ps": 202.5,
                     "insertion_basis": "die qwen_kvsys plan clock insertion (CLAND-MACRO-1)",
                     "insertion_tol_ps": 40, "core_margin": 1.08, "util": 0.5, "slang": True,
                     "max_routing_layer": "M5", "max_fanout": 24,
                     "land_slots": {"d": {"D": 4, "form": "hold_mux"}, "t_rst_n": {"form": "ring_start", "ring": "d"}}}}


def prep(g, rk_root, die="qwen_kvsys", item="kv3_hub_C"):
    m, p, orient = g["master"], g["params"], g["orient"]
    d = Path(rk_root) / m
    d.mkdir(parents=True, exist_ok=True)
    pj = pins(m, p, orient)
    ol = pj["outline_um"]
    (d / "pins.json").write_text(json.dumps(pj, indent=1) + "\n")
    (d / f"{m}.sv").write_text(param_wrap.wrapper_sv(m, BASE, p))
    resets = ["rst_n", "t_rst_n"] + (["rst_xn"] if int(p.get("RSTREP", 0)) > 0 else [])
    (d / "spec.json").write_text(json.dumps(
        {"top": m, "clock_port": "clk", "reset_ports": resets, "sources": [str(d / f"{m}.sv")] + SOURCES,
         "defines": ["SYNTHESIS"], "params": {}, "macros": [], "children": []}, indent=1) + "\n")
    (d / "recipes.json").write_text(json.dumps(recipe(m, d), indent=1) + "\n")
    (d / "plan.json").write_text(json.dumps(
        {"schema": "opentallas.die_plan.v1", "die": {"period_ps": 833},
         "clock": {"insertion_ps": 250, "insertion_ff_ps": 202.5, "insertion_tol_ps": 40},
         "partition_types": {"private_cland_child": {"hard_cores": [
             {"inst": "u_c", "module": m, "outline_um": ol, "origin_um": [0, 0], "pins_file": str(d / "pins.json")}]}}},
        indent=1) + "\n")
    mirror = {"ew": {"W": "R0", "E": "MY"}, "ns": {"S": "R0", "N": "MX"}}[orient]
    (d / "config.json").write_text(json.dumps(
        {"die": die, "base": BASE, "params": p, "param_order": list(p), "orient": orient, "n_inst": len(g["uses"]),
         "items": [item], "bases": [item], "uses": [[item, f"u_bound.{i}", mirror[f]] for i, f in g["uses"]],
         "master": m, "outline_um": ol, "param_text": param_text(p),
         "generator": "tools/die_plan/cland_ring_master.py"}, indent=1) + "\n")
    return d


def gen_kit(d, python=sys.executable):
    m = d.name
    g = REPO / "physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py"
    return subprocess.run([python, "-I", str(g), "--module", m, "--recipes", str(d / "recipes.json"),
                           "--plan", str(d / "plan.json"), "--out", str(d / "kits")],
                          cwd=str(REPO), capture_output=True, text=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["scan", "prep"])
    ap.add_argument("--rtl", required=True)
    ap.add_argument("--pins", required=True, help="the parent type's pins.json (bus faces)")
    ap.add_argument("--widths", default="", help="comma list of ring widths W to harden (default all non-LITE)")
    ap.add_argument("--out")
    ap.add_argument("--prefix", default="kv")
    ap.add_argument("--die", default="qwen_kvsys")
    ap.add_argument("--item", default="kv3_hub_C")
    ap.add_argument("--gen", action="store_true")
    a = ap.parse_args(argv)
    widths = {int(w) for w in a.widths.split(",") if w.strip()}
    gs = select(scan(Path(a.rtl).read_text()), bus_faces(a.pins), widths or None, a.prefix)
    for g in gs:
        print(f"{g['master']}\tW{g['params']['W']}\t{g['orient']}\t{len(g['uses'])}\t{outline(g['params'], g['orient'])}"
              f"\t{param_text(g['params'])}")
    if a.cmd == "prep":
        if not a.out:
            raise SystemExit("prep needs --out")
        for g in gs:
            d = prep(g, a.out, a.die, a.item)
            if a.gen:
                r = gen_kit(d)
                (d / "gen.log").write_text(r.stdout + r.stderr)
                print(g["master"], "gen rc", r.returncode, (r.stdout + r.stderr).strip().splitlines()[-1:])
                if r.returncode:
                    return r.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())

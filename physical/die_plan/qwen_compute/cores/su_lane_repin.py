#!/usr/bin/env python3
"""DIE-QC-57b 10-31 (COORD 18:0x (6)): QC-PLAN pin event for the SU lane hard cores qfd_qc_su_lane_w (u_lane0..7).

The plan pin tables (QC-P6-G0C provisional, cores/su/slw_su_l{0,1}_u_lane<k>_pins.json) do not match the cut RTL
(rtl/physical/qfd_qc_su_lane_w_l<k>.sv, tools/die_plan/qc_su_lane_cut.py): they carry c_i 760 + c_o/ctl_o/stm_o/sc_o
391-428 outputs, no dir, no clk / rst_n, and sit on the 0.024 um track phase (the core kit tracks are 0.012 + 0.048 k).
This re-pins each table to its lane's RTL ports and names the per-lane module in the plan (the eight cut modules are
distinct RTL modules; l0 has c_o 302, l1-l7 248):

  * c_i[i]  : the plan c_i[i] slot (same face / layer / order), dir in;
  * c_o[j]  : the j-th plan OUTPUT slot in table order (c_o, ctl_o, stm_o, sc_o slots), dir out; unused slots dropped;
  * clk, rst_n : M5 on the S face, the two free M5 tracks closest to the face centre (>= 3 tracks from any S pin), dir in
                 (the core kit runs its own CTS balanced to the plan insertion; rst_n = OWNER DECISION 13 synchronous
                 registered input at the data IO budget);
  * every coordinate snapped onto the kit track (M4 y / M5 x: nearest 0.012 + 0.048 k, ties down); face pins keep their
    face coordinate (the kit generator puts the pin on its face).
  * plan partition_types[*].hard_cores[inst u_lane<k>].module 'qfd_qc_su_lane_w' -> 'qfd_qc_su_lane_w_l<k>'.

    python3 su_lane_repin.py --plan PLAN --rtl-dir rtl/physical [--write]     (dry run prints the table summary)
"""
import argparse
import json
import re
from pathlib import Path

BASE = "qfd_qc_su_lane_w"
PORT = re.compile(r"\b(input|output)\s+wire\s+(?:\[(\d+):0\]\s+)?(\w+)")
TRK = {"M4": ("y", 0.012, 0.048), "M5": ("x", 0.012, 0.048)}


def rtl_ports(path, module):
    t = Path(path).read_text()
    m = re.search(r"\bmodule\s+" + re.escape(module) + r"\s*\((.*?)\);", t, re.S)
    if not m:
        raise SystemExit(f"{path}: no module {module}")
    return {n: (d, int(hi) + 1 if hi else 0) for d, hi, n in PORT.findall(m.group(1))}


def snap(v, o, p):
    k = (v - o) / p
    return round(o + p * (int(k) if abs(k - round(k)) > 1e-6 else round(k)), 4)


def repin(table, ports, w, h, module):
    pins = table["pins"]
    if set(ports) != {"clk", "rst_n", "c_i", "c_o"} or ports["c_i"] != ("input", 760):
        raise SystemExit(f"{module}: unexpected RTL ports {ports}")
    ci = {q["name"]: q for q in pins if q["name"].startswith("c_i[")}
    outs = [q for q in pins if not q["name"].startswith("c_i[")]
    n_o = ports["c_o"][1]
    if len(ci) != 760 or n_o > len(outs):
        raise SystemExit(f"{module}: plan c_i {len(ci)} / output slots {len(outs)} vs RTL c_o {n_o}")
    new = []
    for i in range(760):
        q = ci[f"c_i[{i}]"]
        new.append(dict(name=f"c_i[{i}]", layer=q["layer"], x=q["x"], y=q["y"], dir="in"))
    for j in range(n_o):
        q = outs[j]
        new.append(dict(name=f"c_o[{j}]", layer=q["layer"], x=q["x"], y=q["y"], dir="out"))
    for q in new:
        a, o, p = TRK[q["layer"]]
        q[a] = snap(q[a], o, p)
    # clk / rst_n: the two free M5 S-face tracks closest to the face centre (>= 3 tracks from any S-face pin)
    s_used = [q["x"] for q in new if q["layer"] == "M5" and q["y"] < h / 2]
    c0, free = snap(w / 2, 0.012, 0.048), []
    for k in range(int(w / 0.048)):
        for x in ((c0 - 0.048 * k, c0 + 0.048 * k) if k else (c0,)):
            x = round(x, 4)
            if 1.0 < x < w - 1.0 and all(abs(x - u) >= 0.144 - 1e-6 for u in s_used + free):
                free.append(x)
        if len(free) >= 2:
            break
    new += [dict(name="clk", layer="M5", x=free[0], y=0.096, dir="in"),
            dict(name="rst_n", layer="M5", x=free[1], y=0.096, dir="in")]
    xy = [(q["layer"], q["x"], q["y"]) for q in new]
    if len(set(xy)) != len(xy):
        raise SystemExit(f"{module}: duplicate pin sites after re-pin")
    if any(not (0 <= q["x"] <= w and 0 <= q["y"] <= h) for q in new):
        raise SystemExit(f"{module}: pin outside the {w}x{h} outline")
    return dict(schema="opentallas.core_pins.v1", core=module, frame=table.get("frame", "core R0, origin (0,0)"),
                source=("DIE-QC-57b 10-31 QC-PLAN pin event (su_lane_repin.py): cut-RTL ports on the QC-P6-G0C slots "
                        f"(c_i same slots, c_o = first {n_o} output slots in table order, clk/rst_n M5 S face), "
                        "kit-track snapped; NOT SIGNED"), pins=new)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--rtl-dir", default="rtl/physical")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    pp = Path(a.plan)
    plan = json.loads(pp.read_text())
    tables, renamed = {}, 0
    for t, v in sorted(plan["partition_types"].items()):
        for c in v.get("hard_cores") or []:
            if c.get("module") not in (BASE,) and not str(c.get("module", "")).startswith(BASE + "_l"):
                continue
            k = int(re.fullmatch(r"u_lane(\d)", c["inst"]).group(1))
            mod = f"{BASE}_l{k}"
            prev = tables.setdefault(c["pins_file"], (mod, c["outline_um"]))
            if prev[0] != mod:
                raise SystemExit(f"{c['pins_file']}: shared by {prev[0]} and {mod}")
            renamed += c["module"] != mod
            c["module"] = mod
    out = {}
    for pf, (mod, (w, h)) in sorted(tables.items()):
        tb = json.loads((pp.parent / pf).read_text())
        new = repin(tb, rtl_ports(Path(a.rtl_dir) / f"{mod}.sv", mod), w, h, mod)
        out[pf] = new
        print(f"SU_REPIN {pf} {mod}: {len(tb['pins'])} -> {len(new['pins'])} pins "
              f"(c_o {sum(q['name'].startswith('c_o[') for q in new['pins'])}, clk/rst_n M5 S)")
    print(f"SU_REPIN {len(out)} tables, {renamed} plan hard_cores renamed")
    if a.write:
        for pf, new in out.items():
            (pp.parent / pf).write_text(json.dumps(new, indent=1) + "\n")
        raw = pp.read_text()
        ind = 1 if raw.startswith("{\n ") and not raw.startswith("{\n  ") else (2 if raw.startswith("{\n  ") else None)
        pp.write_text(json.dumps(plan, indent=ind) + ("\n" if raw.endswith("\n") else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

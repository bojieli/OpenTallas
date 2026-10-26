#!/usr/bin/env python3
"""D-QC-FE-REACH (PATH-QC 10-26): registered stations on every FE (slice u_fup) crossing over the 405-um reach.

The QC FE tiles (slw_fe_* / sle_fe_*, 622 x 1339 um) carry the slice u_fup leaf: zero-logic forwarders (st_up_c ->
st_up_o, chr_c -> ch_up_o, hr_c -> hr_o, sc_up_c, treq_c, l9_c: W in bus -> E out bus in ONE cycle) and five interface
registers (ch_up_i -> chu_q, st_dn_i -> se_q, sc_dn_i -> scd_q, ag_up_i -> agu_q, cmd_q -> cmd_o).  The 622-um width
alone exceeds one 405-um hop, so plan 54a1aeb5 left > 5k reg-reg arcs over reach per tile (KITS-WAVE-2 r2r census,
GEOM review slw_fe_v1 FAIL STRUCTURAL reach).

  extract  BIND_RTL_DIR --out inputs/fe_fwd_map.json
           per FE type, the bit map of the bound module (bind.py): in bus bit -> u_fup port -> out bus bit, and whether
           the bit passes a u_fup interface register (core = 1) or a zero-logic forwarder (core = 0).
  apply    PLAN.json --map inputs/fe_fwd_map.json [--out CANDIDATE.json] [--report REPORT.json]
           gen_plan.declare_fe_reach_stations: n FIRM stations per FE in bus (internal_stations[] bit_route "chain",
           realised per bit by tools/die_plan/kit_istations.py), lanes landing on the bus get fixed_cycles += n.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# u_fup leaf port semantics (rtl/qwen_dv/s5/s6/qfd_dv_s6_leaves.sv qfd_dv_s6_fup, rtl/qwen_dv/s5/s8/qfd_dv_s8_ce.sv
# qfd_dv_s6_fup_e5): out port -> (in port, registered); every pair is bitwise (cmd_o: + the SETID increment on [7:4])
FUP_PORTS = {"st_up_o": ("st_up_c", 0), "sc_up_o": ("sc_up_c", 0), "hr_o": ("hr_c", 0), "ch_up_o": ("chr_c", 0),
             "treq_o": ("treq_c", 0), "l9_o": ("l9_c", 0),
             "se_q": ("st_dn_i", 1), "scd_q": ("sc_dn_i", 1), "chu_q": ("ch_up_i", 1), "agu_q": ("ag_up_i", 1),
             "cmd_o": ("cmd_q", 1)}
FUP_MODULES = ("qfd_dv_s6_fup", "qfd_dv_s6_fup_e5")
FE_TYPE_RE = re.compile(r"^sl[we]_fe_v\d+$")


def _split_top(s):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch in "({[":
            depth += 1
        elif ch in ")}]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def terms(expr, widths):
    """'{a[3:0], b[7], c}' -> [(name, bit)] LSB first"""
    e = expr.strip()
    if e.startswith("{") and e.endswith("}"):
        parts = _split_top(e[1:-1])
    else:
        parts = [e]
    bits = []
    for p in parts:                                   # MSB first in the concat
        m = re.fullmatch(r"([A-Za-z_]\w*)\s*(?:\[(\d+)(?::(\d+))?\])?", p.strip())
        if not m:
            bits_p = [(p.strip(), None)]              # constant / expression: no source
        else:
            nm, hi, lo = m.group(1), m.group(2), m.group(3)
            if hi is None:
                hi, lo = widths[nm] - 1, 0
            elif lo is None:
                lo = hi
            hi, lo = int(hi), int(lo)
            bits_p = [(nm, b) for b in range(hi, lo - 1, -1)]
        bits.extend(bits_p)
    return list(reversed(bits))


def extract_type(text):
    widths = {m.group(2): int(m.group(1)) + 1 for m in re.finditer(r"\bwire\s+\[(\d+):0\]\s+(\w+)\s*;", text)}
    m = re.search(r"\b(" + "|".join(FUP_MODULES) + r")\b\s*(?:#\([^;]*?\))?\s*u_core\s*\((.*?)\n\s*\);", text, re.S)
    if not m:
        return None
    leaf = m.group(1)
    conn = dict(re.findall(r"\.(\w+)\s*\(([^()]*)\)", m.group(2)))
    # in port bit -> (in bus, bit) through the face register q (<bus>_q)
    pin = {}
    for p, (ip, _) in FUP_PORTS.items():
        if ip not in conn:
            continue
        for j, (nm, b) in enumerate(terms(conn[ip], widths)):
            if b is not None and nm.endswith("_q"):
                pin[(ip, j)] = (nm[:-2], b)
    chains = []
    for bm in re.finditer(r"\bot_dp_ste?\s+#\(\.W\((\d+)\)\)\s+u_bout_(\w+)\s*\(.*?\.d\(([^)]*)\)", text):
        ob = bm.group(2)
        for c, (nm, j) in enumerate(terms(bm.group(3), widths)):
            if j is None or not nm.startswith("w_core_"):
                continue
            op = nm[len("w_core_"):]
            if op not in FUP_PORTS:
                continue
            ip, reg = FUP_PORTS[op]
            src = pin.get((ip, j))
            if src:
                chains.append((src[0], src[1], ob, c, reg))
    # compress into ranges (in_bus, in_lo, in_hi, out_bus, out_lo, core)
    chains.sort()
    rng = []
    for ib, b, ob, c, reg in chains:
        if rng and rng[-1][0] == ib and rng[-1][2] + 1 == b and rng[-1][3] == ob and \
                rng[-1][4] + (b - rng[-1][1]) == c and rng[-1][5] == reg:
            rng[-1][2] = b
        else:
            rng.append([ib, b, b, ob, c, reg])
    return dict(leaf=leaf, chains=rng, bits=len(chains))


def cmd_extract(a):
    d = Path(a.bind_rtl)
    out = dict(schema="opentallas.die_plan.qc_fe_fwd_map.v1", source=str(a.source or d), types={})
    for f in sorted(d.glob("qfd_qc_sl[we]_fe__*.sv")):
        tn = f.stem.split("__", 1)[1]
        if not FE_TYPE_RE.match(tn):
            continue
        r = extract_type(f.read_text())
        if r:
            out["types"][tn] = r
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({tn: dict(leaf=v["leaf"], bits=v["bits"], ranges=len(v["chains"])) for tn, v in out["types"].items()}))


def cmd_apply(a):
    sys.path.insert(0, str(HERE))
    import gen_plan as G
    raw = json.loads(Path(a.plan).read_text())
    fmap = json.loads(Path(a.map).read_text())
    rep = G.declare_fe_reach_stations(raw, fmap)
    Path(a.out or a.plan).write_text(json.dumps(raw, indent=1) + "\n")
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    for tn, r in sorted(rep["types"].items()):
        print(tn, " ".join(f"{b}+{n}" for b, n in sorted(r["in_bus_stations"].items()) if n))
    print(f"FE_REACH stations {rep['stations']} lanes {rep['lanes']}  worst planned hop {rep['worst_hop_um']} um")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    e = sp.add_parser("extract")
    e.add_argument("bind_rtl")
    e.add_argument("--out", required=True)
    e.add_argument("--source", help="provenance string recorded in the map (bind dir @ commit)")
    p = sp.add_parser("apply")
    p.add_argument("plan")
    p.add_argument("--map", default=str(HERE / "inputs" / "fe_fwd_map.json"))
    p.add_argument("--out")
    p.add_argument("--report")
    a = ap.parse_args(argv)
    return {"extract": cmd_extract, "apply": cmd_apply}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())

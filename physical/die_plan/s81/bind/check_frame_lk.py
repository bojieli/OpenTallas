#!/usr/bin/env python3
"""TOK-S81-1 10-28 (COORD 20:10 (6)): the S81 per-frame landing-K gate, run from the bind script (not only from the
compiler).  Every frame instance u_f_* of the as-built die top must land each of its 4 x lanes at the K of the
per-frame landing plan (results/s81_unblock3_1027/fi_seam/frame_lk.json, S81-UNBLOCK-3), and K must be a legal E.

The as-built frame wrapper (col_<M>_l4_lp_asb_<x|nx>, bind/models/s81_asb_models.sv) passes LK to its r0/r1/r2 band
types; a per-instance LK override on the die top (a `.LK(` or `.lk(` connection) wins over the wrapper value.
This is the same rule lower_xs.frame_lk enforces at compile time; it is repeated here so that a bind whose frames
drifted from the landing plan fails at bind time.  Fail closed: missing table, missing row, unparsed LK, mismatch.

    check_frame_lk.py DIE_TOP.v MODELS.sv FRAME_LK.json [--out REPORT.json]
"""
import argparse
import json
import re
import sys
from pathlib import Path

INST = re.compile(r"^\s*(col_h\d+_l4_lp_asb_(?:x|nx))\s*#\(.*?\)\s*(u_f_\w+)\s*\((.*)$")
MOD = re.compile(r"^\s*module\s+(col_h\d+_l4_lp_asb_(?:x|nx))\b")
LKP = re.compile(r"\.LK\(\s*([^()]*?(?:\{[^()]*\})?)\s*\)\)?\s*u_(r[012])\b")
REP = re.compile(r"^\{\s*(\d+)\s*\{\s*(\d+)'d(\d+)\s*\}\s*\}$")
HEX = re.compile(r"^(\d+)'h([0-9a-fA-F]+)$")


def lanes(expr, n=4, w=3):
    """{4{3'd2}} or 12'h492 -> per-lane K list (lane k = lk[3k +: 3]); None when unparsed"""
    e = expr.replace(" ", "")
    m = REP.match(e)
    if m and int(m.group(1)) == n and int(m.group(2)) == w:
        return [int(m.group(3))] * n
    m = HEX.match(e)
    if m and int(m.group(1)) == n * w:
        v = int(m.group(2), 16)
        return [(v >> (w * k)) & ((1 << w) - 1) for k in range(n)]
    return None


def wrapper_lk(models_text):
    out, cur = {}, None
    for line in models_text.splitlines():
        m = MOD.match(line)
        if m:
            cur = m.group(1)
            out[cur] = {}
            continue
        if cur and line.strip().startswith("endmodule"):
            cur = None
            continue
        if cur:
            for e, r in LKP.findall(line):
                out[cur][r] = e
    return out


def check(die_text, models_text, plan):
    errs, rows = [], []
    if plan.get("schema") != "opentallas.s81.frame_lk.v1" or not isinstance(plan.get("rows"), dict):
        return ["frame_lk table: wrong schema or no rows"], rows
    wl = wrapper_lk(models_text)
    seen = set()
    for line in die_text.splitlines():
        m = INST.match(line)
        if not m:
            continue
        master, inst, conns = m.groups()
        seen.add(inst)
        ov = re.search(r"\.(?:LK|lk)\(\s*([^)]*)\)", conns)
        src = "die_top_override" if ov else "wrapper"
        exprs = {"r0": ov.group(1)} if ov else wl.get(master, {})
        row = plan["rows"].get(inst)
        if row is None:
            errs.append(f"{inst}: no frame_lk row")
            continue
        if not exprs:
            errs.append(f"{inst}: wrapper {master} has no LK")
            continue
        for band, e in sorted(exprs.items()):
            ks = lanes(e)
            if ks is None:
                errs.append(f"{inst}.{band}: LK {e!r} unparsed")
                continue
            bad = [k for k in ks if k != row["K"] or k not in row.get("legal_E", [])]
            rows.append(dict(inst=inst, master=master, band=band, source=src, lk=e, lanes=ks, K_plan=row["K"],
                             legal_E=row.get("legal_E"), ok=not bad))
            if bad:
                errs.append(f"{inst}.{band}: lanes {ks} vs plan K {row['K']} legal {row.get('legal_E')}")
    missing = sorted(set(plan["rows"]) - seen)
    if missing:
        errs.append(f"frames in the plan but not in the die top: {missing[:8]} ({len(missing)})")
    if not seen:
        errs.append("no frame instance found in the die top")
    return errs, rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("die_top")
    ap.add_argument("models")
    ap.add_argument("frame_lk")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    p = Path(a.frame_lk)
    if not p.is_file():
        print(f"FRAME_LK FAIL table missing: {p}")
        return 1
    errs, rows = check(Path(a.die_top).read_text(), Path(a.models).read_text(), json.loads(p.read_text()))
    frames = len({r["inst"] for r in rows})
    verdict = "FAIL" if errs else "PASS"
    if a.out:
        Path(a.out).write_text(json.dumps(dict(schema="opentallas.s81.frame_lk_check.v1", verdict=verdict,
                                               frames=frames, errors=errs, rows=rows), indent=1))
    print(f"FRAME_LK {verdict} frames={frames} band_checks={len(rows)} errors={len(errs)}")
    for e in errs[:20]:
        print("  " + e)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())

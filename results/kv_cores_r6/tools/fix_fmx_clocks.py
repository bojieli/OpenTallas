#!/usr/bin/env python3
"""KV-CORES-R6 (2026-10-27): make a head fMX view consistent with its centre-entry canonical view.

KV-CORE-SLICE-1 / KV-CORES-R3 moved the die-clock pins of the canonical view into the 12.8a centre entry island
(M5, y = H/2) but left the _fMX view on the old face slots, so head_type_delta (A) refused it (CLOCK-KV-R24: e6,
7 clock pins neither MX image nor kept).  The fMX view is the MX image of the canonical view by definition; this
tool rewrites ONLY the die-clock pins of the fMX view to the MX image of the canonical clock pins, fail-closed:
  - every pin it changes must match the die-clock regex and sit inside the canonical entry island (|x-W/2|,|y-H/2| <= 4.32);
  - every other pin must already be the MX image or a kept (same-y) reset pin, else it refuses;
  - it writes only inside its own plan dir through plan_views.safe_write (real copies, views.sha256).
    fix_fmx_clocks.py PLAN_DIR VIEW_STEM [--h 216] [--w 216] --report OUT.json
"""
import argparse, hashlib, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_views as PV  # noqa: E402

CLK_RE = re.compile(r"^(?:\w+__)?(ck|clk)(\[0\]|\[None\])?$")
RST_RE = re.compile(r"(^|__)rst_n(\[0\]|\[None\])?$")
ISL_HALF = 4.32


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pd"); ap.add_argument("stem")
    ap.add_argument("--w", type=float, default=216.0); ap.add_argument("--h", type=float, default=216.0)
    ap.add_argument("--report", required=True)
    a = ap.parse_args()
    pd = Path(a.pd)
    cr, fr = f"cores/{a.stem}.json", f"cores/{a.stem}_fMX.json"
    C, F = json.loads((pd / cr).read_text()), json.loads((pd / fr).read_text())
    ca = {p["name"]: p for p in C["pins"]}
    assert set(ca) == {p["name"] for p in F["pins"]}, "pin sets differ"
    fixed, kept, bad = [], [], []
    for q in F["pins"]:
        p = ca[q["name"]]
        mx = abs((a.h - p["y"]) - q["y"]) <= 1e-3 and abs(p["x"] - q["x"]) <= 1e-3 and p["layer"] == q["layer"]
        if mx:
            continue
        if RST_RE.search(q["name"]) and abs(p["y"] - q["y"]) <= 1e-3 and abs(p["x"] - q["x"]) <= 1e-3:
            kept.append(q["name"]); continue
        in_isl = abs(p["x"] - a.w / 2) <= ISL_HALF and abs(p["y"] - a.h / 2) <= ISL_HALF
        if CLK_RE.match(q["name"]) and in_isl:
            old = [q["layer"], q["x"], q["y"]]
            q["layer"], q["x"], q["y"] = p["layer"], p["x"], round(a.h - p["y"], 3)
            fixed.append(dict(pin=q["name"], old=old, new=[q["layer"], q["x"], q["y"]]))
        else:
            bad.append(q["name"])
    if bad:
        raise SystemExit(f"REFUSED: {len(bad)} non-clock pins are neither MX image nor kept reset: {bad[:8]}")
    sha0 = hashlib.sha256((pd / fr).read_bytes()).hexdigest()
    F["source"] = F.get("source", "") + f" | KV-CORES-R6 10-27: {len(fixed)} die-clock pins = MX image of the centre-entry canonical view (fix_fmx_clocks.py)"
    PV.safe_write(pd, fr, json.dumps(F, indent=1) + "\n")
    rep = dict(schema="opentallas.kv_cores_r6.fix_fmx_clocks.v1", plan_dir=str(pd), canonical=cr,
               canonical_sha256=hashlib.sha256((pd / cr).read_bytes()).hexdigest(), fmx=fr, fmx_sha256_before=sha0,
               fmx_sha256_after=hashlib.sha256((pd / fr).read_bytes()).hexdigest(), fixed=fixed, kept_reset=kept)
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print("fixed", len(fixed), "kept", len(kept), rep["fmx_sha256_after"][:8])


if __name__ == "__main__":
    main()

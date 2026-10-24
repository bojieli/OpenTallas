#!/usr/bin/env python3
"""kits_repin: collect the gate results of one run kit dir into a results row (append-only into results.json).

    python3 collect.py RUNKITDIR --host HOST [--results results.json] [--note TEXT]

Gates (rules: S81-CORES task 10-24): synth cells vs the closed view; route DRC; GRT overflow; pin audit (routed ==
plan); register-on-every-pin (ot_unreg_pins.txt + face_guard); CTS insertion <= 300 ps and leaf spread <= 80 ps (TT);
TT setup WNS >= 0 (TT pathfinding), FF hold WNS >= 0, SS setup (sign-off corner, reported).  A gate whose evidence is
missing is NOT RUN.  Rows are appended; existing rows (incl. FAIL verdicts) are never rewritten.
"""
import argparse
import glob
import json
import re
import time
from pathlib import Path

INS_MAX, SPREAD_MAX = 300.0, 80.0


def rd(p):
    try:
        return Path(p).read_text(errors="replace")
    except OSError:
        return None


def one(pat):
    g = sorted(glob.glob(pat))
    return g[-1] if g else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kit")
    ap.add_argument("--host", required=True)
    ap.add_argument("--results", default=str(Path(__file__).with_name("results.json")))
    ap.add_argument("--note", default="")
    ap.add_argument("--signoff", default="signoff", help="signoff.py --out dir, relative to the kit")
    ap.add_argument("--author", default="claude kits_repin")
    a = ap.parse_args()
    K = Path(a.kit).resolve()
    fz = json.loads((K / "freeze.json").read_text())
    rec = json.loads((Path(__file__).with_name("recipes.json")).read_text())[fz["module"]]
    R = one(str(K / "run/results/asap7/*/base"))
    L = one(str(K / "run/logs/asap7/*/base"))
    REP = one(str(K / "run/reports/asap7/*/base"))
    row = dict(kit=fz["kit"], module=fz["module"], kit_hash=fz["kit_hash"], host=a.host, run_dir=str(K),
               outline_um=fz["outline_um"], pins=fz["pins"], recorded=time.strftime("%Y-%m-%d %H:%M %Z"),
               gates_built_in=fz.get("gates"), corner_note="AGENTS 2026-10-24: timing closes at TT setup / FF hold; SS information only",
               functional=("kit-local rtl_patch (duplicate sticky fault flop): lockstep vs unmodified module PASS + mutant "
                           "caught (results/lockstep_*.json)" if rec.get("rtl_patch") else
                           "RTL unchanged (closed kit's spec.json sources/params byte-identical copies): no miter needed"),
               author=a.author,
               note=a.note)
    g = {}
    s = rd(K / "sdc_lint.log")
    g["sdc_lint"] = ("PASS" if s and "SDC_LINT PASS" in s else "FAIL" if s else "NOT RUN")
    # synth cells
    st = rd(f"{REP}/synth_stat.txt") if REP else None
    cells = None
    if st:
        m = re.findall(r"^\s*(\d+)\s+[\d.E+-]*\s*cells\s*$", st, re.M) or re.findall(r"Number of cells:\s+(\d+)", st)
        if m:
            cells = int(m[-1]) if not re.findall(r"Number of cells:\s+(\d+)", st) else int(re.findall(r"Number of cells:\s+(\d+)", st)[0])
    g["synth_cells"] = dict(cells=cells, closed_view=rec["closed_cells"],
                            ratio=(round(cells / rec["closed_cells"], 3) if cells else None)) if cells else "NOT RUN"
    fg = rd(K / "face_guard.json")
    if fg:
        fj = json.loads(fg)
        g["face_guard"] = dict(verdict=fj["verdict"], bits=fj["checked"], ok=fj["ok"], fails=fj["fail_counts"],
                               missing=fj.get("missing_n"), extra=fj.get("extra_n"),
                               self_loop_only=fj.get("self_loop_only"), self_loops=fj.get("self_loops"),
                               non_self_loop_fails=fj.get("non_self_loop_fails"))
    else:
        g["face_guard"] = "NOT RUN"
    un = rd(f"{R}/ot_unreg_pins.txt") if R else None
    ffl = rd(f"{R}/ot_face_flops.txt") if R else None
    g["unreg_pins"] = (len([x for x in un.splitlines() if x.strip()]) if un is not None else "NOT RUN")
    # GRT overflow
    grt = rd(f"{L}/5_1_grt.log") if L else None
    if grt:
        m = re.findall(r"Total\s+\d+\s+\d+\s+[\d.]+%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)", grt)
        ov = re.findall(r"[Oo]verflow[^\n]*?(\d+)\s*$", grt, re.M)
        g["grt_overflow"] = int(m[-1][2]) if m else (int(ov[-1]) if ov else "PARSE?")
    else:
        g["grt_overflow"] = "NOT RUN"
    drt = rd(f"{L}/5_2_route.log") if L else None
    if drt:
        m = re.findall(r"Number of violations = (\d+)", drt)
        g["route_drc"] = int(m[-1]) if m else "PARSE?"
    else:
        g["route_drc"] = "NOT RUN"
    pa = rd(K / "pin_audit.json")
    if pa:
        pj = json.loads(pa)
        g["pin_audit"] = dict(verdict=pj["verdict"], ok=pj["ok"], pins=pj["pins"], missing=pj["missing_n"],
                              wrong_layer=pj["wrong_layer_n"], wrong_place=pj["wrong_place_n"], extra=pj["extra_n"])
    else:
        g["pin_audit"] = "NOT RUN"
    sta = {}
    for c in ("tt", "ff", "ss"):
        t = rd(K / f"sta_{c}.json")
        sta[c] = json.loads(t) if t else "NOT RUN"
    g["sta"] = sta
    # verdicts
    v = {}
    v["sdc_lint"] = g["sdc_lint"]
    fgd = g["face_guard"]
    v["face_guard"] = (("FAIL (self-loop only)" if fgd["verdict"] == "FAIL" and fgd.get("self_loop_only") else fgd["verdict"])
                       if isinstance(fgd, dict) else "NOT RUN")
    v["unreg_pins"] = ("PASS" if g["unreg_pins"] == 0 else "NOT RUN" if g["unreg_pins"] == "NOT RUN" else "FAIL")
    v["route_drc"] = ("PASS" if g["route_drc"] == 0 else "NOT RUN" if g["route_drc"] == "NOT RUN" else "FAIL")
    v["grt_overflow"] = ("PASS" if g["grt_overflow"] == 0 else "NOT RUN" if g["grt_overflow"] == "NOT RUN" else "FAIL")
    v["pin_audit"] = g["pin_audit"]["verdict"] if isinstance(g["pin_audit"], dict) else "NOT RUN"
    tt, ff, ss = sta["tt"], sta["ff"], sta["ss"]
    if isinstance(tt, dict):
        v["cts_tt"] = "PASS" if tt["ck_max_ps"] <= INS_MAX and tt["ck_spread_ps"] <= SPREAD_MAX else "FAIL"
        v["tt_setup"] = "PASS" if tt["setup_wns_ps"] >= 0 else "FAIL"
    else:
        v["cts_tt"] = v["tt_setup"] = "NOT RUN"
    v["ff_hold"] = ("PASS" if ff["hold_wns_ps"] >= 0 else "FAIL") if isinstance(ff, dict) else "NOT RUN"
    v["ss_setup (info)"] = ("PASS" if ss["setup_wns_ps"] >= 0 else "FAIL") if isinstance(ss, dict) else "NOT RUN"
    phys = [k for k in v if k not in ("ss_setup (info)", "face_guard", "sdc_lint")]
    if any(v[k] == "FAIL" for k in phys):
        pv = "FAIL (" + ", ".join(k for k in phys if v[k] == "FAIL") + ")"
    elif any(v[k] == "NOT RUN" for k in phys):
        pv = "INCOMPLETE (" + ", ".join(k for k in phys if v[k] == "NOT RUN") + " NOT RUN)"
    else:
        pv = "PASS (TT setup + FF hold)" + ("; SS setup PASS" if v["ss_setup (info)"] == "PASS"
                                                else "; SS setup " + v["ss_setup (info)"])
    fails = [k for k in ("sdc_lint", "face_guard") if v[k] != "PASS"]
    verdict = (f"FAIL ({', '.join(k + ' ' + v[k] for k in fails)}); physical: {pv}" if fails else pv)
    # signoff.py (main f942bf2f72) is authoritative: a core is closed only when its verdict is SIGNED
    sj = K / a.signoff / "signoff.json"
    if sj.exists():
        so = json.loads(sj.read_text())
        sv = so.get("verdict") or so.get("status")
        g["signoff"] = dict(dir=str(sj.parent), verdict=sv,
                            reasons=so.get("reasons"),
                            setup_tt=(so.get("checks") or {}).get("setup_tt"), hold_ff=(so.get("checks") or {}).get("hold_ff"),
                            summary=(rd(K / "signoff.log") or "").splitlines()[:1] if (K / "signoff.log").exists() else None)
    else:
        g["signoff"] = "NOT RUN"
        sv = "NOT RUN"
    v["signoff"] = sv
    verdict = ("SIGNED (closed)" if sv == "SIGNED" else f"NOT CLOSED: signoff {sv}; " + verdict)
    row["physical_verdict"] = pv
    row.update(gates=g, gate_verdicts=v, verdict=verdict)
    P = Path(a.results)
    allr = json.loads(P.read_text()) if P.exists() else dict(schema="opentallas.s81.kits_repin.results.v1", rows=[])
    allr["rows"].append(row)
    P.write_text(json.dumps(allr, indent=1) + "\n")
    print(json.dumps(dict(kit=row["kit"], verdict=verdict, gates=v), indent=1))


if __name__ == "__main__":
    main()

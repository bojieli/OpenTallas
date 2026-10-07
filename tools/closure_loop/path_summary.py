#!/usr/bin/env python3
"""Closure-loop failure summary: the worst timing path CLASSES of a routed ORFS result at the sign-off corners.

Times <orfs>/results/asap7/*/base/6_final.{odb,sdc,spef} (or --base DIR) with OpenSTA in the ORFS container at
SS (setup) and FF (hold), exactly as tools/w18/corner_sta.py does (same libraries, propagated clocks, optional
--macro views and --post-sdc files), enumerates up to --paths worst endpoints per check, and groups them into classes
by start/end point with bus indices and generated instance numbers folded ([12] -> [*], _123_ -> _*_).  Prints and
writes JSON: per check, the worst --top classes (worst slack, path count, a representative start/end, logic levels).
Read-only on the ORFS dir (the Tcl lives in a private temp dir).

    path_summary.py --orfs-dir RUN/work/orfs [--base DIR] [--src SRCROOT] [--macro DIR] [--post-sdc F] --output S.json
"""
import argparse, json, re, subprocess, tempfile
from pathlib import Path

PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
LIBS = {"ss": ["asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz", "asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz",
               "asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz", "asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib",
               "asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz"],
        "ff": ["asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz", "asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz",
               "asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz", "asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib",
               "asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz"]}


def tcl(corner, macros, post, npaths):
    chk = "max" if corner == "ss" else "min"
    L = [f"read_lef {PLAT}/lef/asap7_tech_1x_201209.lef", f"read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef"]
    L += [f"read_lef /srcroot/{m}/{Path(m).name}.lef" for m in macros]
    L += [f"read_liberty {PLAT}/lib/NLDM/{l}" for l in LIBS[corner]]
    L += [f"read_liberty /srcroot/{m}/{Path(m).name}_{corner}.lib" for m in macros]
    L += ["read_db /base/6_final.odb", "read_sdc /base/6_final.sdc", "read_spef /base/6_final.spef",
          "set_propagated_clock [all_clocks]"] + [f"read_sdc /srcroot/{p}" for p in post]
    L.append(f"""
foreach pe [find_timing_paths -path_delay {chk} -group_path_count {npaths} -endpoint_path_count 1 -sort_by_slack] {{
  set sp [get_full_name [get_property $pe startpoint]]
  set ep [get_full_name [get_property $pe endpoint]]
  set n 0
  foreach pt [get_property $pe points] {{ incr n }}
  puts "OT_P [get_property $pe slack] [expr {{$n / 2}}] $sp $ep"
}}
exit""")
    return "\n".join(L) + "\n"


def fold(name):
    s = re.sub(r"\[\d+\]", "[*]", name)
    s = re.sub(r"(?<=_)\d+(?=_|$)", "*", s)
    s = re.sub(r"\d+", "#", s) if len(s) > 120 else s
    return s


def run(base, srcroot, corner, macros, post, npaths, image):
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "s.tcl").write_text(tcl(corner, macros, post, npaths))
        cmd = ["docker", "run", "--rm", "-v", f"{base}:/base:ro", "-v", f"{td}:/t:ro"]
        if srcroot:
            cmd += ["-v", f"{srcroot}:/srcroot:ro"]
        cmd += [image, "bash", "-lc", "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /t/s.tcl"]
        out = subprocess.run(cmd, capture_output=True, text=True).stdout
    paths = []
    for m in re.finditer(r"^OT_P (\S+) (\d+) (\S+) (\S+)", out, re.M):
        try:
            paths.append(dict(slack_ps=round(float(m[1]), 2), levels=int(m[2]), start=m[3], end=m[4]))
        except ValueError:
            pass
    return paths, out


def classes(paths, top):
    c = {}
    for p in paths:
        k = (fold(p["start"]), fold(p["end"]))
        e = c.setdefault(k, dict(start_class=k[0], end_class=k[1], worst_slack_ps=p["slack_ps"], paths=0,
                                 max_levels=0, example_start=p["start"], example_end=p["end"]))
        e["paths"] += 1
        e["max_levels"] = max(e["max_levels"], p["levels"])
        if p["slack_ps"] < e["worst_slack_ps"]:
            e.update(worst_slack_ps=p["slack_ps"], example_start=p["start"], example_end=p["end"])
    return sorted(c.values(), key=lambda e: e["worst_slack_ps"])[:top]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orfs-dir", type=Path)
    ap.add_argument("--base", type=Path, help="dir holding 6_final.{odb,sdc,spef} (default <orfs>/results/asap7/*/base)")
    ap.add_argument("--src", type=Path, help="source root for --macro / --post-sdc paths")
    ap.add_argument("--macro", action="append", default=[])
    ap.add_argument("--post-sdc", action="append", default=[])
    ap.add_argument("--paths", type=int, default=400)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--corners", default="ss,ff")
    ap.add_argument("--image", default="openroad/orfs:latest")
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    base = a.base or next((a.orfs_dir / "results/asap7").glob("*/base"))
    rec = dict(schema="opentallas.closure_loop.path_summary.v1", base=str(base.resolve()))
    for corner in a.corners.split(","):
        paths, out = run(base.resolve(), a.src.resolve() if a.src else None, corner, a.macro, a.post_sdc, a.paths, a.image)
        key = "setup_ss" if corner == "ss" else "hold_ff"
        rec[key] = dict(paths_seen=len(paths), worst_slack_ps=min((p["slack_ps"] for p in paths), default=None),
                        classes=classes(paths, a.top), errors=re.findall(r"\[ERROR[^\n]*", out)[:5])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    for key in ("setup_ss", "hold_ff"):
        if key in rec:
            print(key, rec[key]["worst_slack_ps"], "classes:")
            for e in rec[key]["classes"]:
                print(f"  {e['worst_slack_ps']:9.2f} ps  n={e['paths']:4d} lv={e['max_levels']:3d}  {e['start_class']} -> {e['end_class']}")


if __name__ == "__main__":
    main()

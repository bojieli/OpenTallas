#!/usr/bin/env python3
"""W18: sign-off-corner STA of a routed ORFS result (AGENTS.md, 2026-09-30: headline clocks close SETUP at SS
and HOLD at FF, 60 ps / 25 ps uncertainty; TT is pathfinding only).

Reads the routed 6_final.odb, its SPEF (the extraction's RC is corner-independent here: ASAP7 ships one RC
deck) and its SDC (which carries the 60/25 ps uncertainty), and times it twice with OpenSTA:
  SS libraries -> setup (report_worst_slack -max, TNS, the worst path)
  FF libraries -> hold  (report_worst_slack -min, the worst path)
Memory macros are read at the same corner from their own views (``--macro DIR``, <name>_ss.lib / _ff.lib).

    python3 tools/w18/corner_sta.py --orfs-dir <keep-workdir>/orfs --output R.json [--macro physical/...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
LIBS = {"ss": ["asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz", "asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz",
               "asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz", "asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib",
               "asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz"],
        "ff": ["asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz", "asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz",
               "asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz", "asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib",
               "asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz"]}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def script(corner: str, base: str, macros: list[str], post_sdc: list[str] = ()) -> str:
    libs = "\n".join(f"read_liberty {PLAT}/lib/NLDM/{l}" for l in LIBS[corner])
    mlibs = "\n".join(f"read_liberty /src/{m}/{Path(m).name}_{corner}.lib" for m in macros)
    mlefs = "\n".join(f"read_lef /src/{m}/{Path(m).name}.lef" for m in macros)
    check = "max" if corner == "ss" else "min"
    post = "\n".join(f"read_sdc /src/{p}" for p in post_sdc)
    return f"""
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
{mlefs}
{libs}
{mlibs}
read_db {base}/6_final.odb
read_sdc {base}/{sdc}
read_spef {base}/6_final.spef
set_propagated_clock [all_clocks]
{post}
puts "OT_CORNER {corner}"
puts "OT_WS [sta::worst_slack_cmd {check}]"
puts "OT_TNS [sta::total_negative_slack_cmd {check}]"
report_checks -path_delay {check} -group_path_count 1 -format full_clock_expanded
set n 0; set wd 1e9
foreach p [get_pins -hierarchical */D] {{ set s [get_property $p slack_{check}]; if {{$s ne "INF"}} {{ if {{$s < 0}} {{ incr n }}; if {{$s < $wd}} {{ set wd $s }} }} }}
puts "OT_VIOL_D_PINS $n"
puts "OT_WS_REG_D $wd"
set wo 1e9
foreach p [all_outputs] {{ set s [get_property $p slack_{check}]; if {{$s ne "INF" && $s < $wo}} {{ set wo $s }} }}
puts "OT_WS_OUT $wo"
set pr [find_timing_paths -path_delay {check} -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 1]
if {{[llength $pr]}} {{ puts "OT_WS_R2R [get_property [lindex $pr 0] slack]" }} else {{ puts "OT_WS_R2R INF" }}
set pi [find_timing_paths -path_delay {check} -from [all_inputs] -to [all_registers -data_pins] -group_path_count 1]
if {{[llength $pi]}} {{ puts "OT_WS_I2R [get_property [lindex $pi 0] slack]" }} else {{ puts "OT_WS_I2R INF" }}
exit
"""


def _f(v):
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def run(orfs: Path, corner: str, macros: list[str], post_sdc: list[str] = ()) -> dict:
    base = next((orfs / "results/asap7").glob("*/base"))
    rel = f"/work/{base.relative_to(orfs)}"
    (orfs / f"w18_sta_{corner}.tcl").write_text(script(corner, rel, macros, post_sdc))
    cmd = ["docker", "run", "--rm", "-v", f"{orfs}:/work", "-v", f"{ROOT}:/src:ro", "openroad/orfs:asap7lock", "bash",
           "-lc", f"/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/w18_sta_{corner}.tcl"]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    (orfs / f"w18_sta_{corner}.log").write_text(out)
    g = lambda k: (re.search(rf"^{k} (\S+)", out, re.M) or [None, None])[1]  # noqa: E731
    return dict(corner=corner, check="setup" if corner == "ss" else "hold",
                worst_slack_ps=round(float(g("OT_WS")) * 1e12, 2) if g("OT_WS") else None,
                tns_ps=round(float(g("OT_TNS")) * 1e12, 1) if g("OT_TNS") else None,
                worst_register_d_slack_ps=float(g("OT_WS_REG_D")) if g("OT_WS_REG_D") else None,
                worst_reg_to_reg_slack_ps=_f(g("OT_WS_R2R")),
                worst_input_to_reg_slack_ps=_f(g("OT_WS_I2R")),
                worst_output_port_slack_ps=float(g("OT_WS_OUT")) if g("OT_WS_OUT") else None,
                violating_d_pins=int(g("OT_VIOL_D_PINS")) if g("OT_VIOL_D_PINS") else None,
                errors=re.findall(r"\[ERROR[^\n]*", out)[:5],
                odb_sha256=sha(base / "6_final.odb"), spef_sha256=sha(base / "6_final.spef"),
                sdc_sha256=sha(base / sdc))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--orfs-dir", type=Path, required=True)
    ap.add_argument("--macro", action="append", default=[], help="repo-relative macro view dir")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--post-sdc", action="append", default=[],
                    help="repo-relative SDC read after the design is loaded and the clock propagated (e.g. a "
                         "-reference_pin die-context boundary); absent: unchanged behaviour")
    a = ap.parse_args(argv)
    o = a.orfs_dir.resolve()
    rec = dict(schema="opentallas.w18.corner_sta.v1", orfs_dir=str(o),
               sdc=(next((o / "results/asap7").glob("*/base")) / "6_final.sdc").read_text()[:600],
               setup_ss=run(o, "ss", a.macro, a.post_sdc), hold_ff=run(o, "ff", a.macro, a.post_sdc),
               post_sdc={p: sha(ROOT / p) for p in a.post_sdc},
               libraries=LIBS, tool_sha256=sha(Path(__file__)),
               policy="AGENTS.md sign-off corners (2026-09-30): setup at SS, hold at FF, 60/25 ps")
    rec["closes_signoff"] = bool(rec["setup_ss"]["worst_slack_ps"] is not None and rec["setup_ss"]["worst_slack_ps"] >= 0
                                 and rec["hold_ff"]["worst_slack_ps"] is not None and rec["hold_ff"]["worst_slack_ps"] >= 0)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("setup_ss", "hold_ff", "closes_signoff")}, indent=1))


if __name__ == "__main__":
    main()

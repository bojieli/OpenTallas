#!/usr/bin/env python3
"""W18: sign-off-corner STA of a routed ORFS result (AGENTS.md, 2026-09-30: headline clocks close SETUP at SS
and HOLD at FF, 60 ps / 25 ps uncertainty; OWNER OPTION B 2026-10-07: setup is closed at TT, SS is a sensitivity).

Reads the routed 6_final.odb, its SPEF (the extraction's RC is corner-independent here: ASAP7 ships one RC
deck) and its SDC (which carries the 60/25 ps uncertainty), and times it twice with OpenSTA:
  TT libraries -> setup (closure)   SS libraries -> setup (sensitivity: ss_sensitivity)
  FF libraries -> hold  (report_worst_slack -min, the worst path)
Memory macros are read at the same corner from their own views (``--macro DIR``, <name>_ss.lib / _ff.lib).

    python3 tools/w18/corner_sta.py --orfs-dir <keep-workdir>/orfs --output R.json [--macro physical/...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
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
               "asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz"],
        "tt": ["asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz", "asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz",
               "asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz", "asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib",
               "asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz"]}
SETUP_CORNERS = ("ss", "tt")   # OWNER OPTION B 2026-10-07 20:45: closure = setup at TT + hold at FF; SS = sensitivity


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# MULTI-VT (2026-10-07): a route made with OT_MULTI_VT carries LVT/SLVT cells (and their LEF libraries) in its odb.
# Timing such a netlist with the RVT libraries alone leaves those instances without a liberty cell, so the verdict
# would be wrong.  The flavours are read from the odb itself (ground truth for any re-STA copy); OT_STA_VT="LVT SLVT"
# forces them.  An RVT-only odb matches nothing: the script and the record stay byte-identical.
_VT_TAG = {"LVT": "L", "SLVT": "SL"}


def extra_vts(odb: Path) -> list[str]:
    forced = os.environ.get("OT_STA_VT", "").split()
    if forced:
        return [v for v in ("LVT", "SLVT") if v in forced]
    found = set()
    pat = re.compile(rb"_ASAP7_75t_(SL|L)(?![A-Za-z0-9_])")
    with open(odb, "rb") as fh:
        tail = b""
        while len(found) < 2:
            chunk = fh.read(1 << 26)
            if not chunk:
                break
            found.update(m.group(1).decode() for m in pat.finditer(tail + chunk))
            tail = chunk[-32:]
    return [v for v in ("LVT", "SLVT") if _VT_TAG[v] in found]


def corner_libs(corner: str, vts: list[str] = ()) -> list[str]:
    return LIBS[corner] + [l.replace("_RVT_", f"_{v}_") for v in vts for l in LIBS[corner]]


def sdc_basename(value: str) -> str:
    """Accept a single Tcl-safe file name within the routed result directory."""
    if value in (".", "..") or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", value):
        raise argparse.ArgumentTypeError("SDC name must be a simple file basename")
    return value


def script(corner: str, base: str, macros: list[str], post_sdc: list[str] = (),
           sdc_name: str = "6_final.sdc", vts: list[str] = ()) -> str:
    sdc_basename(sdc_name)
    libs = "\n".join(f"read_liberty {PLAT}/lib/NLDM/{l}" for l in corner_libs(corner, vts))
    vt_lefs = "".join(f"\nread_lef {PLAT}/lef/asap7sc7p5t_28_{_VT_TAG[v]}_1x_220121a.lef" for v in vts)
    mlibs = "\n".join(f"read_liberty /src/{m}/{Path(m).name}_{corner}.lib" for m in macros)
    mlefs = "\n".join(f"read_lef /src/{m}/{Path(m).name}.lef" for m in macros)
    check = "max" if corner in SETUP_CORNERS else "min"
    post = "\n".join(f"read_sdc /src/{p}" for p in post_sdc)
    return f"""
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef{vt_lefs}
{mlefs}
{libs}
{mlibs}
read_db {base}/6_final.odb
read_sdc {base}/{sdc_name}
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
# find_timing_paths returns one worst path PER GROUP. Select the minimum
# across groups; index 0 can be asynchronous even when core_clk is worse.
set ot_worst INF
foreach ot_path $pr {{
    set ot_slack [get_property $ot_path slack]
    if {{$ot_worst eq "INF" || $ot_slack < $ot_worst}} {{ set ot_worst $ot_slack }}
}}
puts "OT_WS_R2R $ot_worst"
set pi [find_timing_paths -path_delay {check} -from [all_inputs] -to [all_registers -data_pins] -group_path_count 1]
# find_timing_paths returns one worst path PER GROUP. Select the minimum
# across groups; index 0 can be asynchronous even when core_clk is worse.
set ot_worst INF
foreach ot_path $pi {{
    set ot_slack [get_property $ot_path slack]
    if {{$ot_worst eq "INF" || $ot_slack < $ot_worst}} {{ set ot_worst $ot_slack }}
}}
puts "OT_WS_I2R $ot_worst"
exit
"""


def _f(v):
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def run(orfs: Path, corner: str, macros: list[str], post_sdc: list[str] = (),
        sdc_name: str = "6_final.sdc") -> dict:
    sdc_basename(sdc_name)
    base = next((orfs / "results/asap7").glob("*/base"))
    selected_sdc = base / sdc_name
    if not selected_sdc.is_file():
        raise FileNotFoundError(selected_sdc)
    rel = f"/work/{base.relative_to(orfs)}"
    # Pass only non-default arguments: several sign-off wrappers replace this module's script() with a function of the
    # older (corner, base, macros[, post_sdc]) signature (corner_sta_ref, hbm_cp_*, hbm_su_cp_side, qwen tmr signoff);
    # passing sdc_name unconditionally made every one of them raise TypeError (corner_rc=1, "route crashed").
    args = [corner, rel, macros]
    vts = extra_vts(base / "6_final.odb")
    if post_sdc or sdc_name != "6_final.sdc" or vts:
        args.append(post_sdc)
    if sdc_name != "6_final.sdc" or vts:
        args.append(sdc_name)
    if vts:
        # wrappers that replaced script() with the old signature cannot take vts: fail loudly, never time LVT cells
        # without their liberty
        args.append(vts)
    (orfs / f"w18_sta_{corner}.tcl").write_text(script(*args))
    image = os.environ.get("OPENTALLAS_ORFS_IMAGE", "openroad/orfs:asap7lock")
    cmd = ["docker", "run", "--rm", "-v", f"{orfs}:/work", "-v", f"{ROOT}:/src:ro", image, "bash",
           "-lc", f"/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/w18_sta_{corner}.tcl"]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    (orfs / f"w18_sta_{corner}.log").write_text(out)
    g = lambda k: (re.search(rf"^{k} (\S+)", out, re.M) or [None, None])[1]  # noqa: E731
    return dict(corner=corner, check="setup" if corner in SETUP_CORNERS else "hold",
                worst_slack_ps=round(float(g("OT_WS")) * 1e12, 2) if g("OT_WS") else None,
                tns_ps=round(float(g("OT_TNS")) * 1e12, 1) if g("OT_TNS") else None,
                worst_register_d_slack_ps=float(g("OT_WS_REG_D")) if g("OT_WS_REG_D") else None,
                worst_reg_to_reg_slack_ps=_f(g("OT_WS_R2R")),
                worst_input_to_reg_slack_ps=_f(g("OT_WS_I2R")),
                worst_output_port_slack_ps=float(g("OT_WS_OUT")) if g("OT_WS_OUT") else None,
                violating_d_pins=int(g("OT_VIOL_D_PINS")) if g("OT_VIOL_D_PINS") else None,
                errors=re.findall(r"\[ERROR[^\n]*", out)[:5],
                odb_sha256=sha(base / "6_final.odb"), spef_sha256=sha(base / "6_final.spef"),
                sdc_name=sdc_name, sdc_sha256=sha(selected_sdc),
                **({"vt_flavours_added": vts, "libraries": corner_libs(corner, vts)} if vts else {}))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--orfs-dir", type=Path, required=True)
    ap.add_argument("--macro", action="append", default=[], help="repo-relative macro view dir")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--sdc-name", type=sdc_basename, default="6_final.sdc",
                    help="SDC basename in routed results (default: 6_final.sdc)")
    ap.add_argument("--post-sdc", action="append", default=[],
                    help="repo-relative SDC read after the design is loaded and the clock propagated (e.g. a "
                         "-reference_pin die-context boundary); absent: unchanged behaviour")
    a = ap.parse_args(argv)
    o = a.orfs_dir.resolve()
    rec = dict(schema="opentallas.w18.corner_sta.v1", orfs_dir=str(o),
               sdc=(next((o / "results/asap7").glob("*/base")) / a.sdc_name).read_text()[:600], sdc_name=a.sdc_name,
               setup_tt=run(o, "tt", a.macro, a.post_sdc, a.sdc_name),
               setup_ss=run(o, "ss", a.macro, a.post_sdc, a.sdc_name),
               hold_ff=run(o, "ff", a.macro, a.post_sdc, a.sdc_name),
               post_sdc={p: sha(ROOT / p) for p in a.post_sdc},
               libraries=LIBS, tool_sha256=sha(Path(__file__)),
               policy="OWNER OPTION B 2026-10-07: setup at TT (833.333, >= 0), hold at FF (>= 0), DRC 0; setup at SS is "
                      "reported as a sensitivity (ss_sensitivity); 60/25 ps uncertainty")
    rec["ss_sensitivity"] = rec["setup_ss"]["worst_slack_ps"]
    rec["closes_signoff"] = bool(rec["setup_tt"]["worst_slack_ps"] is not None and rec["setup_tt"]["worst_slack_ps"] >= 0
                                 and rec["hold_ff"]["worst_slack_ps"] is not None and rec["hold_ff"]["worst_slack_ps"] >= 0)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("setup_tt", "setup_ss", "hold_ff", "closes_signoff")}, indent=1))


if __name__ == "__main__":
    main()

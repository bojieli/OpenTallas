#!/usr/bin/env python3
"""Closure-loop calibrate stage: measure a block's real clock insertion after CTS, at SS and FF.

Reads <base>/4_1_cts.odb (+ its SDC: 4_cts.sdc, else 3_place.sdc) with placement-estimated parasitics (or a routed
6_final.odb + SPEF if --routed), propagates clocks and reports, per corner, the clock arrival (rise) at the CLK pins of
(a) BOUNDARY registers -- registers whose D is in the fan-out of a data input, or whose output reaches a data output,
i.e. the flops the IO SDC really talks to -- and (b) every register of the clock.  mean / min / max in ps.  Read-only
on the ORFS dir (Tcl in a temp dir).  Writes JSON and prints shell assignments (CK_SS_MEAN=.. CK_FF_MIN=..) that the
closure loop exports into every later stage of the job (boundary values; *_ALL_* for all registers).

    ck_insertion.py --base RUN/work/orfs/results/asap7/<design>/base [--clock ck] [--routed] --output calib.json
"""
import argparse, json, re, subprocess, tempfile
from pathlib import Path

PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"


def tcl(corner, db, sdc, routed, clock):
    C = "SS" if corner == "ss" else "FF"
    par = "read_spef /base/6_final.spef" if routed else f"source {PLAT}/setRC.tcl\nestimate_parasitics -placement"
    return f"""
foreach l [glob {PLAT}/lib/NLDM/*RVT_{C}*] {{ read_liberty $l }}
foreach l [glob {PLAT}/lib/NLDM/*_LVT_{C}_* {PLAT}/lib/NLDM/*_SLVT_{C}_*] {{ if {{![string match *FAKE* $l]}} {{ read_liberty $l }} }}
read_db /base/{db}
read_sdc /base/{sdc}
{par}
set_propagated_clock [all_clocks]
set regs {{}}
foreach p [all_registers -clock_pins -clock [get_clocks {{{clock}}}]] {{ set n [get_full_name $p]; dict set regs [regsub {{/[^/]+$}} $n {{}}] $n }}
set bnd {{}}
set din [all_inputs -no_clocks]
if {{[llength $din]}} {{ foreach pe [find_timing_paths -path_delay max -from $din -to [all_registers -data_pins] -group_path_count 200000 -endpoint_path_count 1] {{ set i [regsub {{/[^/]+$}} [get_full_name [get_property $pe endpoint]] {{}}]; if {{[dict exists $regs $i]}} {{ dict set bnd $i 1 }} }} }}
foreach pe [find_timing_paths -path_delay max -from [all_registers -clock_pins] -to [all_outputs] -group_path_count 200000 -endpoint_path_count 100000] {{ set i [regsub {{/[^/]+$}} [get_full_name [get_property $pe startpoint]] {{}}]; if {{[dict exists $regs $i]}} {{ dict set bnd $i 1 }} }}
dict for {{i cp}} $regs {{
  set a [get_property [get_pins $cp] arrival_max_rise]
  if {{$a eq "" || $a eq "INF" || $a eq "-INF"}} continue
  puts "OT_CK [expr {{[dict exists $bnd $i] ? 1 : 0}}] $a"
}}
exit
"""


def stats(v):
    return dict(n=len(v), mean=round(sum(v) / len(v), 1), min=round(min(v), 1), max=round(max(v), 1)) if v else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--clock", default="ck")
    ap.add_argument("--routed", action="store_true")
    ap.add_argument("--image", default="openroad/orfs:latest")
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    base = a.base.resolve()
    if a.routed:
        db, sdc = "6_final.odb", "6_final.sdc"
    else:
        db = "4_1_cts.odb"
        sdc = next((s for s in ("4_cts.sdc", "3_place.sdc", "2_floorplan.sdc", "1_synth.sdc") if (base / s).exists()), None)
        if not (base / db).exists() or not sdc:
            raise SystemExit(f"no {db} / SDC under {base}")
    rec = dict(schema="opentallas.closure_loop.ck_insertion.v1", base=str(base), db=db, sdc=sdc, clock=a.clock,
               parasitics="spef" if a.routed else "placement-estimated")
    env = {}
    for corner in ("ss", "ff"):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "s.tcl").write_text(tcl(corner, db, sdc, a.routed, a.clock))
            out = subprocess.run(["docker", "run", "--rm", "-v", f"{base}:/base:ro", "-v", f"{td}:/t:ro", a.image, "bash",
                                  "-lc", "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /t/s.tcl"],
                                 capture_output=True, text=True).stdout
        b, al = [], []
        for m in re.finditer(r"^OT_CK (\d) (\S+)", out, re.M):
            x = float(m[2])
            al.append(x)
            if m[1] == "1":
                b.append(x)
        rec[corner] = dict(boundary=stats(b), all=stats(al), errors=re.findall(r"\[ERROR[^\n]*", out)[:5])
        if not al:
            raise SystemExit(f"{corner}: no clock arrivals for clock {a.clock}\n{out[-1500:]}")
        bs = rec[corner]["boundary"] or rec[corner]["all"]
        for k in ("mean", "min", "max"):
            env[f"CK_{corner.upper()}_{k.upper()}"] = round(bs[k])
            env[f"CK_{corner.upper()}_ALL_{k.upper()}"] = round(rec[corner]["all"][k])
    rec["env"] = env
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(" ".join(f"{k}={v}" for k, v in env.items()))


if __name__ == "__main__":
    main()

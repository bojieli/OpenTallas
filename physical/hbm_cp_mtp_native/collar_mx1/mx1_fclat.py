#!/usr/bin/env python3
"""MX1 face-leaf source latency, balanced at the SINKS by the die clock tree (design standard 2026-10-09, option 1).

Root cause of the fc8 -934 ps (2026-10-10, mtp-mx1-1010.log): the face leaf was given source latency = the interior
insertion AND its own local face tree was propagated on top, so the face pin flops / lockups were clocked one local
tree (~1 ns on fc8's corner-fed single root) later than the core flops they hand over to through a half-cycle lockup.
A die CTS never produces that: MX1 is a hard macro with seven clock pins, and a die tree balances macro clock pins by
their internal insertion (pin arrival + internal insertion = one die target), exactly as for any macro clock pin.
With the die reference at the ck pin (core sinks at C), the die delivers face leaf k at

    source_latency(k) = C - F_k          (F_k = measured local insertion of leaf k behind its own port)

so every face sink is clocked at C, the same instant as the core sinks and as the vclk IO reference (CK_<corner>_MEAN).
Nothing is idealised: both local trees stay propagated, all paths are timed, no exceptions/credits are added; the
leaf arrivals become the die-tree obligation recorded in --record (exported with the view for die-level CTS).

Also fixes the in-flow corner selection: in the ORFS multi-mode CTS/route session the TT ("ss") mode has the FF libraries
loaded too, so `[get_libs *_FF_*]` picked the FF value for TT setup (fc8 used 879 = FF mean at the TT check).  The main
SDC now picks FF only when no TT/SS library is loaded (corner_sta FF session); the in-flow FF mode reads fclat_ff.sdc.

Measured on the calibrate (CTS-only) run of the same job: <cal-base>/4_1_cts.odb, placement parasitics, TT and FF.

    mx1_fclat.py --cal-base '<RUN>/routes/<LABEL>_cal/work/orfs/results/asap7/*/base' \
                 --tt-ref $CK_TT_MEAN --ff-ref $CK_FF_MEAN --out-dir physical/hbm_cp_mtp_native/collar_mx1 --record R.json
"""
import argparse, glob, json, statistics, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
LEAVES = ["cks[0]", "ckn[0]", "cke0[0]", "cke1[0]", "ckw0[0]", "ckw1[0]", "cke[0]", "ckw[0]"]
CORE = "ck[0]"

TCL = r"""
foreach l [glob {plat}/lib/NLDM/*RVT_{C}*] {{ read_liberty $l }}
foreach l [glob -nocomplain {plat}/lib/NLDM/*_LVT_{C}_* {plat}/lib/NLDM/*_SLVT_{C}_*] {{ if {{![string match *FAKE* $l]}} {{ read_liberty $l }} }}
foreach l [glob -nocomplain /macros/*_{c}.lib] {{ read_liberty $l }}
read_db /base/4_1_cts.odb
source {plat}/setRC.tcl
estimate_parasitics -placement
create_clock -name ot_core -period 833 [get_ports {{{core}}}]
set ot_i 0
foreach p {{{leaves}}} {{
  if {{[llength [get_ports -quiet $p]]}} {{ create_clock -name ot_leaf_$ot_i -period 833 [get_ports $p]; puts "OT_LEAFCLK ot_leaf_$ot_i $p"; incr ot_i }}
}}
set_propagated_clock [all_clocks]
foreach c [all_clocks] {{
  foreach p [all_registers -clock_pins -clock $c] {{
    set ar [get_property $p arrival_max_rise]; set af [get_property $p arrival_max_fall]
    puts "OT_ARR [get_full_name $c] $ar $af"
  }}
}}
exit
"""


def measure(base: Path, corner: str, image: str, macros: str | None) -> dict:
    with tempfile.TemporaryDirectory(prefix="mx1_fclat_") as td:
        t = Path(td) / "m.tcl"
        t.write_text(TCL.format(plat=PLAT, C=corner.upper(), c=corner.lower(), core=CORE, leaves=" ".join(LEAVES)))
        mounts = ["-v", f"{base}:/base:ro", "-v", f"{td}:/t:ro"] + (["-v", f"{macros}:/macros:ro"] if macros else [])
        p = subprocess.run(["docker", "run", "--rm", *mounts, image, "bash", "-lc",
                            "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /t/m.tcl"],
                           capture_output=True, text=True)
    names, arr = {"ot_core": CORE}, {}
    for line in p.stdout.splitlines():
        f = line.split()
        if line.startswith("OT_LEAFCLK"):
            names[f[1]] = f[2]
        elif line.startswith("OT_ARR"):
            vals = [float(x) for x in f[2:4] if x.replace(".", "", 1).replace("-", "", 1).isdigit()]
            if vals:
                arr.setdefault(f[1], []).append(min(vals))   # tree insertion of the sink (non-inverting buffers)
    if "ot_core" not in arr:
        sys.exit(f"mx1_fclat: {corner}: no core sinks measured (rc={p.returncode})\n{p.stdout[-3000:]}\n{p.stderr[-3000:]}")
    out = {}
    for c, v in arr.items():
        out[names.get(c, c)] = dict(n=len(v), mean=round(statistics.mean(v), 1), min=round(min(v), 1), max=round(max(v), 1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cal-base", required=True, help="glob of the calibrate run's ORFS results base (holds 4_1_cts.odb)")
    ap.add_argument("--tt-ref", type=float, required=True, help="die reference insertion at TT (CK_TT_MEAN)")
    ap.add_argument("--ff-ref", type=float, required=True, help="die reference insertion at FF (CK_FF_MEAN)")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--record", type=Path, required=True)
    ap.add_argument("--macros", default=None, help="host dir with <macro>_tt.lib / _ff.lib")
    ap.add_argument("--image", default="openroad/orfs:latest")
    a = ap.parse_args()
    bases = sorted(glob.glob(a.cal_base))
    bases = [b for b in bases if (Path(b) / "4_1_cts.odb").exists()]
    if len(bases) != 1:
        sys.exit(f"mx1_fclat: need exactly one calibrate base with 4_1_cts.odb, found {bases} for {a.cal_base}")
    base = Path(bases[0]).resolve()
    if a.macros:
        a.macros = str(Path(a.macros).resolve())
    with ThreadPoolExecutor(2) as ex:
        tt, ff = ex.map(lambda c: measure(base, c, a.image, a.macros), ["tt", "ff"])
    ref = {"tt": a.tt_ref, "ff": a.ff_ref}
    lat, warn = {"tt": {}, "ff": {}}, []
    for corner, m in (("tt", tt), ("ff", ff)):
        core = m[CORE]["mean"]
        if abs(core - ref[corner]) > 100:
            warn.append(f"{corner}: measured core mean {core} differs from reference {ref[corner]} by > 100 ps")
        for leaf in LEAVES:
            if leaf in m:
                lat[corner][leaf] = round(ref[corner] - m[leaf]["mean"], 1)
    if not lat["tt"]:
        sys.exit("mx1_fclat: no face leaf has sinks")
    a.out_dir.mkdir(parents=True, exist_ok=True)
    hdr = ("# GENERATED by physical/hbm_cp_mtp_native/collar_mx1/mx1_fclat.py from this job's calibrate CTS db.\n"
           "# Face leaf k is delivered by the die tree at (die reference insertion - local insertion of leaf k), so its\n"
           "# sinks are clocked at the reference instant (balanced at the sinks; option-1 source latency). Trees stay\n"
           "# propagated; no exception or uncertainty change.\n")
    tt_lines = "\n".join(f"  set_clock_latency -source {v} [get_ports -quiet {{{k}}}]" for k, v in lat["tt"].items())
    ff_lines = "\n".join(f"  set_clock_latency -source {v} [get_ports -quiet {{{k}}}]" for k, v in lat["ff"].items())
    (a.out_dir / "fclat.sdc").write_text(
        hdr + "# Corner: FF value only in a session with FF and no TT/SS libraries (corner_sta FF); the in-flow multi-mode\n"
        "# session loads both, its TT mode takes the TT value and its FF mode reads fclat_ff.sdc.\n"
        "if {[llength [get_libs -quiet *_FF_*]] && ![llength [get_libs -quiet *_TT_*]] && ![llength [get_libs -quiet *_SS_*]]} {\n"
        f"{ff_lines}\n}} else {{\n{tt_lines}\n}}\n")
    (a.out_dir / "fclat_ff.sdc").write_text(hdr + "# In-flow FF (hold) mode: FF value unconditionally.\n" + ff_lines.replace("  set", "set") + "\n")
    rec = dict(schema="opentallas.mx1_fclat.v1", cal_base=str(base), reference=ref, measured=dict(tt=tt, ff=ff),
               die_leaf_source_latency_ps=lat, warnings=warn,
               rule="source_latency(leaf) = reference - local_insertion(leaf); face sinks land at the reference")
    a.record.parent.mkdir(parents=True, exist_ok=True)
    a.record.write_text(json.dumps(rec, indent=1))
    print("MX1_FCLAT", json.dumps(lat), *warn, sep="\n")


if __name__ == "__main__":
    main()

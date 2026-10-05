#!/usr/bin/env python3
"""DS-ROM integration checkpoint, step 3: the S81 configuration with every adopted flag ON elaborates as one design.

Designs (Verilator 5.050 --lint-only, -Wno-fatal: an %Error fails, warnings are counted):
  die_c0_selection  ot_v41_rt_die_l20_c8, rtl/dsrom_sys/wavefront_parent/selection.json parameters as committed
                    (PKG_WAVE=0: the control)
  die_c1_wave       the same + PKG_WAVE=1 (WIN 6): the wavefront controller ot_rom_pkg_ctrl_wf_s81 live in the die
  die_c2_allon      c1 + the adopted W11 indexer / streaming select the L20 runtime drives
                    (-GX_IDX=2 -GX_SEL=1 -GIDX_RING=1 -GSUN=256 -GSUM=64 +define+V41_ATT_CUT +define+V41_L20;
                    tools/w17_current_fastpp_die_rt.py driver_flags), i.e. every adopted flag that the die carries
  elem_q_qp         ot_v41_rom_elem_q_qp_w10 (the routed S81 q element), tools/dsrom_qpipe_exact.py source list
                    + the ot_rom_8192x274_m8 behavioural macro; also yosys 0.68 read_verilog -sv + hierarchy -check
                    (macro and ICG as blackboxes)
  head_tp4          ot_s81_native_head_tp4 (+ s81_native_head_carried, ot_hdc_fastfp), OPT_NATIVE_HEAD 0 and 1

The die needs > 60 GB to lint (measured locally before being moved): run it on the compute host under admit.sh.

    python3 tools/dsrom_integ_elaborate.py run  --design NAME --log DIR/NAME.log      (one design, here)
    python3 tools/dsrom_integ_elaborate.py collect --logs DIR [DIR ...] --out results/rtl/dsrom_integration_20261004/elaborate.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V5 = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
Y68 = Path.home() / ".local/opentallas-tools/yosys-0.68/bin/yosys"
SEL = ROOT / "rtl/dsrom_sys/wavefront_parent/selection.json"
ALLON = ["-GX_IDX=2", "-GX_SEL=1", "-GIDX_RING=1", "-GSUN=256", "-GSUM=64", "+define+V41_ATT_CUT", "+define+V41_L20"]


def die_args(wave: int, allon: bool):
    sel = json.loads(SEL.read_text())
    a = [x for x in sel["verilator_args"] if not x.startswith("-GPKG_WAVE=")] + [f"-GPKG_WAVE={wave}"]
    return ["--top-module", sel["top"], *a, *(ALLON if allon else []), "-f", sel["sources_file"]]


def elem_sources():
    src = (ROOT / "tools/dsrom_qpipe_exact.py").read_text()
    ns = {}
    exec(src[src.index("RTL = ["):src.index("PASS =")], ns)
    return ns["RTL"]


HEAD = ["rtl/rom/collectives/ot_rom_coll_pkg.sv", "rtl/hdc/ot_hdc_fastfp.sv",
        "rtl/test/s81_native_head_terminal/native_head_carried.sv",
        "rtl/dsrom_sys/s81_native_head_connect/ot_s81_native_head_tp4.sv",
        "-y", "rtl/rom/collectives", "-y", "rtl/dsrom_sys/s81_native_head"]
DESIGNS = {
    "die_c0_selection": lambda: die_args(0, False),
    "die_c1_wave": lambda: die_args(1, False),
    "die_c2_allon": lambda: die_args(1, True),
    "elem_q_qp": lambda: ["--top-module", "ot_v41_rom_elem_q_qp_w10", *elem_sources(),
                          "physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8.v"],
    "head_tp4": lambda: ["--top-module", "ot_s81_native_head_tp4", *HEAD],
    "head_tp4_native_on": lambda: ["--top-module", "ot_s81_native_head_tp4", "-GOPT_NATIVE_HEAD=1", *HEAD],
}


def cmd_run(a):
    cmd = [str(V5), "--lint-only", "-Wno-fatal", *DESIGNS[a.design]()]
    log = Path(a.log)
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w") as f:
        f.write("CMD " + " ".join(cmd) + "\n")
        f.flush()
        rc = subprocess.run(["/usr/bin/time", "-v", *cmd], cwd=ROOT, stdout=f, stderr=subprocess.STDOUT).returncode
        f.write(f"rc={rc}\n")
    return rc


def parse(log: Path):
    t = log.read_text(errors="replace")
    m_rc = re.search(r"^rc=(\d+)", t, re.M)
    el = re.search(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): ([\d:.]+)", t)
    rss = re.search(r"Maximum resident set size \(kbytes\): (\d+)", t)
    secs = None
    if el:
        parts = [float(x) for x in el.group(1).split(":")]
        secs = sum(p * 60 ** i for i, p in enumerate(reversed(parts)))
    errs = [ln for ln in t.splitlines() if ln.startswith("%Error")]
    warns = re.findall(r"^%Warning-(\w+)", t, re.M)
    kinds = {}
    for w in warns:
        kinds[w] = kinds.get(w, 0) + 1
    cmd = t.splitlines()[0][4:] if t.startswith("CMD ") else None
    rc = int(m_rc.group(1)) if m_rc else None
    return dict(command=cmd, returncode=rc, status=("pass" if rc == 0 and not errs else
                                                    "incomplete" if rc is None else "fail"),
                errors=errs[:50], error_count=len(errs), warning_count=len(warns), warning_kinds=kinds,
                seconds=secs, peak_rss_GB=round(int(rss.group(1)) / 2 ** 20, 2) if rss else None)


def cmd_collect(a):
    ver = subprocess.run([str(V5), "--version"], capture_output=True, text=True).stdout.strip()
    out = dict(schema="opentallas.dsrom-integration.elaborate.v1", tool=ver, flags="-Wno-fatal (errors fail)",
               all_on_flags=ALLON + ["-GPKG_WAVE=1", "-GPKG_WAVE_WIN=6"], designs={})
    for d in a.logs:
        for log in sorted(Path(d).glob("*.log")):
            if log.stem in DESIGNS:
                out["designs"][log.stem] = parse(log)
    if a.extra:
        out.update(json.loads(Path(a.extra).read_text()))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: (v["status"], v["error_count"], v["warning_count"], v["seconds"], v["peak_rss_GB"])
                      for k, v in out["designs"].items()}, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--design", choices=sorted(DESIGNS), required=True)
    r.add_argument("--log", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--logs", nargs="+", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--extra", default="", help="JSON merged into the record (static checks, yosys, widths)")
    a = ap.parse_args()
    return {"run": cmd_run, "collect": cmd_collect}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())

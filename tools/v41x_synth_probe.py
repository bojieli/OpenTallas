#!/usr/bin/env python3
"""Characterise the V4.1x die synthesis blocker: which module, which construct, which Yosys pass.

The die-top size check (tools/rtl_chip_v41x_die_smoke.py, commit 8c46512d) had to stop at `proc`: Yosys's
coarse `synth` flow and an `opt -fast` loop each ran for over 1.5 h in the attention adapter
(ot_hdc_v41x_att_adapt, the core's X_ATT engine wrapper).  This probe runs the coarse flow ONE PASS AT A TIME
under `yosys -t` (a timestamp on every log line) on single modules and on scratch variants, so the record
names the pass that stalls, the module it stalls in, and what removing each suspect construct does:

  att_asis        ot_hdc_v41x_att_adapt at the core's parameters (ot_hdc_core_v41x.sv, u_att)
  att_mitig       the same with the synthesis-script mitigations available without an RTL edit:
                  no `share`, `opt -fast` instead of full `opt`, `memory -nomap` before any `opt`
  att_no_enc      scratch copy: encode_row() (the stored-format re-encoder) replaced by a pass-through
  att_enc_only    the re-encoder alone: NL = 4 copies of encode_row() on input ports, registered
  att_no_div      scratch copy: the variable dividers of kvw() / xel() replaced by counters' low bits
                  (NOT functionally equivalent; isolates the divider cost only)
  me_asis         ot_hdc_v41x_me_adapt at the core's parameters (the brief named it; the log names att_adapt)

Scratch variants are never written into rtl/: the Codex-owned sources stay unedited.  Every run has a wall
timeout; a run that hits it records the pass it was in and the time spent there.

    python3 tools/v41x_synth_probe.py --variants att_asis,att_no_enc --timeout 7200 \\
        --scratch /home/ubuntu/v41dpnr/probe --out results/asap7_physical/v41x_die_synth
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime
import hashlib
import json
import os
import re
import resource
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools"))
YOSYS = os.environ.get("OT_YOSYS", str(TOOLS_ROOT / "yosys-0.68/bin/yosys"))

ATT = ROOT / "rtl/hdc/v41x/ot_hdc_v41x_att_adapt.sv"
ME = ROOT / "rtl/hdc/v41x/ot_hdc_v41x_me_adapt.sv"
# ot_hdc_core_v41x.sv u_att / u_mw parameters
ATT_PARAMS = {"W": 16, "G": 4, "IL": 8, "AW": 24, "NW": 16, "MP": 1, "H": 16, "D": 32, "TD": 32, "NL": 4,
              "TROWS": 160, "NHMAX": 32}
ME_PARAMS = {"W": 16, "G": 4, "IL": 8, "AW": 24, "NW": 16, "MP": 1, "MG": 8, "BAW": 17}
# the attention engine and what it instantiates (rtl/hdc/v41x/ot_hdc_v41x_attn.sv and its tile)
ATT_DEPS = ["rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/proto/ot_fp32_mul_rne_pipe.sv", "rtl/hdc/ot_hdc_delay.sv",
            "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/hdc/ot_hdc_fastfp.sv",
            "rtl/hdc/v41x/ot_hdc_v41x_wgt_bdot.sv", "rtl/hdc/v41x/ot_hdc_v41x_wgt_red.sv",
            "rtl/hdc/v41x/ot_hdc_v41x_wgt_mac.sv", "rtl/hdc/v41x/ot_hdc_v41x_wgt_tile.sv",
            "rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv", "rtl/hdc/v41x/ot_hdc_v41x_attn.sv"]
ME_DEPS = ATT_DEPS[:9]

# The coarse part of Yosys `synth` (techlibs/common/synth.cc, labels begin..coarse) as separate commands,
# with a size checkpoint after each group, then the generic fine mapping.
COARSE = ["proc", "stat:proc", "flatten", "opt_expr", "opt_clean", "check", "opt -nodffe -nosdff", "fsm", "opt",
          "stat:opt", "wreduce", "peepopt", "opt_clean", "alumacc", "share", "opt", "memory -nomap", "opt_clean",
          "stat:coarse"]
MITIG = ["proc", "stat:proc", "flatten", "memory -nomap", "opt_expr", "opt_clean", "opt -fast", "stat:opt",
         "wreduce", "peepopt", "opt_clean", "alumacc", "opt -fast", "opt_clean", "stat:coarse"]
FINE = ["opt -fast -full", "memory_map", "opt -full", "techmap", "opt -fast", "abc -fast", "opt -fast",
        "stat:fine"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def extract_functions(txt: str, names: list[str]) -> str:
    out = []
    for n in names:
        m = re.search(r"function automatic \[[^\]]+\] " + n + r"\(", txt)
        i = m.start()
        j = txt.index("endfunction", i) + len("endfunction")
        out.append(txt[i:j])
    return "\n\n".join(out)


def variant_sources(name: str, scratch: Path) -> tuple[str, list[Path], dict, dict]:
    """(top, files, parameters, the scratch edits made) of one variant."""
    deps = [ROOT / p for p in ATT_DEPS]
    att = ATT.read_text()
    if name in ("att_asis", "att_mitig", "att_asis_fine"):
        return "ot_hdc_v41x_att_adapt", deps + [ATT], ATT_PARAMS, {}
    if name == "att_no_enc":
        call = "{ok, wd} = encode_row(row);"
        assert att.count(call) == 1
        txt = att.replace(call, "{ok, wd} = {1'b1, {(ROWW - 16*D){1'b0}}, row};")
        d = scratch / "att_no_enc.sv"
        d.write_text(txt)
        return "ot_hdc_v41x_att_adapt", deps + [d], ATT_PARAMS, {"replaced": call,
                                                                 "by": "pass-through of the BF16 row, ok = 1"}
    if name == "att_no_div":
        a = "kvw = wb + (c / kk) * ts + (c % kk) * ks;"
        b = "hh = c / kx; k = c % kx;"
        assert att.count(a) == 1 and att.count(b) == 1
        txt = att.replace(a, "kvw = wb + {8'd0, c[31:16]} * ts + {16'd0, c[15:0]} * ks;")
        txt = txt.replace(b, "hh = {16'd0, c[31:16]}; k = {16'd0, c[15:0]};")
        d = scratch / "att_no_div.sv"
        d.write_text(txt)
        return "ot_hdc_v41x_att_adapt", deps + [d], ATT_PARAMS, {
            "replaced": [a, b], "by": "the counter's high / low halves (divider cost isolation; not equivalent)"}
    if name == "att_enc_only":
        funcs = extract_functions(att, ["fp8_code", "e4m3_of", "fp4_group", "encode_row"])
        txt = f"""`timescale 1ns/1ps
// scratch probe: the NL = 4 stored-format re-encoders of ot_hdc_v41x_att_adapt on input ports, registered
module probe_att_encode #(parameter integer D = 32, parameter integer NL = 4) (
    input  wire clk,
    input  wire [NL*16*D-1:0] rows,
    output reg  [NL*(D/32*265+1)-1:0] y
);
    localparam integer GW = 265;
    localparam integer NG = D / 32;
    localparam integer ROWW = NG * GW;
    integer r;
    always @(posedge clk)
        for (r = 0; r < NL; r = r + 1) y[r*(ROWW+1) +: ROWW+1] <= encode_row(rows[r*16*D +: 16*D]);
{funcs}
endmodule
"""
        d = scratch / "probe_att_encode.sv"
        d.write_text(txt)
        return "probe_att_encode", [d], {"D": 32, "NL": 4}, {"extracted": ["fp8_code", "e4m3_of", "fp4_group",
                                                                         "encode_row"]}
    if name == "me_asis":
        return "ot_hdc_v41x_me_adapt", [ROOT / p for p in ME_DEPS] + [ME], ME_PARAMS, {}
    raise SystemExit(f"unknown variant {name}")


def script_for(name: str, top: str, files: list[Path], params: dict, scratch: Path) -> str:
    steps = MITIG if name == "att_mitig" else COARSE
    if name.endswith("_fine") or name in ("att_enc_only", "me_asis", "att_no_enc"):
        steps = steps + FINE
    cmds = [f"read_verilog -sv -DSYNTHESIS -Irtl/hdc/v41 " + " ".join(str(f) for f in files),
            "chparam " + " ".join(f"-set {k} {v}" for k, v in params.items()) + f" {top}",
            f"hierarchy -check -top {top}"]
    for s in steps:
        if s.startswith("stat:"):
            tag = s.split(":")[1]
            cmds.append(f"tee -q -o {scratch}/{name}.stat_{tag}.json stat -json")
        else:
            cmds.append(s)
    return "\n".join(cmds) + "\n"


STEP_RE = re.compile(r"^\[(\d+\.\d+)\]\s+(\d+(?:\.\d+)*)\.\s+Executing (.+?)\.?$")
CMD_RE = re.compile(r"^\[(\d+\.\d+)\]\s+-- (?:Running command|Executing script file) `(.+?)'")


def parse_log(log: Path) -> dict:
    """Top-level commands with their start times (from `yosys -t`), the last one reached, and the deepest
    sub-pass inside it."""
    top, sub, last_t = [], None, 0.0
    with log.open(errors="replace") as fh:
        for line in fh:
            m = STEP_RE.match(line)
            if m:
                t = float(m.group(1))
                last_t = t
                num, what = m.group(2), m.group(3)
                if "." not in num:
                    top.append({"n": int(num), "pass": what, "start_s": t})
                sub = {"n": num, "pass": what, "start_s": t}
                continue
            if line.startswith("["):
                try:
                    last_t = float(line[1:line.index("]")])
                except ValueError:
                    pass
    for i, s in enumerate(top):
        end = top[i + 1]["start_s"] if i + 1 < len(top) else last_t
        s["seconds"] = round(end - s["start_s"], 2)
    return {"passes": top, "last_pass": top[-1] if top else None, "last_sub_pass": sub,
            "log_last_timestamp_s": last_t}


def stat_summary(p: Path) -> dict | None:
    try:
        d = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    des = d.get("design", {})
    mods = {re.sub(r"^\$paramod\$[0-9a-f]+\\\\?", "", k): {"cells": v.get("num_cells"),
                                                        "memory_bits": v.get("num_memory_bits")}
            for k, v in d.get("modules", {}).items()}
    types = des.get("num_cells_by_type", {})
    top_types = dict(sorted(types.items(), key=lambda kv: -kv[1])[:12])
    return {"cells": des.get("num_cells"), "wire_bits": des.get("num_wire_bits"),
            "memory_bits": des.get("num_memory_bits"), "top_cell_types": top_types, "modules": mods}


def run_variant(name: str, scratch: Path, timeout: int) -> dict:
    scratch.mkdir(parents=True, exist_ok=True)
    top, files, params, edits = variant_sources(name, scratch)
    ys = scratch / f"{name}.ys"
    ys.write_text(script_for(name, top, files, params, scratch))
    log = scratch / f"{name}.log"
    t0 = time.time()
    cmd = ["/usr/bin/time", "-v", "-o", str(scratch / f"{name}.time"), YOSYS, "-t", "-q", "-l", str(log), "-s", str(ys)]
    proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            start_new_session=True)
    try:
        _, err = proc.communicate(timeout=timeout)
        rc, timed_out = proc.returncode, False
        err = (err or "")[-2000:]
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, 9)
        proc.communicate()
        rc, timed_out, err = None, True, ""
    wall = time.time() - t0
    peak_kb = None
    tf = scratch / f"{name}.time"
    if tf.is_file():
        m = re.search(r"Maximum resident set size \(kbytes\): (\d+)", tf.read_text())
        peak_kb = int(m.group(1)) if m else None
    rec = {"variant": name, "top": top, "parameters": params, "scratch_edits": edits,
           "sources": {rel(f): sha(f) for f in files},
           "script": [ln for ln in ys.read_text().splitlines()][1:],
           "returncode": rc, "timed_out": timed_out, "timeout_s": timeout, "wall_s": round(wall, 1),
           "peak_rss_gb": round(peak_kb / 1048576, 2) if peak_kb else None, "stderr_tail": err,
           "log": parse_log(log) if log.is_file() else None,
           "stats": {t: stat_summary(scratch / f"{name}.stat_{t}.json") for t in ("proc", "opt", "coarse", "fine")}}
    if rec["log"] and rec["log"]["passes"]:
        slow = sorted(rec["log"]["passes"], key=lambda s: -s.get("seconds", 0))[:5]
        rec["slowest_passes"] = [{"pass": s["pass"], "seconds": s["seconds"]} for s in slow]
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variants", default="att_asis,att_mitig,att_no_enc,att_enc_only,att_no_div,me_asis")
    ap.add_argument("--timeout", type=int, default=7200)
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "results/asap7_physical/v41x_die_synth")
    ap.add_argument("--jobs", type=int, default=6)
    a = ap.parse_args()
    names = a.variants.split(",")
    a.out.mkdir(parents=True, exist_ok=True)
    yv = subprocess.run([YOSYS, "-V"], capture_output=True, text=True).stdout.strip()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        futs = {ex.submit(run_variant, n, a.scratch, a.timeout): n for n in names}
        for f in cf.as_completed(futs):
            rec = f.result()
            rec.update({"schema": "opentallas.v41x_synth_probe.v1", "tool": "tools/v41x_synth_probe.py",
                        "yosys": yv, "commit": head, "host": os.uname().nodename,
                        "date": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")})
            (a.out / f"probe_{rec['variant']}.json").write_text(json.dumps(rec, indent=1) + "\n")
            print(rec["variant"], "rc", rec["returncode"], "timeout" if rec["timed_out"] else "",
                  "wall", rec["wall_s"], "last", (rec["log"] or {}).get("last_pass"), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

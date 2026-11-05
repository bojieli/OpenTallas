#!/usr/bin/env python3
"""DIE-KV-70/ING 11-04 qkd_hr_ingest_eng RE-FORM: wrapper + core json on qkd_host_native_engine_ing1 (results/kv_ing_rf_1104).
usage (repo root): ing_rf_1104.py < OLD_KIT/core.json
Ports of the hard core unchanged. r_v / r_addr are constant 0 (no RMW read at QPIPE 2), rd_v / rd_data unused (dead input list).
Core json file list: repo-relative; the replaced engine and quantiser are dropped so nothing else can bind them."""
import json, re, sys
from pathlib import Path
SRC = Path("results/kv_host_regen_1/rtl/qkd_hr_ingest_eng")
OUT = Path("results/kv_ing_rf_1104/rtl/qkd_hr_ingest_eng")
t = (SRC / "qkd_hr_ingest_eng.sv").read_text()
t, n = re.subn(r"^\s*qkd_host_native_engine #\(.*\) (\S+) \($", r"    qkd_host_native_engine_ing1 \1 (", t, flags=re.M)
assert n == 1
for port in ("clk_bank", "clk_out", "r_v", "r_rdy", "r_addr", "rd_v", "rd_data", "n_beats"):
    t, n = re.subn(rf"^\s*\.{port}\(.*\n", "", t, flags=re.M)
    assert n == 1, port
t, n = re.subn(r"^\s*wire n\d+;\n", "", t, flags=re.M)
assert n > 0
t, n = re.subn(r",\n(\s*\);\s*\nendmodule)", r"\n\1", t)
if n != 1:
    t, n = re.subn(r"(\.n_sectors\(.*\)),?\n\s*\);", r"\1\n    );", t)
    assert n == 1
t, n = re.subn(r"\nendmodule", "\n    assign r_v[0] = 1'b0;\n    assign r_addr = 32'd0;\nendmodule", t)
assert n == 1
t = t.replace("do not edit.", "do not edit. DIE-KV-70/ING 11-04: engine = qkd_host_native_engine_ing1, see its header.", 1)
(OUT / "qkd_hr_ingest_eng.sv").write_text(t)
cj = json.load(open(SRC / "qkd_hr_ingest_eng_core.json"))
DROP = re.compile(r"/(qkd_hr_ingest_eng|qkd_host_native_engine|ot_hdc_ingest_fp8q)\.sv$")
files = []
for f in json.load(sys.stdin)["files"]:
    if DROP.search(f):
        continue
    m = re.search(r"/(rtl/|physical/|results/)(.*)$", f)
    files.append(m.group(1) + m.group(2) if m else f)
new = sorted(str(p) for p in OUT.glob("*.sv"))
cj["files"] = new + files
cj["member_modules"] = {"u_eng": "qkd_host_native_engine_ing1"}
cj["rf_1104"] = {"transform": "physical/die_plan/qwen_kvsys/cores/harden/ing_rf_1104.py",
                 "form": "DIE-KV-70/ING: cuts in the engine header; r_v, r_addr const 0"}
(OUT / "qkd_hr_ingest_eng_core.json").write_text(json.dumps(cj, indent=1) + "\n")
print("files", len(cj["files"]), "new", len(new))

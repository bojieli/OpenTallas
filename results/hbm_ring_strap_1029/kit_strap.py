#!/usr/bin/env python3
"""HBM-CORES-KITS-10: apply the COORD-approved qid -> strap_qid ID-strap change to a ring_ag kit copy (OWNER 10-25 option B:
strap_* tied at the parent, no pin register, set_false_path -from [get_ports {strap_*}]). Kit-local; the generator change
(face_shell.py / gen_core_kit_hbm.py strap support) is a separate shared-tools item."""
import json, re, sys
from pathlib import Path
K = Path(sys.argv[1])
FP = "set_false_path -from [get_ports {strap_qid}]"
def sub_file(p, pat, rep, cnt_expect=None):
    t = p.read_text(); n = len(re.findall(pat, t)); t2 = re.sub(pat, rep, t)
    if cnt_expect is not None and n != cnt_expect: raise SystemExit(f"{p}: {n} matches of {pat}, expected {cnt_expect}")
    p.write_text(t2); return n
# RTL top (face shell): port rename + no face register
f = next((K / "rtl").glob("*__fshell.sv")); t = f.read_text()
t0 = t
t = t.replace("    input wire [1:0] qid,\n", "    input wire [1:0] strap_qid,  // ID strap (OWNER 10-25 B): tied at the parent, no pin register\n")
t = re.sub(r"    wire \[1:0\] qid__fq;\n    \(\* keep \*\) ot_hbm_face_reg #\(\.W\(2\)\) u_bin_qid \(\.clk\(clk\), \.d\(qid\), \.q\(qid__fq\)\);\n", "", t)
t = t.replace("        .qid(qid__fq),\n", "        .qid(strap_qid),\n")
if t.count("strap_qid") != 2 or "qid__fq" in t or "u_bin_qid" in t: raise SystemExit("fshell edit failed")
f.write_text(t)
# pins / plan pins / io.tcl
pj = json.loads((K / "pins.json").read_text()); n = 0
for p in pj:
    if p.get("bus") == "qid": p["bus"] = "strap_qid"; n += 1
assert n == 2, n
(K / "pins.json").write_text(json.dumps(pj, indent=1))
sub_file(K / "plan_pins.json", r'"qid\[', '"strap_qid[', 2)
sub_file(K / "io.tcl", r"\{qid\[", "{strap_qid[", 2)
# straps declaration (face_guard.kit_strap_list / sdc_lint straps)
(K / "straps.json").write_text(json.dumps({"schema": "opentallas.kit_straps.v1", "straps": ["strap_qid"],
    "note": "ring_ag quarter id, OWNER 10-25 option B, COORD ASK YES 2026-10-29 05:35"}, indent=1) + "\n")
sl = json.loads((K / "sdc_lint.json").read_text())
sl["inputs"] = ["strap_qid" if x == "qid" else x for x in sl["inputs"]]
if isinstance(sl.get("io_floor_ps"), dict) and "qid" in sl["io_floor_ps"]:
    sl["io_floor_ps"]["strap_qid"] = sl["io_floor_ps"].pop("qid")
sl["straps"] = ["strap_qid"]
(K / "sdc_lint.json").write_text(json.dumps(sl, indent=1))
# golden SDC
s = (K / "constraint.sdc").read_text()
s = re.sub(r"(set non_clk_in \[get_ports \{[^}]*?)\bqid\b", r"\1strap_qid", s)
assert "strap_qid" in s and FP not in s
s += f"# ID straps (OWNER 10-25 option B): tied at the parent, quasi-static\n{FP}\n"
(K / "constraint.sdc").write_text(s)
# stage SDCs already written by the run
for p in sorted((K / "run/results").glob("asap7/*/base/*.sdc")):
    if "{qid[" not in p.read_text(): continue
    sub_file(p, r"\{qid\[", "{strap_qid[", 6); p.write_text(p.read_text() + FP + "\n")
# face shell record
fs = json.loads((K / "face_shell.json").read_text())
for k in ("widths", "dirs", "keep"):
    fs[k].pop("qid", None)
fs["in_bits"] -= 2; fs["face_flops"] -= 2; fs["in_buses"] -= 1
fs.setdefault("straps", ["strap_qid"])
(K / "face_shell.json").write_text(json.dumps(fs, indent=1))
print("KIT_STRAP_OK", K)

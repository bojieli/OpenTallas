#!/usr/bin/env python3
"""DIE-S81-67 11-06 S81 plan event: kv_leaf types that inline the SOFT ot_s81sl_vn_b declare -DOT_S81_VN_CONST_ZERO.

Root cause (lec.json, kv_leaf__t1/t3 pre-floor LEC NOT EQUIVALENT, 1027 differs, all in u_u_vn_u_b): the unreset
chunk-sum store lv[*][31] is constant 0 (sums of squares) so Yosys folds it, while the LEC gold reader keeps an unreset
(arbitrary power-up) bit -> a_a/a_b[31] and the tree cone differ.  DIE-S81-31/VEZ 10-29 fixed exactly this for the vn_b
CORE with the opt-in define (lv read sign-masked; miter-proved: vn z PASS 40000 cyc, over-mask control FAILS);
recipes.json sets it for the hard vn_a/vn_b/ve_m cores, but the plan types that inline vn_b soft never got it.
gen_phys.type_verilog_defines() feeds a plan type's verilog_defines to synthesis, RTL lint and the LEC gold alike.
Text edit (one line per type) so the rest of the plan file stays byte-identical; usage: vnzero_event_1106.py REPO
"""
import json, re, sys
from pathlib import Path
P_PATH = Path(sys.argv[1]) / "physical/die_plan/s81/plan_h2_2249.json"
DEF = "OT_S81_VN_CONST_ZERO"
txt = P_PATH.read_text()
P = json.loads(txt)
types = sorted(t for t in P["partition_types"] if t.startswith("ot_s81sl_kv_leaf__t"))
want = json.loads(txt)
for t in types:
    v = want["partition_types"][t].setdefault("verilog_defines", [])
    if DEF not in v:
        v.append(DEF)
for t in types:
    if "verilog_defines" in P["partition_types"][t]:
        raise SystemExit(f"{t} already declares verilog_defines; edit by hand")
    m0 = re.search(r'(?m)^( +)"%s": \{\n' % re.escape(t), txt)
    m = m0 and re.compile(r'(?m)^%s "module": "[^"\n]*",\n' % m0.group(1)).search(txt, m0.end())
    if not m:
        raise SystemExit(f"{t}: partition_types entry not found in the expected text form")
    ins = '%s "verilog_defines": ["%s"],\n' % (m0.group(1), DEF)
    txt = txt[:m.end()] + ins + txt[m.end():]
assert json.loads(txt) == want, "text edit does not equal the intended plan change"
P_PATH.write_text(txt)
print("types:", types)

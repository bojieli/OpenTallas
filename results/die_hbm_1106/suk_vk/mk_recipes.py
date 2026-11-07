#!/usr/bin/env python3
"""part55: recipes_b2.json + wrappers/oneclk for the new SU lane pin tables (the old sha rows stay).  mk_recipes.py REPO PLAN_NEW_DIR"""
import hashlib, json, re, sys
from pathlib import Path
R = Path(sys.argv[1]); P = Path(sys.argv[2]); A = R / "physical/die_plan/hbm_arch_cores"
rp = A / "recipes_b2.json"; t = rp.read_text()
for m, W in (("ot_hbm_su_pg_lane_exp_x_core", 328.32), ("ot_hbm_su_pg_lane_full_x_core", 371.52)):
    sh = hashlib.sha256((P / ("cores/%s__%gx207.36__d44v_p55.json" % (m, W))).read_bytes()).hexdigest()
    rel = "physical/die_plan/hbm_arch_cores/wrappers/oneclk/%s__p55.sv" % m
    w0 = (R / ("physical/die_plan/hbm_arch_cores/wrappers/oneclk/%s.sv" % m)).read_text()
    w1 = re.sub(r"pin table [0-9a-f]{64}\.", "pin table %s (d44v part 55: only the clk row moved)." % sh, w0, count=1)
    assert w1 != w0
    (R / rel).write_text(w1)
    # recipe row text edit: keep the file byte-stable elsewhere; the row holds this module's only wrapper_by_pins_sha256 map
    pat = re.compile(r'("wrapper_by_pins_sha256": \{\n)(\s*)("[0-9a-f]{64}": "physical/die_plan/hbm_arch_cores/wrappers/oneclk/%s\.sv")(\n)' % re.escape(m))
    assert len(pat.findall(t)) == 1, m
    t = pat.sub(lambda q: '%s%s"%s": "%s",\n%s%s%s' % (q[1], q[2], sh, rel, q[2], q[3], q[4]), t)
    print(m, sh[:12], rel)
json.loads(t); rp.write_text(t)

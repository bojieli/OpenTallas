#!/usr/bin/env python3
"""S81-RCK-3 11-06 S81 plan event (COORD 09:41 ruling (1), declared PG-region change): the 11 serdes types gain
  "phy_pg_west_notch_um": 4.32   -> their PHY supply region starts at the PMA macro west edge - 4.32 (site grid) instead of
                                    the partition edge (gen_phys.phy_pg_west_notch); die.pg.domains (die VDDPHY mesh,
                                    bumps) is unchanged, the region still covers every PMA macro.
  "rck_band": {"inst": "u_bound.u_core.u_prx"} -> rck_band.tcl puts the receiver's first-stage capture flops FIRM on the
                                    rows right under the region at their macro pin x.
Why (measured, serdes__t4 attempt_8 4_cts, S81-RCK-2 09:28): the PMA clock pins (RX pma_rck 332.7,1082.1; TX ck
330.7,1093.1) sat 401/412 um inside the no-core-cell PHY region, so their clock wires cost ~680 ps: RX rck setup -1059 TT
(544 ep prx/q -> u_dec.u_face_p_d), TX FF hold -450 (9580 ep).  The notch frees 0.172 mm2 on t4 (10.9 % of the PHY strip,
no macro under it).  Pilot evidence: serdes__t4_vA (see the READY post).
Text edit (lines inserted after each type's "module" line) so the rest of the plan stays byte-identical.
Usage: rck_form_event_1106.py REPO
"""
import json
import re
import sys
from pathlib import Path

P_PATH = Path(sys.argv[1]) / "physical/die_plan/s81/plan_h2_2249.json"
KEYS = {"phy_pg_west_notch_um": 4.32, "rck_band": {"inst": "u_bound.u_core.u_prx"}}
txt = P_PATH.read_text()
P = json.loads(txt)
types = sorted(t for t in P["partition_types"] if t.startswith("serdes__"))
assert len(types) == 11, types
want = json.loads(txt)
for t in types:
    if any(k in P["partition_types"][t] for k in KEYS):
        raise SystemExit(f"{t} already declares a class-form key; edit by hand")
    want["partition_types"][t].update(json.loads(json.dumps(KEYS)))
for t in types:
    m0 = re.search(r'(?m)^( +)"%s": \{\n' % re.escape(t), txt)
    m = m0 and re.compile(r'(?m)^%s "module": "[^"\n]*",\n' % m0.group(1)).search(txt, m0.end())
    if not m:
        raise SystemExit(f"{t}: partition_types entry not found in the expected text form")
    ind = m0.group(1) + " "
    ins = "".join(f'{ind}"{k}": {json.dumps(v)},\n' for k, v in KEYS.items())
    txt = txt[:m.end()] + ins + txt[m.end():]
assert json.loads(txt) == want, "text edit does not equal the intended plan change"
P_PATH.write_text(txt)
print("types:", types)

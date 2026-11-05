#!/usr/bin/env python3
"""S81 serdes KP4 core path fix (COORD 11-05 12:31, DIE-S81-62 12:30 RESULT): the 11 serdes types placed the signed KP4
core ot_s81_kp4_dchn at u_phy.u_dec.u_chn (delta_serdes_kp4_1105.py), but the bound type wrapper instantiates the
column ot_pdie_serdes_col as u_core (bind rtl s81p_serdes__t*.sv / serdes__t*__cl*.sv), and inside it u_dec =
ot_s81_kp4_dec_native_flat_lp (col.sv:76) holds u_chn = ot_s81_kp4_dchn (lp.sv:114, no generate).  KIT_PREFLIGHT
correctly refuses 'component u_phy is neither an instance nor a generate'.  This delta renames the hard core inst
only: no site, outline, pin, clock, reset or define change (contents u_phy stays the descriptive PHY record that
reset_from_master names).
usage: delta_serdes_path_1105.py PLAN_IN PLAN_OUT"""
import json, re, sys
from pathlib import Path

OLD, NEW, MODULE = "u_phy.u_dec.u_chn", "u_core.u_dec.u_chn", "ot_s81_kp4_dchn"
TYPES = ["serdes__t12", "serdes__t13", "serdes__t14", "serdes__t15__cla2127225", "serdes__t15__cla3d02796",
         "serdes__t16", "serdes__t1__clb45db5be", "serdes__t1__clfe1f0815", "serdes__t2", "serdes__t3", "serdes__t4"]
NOTE = "; inst u_core.u_dec.u_chn = bound wrapper column ot_pdie_serdes_col u_core (DIE-S81-63 11-05 path fix)"


def main():
    src, dst = sys.argv[1:3]
    p = json.load(open(src))
    done = []
    for n in TYPES:
        hcs = [h for h in p["partition_types"][n].get("hard_cores", []) if h["module"] == MODULE]
        assert len(hcs) == 1 and hcs[0]["inst"] == OLD, (n, [h["inst"] for h in hcs])
        hcs[0]["inst"] = NEW
        hcs[0]["note"] = hcs[0].get("note", "") + NOTE
        done.append(n)
    left = [n for n, t in p["partition_types"].items() for h in t.get("hard_cores", []) if h["inst"] == OLD]
    assert not left, left
    sys.path.insert(0, str(Path(__file__).resolve().parent)); import compact_plan as CP
    text = open(src).read()                 # changed blocks only, spliced into the source text
    for n in done:
        m = re.search('^  "' + re.escape(n) + '": ', text, re.M)
        _, j = json.JSONDecoder().raw_decode(text, m.end())
        text = text[:m.end()] + CP._d(p["partition_types"][n], 2) + text[j:]
    assert json.loads(text) == p
    open(dst, "w").write(text)
    print(json.dumps({"renamed": done, "from": OLD, "to": NEW}))


if __name__ == "__main__":
    main()

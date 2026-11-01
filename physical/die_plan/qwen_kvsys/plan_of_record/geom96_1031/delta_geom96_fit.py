#!/usr/bin/env python3
"""DIE-KV-58 10-31 (GEOM-96 io_cor, DIE-KV-58 ruling variant A): kv3_io_cor leaves budgets.cland_fit_resize_off_types,
so its kit gets the default OT_CLAND_FIT_RESERVE=resize (gen_phys._cland_fit_mode, AUTOBUILD-PIPE-4): FIRM ring cells
are fitted on their widest drive variant, so the in-place upsize of the 16 ring dsel INVx1 -> INVx2 cannot grow over a
TAPCELL (a4 DPL-0033).  DIE-KV-56 had exempted io_cor because 'OT_CLAND no legal ... landing_ready_ft10_i' under
resize; the i_host_fdi band now fills along x (ring_place ff + fill_axis x).  Variant B (=1, budgets.cland_fit_reserve)
is not taken: it is die-wide.  It was the only entry, so the key is dropped.  Nothing else changes (asserted).
usage: delta_geom96_fit.py PLAN_IN PLAN_OUT"""
import copy, json, sys

src, dst = sys.argv[1:3]
text = open(src).read()
raw = json.loads(text)
orig = copy.deepcopy(raw)
assert raw["budgets"]["cland_fit_resize_off_types"] == ["kv3_io_cor"]
old = ',\n  "cland_fit_resize_off_types": [\n   "kv3_io_cor"\n  ]\n },'
assert text.count(old) == 1
text = text.replace(old, '\n },')
new = json.loads(text)
del orig["budgets"]["cland_fit_resize_off_types"]
assert new == orig
open(dst, "w").write(text)
print("kv3_io_cor: cland_fit_resize_off_types removed -> OT_CLAND_FIT_RESERVE=resize")

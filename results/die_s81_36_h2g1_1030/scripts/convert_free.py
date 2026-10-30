"""DIE-S81-36/H2G1 phase A: re-convert the ADMITTED H2 tree (codex/h2-window-1030 tpqt_slew_geometry plan record,
unchanged masters/count/depth/memberships/sinks) onto FREE native sites of the preserved native 3_place
(56af214f...): the canonical converter site rule plus every placed native instance as a hard BLOCKAGE.
Converter only (no model). Writes conv/convert_free.json (per-node displacement) and conv/rec_free.json
(record with nodes_xy = converted free centres; each driven wire segment lengthened by the driver displacement,
hub kept, so moved children become landed stubs -- conservative wire)."""
from pathlib import Path
import copy, json, sys
R = Path("/srv/opentallas-scratch2/claude/codex-h2-window-1030"); S = R / "src"; D = Path(sys.argv[1])
sys.path.insert(0, str(S / "tools/die_plan"))
import core_plan_to_infra as C
rec = json.loads((R / "tpqt_slew_geometry/plan_geometry.json").read_text())[0]
sites = C.read_sites(R / "baseline/sites.txt")
nat = [tuple(map(float, l.split()[2:6])) for l in (D / "conv/native_occ.txt").read_text().splitlines()]
import bisect, math
_init = C.SiteMap.__init__
def _init_native(self, sites_, strap_clear_um=0.024):
    # canonical init (fixed + hard blockages), then the native instances marked with a row-bisect index (same
    # row-overlap / site-span arithmetic as the canonical loop, only indexed)
    _init(self, sites_, strap_clear_um)
    ys = [row[1] for row in self.rows]
    for (a, b, c, d) in nat:
        k = max(0, bisect.bisect_left(ys, b - self.sh - 1e-6) - 1)
        while k < len(self.rows) and self.rows[k][1] < d - 1e-6:
            if self.rows[k][1] + self.sh > b + 1e-6:
                for s in range(self._s(a, k), self._s(c - 1e-6, k) + 1):
                    self.occ[k].setdefault(s, "#native")
            k += 1
C.SiteMap.__init__ = _init_native
import os
_pl = C.SiteMap.place
C.SiteMap.place = lambda self, name, master, x, y, max_um=20.0: _pl(self, name, master, x, y, max_um=float(os.environ.get("MAXUM", max_um)))
sl = C.convert(rec, sites, "dsfd_coll_lane_w_safe8_ntf", "ck[0]", ndr=(1, 1))
pre = "mp_ck_"
new = {t["name"][len(pre):]: t["xy_um"] for t in sl["core_tree"]["nodes"]}
man = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
r2 = copy.deepcopy(rec); old = {n[0]: list(n[2]) for n in rec["nodes_xy"]}
for n in r2["nodes_xy"]:
    n[2] = list(new[n[0]])
added = 0.0
for w in r2["wire_paths"]:
    e = w["edge"]; k = len(w["segs"]); names = [e + "_br"] + [e + "_r%d" % i for i in range(k - 1)] + [e]
    for i in range(k):
        d = names[i]
        assert d in old, d
        assert man(old[d], w["paths"][i][0]) < 1e-6, (d, old[d], w["paths"][i][0])
        dd = man(old[d], new[d]); w["segs"][i] += dd; added += dd
        w["paths"][i] = [list(new[d])] + w["paths"][i]
disp = sorted(((man(old[k], new[k]), k) for k in old), reverse=True)
r2["name"] = rec["name"] + "_free_native_sites"
r2["free_site_reconvert"] = dict(event="DIE-S81-36/H2G1 2026-10-30", rule="canonical converter + no overlap with any placed native instance of 3_place 56af214f",
                                 native_blockages=len(nat), added_driver_wire_um=round(added, 4))
out = dict(conversion=sl["plan_conversion"], native_blockages=len(nat), max_disp=disp[0], over2=sum(1 for d, _ in disp if d > 2),
           over5=sum(1 for d, _ in disp if d > 5), moved=sum(1 for d, _ in disp if d > 1e-6), top10=disp[:10], added_driver_wire_um=round(added, 4))
(D / "conv/convert_free.json").write_text(json.dumps(out, indent=1) + "\n"); (D / "conv/rec_free.json").write_text(json.dumps([r2]) + "\n")
print(json.dumps({k: v for k, v in out.items() if k != "conversion"}), json.dumps(sl["plan_conversion"]["displacement_um"]))

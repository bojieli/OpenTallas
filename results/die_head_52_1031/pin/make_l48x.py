#!/usr/bin/env python3
"""DIE-HEAD-52 plan event l48x = l48w + raw-export pin fix (COORD 18:0x (4), HEAD-RINGHOLD-2 17:49 (1)).
Every reset_start_raw_<k> export pin (M7 landing_contract pin; the reset_start_raw_exports record keeps the exact raw
FF source xy, which G0C proves against the actual reset tree) that overlaps a
same-layer pin of another net in the generated io.tcl (pin52/ov_*.json from pinov.py; all 51 hits are die spine
tap pins clk/clk_t<n>) moves along its M7 track by +-1.728 um (the HEAD-RINGHOLD-2 hd_turn_a offset, 739.8 -> 741.528)
to the first offset that clears every same-layer pin of the type and stays inside the outline.  hd_turn_a gets the
exact HEAD-RINGHOLD-2 l48g pin value [27.0, 741.528].  No RTL, net, tap or other pin change.
usage: make_l48x.py SRC_DIR OV_JSON OUT_DIR WT"""
import json, shutil, sys, re
from pathlib import Path
src, ovf, out, wt = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
sys.path.insert(0, wt + "/tools/die_plan")
import schema as S, gen_phys as G
raw = json.loads((src / "source_plan.json").read_text()); ov = json.loads(Path(ovf).read_text())
P = S.Plan(json.loads(json.dumps(raw)))
rx = re.compile(r"place_pin -pin_name \{?([^ }]+)\}? -layer (\S+) -location \{([-\d.]+) ([-\d.]+)\} -pin_size \{([-\d.]+) ([-\d.]+)\}")
RW, RH = 0.08, 0.432
rep = {}
for tn, r in sorted(ov.items()):
    hits = r.get("overlaps") or []
    if not hits: continue
    t = raw["partition_types"][tn]; W, H = t["outline_um"]
    rects = []
    for l in G.io_tcl(P, tn, G.type_pins(P, tn)).splitlines():
        m = rx.match(l)
        if m:
            n, ly, x, y, w, h = m.groups(); x, y, w, h = map(float, (x, y, w, h))
            rects.append((n, ly, x - w / 2, y - h / 2, x + w / 2, y + h / 2))
    lc = {p["name"]: p for p in t["clock"]["landing_contract"]["pins"]}
    ex = {e["port"]: e for e in t.get("reset_start_raw_exports", [])}
    for h in hits:
        names = [n for n in h[:2] if n.startswith("rst_start_raw")]
        assert len(names) == 1 and h[2] == "M7", h
        n = names[0]; p, e = lc[n], ex[n]
        x, y0 = p["xy_um"]
        if tn == "hd_turn_a" and n == "rst_start_raw_2":
            new = [27.0, 741.528]
        else:
            new = None
            for d in (1.728, -1.728, 3.456, -3.456, 5.184, -5.184):
                y = round(y0 + d, 4)
                box = (x - RW / 2, y - RH / 2, x + RW / 2, y + RH / 2)
                if box[1] < 0 or box[3] > H: continue
                if any(q[1] == "M7" and q[0] != n and box[0] < q[4] and q[2] < box[2] and box[1] < q[5] and q[3] < box[3]
                       for q in rects):
                    continue
                new = [x, y]; break
            assert new, (tn, n)
        dy = round(new[1] - y0, 4)
        rep.setdefault(tn, []).append(dict(pin=n, tap=[q for q in h[:2] if q != n][0], dy_um=dy,
                                           old_pin=list(p["xy_um"]), new_pin=list(new),
                                           export_source_xy_kept=list(e["xy_um"])))
        p["xy_um"] = list(new)     # the export record keeps the raw FF (source) xy: landing_contract._typed_raw_reset_output
if out.exists(): shutil.rmtree(out)
shutil.copytree(src, out)
(out / "source_plan.json").write_text(json.dumps(raw, indent=1) + "\n")
(out / "l48x_report.json").write_text(json.dumps(rep, indent=1) + "\n")
print(len(rep), "types", sum(len(v) for v in rep.values()), "raw-export pins moved")

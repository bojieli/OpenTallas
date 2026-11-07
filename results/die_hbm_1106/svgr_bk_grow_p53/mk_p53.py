#!/usr/bin/env python3
"""DIE-HBM-82-SVGR d44v part 53 (plan-owner approved DIE-HBM-82 (A)): ot_svgr_bk 259.2 x 207.36 -> 302.4 x 207.36 (+43.2 on the
core-local E face, where the bank FIFOs sit; vC..vO measured: GRT vertical overflow over the SRAM column, east strip too small for
~6000 um2 of CDC FIFO storage).  16 instances (q_hub_nw/ne u_svg_Q{0..3}__b{0,1}, MX and MY).
 * core frame: macros (core_macros.json rects) and every W/N/S/interior pin keep their core-frame site; the 1148 E-face pins
   (in_data, in_v, cr) move +43.2 with the face.  New table cores/ot_svgr_bk__302.4x207.36__d44v_p53.json = the probe-W table
   (pins sha cf83c518e5c3, the table the GRT probes vPW45/vPW60 ran on).  clock_entries (core frame) unchanged.
 * parent placement: the 43.2 is split over the two streets so no neighbour moves: the core-local W face moves 25.92 out
   (street to ot_svgr_top 43.2 -> 17.28), the core-local E face 17.28 out (street to ot_svgr_own 34.56 -> 17.28); origins stay on
   the 8.64 lattice (MX: x -25.92, MY: x -17.28).  Clock taps follow their core-frame entry.
 * internal stations / ft slots: station_resite.py + hyb.py (chains the grow touched) + ft_nudge.py, as part 49.
    mk_p53.py PLANDIR   (unpacked d44v copy; edited in place)"""
import hashlib, json, sys
from pathlib import Path
D = Path(sys.argv[1]); M = "ot_svgr_bk"; W0, W1, H = 259.2, 302.4, 207.36; SW, SE, G = 25.92, 17.28, 8.64
assert abs(SW + SE - (W1 - W0)) < 1e-9
OLDF = "cores/ot_svgr_bk__259.2x207.36__d44v_split.json"; NEWF = "cores/ot_svgr_bk__302.4x207.36__d44v_p53.json"
PROBE_SHA = "cf83c518e5c37d70cb50fa9e3dd11a7c623e1befeaf1ea1178e7799fdba73591"
p = json.loads((D / "die_plan.json").read_text())
pins = json.loads((D / OLDF).read_text()); ne = 0
for q in pins:
    if q["x"] > W0 - 0.2:
        q["x"] = round(q["x"] + (W1 - W0), 3); ne += 1
b = (json.dumps(pins, indent=1)).encode()
if hashlib.sha256(b).hexdigest() != PROBE_SHA: b += b"\n"
assert hashlib.sha256(b).hexdigest() == PROBE_SHA, "new table != probe-W table"
(D / NEWF).write_bytes(b)
rep = dict(event="part53", module=M, outline=[[W0, H], [W1, H]], e_face_pins_moved=ne, pins=len(pins), instances=[], taps=[])
n = 0
for tn, t in p["partition_types"].items():
    hc = t.get("hard_cores") or []; TW, TH = t["outline_um"]
    for c in [c for c in hc if c["module"] == M]:
        assert c["outline_um"] == [W0, H] and c["pins_file"] == OLDF, (tn, c["inst"])
        o = c.get("orient", "R0"); x0, y0 = c["origin_um"]
        if o in ("R0", "MX"): nx0, tdx = round(x0 - SW, 3), -SW
        elif o in ("MY", "R180"): nx0, tdx = round(x0 - SE, 3), +SW
        else: raise SystemExit(("orient", tn, c["inst"], o))
        r = (nx0, y0, nx0 + W1, y0 + H)
        assert r[0] >= 0 and r[2] <= TW, ("outside type", tn, c["inst"])
        for d in hc:
            if d is c: continue
            (a, bb), (w, h) = d["origin_um"], d["outline_um"]
            if d["module"] == M and (a, bb) == (x0, y0): continue
            assert not (a < r[2] + G - 1e-6 and a + w > r[0] - G + 1e-6 and bb < r[3] + G - 1e-6 and bb + h > r[1] - G + 1e-6), \
                ("street/overlap", tn, c["inst"], d["inst"], (a, bb, w, h), r)
        for ch in t.get("channels") or []:
            a, bb, cc, dd = ch["rect_um"]
            assert not (a < r[2] and cc > r[0] and bb < r[3] and dd > r[1]), ("channel", tn, c["inst"], ch["rect_um"])
        c["origin_um"] = [nx0, y0]; c["outline_um"] = [W1, H]; c["pins_file"] = NEWF
        c["note"] = (c.get("note", "") + " | DIE-HBM-82-SVGR d44v part 53: %gx%g (+43.2 core-local E; local W face %g out, local E face %g out; pins core-frame, E face +43.2)" % (W1, H, SW, SE)).strip(" |")
        rep["instances"].append(dict(type=tn, inst=c["inst"], orient=o, origin=[[x0, y0], [nx0, y0]])); n += 1
        nt = 0
        for tp in (t.get("clock") or {}).get("taps") or []:
            if tp.get("kind") == "core" and tp.get("name") == c["inst"]:
                ox = tp["xy"][0]; tp["xy"] = [round(ox + tdx, 4), tp["xy"][1]]; nt += 1
                tp["note"] = (tp.get("note", "") + " | part53: x %+g with its core-frame entry" % tdx).strip(" |")
                rep["taps"].append(dict(type=tn, tap=tp["name"], x=[ox, tp["xy"][0]]))
        assert nt == 1, (tn, c["inst"], nt)
        for s in t.get("contents") or []:
            assert not (s.get("inst") == c["inst"] and "origin_um" in s), ("contents entry", tn, c["inst"])
assert n == 16, n
cm = json.loads((D / "core_macros.json").read_text())
assert cm["cores"][M]["outline_um"] == [W0, H]
cm["cores"][M]["outline_um"] = [W1, H]
cm["cores"][M]["basis"] = cm["cores"][M].get("basis", "") + " | part53 (DIE-HBM-82-SVGR): +43.2 um core-local E (FIFO strip), same macros, same rects"
(D / "core_macros.json").write_text(json.dumps(cm, indent=1) + "\n")
(D / "die_plan.json").write_text(json.dumps(p))
(D / "part53_mk.json").write_text(json.dumps(rep, indent=1) + "\n")
print(json.dumps(dict(instances=n, e_face_pins_moved=ne, taps=len(rep["taps"]))))

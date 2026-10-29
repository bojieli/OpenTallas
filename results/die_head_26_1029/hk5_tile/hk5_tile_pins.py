#!/usr/bin/env python3
"""DIE-HEAD-26 plan delta hk5_tile (GEOM-55 FAIL fix V1, COORD 10-29 07:0x): move the hd_tile data bus windows i (W) / o (E)
from y [354.24, 654.272] to y [708.48, 1008.512] (the free W/E face bands above the elemA cores eA2/eA3, next to the CA landing
ring at y 706-788 and the free E band x 501-708 beside elemB), so every i bit lands <=150 um from its ring gate.  The tile chain
abuts tile->tile (same type, same window), so only the tile-facing ft-slot windows of the chain-end neighbours move:
hd_spn_{e,w}shim_{tx,rx} (spine side stays at 354.24-654.272 -> in-shim jog, stations unchanged) and hd_turn_a (tile side; S face
unchanged).  hd_turn_b's tile-facing window is in its own frame (origin +336.96) -> [371.52, 671.552], fits its 699.84 height.
Shims (682.56) and turn_a (673.92) grow to the tile height 1036.8 (same origin) so the new window lies on their face.
usage: hk5_tile_pins.py IN_PLAN OUT_PLAN"""
import json, sys
OLD = [354.24, 654.272]
NEW = [708.48, 1008.512]
TILE_H = 1036.8
p = json.load(open(sys.argv[1]))
pt = p["partition_types"]
parts = {x["name"]: x for x in p["partitions"]}
log = []
for b in pt["hd_tile"]["buses"]:
    if b["name"] in ("i", "o"):
        assert b["window_um"] == OLD, b
        b["window_um"] = list(NEW); log.append(f"hd_tile.{b['name']} {OLD} -> {NEW}")
# which ft-slot side of each neighbour type faces a tile: from the ports (src part/bus -> dst part/bus)
side = {}
for l in p["ports"]:
    s, d = l.get("src", {}), l.get("dst", {})
    if "part" not in s or "part" not in d:
        continue
    ts, td = parts[s["part"]]["type"], parts[d["part"]]["type"]
    if ts == "hd_tile" and td != "hd_tile":
        side.setdefault(td, set()).add(("in", d["bus"], round(parts[d["part"]]["origin_um"][1] - parts[s["part"]]["origin_um"][1], 3)))
    if td == "hd_tile" and ts != "hd_tile":
        side.setdefault(ts, set()).add(("out", s["bus"], round(parts[s["part"]]["origin_um"][1] - parts[d["part"]]["origin_um"][1], 3)))
for tn, ss in sorted(side.items()):
    t = pt[tn]
    offs = {round(o, 3) for _, _, o in ss}
    assert len(offs) == 1, (tn, offs)            # every instance sits at one y offset to its tile
    off = offs.pop()
    for kind, bus, _ in sorted(ss):
        slot = next(f for f in t["ft_slots"] if bus in (f["name"] + "_i", f["name"] + "_o", f["name"], f"{f['name']}_{kind}"))
        key = f"{kind}_window_um"
        want_old = [round(OLD[0] - off, 3), round(OLD[1] - off, 3)]
        assert [round(x, 3) for x in slot[key]] == want_old, (tn, key, slot[key], want_old)
        slot[key] = [round(NEW[0] - off, 3), round(NEW[1] - off, 3)]
        log.append(f"{tn}.{slot['name']}.{key} {want_old} -> {slot[key]} (frame offset {off})")
    w, h = t["outline_um"]
    need = NEW[1] - off + 4.32
    if h < need:
        nh = round(TILE_H + min(0.0, -off), 3) if off >= 0 else round(TILE_H, 3)
        nh = max(nh, need)
        t["outline_um"] = [w, round(min(TILE_H - max(0.0, off), nh) if off >= 0 else nh, 3)]
        log.append(f"{tn}.outline {[w, h]} -> {t['outline_um']}")
        t["note"] = (t.get("note", "") + " | DIE-HEAD-26 hk5_tile: grown to the tile height so the moved tile-facing window "
                     f"{NEW} lies on its face (GEOM-55)").strip(" |")
# spine side (no in-shim jog, which would need extra stations = added cycles): hd_spn row buses xw_o/xe_o (o-row, spine frame
# +1036.8) and bw_i/be_i (b-row) move by the same +354.24, and the shims' spine-facing windows with them -> every shim stays a
# straight channel, station counts and lane latency unchanged.
DY0 = NEW[0] - OLD[0]
for sn in ("hd_spn", "hd_spn_end"):
  for b in pt[sn]["buses"]:
    if b["name"] in ("xw_o", "xe_o", "bw_i", "be_i"):
        o = [round(x + DY0, 3) for x in b["window_um"]]
        assert o[1] <= pt[sn]["outline_um"][1] - 4.32, (b, o)
        log.append(f"{sn}.{b['name']} {b['window_um']} -> {o}"); b["window_um"] = o
for tn in ("hd_spn_eshim_tx", "hd_spn_eshim_rx", "hd_spn_wshim_tx", "hd_spn_wshim_rx"):
    for f in pt[tn]["ft_slots"]:
        for key in ("in_window_um", "out_window_um"):
            if f[key] == OLD:
                f[key] = list(NEW); log.append(f"{tn}.{f['name']}.{key} (spine side) {OLD} -> {NEW}")
# die-frame port geometry (ports that carry face/window_um) on every tile i/o crossing moves with the tile window
DY = NEW[0] - OLD[0]
nport = 0
for l in p["ports"]:
    s, d = l.get("src", {}), l.get("dst", {})
    ends = [(e, parts[e["part"]]) for e in (s, d) if "part" in e]
    tiles = [(e, q) for e, q in ends if (q["type"] == "hd_tile" and e["bus"] in ("i", "o"))
             or (q["type"].startswith("hd_spn_") and "shim" in q["type"])]
    if not tiles or "window_um" not in l:
        continue
    oy = tiles[0][1]["origin_um"][1]
    assert l["face"] in ("E", "W") and [round(x - oy, 3) for x in l["window_um"]] == OLD, (l, oy)
    l["window_um"] = [round(x + DY, 3) for x in l["window_um"]]
    nport += 1
log.append(f"ports with die-frame window moved +{DY}: {nport}")
p["note"] = p.get("note", "") + " | DIE-HEAD-26 hk5_tile: hd_tile i/o windows 354.24-654.272 -> 708.48-1008.512 (GEOM-55 ring reach)"
json.dump(p, open(sys.argv[2], "w"), indent=1)
print("\n".join(log))

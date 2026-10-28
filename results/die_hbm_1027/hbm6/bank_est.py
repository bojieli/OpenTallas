"""DIE-HBM-6 (B) estimate: hub station banks as template-replica relay hard cores.
Site = station register location snapped to a bin (BIN um). Bank types = width set W (bits).
Sites with >= THR bits become banks; the rest stay soft glue. Cells: flop + F buffers per bit."""
import json, sys, collections, math
P = json.load(open(sys.argv[1])); F = 1.3
CUT = {"q_hub_nw": 3957.12, "q_hub_ne": 8216.64 - 3957.12}   # W/E cut, local x (NE = MY mirror)
def soft_pts(t):
    H = t["hard_cores"]; out = []
    for c in t["contents"]:
        if any(h["inst"] == c["inst"] or h["inst"].startswith(c["inst"] + "_") or h["inst"].startswith(c["inst"] + ".") for h in H):
            continue
        out.append((c["origin_um"][0] + c["outline_um"][0] / 2, c["cells"]))
    return out
for BIN in (8.64, 34.56):
  for W in ([256, 1024], [64, 256, 1024], [128, 512, 2048], [64, 256, 1024, 4096]):
    for THR in (64, 128, 256):
      row = []
      for tn in ("q_hub_nw", "q_hub_ne"):
        t = P["partition_types"][tn]; cut = CUT[tn]
        site = collections.Counter(); sx = {}
        for s in t["internal_stations"]:
            for r in s["regs_um"]:
                k = (round(r[0] / BIN), round(r[1] / BIN)); site[k] += s["bits"]; sx[k] = r[0]
        inst = collections.Counter(); banked = 0; glue = {"W": 0.0, "E": 0.0}; pinbits = 0
        for k, b in site.items():
            side = "W" if sx[k] < cut else "E"
            if b >= THR:
                rem = b; banked += b
                for w in sorted(W, reverse=True)[:-1]:
                    n = rem // w; inst[w] += n; rem -= n * w
                inst[W[0]] += math.ceil(rem / W[0]) if rem else 0
                pinbits += 2 * b
            else:
                glue[side] += b * F
        for x, c in soft_pts(t):
            glue["W" if x < cut else "E"] += c
        row.append((tn, dict(inst), sum(inst.values()), banked, int(glue["W"]), int(glue["E"]), pinbits))
      ok = all(r[4] <= 360e3 and r[5] <= 360e3 for r in row)
      print(f"BIN {BIN} W {W} THR {THR}: " + " | ".join(f"{r[0]} inst {r[2]} {r[1]} banked {r[3]} halfW {r[4]/1e3:.0f}k halfE {r[5]/1e3:.0f}k" for r in row), "OK" if ok else "HALF>360k")

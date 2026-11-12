"""legalise the hand 2x2 ROM block: same block for all 11 stm types, no planned xy (clock/reset/straps/ft regs) inside a
ROM box + halo; scan origins on 8.64 near the N window."""
import json, sys, itertools
p = json.load(open(sys.argv[1]))
G = 8.64; W, H = 121.848, 62.952; HALO = 4.32
KEYS = {"xy", "xy_um", "sites_um", "regs_um", "tap_um", "bit_sites_um"}
def xys(o, key=None):
    if isinstance(o, dict):
        for k, v in o.items(): yield from xys(v, k)
    elif isinstance(o, list):
        if len(o) == 2 and all(isinstance(a, (int, float)) for a in o):
            if key in KEYS: yield o
        else:
            for v in o: yield from xys(v, key)
import collections
for tn, t in sorted(p["partition_types"].items()):
  if not tn.startswith(("sle_stm", "slw_stm")): continue
  pts = []
  ck = t.get("clock", {})
  for k, o in (("count_straps", t.get("count_straps")), ("ft_slots", t.get("ft_slots")), ("is", t.get("internal_stations")),
               ("taps", ck.get("taps")), ("edge", ck.get("edge_clocks")), ("pins", ck.get("landing_contract", {}).get("pins"))):
      pts += [tuple(a) for a in xys(o or [])]
  pts = [(a, b) for a, b in pts if b > 700]
  def ok(x, y):
      x0, y0, x1, y1 = x - HALO, y + 0.012 - HALO, x + W + HALO, y + H + HALO
      return not any(x0 < a < x1 and y0 < b < y1 for a, b in pts)
  res = []
  for i in range(1, 30):
      for cg in range(4, 12):          # column gap in grid units (34.56 .. 95)
          xl = i * G; xr = xl + round((W + cg * G) / G) * G
          if xr + W > 613.44 - 8: continue
          for j in range(95, 150):
              yt = j * G
              if yt + H > 1339.2 - 25: continue
              for rg in range(2, 8):
                  yb = yt - round((H + rg * G) / G) * G
                  if all(ok(*q) for q in ((xl, yt), (xr, yt), (xl, yb), (xr, yb))):
                      cx = (xl + xr + W) / 2
                      res.append(((1339.2 - (yt + H)) + abs(cx - 185) + (yt - yb - H), xl, xr, yt, yb))
  res.sort()
  for r in res[:2]: print(tn, len(pts), [round(v, 2) for v in r])
# common candidates
CANDS = [(xl, xr, yt, yb) for xl in (17.28, 25.92, 34.56, 43.2) for xr in (207.36, 216.0, 224.64, 233.28, 241.92)
         for yt in (1218.24, 1226.88, 1235.52, 1244.16) for yb in (1140.48, 1149.12, 1157.76, 1166.4) if yt - yb >= 69 and xr - xl >= 155]
good = []
for c in CANDS:
    allok = True
    for tn, t in sorted(p["partition_types"].items()):
        if not tn.startswith(("sle_stm", "slw_stm")): continue
        pts = []
        ck = t.get("clock", {})
        for k, o in (("count_straps", t.get("count_straps")), ("ft_slots", t.get("ft_slots")), ("is", t.get("internal_stations")),
                     ("taps", ck.get("taps")), ("edge", ck.get("edge_clocks")), ("pins", ck.get("landing_contract", {}).get("pins"))):
            pts += [tuple(a) for a in xys(o or [])]
        def ok2(x, y):
            x0, y0, x1, y1 = x - HALO, y + 0.012 - HALO, x + W + HALO, y + H + HALO
            return not any(x0 < a < x1 and y0 < b < y1 for a, b in pts)
        if not all(ok2(*q) for q in ((c[0], c[2]), (c[1], c[2]), (c[0], c[3]), (c[1], c[3]))):
            allok = False; break
    if allok:
        good.append(((1339.2 - c[2] - H) + abs((c[0] + c[1] + W) / 2 - 185) + (c[2] - c[3] - H), c))
good.sort(); print("COMMON", good[:6])

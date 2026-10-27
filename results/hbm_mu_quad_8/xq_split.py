#!/usr/bin/env python3
"""HBM-MU-QUAD-8 (COORD quad-7 ruling; GEOM-28 (3) xq HOLD): split the xq_pegress E-face pins by partner side.
Per-bus partner side from the c14 station chains (both instances p0 MX / p1 R0, NW = NE type frame):
  xw_data (2048, partition face buses L28/L29/L32/L33: W / outer-face side for both instances) -> W face M4 + S face M5
          (core S = die-up for MX p0 toward L29 at the N partition face, die-down for R0 p1 toward L32/L33 at the S face)
  rwq (1024, bfq0-3 to the E), bq_* / ed* / rn (xl_ctl, E/S)               -> stay on E, re-spread over the full face
  bq_d (2048, bd ring) stays N (p0 bd E-below, p1 bd W-above: no common better face)
  clk_w / clk_s were M5 pins on the E face (off track) -> N face beside clk/clk_c/clk_e (one entry cluster).
Outline unchanged (181.44x276.48, content TRIAL).  usage: xq_split.py PLANDIR [NW=1296]"""
import json, sys, collections
from pathlib import Path
d = Path(sys.argv[1]); NW = int(sys.argv[2]) if len(sys.argv) > 2 else 1296
f = d / "cores/ot_hgi_sm_xload_xq_pegress__181.44x276.48__content_trial.json"
pins = json.loads(f.read_text()); W, H = 181.44, 276.48
EW, NS = 0.019, 0.019   # edge inset used by the existing table (x 0.019 / 181.421, y 0.019 / 276.461)
def face(q):
    x, y = q["x"], q["y"]; dd = [x, W-x, y, H-y]; return "WESN"[dd.index(min(dd))]
def tracks(lo, hi, n, pitch=0.048, off=0.024, avoid=()):
    k0 = int((lo-off)/pitch)+1; k1 = int((hi-off)/pitch); ks = [k for k in range(k0, k1+1) if round(off+k*pitch, 3) not in avoid]
    if n > len(ks): raise SystemExit(f"{n} pins > {len(ks)} tracks")
    return [round(off+ks[int(i*len(ks)/n)]*pitch, 3) for i in range(n)]
key = lambda q: (q["name"].split("[")[0], int(q["name"].split("[")[1][:-1]) if "[" in q["name"] else 0)
xw = sorted([q for q in pins if q["name"].startswith("xw_data[")], key=key)
east = sorted([q for q in pins if face(q) == "E" and not q["name"].startswith(("xw_data[", "clk_"))], key=lambda q: q["y"])
west_keep = [q for q in pins if face(q) == "W"]
n_used = {q["x"] for q in pins if face(q) == "N"}
before = collections.Counter(face(q) for q in pins)
# W face M4: xw_data[0:NW] evenly over y 8.64..267.84, avoiding the existing W pins' tracks
for q, y in zip(xw[:NW], tracks(8.64, 267.84, NW, avoid={q["y"] for q in west_keep})):
    q.update(layer="M4", x=EW, y=y)
# S face M5: xw_data[NW:] evenly over x 8.64..172.8
for q, x in zip(xw[NW:], tracks(8.64, 172.8, len(xw)-NW)):
    q.update(layer="M5", x=x, y=NS)
# E face: remaining pins re-spread in their existing order over y 8.64..267.84
for q, y in zip(east, tracks(8.64, 267.84, len(east))):
    q.update(y=y)
# clk_w / clk_s -> N face, first free M5 tracks right of clk_e
free = [round(0.024+k*0.048, 3) for k in range(1903, 2500) if round(0.024+k*0.048, 3) not in n_used]
for q, x in zip([q for q in pins if q["name"] in ("clk_w", "clk_s")], free[:2]):
    q.update(layer="M5", x=x, y=round(H-NS, 3))
after = collections.Counter(face(q) for q in pins)
L = dict(N=W, S=W, E=H, W=H)
f.write_text(json.dumps(pins, indent=1) + "\n")
rep = dict(before=dict(before), after=dict(after), avg_pins_per_um={k: round(v/L[k], 2) for k, v in after.items()}, NW=NW)
(d / "xq_split_report.json").write_text(json.dumps(rep, indent=1) + "\n"); print(rep)

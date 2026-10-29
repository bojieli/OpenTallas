#!/usr/bin/env python3
"""QC-A0-KITS-7 10-28: ONE placement rule for the A0 parent hard-children sites (COORD 19:54 ruling: the site set comes
from one rule, not hand nudges).  Input = the Codex A0 child fixture sites (parent_{nk,nl}_children.json, at_exact);
output = cores/a0/parent/{nk,nl}_children.json with the rule recorded.

RULE (applied to every child, pushes only to the right, smallest legal x):
  (a) track phase: the child's vertical-layer pins stay on the parent's M5 track grid (pitch 0.048, offset 0.012):
        R0  -> x       == 0     (mod 0.048)
        MY  -> x + w   == 2*0.012 = 0.024 (mod 0.048)    (the mirror axis x + w/2 lies on the M5 track grid)
      y is unchanged (R0/MY keep y; M4 pins are horizontal).  KIT_PREFLIGHT macro_pin_grid finding: the MY rawleafs at
      x 142.128 (x + w == 0 mod 0.048) put 51 M5 pins 24 nm off track.
  (b) channels: >= 10.8 um (kit_contract MIN_CHANNEL_UM) between any two children that overlap in y, and between
      consecutive x-overlap macro columns (kit_contract macro_channels' column model).
Iterated to a fixed point; fails if a child leaves the outline (minus the core margin).
  python3 a0_child_sites.py FIXTURE_DIR OUT_DIR   (results/qc_a0_kits_7_1028/build_parent_inputs.py imports place())"""
import hashlib
import json
import sys
from pathlib import Path

PITCH, OFF = 0.048, 0.012        # ASAP7 M5 (vertical) pitch / platform make_tracks offset
MIN_GAP = 10.8                   # tools/die_plan/kit_contract.py MIN_CHANNEL_UM
OUTLINE = (457.92, 1157.76)      # A0 hard-core outline (cores/a0_core.json)
MARGIN = 4.32
NM = 1000                        # integer nm arithmetic
RULE = ("QC-A0-KITS-7 a0_child_sites.py: (a) R0 x == 0, MY x+w == 0.024 (mod 0.048 M5 pitch; mirror axis on the M5 "
        "track grid); (b) >= 10.8 um between y-overlapping children and between x-overlap macro columns; smallest "
        "legal x, pushed right only; y unchanged")


def lattice_x(x_nm, w_nm, orient):
    """smallest x' >= x on the rule-(a) lattice for this orientation"""
    p = round(PITCH * NM)
    want = 0 if orient == "R0" else (round(2 * OFF * NM) - w_nm) % p
    return x_nm + ((want - x_nm) % p)


def clusters(cs):
    bs = sorted(cs, key=lambda c: c["x"])
    out = []
    for c in bs:
        if out and c["x"] < max(d["x"] + d["w"] for d in out[-1]):
            out[-1].append(c)
        else:
            out.append([c])
    return out


def place(children):
    gap = round(MIN_GAP * NM)
    cs = [dict(c, x=round(c["at"][0] * NM), y=round(c["at"][1] * NM), w=round(c["size_um"][0] * NM),
               h=round(c["size_um"][1] * NM)) for c in children]
    for c in cs:
        if c["orient"] not in ("R0", "MY"):
            raise SystemExit(f"{c['inst']}: orient {c['orient']} has no rule (R0/MY only)")
    for _ in range(100):
        moved = False
        for c in cs:
            nx = lattice_x(c["x"], c["w"], c["orient"])
            if nx != c["x"]:
                c["x"], moved = nx, True
        for a in cs:                      # (b) y-overlapping neighbours
            for b in cs:
                if a is b or not (a["x"] <= b["x"]) or a["x"] == b["x"] and id(a) > id(b):
                    continue
                if a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"] and b["x"] < a["x"] + a["w"] + gap:
                    b["x"] = lattice_x(a["x"] + a["w"] + gap, b["w"], b["orient"])
                    moved = True
        cl = clusters(cs)                 # (b) column channels
        for left, right in zip(cl, cl[1:]):
            hi = max(d["x"] + d["w"] for d in left)
            for d in right:
                if d["x"] < hi + gap:
                    d["x"] = lattice_x(hi + gap, d["w"], d["orient"])
                    moved = True
        if not moved:
            break
    else:
        raise SystemExit("site rule did not converge")
    for c in cs:
        if c["x"] < MARGIN * NM or c["x"] + c["w"] > (OUTLINE[0] - MARGIN) * NM:
            raise SystemExit(f"{c['inst']}: x {c['x'] / NM} leaves the outline")
    return cs


def main():
    fx, out = Path(sys.argv[1]), Path(sys.argv[2])
    rec = {}
    for t in ("nk", "nl"):
        fb = (fx / f"parent_{t}_children.json").read_bytes()
        src = json.loads(fb)
        cs = place(src)
        moves = {}
        ch = []
        for s, c in zip(src, cs):
            x = c["x"] / NM
            d = round(x - s["at"][0], 3)
            if d:
                moves[f"{s['module']} {s['orient']} x {s['at'][0]}"] = f"+{d}"
            ch.append(dict(inst=s["inst"], module=s["module"], at=[x, s["at"][1]], orient=s["orient"],
                           size_um=s["size_um"]))
        (out / f"{t}_children.json").write_text(json.dumps(dict(
            schema="opentallas.qc.a0_parent_children.v1", parent=f"qfd_tile_{t}_a0c",
            source=f"Codex A0 child fixture parent_{t}_children.json (sha256 {hashlib.sha256(fb).hexdigest()})",
            site_rule=RULE,
            moves=moves, children=ch), indent=1) + "\n")
        rec[t] = moves
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main()

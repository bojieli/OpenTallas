#!/usr/bin/env python3
"""Audit the compact BF die assembly against its closed pin geometry.

Does not replace child qualification or the full die hop/STA gates. Emits the
missing native BF transport pins explicitly rather than silently tying them.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_s81_fulldie as G
from s81.bf_direct_pins import coverage, groups, SEAM_UM, VIEW


def audit(mutate=False):
    f = G.real_lef(f"{VIEW}/ot_s81_bf_front/ot_s81_bf_front.lef")
    c = G.real_lef(f"{VIEW}/ot_v41_bf_col/ot_v41_bf_col.lef")
    assert (f["w"], f["h"]) == (100.224, 198.72)
    assert (c["w"], c["h"]) == (450.144, 198.72)
    bad, longest, bits = [], 0, 0
    for side in (0, 1):
        for cp, fp in zip(groups(True)["ci"], groups(False)[f"c{side}"]):
            cl, cr = c["pins"][cp]
            fl, fr = f["pins"][fp]
            cy, fy = (cr[1] + cr[3]) / 2, (fr[1] + fr[3]) / 2
            if mutate and bits == 0:
                fy += 0.048
            if cl != "M4" or fl != "M4" or abs(cy - fy) > 1e-6:
                bad.append((cp, fp, cy, fy, cl, fl))
            # East column is MY: both seam pins face the front on the same
            # track; endpoint distance includes the actual pin inset.
            cx = (cr[0] + cr[2]) / 2
            fx = (fr[0] + fr[2]) / 2
            hop = (c["w"] - cx) + SEAM_UM + (fx if side == 0 else f["w"] - fx)
            longest = max(longest, hop)
            bits += 1
    assert not bad, bad[:3]
    width = 2 * c["w"] + f["w"] + 2 * SEAM_UM
    assert abs(width - 1002.888) < 1e-6
    covered = coverage(G)
    for row in covered.values():
        p = ROOT / row["view"]
        row["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
        row["uncovered_by_port"] = {}
        for pin in row.pop("uncovered"):
            base = pin.split("[")[0]
            row["uncovered_by_port"][base] = row["uncovered_by_port"].get(base, 0) + 1
    return dict(schema="s81-bf-direct-geometry-v1", width_um=width, height_um=f["h"],
                seam_um=SEAM_UM, seam_bits=bits, misaligned=0, max_seam_hop_um=round(longest, 3),
                views=covered, native_transport_complete=False,
                native_transport_remedy="Carry BF family control and BF16 stream from the production PQ union lane; hph is a HALF=0 diagnostic",
                child_qualification="Separate child_lint and die access gates remain required")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    rec = audit()
    try:
        audit(mutate=True)
    except AssertionError:
        rec["mutant_shift_track"] = "FAIL as required"
    else:
        raise AssertionError("seam track shift mutant survived")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(f"BF_DIRECT_AUDIT PASS bits={rec['seam_bits']} width={rec['width_um']} mutant=FAIL native_transport=OPEN")


if __name__ == "__main__":
    main()

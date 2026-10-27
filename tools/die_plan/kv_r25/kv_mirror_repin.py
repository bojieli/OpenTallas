#!/usr/bin/env python3
"""CLOCK-KV-R25 (COORD GATE-PINS-2): make every mirrored pin view an EXACT image of its R0 view (one GDS per type).

    kv_mirror_repin.py CORES_DIR OUT_DIR --report R.json

Pairs (R0 view, variant, op).  For an MX variant, a pin whose variant position is not the MX image of its R0 position
(the 'kept' sub-core reset pins <sub>__rst_n on the N/S face) is moved IN THE R0 VIEW to an MX-invariant site: the
core centre row y = H/2 inside the 12.8a centre entry island (M5 under the entry stack, same as the core rst_n of
KV-CORE-SLICE-1), on the free M5 track nearest the centre that is >= 2 tracks from every other pin of the row and clear
of the M5 PG stripe pair; then the variant is rewritten as the exact image of the new R0 view (stale variant clocks,
e6 fMX, become the image of the R0 centre entry too).  For the MY head_p pair only the fMY view is used by the plan: the
R0 view is rewritten as the exact MY image of fMY.  Data pins never move.  Written as <stem>_r25m.json in OUT_DIR.
"""
import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kv_island_ports import pg_ok, M5_OFF, M5_PITCH  # noqa: E402

ISL_HALF = 4.32
PAIRS = [("kv3_pv_pair_pins", "kv3_pv_pair_pins_fMX", "MX"),
         ("kv3_head_eighth_e0_pins", "kv3_head_eighth_e0_pins_fMX", "MX"),
         ("kv3_head_eighth_e5_pins", "kv3_head_eighth_e5_pins_fMX", "MX"),
         ("kv3_head_eighth_e6_pins", "kv3_head_eighth_e6_pins_fMX", "MX"),
         ("qkd_kvs_pc_h_head_p_pins_fMY", "qkd_kvs_pc_h_head_p_pins", "MY")]   # (master, image, op)


def outline(d):
    return tuple(float(v) for v in d["frame"].split("outline ")[1].split(" x "))


def image(p, op, w, h):
    q = dict(p)
    if op == "MX":
        q["y"] = round(h - p["y"], 4)
    else:
        q["x"] = round(w - p["x"], 4)
    return q


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cores")
    ap.add_argument("out")
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    src, out = Path(a.cores), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rep = {}
    for base, var, op in PAIRS:
        B = json.loads((src / f"{base}.json").read_text())
        V = json.loads((src / f"{var}.json").read_text())
        w, h = outline(B)
        vb = {p["name"]: p for p in V["pins"]}
        moved = []
        NB = copy.deepcopy(B)
        if op == "MX":
            bad = [p for p in NB["pins"] if (round(vb[p["name"]]["x"], 4), round(vb[p["name"]]["y"], 4)) !=
                   (round(p["x"], 4), round(h - p["y"], 4))]
            cy = round(h / 2, 4)
            row = [p for p in NB["pins"] if abs(p["y"] - cy) < 1.0 and p["layer"] == "M5"]
            ents = [p for p in row if p["name"].endswith("clk[0]") or p["name"] in ("ck[0]", "clk", "rst_n[0]")]
            cx = sum(p["x"] for p in ents) / len(ents) if ents else w / 2
            for p in bad:
                if p["name"].split("__")[-1].startswith("clk") and abs(p["y"] - cy) < 1e-6:
                    continue        # R0 clock already at the centre entry (MX-invariant): only the variant was stale
                if "rst_n" not in p["name"] or p["layer"] != "M5":
                    raise SystemExit(f"{base}: asymmetric pin {p['name']} is not an M5 reset pin: not re-pinned")
                used = [q["x"] for q in row]
                k0 = round((cx - M5_OFF) / M5_PITCH)
                for d in range(0, 200):
                    hit = None
                    for k in (k0 + d, k0 - d):
                        x = round(M5_OFF + k * M5_PITCH, 4)
                        if pg_ok(x) and all(abs(x - u) > 2 * M5_PITCH - 1e-6 for u in used) and abs(x - w / 2) <= ISL_HALF - 0.1:
                            hit = x
                            break
                    if hit is not None:
                        break
                if hit is None:
                    raise SystemExit(f"{base}: no free centre-island track for {p['name']}")
                moved.append(dict(pin=p["name"], from_=[p["x"], p["y"]], to=[hit, cy]))
                p["x"], p["y"] = hit, cy
                row.append(p)
            NB["source"] = B["source"] + (" | CLOCK-KV-R25 10-27 (COORD GATE-PINS-2): MX-asymmetric reset pins -> centre "
                                          "entry row (MX-invariant); variant views = exact images")
            NV = copy.deepcopy(V)
            NV["pins"] = [image(p, op, w, h) for p in NB["pins"]]
            NV["source"] = V["source"] + f" | CLOCK-KV-R25 10-27: rewritten as the exact {op} image of {base}_r25m.json"
            outs = {base: NB, var: NV}
        else:   # MY head_p: master = fMY (plan view); image = R0 view
            NV = copy.deepcopy(V)
            NV["pins"] = [image(p, op, w, h) for p in B["pins"]]
            NV["source"] = V["source"] + f" | CLOCK-KV-R25 10-27: rewritten as the exact {op} image of {base}_r25m.json (unused by hm_r24)"
            diff = [p["name"] for p in NV["pins"] if (p["x"], p["y"]) != (vb[p["name"]]["x"], vb[p["name"]]["y"])]
            moved = [dict(pin=n, note="R0 view (unused) now the image of the plan fMY view") for n in diff]
            outs = {base: B, var: NV}
        for stem, d in outs.items():
            body = (json.dumps(d, indent=1) + "\n").encode()
            (out / f"{stem}_r25m.json").write_bytes(body)
        # verify exact image
        mb = {p["name"]: p for p in outs[base]["pins"]}
        mv = {p["name"]: p for p in outs[var]["pins"]}
        nimg = sum(1 for n, p in mb.items() if (image(p, op, w, h)["x"], image(p, op, w, h)["y"], p["layer"]) !=
                   (mv[n]["x"], mv[n]["y"], mv[n]["layer"]))
        rep[base] = dict(variant=var, op=op, moved=moved, non_image_pins_after=nimg, pins=len(mb),
                         sha256={s: hashlib.sha256((out / f"{s}_r25m.json").read_bytes()).hexdigest() for s in outs})
        print(base, var, op, "moved", len(moved), "non-image after", nimg)
        for m in moved:
            print("   ", m)
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")


if __name__ == "__main__":
    main()

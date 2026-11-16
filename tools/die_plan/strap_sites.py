"""strap_sites.py (QC-CB-GEN-1115, FABLE-PD-QC-1115 class "static strap-port nets"): site every ID strap port on the pin face of the tile it feeds.

The plan puts all strap ports (plan id_straps[].sites_um) at one hub in the middle channel; a tile_id pin on the tile face away from
the hub makes a static 1 mm net over the tile (cbn_q11: 36 of the 48 macro-crossing 2-pin nets).  Rule, per type and per strap
strap_u_t_<X>_<Y>_tile_id (consumer = hard core u_t<X><Y>, pin tile_id[i]):
  face   = the tile face that holds the consumer pins (W or E, from the pin x against the placed bbox centre)
  site   = SITE_OUT_UM outside that face, M5 track snapped (landing_contract.on_track), bit i at the centroid y + (i - (w-1)/2) * SITE_PITCH_UM
  checks = never inside any hard-core bbox grown by HALO_UM, inside the die, >= CLEAR_UM from every other planned interior pin of the
           type (taps, landings, other straps, reset pins ...); a colliding site moves in whole track steps along y (up to 40 steps),
           else the strap is left on its plan sites and reported.
A strap whose current sites are all within NEAR_UM (Manhattan) of the consumer pins is left alone (t22 in the cb family).
Output rows JSON (type -> strap -> {face, sites_um, before_um, after_um}) + a crossers table: the 2-pin-net macro-crossing count of the
class before / after by the same bbox test the kit's macro_cross_check.tcl uses (> 300 um, a leg over a macro interior).
python3 -I tools/die_plan/strap_sites.py PLAN.json --out DIR [--types a,b] [--type-re '^cb']"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys as G      # noqa: E402
import landing_contract as LC   # noqa: E402
import schema as S        # noqa: E402

SITE_OUT_UM = 6.48
SITE_PITCH_UM = 0.864
HALO_UM = 4.32
CLEAR_UM = 0.864
NEAR_UM = 150.0
CROSS_MIN_UM = 300.0
TILE_ID = re.compile(r"^strap_u_t_(\d+)_(\d+)_tile_id$")


def _core_pins(plan_dir, core):
    f = Path(core["pins_file"])
    f = f if f.is_absolute() else plan_dir / f
    return {p["name"]: p for p in json.loads(f.read_text())["pins"]}


def _placed(core, p):
    """core-frame pin (x, y) -> type frame, using the plan's own orientation transform (gen_phys._orient_rect_r)"""
    w, h = core["outline_um"]
    ox, oy = core["origin_um"]
    tx, ty = core.get("track_offset_um", [0, 0])
    x0, y0, _, _ = G._orient_rect_r((p["x"], p["y"], p["x"], p["y"]), w, h, core.get("orient", "R0"))
    return ox + tx + x0, oy + ty + y0


def _bbox(core):
    w, h = core["outline_um"]
    ox, oy = core["origin_um"]
    tx, ty = core.get("track_offset_um", [0, 0])
    if core.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
        w, h = h, w
    return ox + tx, oy + ty, ox + tx + w, oy + ty + h


def crosses(a, b, boxes, min_um=CROSS_MIN_UM):
    """the macro_cross_check.tcl test on two points: Manhattan > min and a bbox leg over a macro interior"""
    if abs(a[0] - b[0]) + abs(a[1] - b[1]) <= min_um:
        return False
    xl, xh, yl, yh = min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1])
    for x0, y0, x1, y1 in boxes:
        x0, y0, x1, y1 = x0 + 2, y0 + 2, x1 - 2, y1 - 2
        hx, hy = min(xh, x1) - max(xl, x0), min(yh, y1) - max(yl, y0)
        if hx > 0 and hy > 0 and (hx > min_um or hy > min_um):
            return True
    return False


def _declared_interior(t):
    """interior pin sites the plan declares for type t (everything but the tile_id straps being moved): other straps, reset spine pins,
    landing-contract pins, clock taps.  Generated tap-grid / reset pins need the plan's sink files and are not read here: the kit's own
    port audit (pin_audit.py) is the final collision gate."""
    out = []
    for sp in (t.get("id_straps") or []) + (t.get("count_straps") or []) + (t.get("reset_spine_pins") or []):
        if TILE_ID.match(sp.get("name", "")):
            continue
        out += [tuple(map(float, xy)) for xy in sp.get("sites_um") or []]
    ck = t.get("clock") or {}
    out += [tuple(map(float, p["xy_um"])) for p in (ck.get("landing_contract") or {}).get("pins", []) if p.get("xy_um")]
    out += [tuple(map(float, tp["xy"])) for tp in ck.get("taps") or [] if tp.get("xy")]
    return out


def site_type(P, tn, plan_dir):
    t = P.types[tn]
    cores = {c["inst"]: c for c in t.get("hard_cores", []) or []}
    boxes = [_bbox(c) for c in cores.values()]
    W, H = t["outline_um"]
    taken = _declared_interior(t)
    rows, before, after, skipped = {}, 0, 0, []
    for sp in (t.get("id_straps") or []) + (t.get("count_straps") or []):
        m = TILE_ID.match(sp["name"])
        if not m or not sp.get("sites_um"):
            continue
        core = cores.get(f"u_t{m.group(1)}{m.group(2)}")
        if core is None:
            skipped.append((sp["name"], "no consumer core"))
            continue
        pins = _core_pins(plan_dir, core)
        want = [_placed(core, pins[f"tile_id[{i}]"]) for i in range(sp["width"])]
        cur = [tuple(s) for s in sp["sites_um"]]
        nb = sum(crosses(c, w, boxes) for c, w in zip(cur, want))
        near = all(abs(c[0] - w[0]) + abs(c[1] - w[1]) <= NEAR_UM for c, w in zip(cur, want))
        before += nb
        if near:
            continue
        x0, y0, x1, y1 = _bbox(core)
        west = abs(want[0][0] - x0) < abs(want[0][0] - x1)
        sx = x0 - SITE_OUT_UM if west else x1 + SITE_OUT_UM
        yc = sum(w[1] for w in want) / len(want)
        used = list(taken)
        for off in range(0, 41):
            ok, new = True, []
            for sgn in ((1,) if off == 0 else (1, -1)):
                dy = sgn * off * SITE_PITCH_UM * 1.0
                new = []
                for i in range(sp["width"]):
                    x, y = LC.on_track(P, sp["layer"], sx, yc + dy + (i - (sp["width"] - 1) / 2) * SITE_PITCH_UM)
                    new.append((round(x, 4), round(y, 4)))
                ok = all(0 <= x <= W and 0 <= y <= H for x, y in new)
                ok = ok and not any(b[0] - HALO_UM < x < b[2] + HALO_UM and b[1] - HALO_UM < y < b[3] + HALO_UM
                                    for x, y in new for b in boxes)
                ok = ok and not any(abs(x - ux) < CLEAR_UM and abs(y - uy) < CLEAR_UM for x, y in new for ux, uy in used)
                if ok:
                    break
            if ok:
                break
        if not ok:
            skipped.append((sp["name"], "no collision-free site column"))
            after += nb
            continue
        taken += new
        na = sum(crosses(c, w, boxes) for c, w in zip(new, want))
        after += na
        rows[sp["name"]] = dict(face="W" if west else "E", sites_um=[list(s) for s in new], crossers_before=nb, crossers_after=na)
    return rows, before, after, skipped


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--out", required=True)
    ap.add_argument("--types", default="")
    ap.add_argument("--type-re", default=r"^cb[nfx]_")
    a = ap.parse_args(argv)
    P = S.Plan(S.load(a.plan))
    plan_dir = Path(a.plan).resolve().parent
    names = [n for n in P.types if (n in a.types.split(",") if a.types else re.match(a.type_re, n))]
    out, table = {}, []
    for tn in sorted(names):
        rows, b, af, sk = site_type(P, tn, plan_dir)
        if rows or sk:
            out[tn] = dict(straps=rows, skipped=sk)
        table.append((tn, b, af, len(rows), len(sk)))
    od = Path(a.out)
    od.mkdir(parents=True, exist_ok=True)
    (od / "strap_rows_cb.json").write_text(json.dumps(out, indent=1) + "\n")
    lines = ["type\ttile_id_crossers_before\tafter\tstraps_moved\tskipped"] + ["\t".join(map(str, r)) for r in table]
    (od / "strap_rows_cb_table.tsv").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

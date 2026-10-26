#!/usr/bin/env python3
"""QC-A0 10-24: A0 v7 core clock taps = the R4 GRID (CP1 r8 RULING, COORD 10-23 21:26) + the v6 sink-anchored taps as
ADDITIONS (tools/die_plan/README.md "Tap method": every partition gets a grid of taps at budgets.tap_pitch_um 400 um,
every sink on its nearest tap; clock.tap_mode grid+sinks only ADDS sink-anchored taps, never replaces the grid).

The A0 core (457.92 x 1157.76) is a hard core of the CB quad partitions; its taps are interior M7 pins where the die
spine drops M8 -> M7.  v6 (gen_a0c6_taps.py) had ONLY sink-anchored taps (k-medians of the v5 placed flops, NK 32 /
NL 31).  v7:
  grid      schema.tap_grid's rule on the core outline: ceil(w/400) x ceil(h/400) = 2 x 3 taps at the cell centres,
            moved off the hard children by schema.tap_clear (>= 8.64 um from every child box, inside the outline,
            >= 8.64 um from the taps already placed), then snapped like v6 (x on an M7 track in a PG-free band, y on an
            M6 track) and re-checked clear;
  additions every v6 sink tap that is not within taps.SEP_UM (8.64 um, one spine drop) of a grid tap, in v6 order.
Names: ck = grid tap 0 (SW cell; the RTL clock port), ck_t1..ck_t5 the other grid taps (row-major from SW), then the
additions ck_t6.. .  Reset landing copies keep the tap they had in v6 (renamed); a copy whose v6 tap merged into a grid
tap follows that grid tap.

    gen_a0c7_taps.py nk|nl            writes tools/qwen_romleaf/a0core/{qfd_tile_<k>_a0c7_pins.tcl, a0c7_<k>_taps.json,
                                      a0c7_<k>_rst_taps.tsv} from the v6 kit / tap files
"""
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import schema as S  # noqa: E402
import taps as T  # noqa: E402
from gen_a0c6_taps import free_x  # noqa: E402

PITCH_UM = 400.0
M6_PITCH, M6_OFF = 0.064, 0.016


def snap_y(y):
    return round(M6_OFF + M6_PITCH * round((y - M6_OFF) / M6_PITCH), 3)


def children(k):
    fp = json.loads((ROOT / f"physical/ref_tile/qfd_tile_{k}_a0cv6/floorplan.json").read_text())
    W, H = fp["die"][2], fp["die"][3]
    boxes = [dict(origin_um=[b["x"], b["y"]], outline_um=[b["w"], b["h"]]) for b in fp["blocks"] if b.get("kind") == "child"]
    return W, H, boxes


def clear_of(boxes, x, y, W, H, clear=S.TAP_CLEAR_UM):
    if not (clear <= x <= W - clear and clear <= y <= H - clear):
        return False
    for b in boxes:
        (ox, oy), (cw, ch) = b["origin_um"], b["outline_um"]
        if ox - clear < x < ox + cw + clear and oy - clear < y < oy + ch + clear:
            return False
    return True


def grid_taps(W, H, boxes, pitch=PITCH_UM):
    """schema._grid_taps on the core outline with the children as hard_cores (tap_clear), snapped to the pin tracks."""
    t = dict(outline_um=[W, H], hard_cores=boxes)
    nx, ny = max(1, math.ceil(W / pitch - 1e-9)), max(1, math.ceil(H / pitch - 1e-9))
    out = []
    for j in range(ny):
        for i in range(nx):
            x, y = S.tap_clear(t, (i + 0.5) * W / nx, (j + 0.5) * H / ny, [(a, b) for _, a, b in out])
            sx, sy = free_x(x), snap_y(y)
            if not clear_of(boxes, sx, sy, W, H):
                # the snap moved it back into a halo: walk the snapped x outward on the free tracks
                for dx in [d * 0.064 for d in range(1, 400)]:
                    for cand in (free_x(x + dx), free_x(x - dx)):
                        if cand is not None and clear_of(boxes, cand, sy, W, H):
                            sx = cand
                            break
                    else:
                        continue
                    break
            assert clear_of(boxes, sx, sy, W, H), (i, j, sx, sy)
            out.append(("ck" if not out else f"ck_t{len(out)}", sx, sy))
    return out


def build(k):
    W, H, boxes = children(k)
    v6 = json.loads((HERE / f"a0c6_{k}_taps.json").read_text())
    grid = grid_taps(W, H, boxes)
    taps = [dict(name=n, xy=[x, y], kind="grid") for n, x, y in grid]
    rename = {}
    for tp in v6["taps"]:
        x, y = tp["xy"]
        near = [g for g in taps if g["kind"] == "grid" and abs(g["xy"][0] - x) + abs(g["xy"][1] - y) < T.SEP_UM]
        if near:
            rename[tp["name"]] = near[0]["name"]
            near[0].setdefault("merged_v6", []).append(tp["name"])
            continue
        n = f"ck_t{len(taps)}"
        rename[tp["name"]] = n
        taps.append(dict(name=n, xy=[x, y], kind="sinks", v6=tp["name"], sinks_v5=tp["sinks"], reach_um=tp["reach_um"]))
    # reset copies: v6 table (inst, tap, x, y, move) -> the renamed tap's site
    site = {t["name"]: t["xy"] for t in taps}
    rst = []
    for line in (HERE / f"a0c6_{k}_rst_taps.tsv").read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        inst, tap = line.split("\t")[:2]
        n = rename[tap]
        rst.append((inst, n, site[n][0], site[n][1]))
    # pins: the v6 pin plan without its clock taps + the v7 taps
    pins_in = (HERE / f"qfd_tile_{k}_a0c6_pins.tcl").read_text().splitlines(keepends=True)
    keep = [l for l in pins_in if not re.match(r"place_pin -pin_name \{ck(_t\d+)?\}", l)
            and not l.startswith("# QC-P6-A0 10-23 A0 v6") and not l.startswith("# k-medians")
            and not l.startswith("# (") ]
    hdr = (f"# QC-A0 10-24 A0 v7 ({k.upper()}): {len(taps)} interior M7 clock taps = R4 grid {sum(t['kind'] == 'grid' for t in taps)} "
           f"({PITCH_UM:.0f}-um pitch, CP1 r8 RULING) + {sum(t['kind'] == 'sinks' for t in taps)} v6 sink-anchored ADDITIONS "
           f"(gen_a0c7_taps.py); every tap a die-spine M8 -> M7 drop.\n")
    body = "".join(f"place_pin -pin_name {{{t['name']}}} -layer M7 -location {{{t['xy'][0]} {t['xy'][1]}}} "
                   f"-pin_size {{0.032 0.768}}   ;# {t['kind']}" +
                   (f" (v6 {t['v6']}, {t['sinks_v5']} v5 sinks)" if t["kind"] == "sinks" else
                    (f" (absorbs v6 {','.join(t['merged_v6'])})" if t.get("merged_v6") else "")) + "\n" for t in taps)
    (HERE / f"qfd_tile_{k}_a0c7_pins.tcl").write_text("".join(keep) + hdr + body)
    with open(HERE / f"a0c7_{k}_rst_taps.tsv", "w") as f:
        f.write("# inst\ttap\tx_um\ty_um (gen_a0c7_taps.py: v6 reset landing copy -> its v6 tap, renamed / merged into v7)\n")
        for r in rst:
            f.write("\t".join(str(v) for v in r) + "\n")
    rec = dict(tool="tools/qwen_romleaf/a0core/gen_a0c7_taps.py", rule="R4 grid 400 um + v6 sink taps as additions "
               "(CP1 r8 RULING COORD 10-23 21:26)", outline_um=[W, H], pitch_um=PITCH_UM,
               grid=sum(t["kind"] == "grid" for t in taps), additions=sum(t["kind"] == "sinks" for t in taps),
               n_taps=len(taps), v6_merged_into_grid=sorted(n for t in taps for n in t.get("merged_v6", [])),
               taps=taps, rename_v6=rename, reset_copies=len(rst))
    (HERE / f"a0c7_{k}_taps.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(f"{k}: {len(taps)} taps = grid {rec['grid']} + additions {rec['additions']}; v6 merged {rec['v6_merged_into_grid']}; "
          f"grid {[(t['name'], t['xy']) for t in taps if t['kind'] == 'grid']}")
    return rec


if __name__ == "__main__":
    for k in sys.argv[1:] or ["nk", "nl"]:
        build(k)

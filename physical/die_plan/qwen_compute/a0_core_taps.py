"""QC-P6-A0 10-23: declare the A0 core clock drops per CB quad from inputs/a0_core_taps.json (GEOM-REVIEW7 18:34).

A0 v6 (kits qfd_tile_n{k,l}_a0cv6) has 32 (NK) / 31 (NL) interior M7 clock tap pins, sink-anchored on the placed flop
columns; every pin is a die-spine M8 -> M7 drop.  This replaces each core's single '<inst>.ck' tap in the CB quad's
clock.taps with one 'kind: core' tap per core pin (type frame: core origin + track offset, MY mirrors x), each carrying
the plan insertion budget (250 +/- 40 at the slowest sink, R4) and the neighbour budget (<= 80 ps) in its note, so the
spine generator and G0 (check_taps_cores: inside the outline, unique names) see ~127-128 drops per quad instead of 4.
No input file -> no change (the plan regenerates byte-identically).  Raises on a budget that contradicts the die clock.
"""
import json
from pathlib import Path


def declare(P, path, die_clock):
    path = Path(path)
    if not path.is_file():
        return None
    cfg = json.loads(path.read_text())
    ins, tol, nb = cfg["insertion_ps"], cfg["insertion_tol_ps"], cfg["neighbour_skew_ps"]
    if abs(ins - die_clock["insertion_ps"]) > die_clock["insertion_tol_ps"] or nb > die_clock["neighbour_skew_ps"]:
        raise ValueError(f"a0_core_taps: budget {ins}+/-{tol} ps, neighbour {nb} contradicts the die clock {die_clock}")
    per_quad = {}
    for tn, t in sorted(P.types.items()):
        hcs = [hc for hc in t.get("hard_cores", [])
               if hc.get("module", "").startswith(("qfd_tile_nk_a0c", "qfd_tile_nl_a0c"))]
        if not hcs:
            continue
        old = {f"{hc['inst']}.ck" for hc in hcs}
        root = t["clock"]["tap_um"]
        taps = [tp for tp in t["clock"].get("taps", []) if tp["name"] not in old]
        n = 0
        for hc in hcs:
            v = "nl" if hc["module"].startswith("qfd_tile_nl") else "nk"
            var = cfg["variants"][v]
            if "reset_depth" in var:
                depth = var["reset_depth"]
                if not isinstance(depth, int) or isinstance(depth, bool) or depth < 1:
                    raise ValueError("a0_core_taps: reset_depth must be a positive integer")
                hc.setdefault("reset", {})["depth"] = depth
            cw, _ = hc["outline_um"]
            ox, oy = hc["origin_um"]
            dx, dy = hc.get("track_offset_um", [0.0, 0.0])
            for tp in var["taps"]:
                x, y = tp["xy"]
                xy = [round(ox + dx + (cw - x if hc.get("orient") == "MY" else x), 4), round(oy + dy + y, 4)]
                taps.append(dict(name=f"{hc['inst']}.{tp['name']}", kind="core", xy=xy, orient=hc.get("orient", "R0"),
                                 insertion_ps=ins, insertion_tol_ps=tol,
                                 budget_owner=f"{var['kit']} post-CTS OT_TAP_CHECK (slowest sink <= {ins + tol} ps TT)",
                                 from_root_um=round(abs(xy[0] - root[0]) + abs(xy[1] - root[1]), 1),
                                 note=f"A0 {v.upper()} core tap {tp['name']} ({var['layer']} pin, spine M8 -> M7 drop, "
                                      f"length-matched branch); neighbour/core-to-core skew <= {nb} ps TT+FF on RC; "
                                      f"v5-placed sinks {tp['sinks_v5']}, reach {tp['reach_um']} um"))
                n += 1
        t["clock"]["taps"] = taps
        per_quad[tn] = n
    return dict(source=str(path.name), insertion_ps=ins, insertion_tol_ps=tol, neighbour_skew_ps=nb,
                taps_per_core={v: len(x["taps"]) for v, x in cfg["variants"].items()}, drops_per_quad=per_quad)

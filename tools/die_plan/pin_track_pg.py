#!/usr/bin/env python3
"""pin_track_pg.py -- C-PIN-TRACK-PG (C-STREET-R2, 11-26): PG-aware hard-core pin tracks and PG-pitch macro moves.  Opt-in, default off.

Cases (FABLE-INDEP / CLASS-OWNERS-R2 11-26): S81 t23 c985 W M4 pins 504/769 blocked by PG via pads; S81 mus_C PDN-0110 x1 (missing M5-M6 via);
HEAD host_w 45 PDN-0110 after a 2.592 um SRAM shift (M5 VDD strap overlaps M4 rail ends by 12 nm, no via); HEAD lep0N f797 428 pair edge pins
on PG stripes.  Common cause: a hard core whose origin is off the 4.32 um PG pitch moves every pin of its faces onto a different phase of the
partition PG stripes (schema.PART_PG_BANDS), and a horizontal M4/M6 pin ends inside the vertical M5/M7 stripe band where the PG via pad sits.

Plan flag (default off, no effect when absent): top-level  pin_track_pg: {"pg": 1}.  Everything here is pure functions; nothing edits a plan.

  pin_blocked(layer, x)         pin on `layer` whose along-stripe coordinate is x (type frame): True if a PG stripe band / via pad covers it
                                (vertical pins M5/M7: own band; horizontal pins M4: M5 band; M6: M7 and M5 bands)
  free_tracks(layer, tracks)    PG-aware pick: the tracks of one layer that are not blocked (never reorders)
  snap_origin(o, mode)          macro origin snapped to the PG pitch (nearest | down | up); 4.32 um lattice
  on_pitch(o)                   origin already on the PG pitch
  census(t, pins_for)           report-only per type: {cores, off_pitch, pins, blocked, pdn_0110_est}; pdn_0110_est = pins blocked on cores whose
                                origin is off the pitch (the HEAD host_w mechanism); never a gate
"""
import math

import schema as S

PG_PITCH_UM = 4.32
EPS = 1e-3
VERT = {"M3", "M5", "M7", "M9"}
# horizontal layer -> vertical PG bands its pin end / via pad can sit under
HORIZ_BANDS = {"M4": ("M5",), "M6": ("M7", "M5"), "M2": ("M5",), "M8": ("M7",)}


def enabled(raw):
    f = (raw or {}).get("pin_track_pg") if isinstance(raw, dict) else None
    return bool(isinstance(f, dict) and f.get("pg"))


def pin_blocked(layer, x):
    if layer in VERT:
        return S.pg_blocked(layer, x)
    return any(S.pg_blocked(b, x) for b in HORIZ_BANDS.get(layer, ()))


def free_tracks(layer, tracks):
    return [x for x in tracks if not pin_blocked(layer, x)]


def on_pitch(v):
    return abs(v / PG_PITCH_UM - round(v / PG_PITCH_UM)) * PG_PITCH_UM < EPS


def snap_origin(o, mode="nearest"):
    f = {"nearest": round, "down": math.floor, "up": math.ceil}[mode]
    return [round(f(v / PG_PITCH_UM - 1e-9 if mode != "nearest" else v / PG_PITCH_UM) * PG_PITCH_UM, 4) for v in o]


def census(t, pins_for, snap=False):
    """pins_for(core) -> [(layer, x_local, y_local)] in the core frame; orientation + origin applied here (core outline / orient / origin_um)."""
    out = dict(cores=0, off_pitch=0, pins=0, blocked=0, pdn_0110_est=0, missing_tables=0)
    for c in t.get("hard_cores") or []:
        if not (c.get("origin_um") and c.get("outline_um")):
            continue
        pl = pins_for(c)
        if not pl:
            if c.get("pins_file"):
                out["missing_tables"] += 1
            continue
        out["cores"] += 1
        org = snap_origin(c["origin_um"]) if snap else c["origin_um"]
        off = not (on_pitch(org[0]) and on_pitch(org[1]))
        out["off_pitch"] += off
        w, h = c["outline_um"]
        o = c.get("orient", "R0")
        nb = 0
        for ly, x, y in pl:
            X = w - x if o in ("MY", "R180") else x
            if pin_blocked(ly, org[0] + X):
                nb += 1
        out["pins"] += len(pl)
        out["blocked"] += nb
        if off:
            out["pdn_0110_est"] += nb
    return out


def _resolver(raw, plan_path, tree):
    import json
    from pathlib import Path
    from types import SimpleNamespace

    import plan_inputs

    roots = raw.get("plan_root") or []
    roots = [roots] if isinstance(roots, str) else list(roots)
    if tree:
        roots.append(str(tree))
    context = SimpleNamespace(path=plan_path, raw={"plan_root": roots})
    ancestors = list(Path(plan_path).resolve().parents[1:3]) if plan_path else []
    cache = {}

    def pins_for(c):
        pf = c.get("pins_file")
        if not pf:
            return []
        if pf not in cache:
            path = plan_inputs.resolve(context, pf)
            if path is None and not Path(pf).is_absolute():
                path = next((d / pf for d in ancestors if (d / pf).is_file()), None)
            cache[pf] = []
            if path is not None:
                j = json.loads(path.read_text())
                rows = j if isinstance(j, list) else j.get("pins", [])
                cache[pf] = [(q["layer"], q["x"], q["y"]) for q in rows
                             if isinstance(q, dict) and {"layer", "x", "y"} <= q.keys()]
        return cache[pf]

    return pins_for


def findings(raw, plan_path=None, tree=None, pins_for=None, **kw):
    """report-only ADV-PIN-TRACK-PG lines; empty unless the plan flag pin_track_pg.pg (or OT_PIN_TRACK_PG=1) is set.  Never raises."""
    import os
    if not (enabled(raw) or os.environ.get("OT_PIN_TRACK_PG") == "1"):
        return []
    out, pf = [], pins_for or _resolver(raw, plan_path, tree)
    n_off = n_blk = n_missing = 0
    try:
        pt = raw.get("partition_types") or {}
    except AttributeError:
        return out
    for name, t in sorted(pt.items()):
        try:
            a = census(t, pf)
        except Exception as e:  # a malformed type never stops the others
            out.append(f"WARN ADV-PIN-TRACK-PG {name}: not checked ({type(e).__name__}: {str(e)[:80]})")
            continue
        if a["off_pitch"] or a["pdn_0110_est"]:
            n_off += 1
            b = census(t, pf, snap=True)
            out.append(f"WARN ADV-PIN-TRACK-PG {name}: {a['off_pitch']}/{a['cores']} hard core origin(s) off the {PG_PITCH_UM} um PG pitch, "
                       f"{a['blocked']}/{a['pins']} pins under PG stripe/via-pad bands ({a['pdn_0110_est']} on off-pitch cores = PDN-0110 estimate); "
                       f"snapped to pitch: {b['blocked']} blocked; fix: move the macro in {PG_PITCH_UM} um steps (snap_origin) and pick pin tracks with free_tracks")
        n_blk += a["blocked"]
        n_missing += a["missing_tables"]
    out.append(f"WARN ADV-PIN-TRACK-PG summary {n_off} type(s) with off-pitch cores or PDN-0110 estimate, "
               f"{n_blk} blocked pins, of {len(pt)} types. {n_missing} declared pin table uses unavailable or empty")
    return out

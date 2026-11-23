"""ADV-PORT-WINDOW-PAIR (PRECHECK-R2, COORD 11-22; an estimator, never a gate).

Both ends of a die-level port must declare the SAME pin geometry in the die frame: the port's own face/window_um/layers
(when given), the source type's bus / ft-slot `_o` window and the destination type's bus / ft-slot `_i` window, each
mapped through its partition's origin + orient.  schema.py validate refuses any pair that differs (face, layers, order,
or a window end by > 1e-6 um: "port P: src type geometry ... != dst type geometry ... in the die frame").  A type split or
a pin nudge on ONE side re-snaps that side's window while the other side's type is unchanged (S81 J8 53ad14f1fc91 /
94a9f357e401: SVC primary split moved svc_1_rs ft8_o by 0.212 um vs slice_station__t8 ft9_i, svc_15_rs ft7_o by 0.02 um vs
slice_station__t22 ft9_i; the replan died at schema after the gate started).

This module reproduces exactly that comparison (schema.Plan._type_geom / geom_to_die / port_geom_from, the decl loop in
validate) on the raw plan dict with stdlib only, without building the Plan or running the rest of validate: one pass over
raw["ports"], seconds on the 100-MB S81 plan.
"""
import time

CHECK = "ADV-PORT-WINDOW-PAIR"
DIE_PART = "@die"
OPP = dict(N="S", S="N", E="W", W="E")
TOL = 1e-6                     # schema.py validate tolerance on a window end
MAX_LINES = 20


def _type_face(orient, face):
    """schema.Plan.type_face (an involution: also die_face)."""
    if orient in ("MX", "R180") and face in "NS":
        return OPP[face]
    if orient in ("MY", "R180") and face in "EW":
        return OPP[face]
    return face


def _type_geom(t, bus):
    """schema.Plan._type_geom: (type face, window, layers, order) declared on the type for `bus`, or None."""
    for b in t.get("buses") or []:
        if b.get("name") == bus and "window_um" in b and "face" in b and "layers" in b:
            return b["face"], b["window_um"], b["layers"], b.get("order", "lsb_low"), "bus"
    for s_ in t.get("ft_slots") or []:
        for sfx, fk, wk in (("_i", "in_face", "in_window_um"), ("_o", "out_face", "out_window_um")):
            if bus == str(s_.get("name")) + sfx and wk in s_:
                stem = "in" if sfx == "_i" else "out"
                lays = s_.get(stem + "_layers", s_.get("layers"))
                if lays:
                    return s_[fk], s_[wk], lays, s_.get(stem + "_order", s_.get("order", "lsb_low")), "ft_slot"
    return None


def _geom_to_die(p, t, g):
    """schema.Plan.geom_to_die for one instance."""
    tf, (a, b), lays, order, src = g
    a, b = float(a), float(b)
    w, h = t["outline_um"]
    o = p.get("orient", "R0")
    df = _type_face(o, tf)
    if tf in "EW":
        base, ext, flip = p["origin_um"][1], h, o in ("MX", "R180")
    else:
        base, ext, flip = p["origin_um"][0], w, o in ("MY", "R180")
    if flip:
        a, b = ext - b, ext - a
        order = "lsb_high" if order == "lsb_low" else "lsb_low"
    return df, [round(float(base) + a, 6), round(float(base) + b, 6)], list(lays), order, src


def _side_geom(parts, types, pr, side):
    e = pr[side]
    part = e.get("part")
    if part == DIE_PART or part not in parts or parts[part].get("type") not in types:
        return None
    t = types[parts[part]["type"]]
    g = _type_geom(t, e.get("bus"))
    if g is None:
        return None
    df, win, lays, order, src = _geom_to_die(parts[part], t, g)
    if side == "dst" and pr["src"].get("part") != DIE_PART:
        df = OPP[df]
    return df, win, lays, order, src


def pair_mismatches(raw):
    """[(port id, (na, ga), (nb, gb), what, delta_um)] for every consecutive declared geometry pair schema would refuse."""
    types = raw.get("partition_types") or {}
    parts = {p.get("name"): p for p in raw.get("partitions") or []}
    out = []
    for pr in raw.get("ports") or []:
        try:
            if not isinstance(pr.get("src"), dict) or not isinstance(pr.get("dst"), dict):
                continue
            decl = []
            if all(k in pr for k in ("face", "layers", "window_um")):
                decl.append(("port", (pr["face"], [float(v) for v in pr["window_um"]], list(pr["layers"]),
                                      pr.get("order", "lsb_low"), "port")))
            for side in ("src", "dst"):
                try:
                    g = _side_geom(parts, types, pr, side)
                except (KeyError, TypeError, ValueError, IndexError):
                    g = None
                if g:
                    decl.append((side, g))
            for (na, ga), (nb, gb) in zip(decl, decl[1:]):
                what = []
                if ga[0] != gb[0]:
                    what.append(f"face {ga[0]} vs {gb[0]}")
                if ga[2] != gb[2]:
                    what.append(f"layers {'/'.join(ga[2])} vs {'/'.join(gb[2])}")
                if ga[3] != gb[3]:
                    what.append(f"order {ga[3]} vs {gb[3]}")
                d = max(abs(x - y) for x, y in zip(ga[1], gb[1]))
                if d > TOL:
                    what.append(f"window off by {d:.3f} um")
                if what:
                    out.append((pr.get("id", "?"), (na, ga), (nb, gb), "; ".join(what), d))
        except Exception:  # noqa: BLE001  one malformed port never stops the scan
            continue
    return out


def _end(raw_parts, pr, side, g):
    e = pr.get(side, {}) if side in ("src", "dst") else {}
    if side == "port":
        s = pr.get("src", {})
        return f"port decl (src {s.get('part')}({raw_parts.get(s.get('part'), {}).get('type')}).{s.get('bus')})"
    p = raw_parts.get(e.get("part"), {})
    return f"{side} {e.get('part')}({p.get('type')}).{e.get('bus')}"


def findings(raw, plan_path, tree=None, **kw):
    """WARN ADV-PORT-WINDOW-PAIR lines (capped) + one count line; never raises."""
    try:
        t0 = time.time()
        if not isinstance(raw, dict) or not raw.get("ports"):
            return [f"WARN {CHECK} not checked: plan has no ports"]
        parts = {p.get("name"): p for p in raw.get("partitions") or []}
        ports = {p.get("id"): p for p in raw.get("ports") or []}
        ninst = {}
        for p in parts.values():
            ninst[p.get("type")] = ninst.get(p.get("type"), 0) + 1
        mm = pair_mismatches(raw)
        mm.sort(key=lambda r: -r[4])
        out = []
        for pid, (na, ga), (nb, gb), what, d in mm[:MAX_LINES]:
            pr = ports.get(pid, {})
            ta = parts.get(pr.get(na, {}).get("part"), {}).get("type") if na != "port" else None
            tb = parts.get(pr.get(nb, {}).get("part"), {}).get("type") if nb != "port" else None
            share = ", ".join(f"{tn} has {ninst.get(tn, 0)} instances" for tn in (ta, tb) if tn)
            out.append(f"WARN {CHECK} port {pid}: {_end(parts, pr, na, ga)} {ga[4]} {ga[0]} [{ga[1][0]:.3f}, {ga[1][1]:.3f}] "
                       f"{'/'.join(ga[2])} vs {_end(parts, pr, nb, gb)} {gb[4]} {gb[0]} [{gb[1][0]:.3f}, {gb[1][1]:.3f}] "
                       f"{'/'.join(gb[2])} in the die frame: {what} (schema tolerance {TOL:g} um; validate refuses the plan)"
                       f"; fix: re-snap one side's type window to the other ({share}; a shared type moves every instance)")
        if mm:
            out.append(f"WARN {CHECK} {len(mm)} port(s) whose two ends disagree in the die frame"
                       f"{' (first ' + str(MAX_LINES) + ' listed)' if len(mm) > MAX_LINES else ''}; "
                       f"{len(ports)} ports checked in {time.time() - t0:.1f} s")
        return out
    except Exception as e:  # noqa: BLE001
        return [f"WARN {CHECK} not checked: {type(e).__name__}: {str(e)[:200]}"]


if __name__ == "__main__":
    import json
    import sys
    t0 = time.time()
    raw = json.load(open(sys.argv[1]))
    t1 = time.time()
    for ln in findings(raw, sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None):
        print(ln)
    print(f"# load {t1 - t0:.1f} s, check {time.time() - t1:.2f} s")

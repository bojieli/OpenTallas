"""ADV-SITE-IN-MACRO (SITE-IN-MACRO lane 11-25; an estimator, never a gate): plan sites on a hard core or off the outline.

KV A5t3-A5t6: all 19 kv3_pc_v1 types failed place because the register-bank bit sites of internal_stations[bus:i_ectl_Q_N_kf]
sat on u_kvpc1_f (22 of 1,240 sites in 8 types).  A CORE-PLACE row re-sited the dependent core and left the row's bit_sites_um
(and the plan regs_um they derive from) at the old position.  Every existing guard missed it:
  - place_precheck OVERLAP ("exact packed bank overlaps hard macro") reads packed in-bus banks only, with halo 0, and runs after
    an apply (precheck_hook), report only, so the kits queued before the post was read;
  - ADV-BITSITE-AREA / BANK-OFFAREA test the core area and site-vs-site collisions, never site-vs-macro;
  - ADV-SITE-COLLIDE KEEPOUT looks at landing START / status / local-reset windows only.
This check covers EVERY site-bearing plan key of a partition type (type frame, um):
  internal_stations / ft_slots   regs_um (points), bit_sites_um + face_bit_sites_um (cell footprints)
  soft_reg_banks / clock.soft_reg_banks   bit_sites_um
  relay_sites                    points
  CLAND seats                    landing START stages, status stages / anchors, local resets, collector local sources,
                                 reset taps / relays, reset START raw exports (adv_site_collide.type_items)
CLAND seats (landing START / status / local-reset windows, collector sources, reset taps) lying in a core are counted apart
(`cland`, informational): landing_place moves them clear of every core at gen (ADV-SITE-COLLIDE KEEPOUT prices the move), so they
are not a placement refusal.  The FIRM keys (regs_um, bit_sites_um, face_bit_sites_um, relay_sites, soft banks) are what global_place
refuses ("exact packed bank overlaps hard macro", KV A5t6).  A type is a WARN when a FIRM site is in a core / halo.

ADV-SITE-OFF-OUTLINE (COORD K10 11-25, FABLE-RC-KV SITE-OFF-OUTLINE): a FAIL class, never a WARN.  Every site above (station regs / bit
sites, relay sites, soft banks, CLAND seats incl. collector local sources and reset taps) plus the port pins and clock taps
(port_tap_points: landing-contract pins, reset_spine_pins sites, clock.added_taps, clock.edge_clocks tap_um) whose footprint leaves
[0, W] x [0, H] is one FAIL ADV-SITE-OFF-OUTLINE line per type (off_outline_findings; plan_gate_pre runs it as a blocking class).  A site
off the outline cannot be placed: KV D29 kv3_pv_v1e died at 5_1_grt on GRT-0209 for the edge clock port fclk_in_i_slg_E_N_rsp_d1 that
A5t8 still carried at (-32.16, 2.656) with its collector local source at (-32.07, 0).

A site is IN-MACRO when its footprint (a point for a point site) overlaps a hard_cores[] / lef contents[] footprint grown by that
core's halo_um (touching is not overlapping); it is reported as `core` when it overlaps the core itself and `halo` when only the
halo ring.  A site is OFF-OUTLINE when its footprint leaves [0, W] x [0, H].  regs_um of a row that also has bit_sites_um is one
bank point, not a cell (adv_site_collide station_bits): it is still counted, under its own key.

Fix: re-site the row from its CURRENT core placement (plan_site_derive.py / the row tool that moved the core must recompute the
dependent bit_sites_um in the same row).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_geom_static as G  # noqa: E402

CHECK = "ADV-SITE-IN-MACRO"
OFF_CHECK = "ADV-SITE-OFF-OUTLINE"
EPS = 1e-6
MAX_EX = 3


def core_rects(t):
    """-> [(x0, y0, x1, y1, halo, name)] hard cores and lef contents with their own halo (halo_um, 0 when absent)"""
    out = []
    for h in list(t.get("hard_cores") or []) + [c for c in (t.get("contents") or []) if isinstance(c, dict) and c.get("lef")]:
        try:
            (x0, y0), (w, hh) = h["origin_um"], h["outline_um"]
            halo = float(h.get("halo_um") or 0.0)
        except (KeyError, TypeError, ValueError):
            continue
        if h.get("orient", "R0") in G.ROT:
            w, hh = hh, w
        out.append((float(x0), float(y0), float(x0) + float(w), float(y0) + float(hh), halo, h.get("inst") or h.get("name") or "core"))
    return out


def gen_snapped_ft(t):
    """ft_slots as the kit gets them: gen_phys runs ft_bit_sites.snap_slots(core_box=CORE_AREA, blocks=type_blocks) which clamps every
    explicit ft bit site into the core and moves it off every block (positions only), so the plan's raw ft bit sites (S81 c9t43: 26,411
    off the outline) are judged AFTER that snap.  -> (slots, None) or (planned slots, refusal text) when gen would refuse."""
    slots = t.get("ft_slots") or []
    if not any(isinstance(e, dict) and e.get("bit_sites_um") for e in slots):
        return slots, None
    try:
        import copy
        import ft_bit_sites as FB
        import kit_fit
        fca = kit_fit.kit_core_area(t)
        return FB.snap_slots(copy.deepcopy(slots), fca[:2], core_box=fca, blocks=FB.type_blocks(t))[0], None
    except Exception as e:  # noqa: BLE001 -- gen refuses (no free site in 16.2 um) or an older tree: judge the planned sites
        return slots, f"{type(e).__name__}: {str(e)[:120]}"


def sites(t):
    """-> [(key, label, x, y, w, h)] every site of one type; points have w = h = 0"""
    import adv_site_collide as SC
    out = []
    ft_snapped, _ft_err = gen_snapped_ft(t)
    for key_, key in (("ft_slots", "ft_slots"), ("internal_stations", "internal_stations")):
        for k, e in enumerate(ft_snapped if key == "ft_slots" else t.get(key) or []):
            if not isinstance(e, dict):
                continue
            nm = e.get("name") or e.get("conn") or k
            cw, ch = G._cell(e)
            for j, p in enumerate(e.get("regs_um") or []):
                if G._pt(p):
                    out.append((f"{key}.regs_um", f"{key}[{nm}].regs_um[{j}]", float(p[0]), float(p[1]), 0.0, 0.0))
            for j, st in enumerate(e.get("bit_sites_um") or []):
                for b, p in enumerate(st or []):
                    if G._pt(p):
                        out.append((f"{key}.bit_sites_um", f"{key}[{nm}].bit_sites_um[{j}][{b}]", float(p[0]), float(p[1]), cw, ch))
            for b, p in enumerate(e.get("face_bit_sites_um") or []):
                if G._pt(p):
                    out.append((f"{key}.face_bit_sites_um", f"{key}[{nm}].face_bit_sites_um[{b}]", float(p[0]), float(p[1]), cw, ch))
    for key, src in (("soft_reg_banks", t.get("soft_reg_banks")), ("clock.soft_reg_banks", (t.get("clock") or {}).get("soft_reg_banks"))):
        for k, e in enumerate(src or []):
            if isinstance(e, dict):
                cw, ch = G._cell(e)
                for b, p in enumerate(e.get("bit_sites_um") or []):
                    if G._pt(p):
                        out.append((f"{key}.bit_sites_um", f"{key}[{e.get('id', k)}].bit_sites_um[{b}]", float(p[0]), float(p[1]), cw, ch))
    for kind, name, x, y in SC.type_items(t):
        if name.startswith(("ft_slots[", "internal_stations[")):         # regs_um: listed above with its own key
            continue
        key = "relay_sites" if name.startswith("relay_sites[") else "cland_seats"
        out.append((key, name, x, y, 0.0, 0.0))
    return out


def classify(t, ss=None):
    """-> (n_sites, [(key, label, x, y, core name, 'core'|'halo')], [(key, label, x, y)] off outline)"""
    ss = sites(t) if ss is None else ss
    cr = core_rects(t)
    ow, oh = (float(v) for v in t["outline_um"][:2])
    inm, off = [], []
    for key, lab, x, y, w, h in ss:
        if max(-x, -y, x + w - ow, y + h - oh) > EPS:
            off.append((key, lab, x, y))
        best = None
        for x0, y0, x1, y1, halo, nm in cr:
            if x < x1 + halo - EPS and x0 - halo + EPS < x + w and y < y1 + halo - EPS and y0 - halo + EPS < y + h:
                kind = "core" if (x < x1 - EPS and x0 + EPS < x + w and y < y1 - EPS and y0 + EPS < y + h) else "halo"
                if best is None or kind == "core":
                    best = (key, lab, x, y, nm, kind)
        if best:
            inm.append(best)
    return len(ss), inm, off


def _xy(p):
    return isinstance(p, (list, tuple)) and len(p) >= 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in p[:2])


def port_tap_points(t):
    """-> [(key, label, x, y)] port pins and clock taps of one type (points): clock.landing_contract.pins xy_um, reset_spine_pins
    sites_um, clock.added_taps xy, clock.edge_clocks tap_um (one point or a list of points)"""
    out = []
    ck = t.get("clock") or {}
    for j, p in enumerate((ck.get("landing_contract") or {}).get("pins") or []):
        if isinstance(p, dict) and _xy(p.get("xy_um")):
            out.append(("port_pins", f"landing_contract.pins[{p.get('name', j)}]", float(p["xy_um"][0]), float(p["xy_um"][1])))
    for j, p in enumerate(t.get("reset_spine_pins") or []):
        for k, q in enumerate((p.get("sites_um") or []) if isinstance(p, dict) else []):
            if _xy(q):
                out.append(("port_pins", f"reset_spine_pins[{p.get('name', j)}].sites_um[{k}]", float(q[0]), float(q[1])))
    for j, a in enumerate(ck.get("added_taps") or []):
        if isinstance(a, dict) and _xy(a.get("xy")):
            out.append(("clock_taps", f"clock.added_taps[{a.get('name', j)}]", float(a["xy"][0]), float(a["xy"][1])))
    for j, e in enumerate(ck.get("edge_clocks") or []):
        tp = e.get("tap_um") if isinstance(e, dict) else None
        for k, q in enumerate([tp] if _xy(tp) else (tp or []) if isinstance(tp, list) else []):
            if _xy(q):
                out.append(("clock_taps", f"clock.edge_clocks[{e.get('port') or e.get('name') or j}].tap_um" + (f"[{k}]" if not _xy(tp) else ""),
                            float(q[0]), float(q[1])))
    return out


def off_outline(t, off=None):
    """-> [(key, label, x, y)] every site (sites(), footprints) and port pin / clock tap (points) outside [0, W] x [0, H]"""
    off = list(classify(t)[2] if off is None else off)
    ow, oh = (float(v) for v in t["outline_um"][:2])
    off += [e for e in port_tap_points(t) if max(-e[2], -e[3], e[2] - ow, e[3] - oh) > EPS]
    return off


def off_outline_findings(raw, **_kw):
    """ADV-SITE-OFF-OUTLINE: one FAIL line per type with any site / port pin / clock tap off the outline (+ a LIST total)"""
    out, n = [], 0
    for tn, t in G._types(raw):
        if not t.get("outline_um"):
            continue
        off = off_outline(t)
        if not off:
            continue
        n += len(off)
        by = {}
        for e in off:
            by[e[0]] = by.get(e[0], 0) + 1
        ow, oh = (float(v) for v in t["outline_um"][:2])
        ex = "; ".join(f"{e[1]} at ({e[2]:g}, {e[3]:g})" for e in off[:MAX_EX])
        out.append(f"FAIL {OFF_CHECK} {tn}: {len(off)} object(s) outside the {ow:g}x{oh:g} outline (e.g. {ex}) [by key "
                   + ", ".join(f"{k} {v}" for k, v in sorted(by.items())) + "] (fix: re-site inside the outline; a site off the outline cannot place, GRT-0209)")
    if out:
        out.append(f"LIST {OFF_CHECK} {len(out)} type(s), {n} object(s) off the outline")
    return out


def counts(raw):
    """{type: dict(sites, in_core, in_halo (FIRM keys), cland (CLAND seats in a core / halo), off_outline, by_key, in_macro, off)}
    of the types with a FIRM site in a core or any site off the outline"""
    res = {}
    for tn, t in G._types(raw):
        n, inm, off = classify(t)
        firm = [e for e in inm if e[0] != "cland_seats"]
        if not firm and not off:
            continue
        by = {}
        for e in firm:
            by[e[0]] = by.get(e[0], 0) + 1
        for e in off:
            by[e[0] + "(off-outline)"] = by.get(e[0] + "(off-outline)", 0) + 1
        res[tn] = dict(sites=n, in_core=sum(1 for e in firm if e[5] == "core"), in_halo=sum(1 for e in firm if e[5] == "halo"),
                       cland=len(inm) - len(firm), off_outline=len(off), by_key=by, in_macro=firm, off=off)
    return res


def cland_total(raw):
    """CLAND seats in a core / halo over ALL types (informational: landing_place moves them at gen)"""
    return sum(1 for _tn, t in G._types(raw) for e in classify(t)[1] if e[0] == "cland_seats")


def findings(raw, plan_path=None, tree=None, **_kw):
    out = []
    res = counts(raw)
    for tn, r in sorted(res.items()):
        parts = []
        if r["in_core"] or r["in_halo"]:
            ex = "; ".join(f"{x[1]} at ({x[2]:g}, {x[3]:g}) on {x[4]}" for x in r["in_macro"][:MAX_EX])
            parts.append(f"{r['in_core'] + r['in_halo']} in hard core ({r['in_core']} on the core, {r['in_halo']} in its halo only; e.g. {ex})")
        if r["cland"]:
            parts.append(f"+{r['cland']} CLAND seats in a core (kit moves them)")
        if not parts:                                             # off the outline only: the FAIL ADV-SITE-OFF-OUTLINE class carries it
            continue
        out.append(f"WARN {CHECK} {tn}: {r['sites']} sites: " + "; ".join(parts)
                   + " [by key " + ", ".join(f"{k} {v}" for k, v in sorted(r["by_key"].items())) + "]")
    if out:
        out.append(f"LIST {CHECK} {len(res)} type(s): {sum(r['in_core'] for r in res.values())} on a core, "
                   f"{sum(r['in_halo'] for r in res.values())} in a halo only, {sum(r['off_outline'] for r in res.values())} off the outline (FAIL {OFF_CHECK}), "
                   f"{cland_total(raw)} CLAND seats in a core on all types (informational) "
                   f"(fix: re-site the row's dependent bit_sites_um / regs_um from the current core placement)")
    return out


if __name__ == "__main__":
    import json
    raw = json.loads(Path(sys.argv[1]).read_text())
    for line in off_outline_findings(raw) + findings(raw, sys.argv[1]):
        print(line)

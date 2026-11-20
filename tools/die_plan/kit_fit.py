"""kit_fit: KITFIT-1116 (COORD, S81 F2s3: 372 hard-core half pairs overlapping by 1.116 um passed compose, bind, G0, lint and kit preflight and failed
only at the kit macro floorplan).  The kit generator (gen_phys.type_macros) places every hard core at origin_um + track_offset_um; the plan checks
compared origins only, so two halves with different offsets (+0.108 / +0.684 um) overlapped in the kit and not in the plan.  This module judges the
boxes the kit will really place, for every type of every die:

  overlap   two placed macros whose boxes intersect by more than EPS (each pair listed with the overlap in x and y)
  halo      two macros closer than the halo (type key macro_halo_um, else the die / call argument halo; default 0 = overlap only)

Pure functions on the raw plan dict; used by G0 (check.py check_kit_core_fit) and the pre-bind gate (plan_gate_pre.py class KITFIT)."""
import math

EPS = 1e-6


def placed_boxes(t):
    """[(inst, x0, y0, x1, y1)] of the macros the kit places for type dict t: hard_cores with a lef + contents with a lef and an origin, at
    origin + track_offset (gen_phys.type_macros); physical_parts of a content at their own origin"""
    out, cores = [], set()
    for c in t.get("hard_cores", []) or []:
        cores.add(c.get("inst"))
        if not (c.get("lef") and c.get("origin_um") and c.get("outline_um")):
            continue
        ox, oy = c.get("track_offset_um", [0.0, 0.0])
        x, y = c["origin_um"][0] + ox, c["origin_um"][1] + oy
        out.append((c.get("physical_inst") or c["inst"], x, y, x + c["outline_um"][0], y + c["outline_um"][1]))
    for c in t.get("contents", []) or []:
        for q in c.get("physical_parts", []) or []:
            if q.get("origin_um") and q.get("outline_um"):
                x, y = q["origin_um"]
                out.append((q.get("physical_inst") or c.get("inst"), x, y, x + q["outline_um"][0], y + q["outline_um"][1]))
        if c.get("lef") and c.get("inst") not in cores and c.get("origin_um") and c.get("outline_um"):
            x, y = c["origin_um"]
            out.append((c.get("physical_inst") or c["inst"], x, y, x + c["outline_um"][0], y + c["outline_um"][1]))
    return out


CORE_MARGIN_UM = 4.32      # row 0.27 / site 0.054 aligned


def kit_core_area(t, default_margin=CORE_MARGIN_UM):
    """Exact type outline with optional [W,S,E,N] row/site-aligned core insets.

    Die-edge PHYs may consume the full outline width; the per-type opt-in changes
    placement rows only, without shifting the outline, macro origins or plan pins.
    """
    w,h=t["outline_um"]
    margins=t.get("kit_core_margins_um")
    if margins is None:
        margins=[default_margin]*4
        # KW-FIX-45 11-11 (DIE-HBM-100, hbm-phy-place: IFP-0002 / MPL-0034 on PHY_NC/NE/NW): a hard wrapper whose single hard
        # macro reaches a die edge (within default_margin of it) gets no core margin on that side: the macro sits at the die
        # origin / spans the frozen outline, so a 4.32 um inset core can neither contain nor place it.  Every other type is
        # unchanged; an explicit kit_core_margins_um still wins.
        hc=[c for c in t.get("hard_cores",[]) if c.get("lef") and c.get("outline_um") and c.get("origin_um")]
        from schema import full_area_hard_ip
        if not hc and full_area_hard_ip(t):       # QC-PHY-1 11-14: bare full-area hard IP in contents[] (same rule)
            hc=list(t["contents"])
        if t.get("hard") and len(hc)==1:
            (ox,oy),(mw,mh)=hc[0]["origin_um"],hc[0]["outline_um"]
            eps=1e-6
            margins=[0.0 if ox<=default_margin+eps else default_margin,      # W
                     0.0 if oy<=default_margin+eps else default_margin,      # S
                     0.0 if ox+mw>=w-default_margin-eps else default_margin, # E
                     0.0 if oy+mh>=h-default_margin-eps else default_margin] # N
    if not isinstance(margins,(list,tuple)) or len(margins)!=4:
        raise ValueError("kit_core_margins_um must be [W,S,E,N]")
    for v,step in zip(margins,(0.054,0.27,0.054,0.27)):
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:
            raise ValueError("kit_core_margins_um entries must be finite nonnegative numbers")
        if abs(v/step-round(v/step))>1e-6:
            raise ValueError("kit_core_margins_um must align W/E to 0.054 um and S/N to 0.27 um")
    west,south,east,north=margins
    if west+east>=w or south+north>=h:
        raise ValueError("kit_core_margins_um leaves no placement core")
    return [west,south,w-east,h-north]


def findings(types, halo=0.0, max_msgs=40, core_margin=None):
    """-> [str]: 'KITFIT-OVERLAP|HALO|OUTLINE type T: ...' lines, at most max_msgs plus one count line; [] = clean"""
    out, n = [], 0
    for tn, t in sorted((types or {}).items()):
        if not isinstance(t, dict):
            continue
        h = float(t.get("macro_halo_um", halo) or 0.0)
        bx = placed_boxes(t)
        # S81-TAIL-1118 (gunit__t1 MPL-0034): the kit floorplan CORE_AREA is the outline inset by gen_phys.CORE_MARGIN_UM; a core
        # placed at origin + track_offset past it stops the place stage (u_ahi top 1222.572 vs core top 1222.56) and passed G0
        ow = t.get("outline_um")
        if core_margin is not None and ow and len(ow) == 2:
            try:
                west, south, east, north = kit_core_area(t, core_margin)
            except ValueError as exc:
                n += 1
                out.append(f"KITFIT-CORE-AREA type {tn}: {exc}")
            else:
                for a, ax0, ay0, ax1, ay1 in bx:
                    over = max(west - ax0, south - ay0, ax1 - east, ay1 - north)
                    if over > EPS:
                        n += 1
                        out.append(f"KITFIT-OUTLINE type {tn}: {a} placed [{ax0:g},{ay0:g}]-[{ax1:g},{ay1:g}] "
                                   f"is {over:.4g} um outside the kit CORE_AREA [{west:g},{south:g}]-"
                                   f"[{east:g},{north:g}]: place_macro MPL-0034")
        for i, (a, ax0, ay0, ax1, ay1) in enumerate(bx):
            for b, bx0, by0, bx1, by1 in bx[i + 1:]:
                dx = min(ax1, bx1) - max(ax0, bx0)
                dy = min(ay1, by1) - max(ay0, by0)
                if dx > EPS and dy > EPS:
                    n += 1
                    out.append(f"KITFIT-OVERLAP type {tn}: {a} / {b} overlap {dx:.4g} x {dy:.4g} um at their kit offsets (placed "
                               f"[{ax0:g},{ay0:g}]-[{ax1:g},{ay1:g}] vs [{bx0:g},{by0:g}]-[{bx1:g},{by1:g}])")
                elif h > 0 and dx > -h + EPS and dy > -h + EPS:
                    n += 1
                    out.append(f"KITFIT-HALO type {tn}: {a} / {b} are {max(-dx, -dy):.4g} um apart, halo {h:g} um")
    return out[:max_msgs] + ([f"KITFIT: {n} finding(s) in all, first {max_msgs} listed"] if n > max_msgs else [])

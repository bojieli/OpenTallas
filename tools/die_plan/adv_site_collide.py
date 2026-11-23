"""ADV-SITE-COLLIDE (PRECHECK-R2, COORD 11-22; an estimator, never a gate).

Single-cell FIRM sites the kit pins at plan points of a partition type (type frame): landing reader/writer START stages,
landing status input stages + anchors, landing local reset copies, collector local sources, reset START raw exports,
station registers (ft_slots / internal_stations regs_um), reset local taps, reset-tree anchor relays and relay_sites.
Each takes a +-2.16 um (4.32 um) window in landing_placement.tcl (cland_put / cland_put_start / status / local-reset /
collector; the grow x2..x32 only finds rows nothing FIRM took first).  Kit generation (landing_place._status_reset_groups /
_chain_clear_of_hard_cores) first moves a START / status / local-reset window whose row-free share is < 0.25 (rows cut
2.17 um round every hard core) to the nearest window clear of every core by 4.32 um; this module applies the same law, so
both findings below use the sites the kit will actually use.

  CROWD    one 4.32-um window (|dx|, |dy| < 2.16 about one site) holding >= 4 sites at >= 3 distinct points (points
           < 0.1 um apart are one: a reset copy sited ON its consumer is one point), >= 2 of them not relay_sites, and one
           point with >= 2 points of ANOTHER site family next to it (families: START + START local resets / status +
           status local resets + raw exports / station + collector / relay).  That is a row of one lane landing on the sites of another.  Designed layouts stay
           clean: START fans sharing one point per stage (KV / QC: up to 46 branches), station regs with their own
           collector (QC coll_ft*, KV kv3_pv_* face rows), START fstart_* local resets beside their stages (S81), status stages with their reset copies (HEAD hd_spn), bus-bit relay rows (relay_sites
           keyed ...[N]: excluded, hd_tile 27 bits in 4.3 um), a relay_sites row beside one status point (hd_spn_end).
           Real positive: HEAD r18m (3dd49f406010) hd_lep0N_w, the LEP-RSTART-2 reader START stage coll_i0[1] at
           (485.61, 1370) beside the coll_o1 / coll_o2 status stages (487.06 / 487.92, 1370) + local reset k12 (487.06):
           w10 died at place "OT_CLAND no legal site for u_cland_sin_coll_o1_coll_i0_0".  r18n (341dbb140f8f) moved the
           START stages to y 1380: clean.
  KEEPOUT  (a) a START / status / local-reset site the kit moves > 8.64 um off its plan point because it lies inside a
           hard core (the move lengthens its hops and may land it on other sites), or no clear window exists (gen
           fails); (b) a site whose rows only the HALO-1 ring (hard_cores[].halo_um, a permanent placement blockage that
           landing_place does not see) blocks.  Stations / reset taps in cores stay plan_gate_pre GEOM's (cl_* refused,
           others counted), relay_sites in cores are counted only.

Fix (CROWD): move the row-added site(s) >= 4.32 um off the others (or onto the same point when they may share a window).
Fix (KEEPOUT): put the site outside the core + 4.32 um (+ halo) at plan time, where the hop budget was computed.
"""
import os
import re
import time

CHECK = "ADV-SITE-COLLIDE"
WIN_HALF_UM = 2.16           # landing_placement.tcl: every single-cell window is the plan point +- 2.16 um
CROWD_K = 4                  # sites in one window ...
CROWD_PTS = 3                # ... at >= this many distinct points ...
PT_TOL_UM = 0.1              # (points closer than this are one point)
LATTICE_TOL_UM = 0.01        # members are STRICTLY closer than 2.16 um: sites on a 2.16-um lattice (KV kv3_pv_v7 collector
                             # grid round its START stages, hd_spn_end relay rows) each own a window by design
CROWD_FOREIGN = 2            # ... and one point with >= this many points of another family in the window
MOVE_WARN_UM = 8.64          # KEEPOUT (a): kit move longer than two windows
ROW_CUT_UM = 2.17            # landing_place._row_free_fraction: rows cut beside every macro
CLEAR_MARGIN_UM = 4.32       # landing_place._clear_of_hard_cores margin and outline edge
ROW_FREE_MIN = 0.25          # landing_place: a window with a smaller row share moves
MAX_LINES = 20
BIT_RELAY = re.compile(r"\[\d+\]$")             # relay_sites keyed by a register BIT (u_x/q[42], o_r[13]): bus-bit relay rows
# a local reset copy whose consumers are all START cells (u_cland_fstart_* / origin / rstart_rx / reader|writer_start_*)
# is kind local_reset_start (START family: S81 fstart_<k> beside its writer START stages is a design); a collector local
# source sits on its ft slot's station register (QC coll_ft*, KV kv3_pv_* face rows): station family
START_CONSUMER = re.compile(r"^u_cland_(fstart|origin|rstart|reader_start|writer_start)")
FAMILY = dict(start="start", local_reset_start="start", status="status", local_reset="status", raw_export="status",
              station="station", collector="station", reset_tap="relay", reset_relay="relay", relay="relay")
#             not counted: relay_bit (bus-bit relay rows) and station_bits (a station register whose bits the plan sites
#             one by one in bit_sites_um: its regs_um point is no single cell; S81 slice_station__t8 ft8 regs[4] 1.1 um
#             from 6 writer START stages since J7, KV kv3_pv_v4 / v12 / v1n)
MOVED_KINDS = ("start", "status", "local_reset", "local_reset_start")  # landing_place moves these out of hard cores


def _xy(p):
    try:
        if isinstance(p[0], bool) or isinstance(p[1], bool):
            return None
        return float(p[0]), float(p[1])
    except (TypeError, ValueError, IndexError, KeyError):
        return None


def type_items(t):
    """[(kind, name, x, y)] of every single-cell FIRM plan point of one partition type (type frame, um)."""
    out = []

    def add(kind, name, p):
        q = _xy(p) if p is not None else None
        if q:
            out.append((kind, name, q[0], q[1]))

    for sl in t.get("ft_slots") or []:
        k = "station_bits" if sl.get("bit_sites_um") else "station"
        for j, p in enumerate(sl.get("regs_um") or []):
            add(k, f"ft_slots[{sl.get('name')}].regs_um[{j}]", p)
    for st in t.get("internal_stations") or []:
        k = "station_bits" if st.get("bit_sites_um") else "station"
        for j, p in enumerate(st.get("regs_um") or []):
            add(k, f"internal_stations[{st.get('conn')}].regs_um[{j}]", p)
    rs = t.get("reset") or {}
    for j, p in enumerate(rs.get("local_taps_um") or []):
        add("reset_tap", f"reset.local_taps_um[{j}]", p)
    if rs.get("tap_um"):
        add("reset_tap", "reset.tap_um", rs.get("tap_um"))
    rel = t.get("relay_sites")
    if isinstance(rel, dict):
        for n, p in rel.items():
            add("relay_bit" if BIT_RELAY.search(str(n)) else "relay", f"relay_sites[{n}]", p)
    for i, e in enumerate(t.get("reset_start_raw_exports") or []):
        if isinstance(e, dict):
            add("raw_export", f"reset_start_raw_exports[{e.get('name', i)}]", e.get("xy_um"))
    ck = t.get("clock") or {}
    for key in ("landing_reader_start", "landing_writer_start"):
        br = ck.get(key).get("branches") if isinstance(ck.get(key), dict) else None
        for b, v in (br or {}).items():
            for j, s in enumerate(v.get("stages") or [] if isinstance(v, dict) else []):
                if isinstance(s, dict):
                    add("start", f"{key[8:]}.{b}.stages[{j}]", s.get("xy_um"))
    st = ck.get("landing_status_input_stages")
    if isinstance(st, dict):
        for o, d in st.items():
            for i_, lst in (d.items() if isinstance(d, dict) else ()):
                for j, s in enumerate(lst or []):
                    if isinstance(s, dict):
                        add("status", f"status_stage.{o}.{i_}[{j}]", s.get("xy_um"))
    an = ck.get("landing_status_anchors")
    if isinstance(an, dict):
        for n, p in an.items():
            add("status", f"status_anchor.{n}", p)
    for j, r in enumerate(ck.get("landing_local_resets") or []):
        if isinstance(r, dict):
            cons = [str(c) for c in r.get("consumers") or []]
            st_ = bool(cons) and all(START_CONSUMER.match(c) for c in cons)
            add("local_reset_start" if st_ else "local_reset", f"local_reset.{r.get('name', j)}({r.get('raw', '')})", r.get("xy_um"))
    rta = ck.get("reset_tree_anchor").get("relays") if isinstance(ck.get("reset_tree_anchor"), dict) else None
    if isinstance(rta, dict):
        for n, v in rta.items():
            add("reset_relay", f"reset_tree_anchor.{n}", v.get("xy") if isinstance(v, dict) else v)
    lc = ck.get("landing_contract") if isinstance(ck.get("landing_contract"), dict) else {}
    for j, c in enumerate(lc.get("collector_local_sources") or []):
        if isinstance(c, dict):
            add("collector", f"collector_local_sources[{c.get('name', j)}]", c.get("xy_um"))
    seen, uniq = set(), []
    for it in out:                     # one plan entry listed twice is one site
        k = (it[0], it[1], round(it[2], 3), round(it[3], 3))
        if k not in seen:
            seen.add(k)
            uniq.append(it)
    return uniq


def core_boxes(t):
    out = []
    for c in t.get("hard_cores") or []:
        try:
            ox, oy = c["origin_um"]
            w, h = c["outline_um"]
            halo = float(c.get("halo_um") or 0.0)
        except (KeyError, TypeError, ValueError):
            continue
        out.append((str(c.get("inst", "?")), float(ox), float(oy), float(ox) + float(w), float(oy) + float(h), halo))
    return out


def _row_free_fraction(cores, rect, halo=ROW_CUT_UM):
    """landing_place._row_free_fraction: share of the window outside every core + its row cut (16 x 16 samples)."""
    x0, y0, x1, y1 = rect
    hit = [(a - halo - e, b - halo - e, c + halo + e, d + halo + e) for a, b, c, d, e in cores
           if x0 < c + halo + e and x1 > a - halo - e and y0 < d + halo + e and y1 > b - halo - e]
    if not hit:
        return 1.0
    n = 16
    pts = [(x0 + (i + .5) * (x1 - x0) / n, y0 + (j + .5) * (y1 - y0) / n) for i in range(n) for j in range(n)]
    return sum(not any(a <= x <= c and b <= y <= d for a, b, c, d in hit) for x, y in pts) / len(pts)


def _clear_of_hard_cores(cores, outline, rect, margin=CLEAR_MARGIN_UM):
    """landing_place._clear_of_hard_cores (no halo, as the kit): the window, or the nearest one clear of every core by
    margin; None when none fits the outline (gen raises 'no window clear of hard cores')."""
    x0, y0, x1, y1 = rect
    w, h = x1 - x0, y1 - y0
    width, height = outline
    xs = {x0} | {v for a, _, c, _, _ in cores for v in (a - margin - w, c + margin)}
    ys = {y0} | {v for _, b, _, d, _ in cores for v in (b - margin - h, d + margin)}
    edge = CLEAR_MARGIN_UM
    xs = [x for x in xs if edge <= x and x + w <= width - edge]
    ys = [y for y in ys if edge <= y and y + h <= height - edge]
    for _, x, y in sorted((abs(x - x0) + abs(y - y0), x, y) for x in xs for y in ys):
        if not any(x < c + margin and x + w > a - margin and y < d + margin and y + h > b - margin
                   for a, b, c, d, _ in cores):
            return [x, y, x + w, y + h]
    return None


def kit_sites(t, items, half=WIN_HALF_UM):
    """(sites, moves, halo_hits): sites = items at the kit's window centre; moves = [(item, new xy | None, core inst)];
    halo_hits = [(item, core inst, halo)] for windows whose rows only a HALO-1 ring blocks."""
    boxes = core_boxes(t)
    if not boxes:
        return items, [], []
    cores0 = [(a, b, c, d, 0.0) for _, a, b, c, d, _ in boxes]
    coresh = [(a, b, c, d, e) for _, a, b, c, d, e in boxes]
    anyhalo = any(e > 0 for _, _, _, _, _, e in boxes)
    outline = t.get("outline_um") or (float("inf"), float("inf"))
    sites, moves, halo_hits = [], [], []
    for it in items:
        kind, name, x, y = it
        if kind not in MOVED_KINDS:
            sites.append(it)
            continue
        r = [x - half, y - half, x + half, y + half]
        if _row_free_fraction(cores0, r) >= ROW_FREE_MIN:
            sites.append(it)
            if anyhalo and _row_free_fraction(coresh, r) < ROW_FREE_MIN:
                inst = next((n for n, a, b, c, d, e in boxes if e > 0 and a - e - half < x < c + e + half
                             and b - e - half < y < d + e + half), "?")
                halo_hits.append((it, inst, max(e for *_, e in boxes)))
            continue
        inst = next((n for n, a, b, c, d, _ in boxes if a - ROW_CUT_UM - half < x < c + ROW_CUT_UM + half
                     and b - ROW_CUT_UM - half < y < d + ROW_CUT_UM + half), "?")
        nr = _clear_of_hard_cores(cores0, outline, r)
        if nr is None:
            moves.append((it, None, inst))
            sites.append(it)
            continue
        nx, ny = (nr[0] + nr[2]) / 2, (nr[1] + nr[3]) / 2
        moves.append((it, (nx, ny), inst))
        sites.append((kind, name + f"<-moved from ({_f(x)},{_f(y)})", nx, ny))
    return sites, moves, halo_hits


def _points(mem):
    """[(x, y, {families})] merging members < PT_TOL_UM apart."""
    pts = []
    for kind, _, x, y in mem:
        fam = FAMILY.get(kind)
        for p in pts:
            if abs(x - p[0]) < PT_TOL_UM and abs(y - p[1]) < PT_TOL_UM:
                p[2].add(fam)
                break
        else:
            pts.append((x, y, {fam}))
    return pts


def _crowded(mem, k=CROWD_K, kpts=CROWD_PTS, kforeign=CROWD_FOREIGN):
    if len(mem) < k:
        return False
    pts = _points(mem)
    if len(pts) < kpts or len(_points([m for m in mem if FAMILY.get(m[0]) != "relay"])) < 2:
        return False
    return any(sum(1 for q in pts if q is not p and not (q[2] & p[2])) >= kforeign for p in pts)


def crowd_windows(sites, half=WIN_HALF_UM, k=CROWD_K, kpts=CROWD_PTS):
    """[(n, centre index, [member indexes])], one per cluster (windows sharing a member merge, the fullest kept)."""
    items = [s for s in sites if s[0] in FAMILY]
    cell = 2 * half
    grid = {}
    for i, s in enumerate(items):
        grid.setdefault((int(s[2] // cell), int(s[3] // cell)), []).append(i)
    hits = []
    for i, (_, _, x, y) in enumerate(items):
        gx, gy = int(x // cell), int(y // cell)
        mem = [j for dx in (-1, 0, 1) for dy in (-1, 0, 1) for j in grid.get((gx + dx, gy + dy), ())
               if abs(items[j][2] - x) < half - LATTICE_TOL_UM and abs(items[j][3] - y) < half - LATTICE_TOL_UM]
        if _crowded([items[j] for j in mem], k, kpts):
            hits.append((len(mem), i, sorted(mem)))
    hits.sort(key=lambda h: (-h[0], h[1]))
    taken, out = set(), []
    for n, i, mem in hits:
        if not (taken & set(mem)):
            out.append((n, items[i], [items[j] for j in mem]))
        taken |= set(mem)
    return out


def core_counts(t, items):
    """{kind: n} of non-landing sites (relay_sites, stations, reset taps / relays) strictly inside a hard core box."""
    boxes = core_boxes(t)
    n = {}
    if not boxes:
        return n
    for kind, _, x, y in items:
        if kind in MOVED_KINDS or kind == "collector":
            continue
        if any(a < x < c and b < y < d for _, a, b, c, d, _ in boxes):
            n[kind] = n.get(kind, 0) + 1
    return n


def _f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def findings(raw, plan_path, tree=None, half=WIN_HALF_UM, **kw):
    """WARN ADV-SITE-COLLIDE lines (capped at MAX_LINES) + one count line; never raises."""
    try:
        t0 = time.time()
        types = raw.get("partition_types") if isinstance(raw, dict) else None
        if not types:
            return [f"WARN {CHECK} not checked: plan has no partition_types"]
        used = {p.get("type") for p in raw.get("partitions") or [] if isinstance(p, dict)}
        crowd, keep, halo, incore = [], [], [], {}
        nsites = 0
        for tn, t in types.items():
            if not isinstance(t, dict) or t.get("hard") is True or (used and tn not in used):
                continue
            items = type_items(t)
            nsites += len(items)
            sites, moves, hh = kit_sites(t, items, half)
            for n, c, mem in crowd_windows(sites, half):
                crowd.append((tn, n, c, mem))
            for it, nxy, inst in moves:
                d = float("inf") if nxy is None else abs(nxy[0] - it[2]) + abs(nxy[1] - it[3])
                if d > MOVE_WARN_UM:
                    keep.append((tn, it, nxy, inst, d))
            halo += [(tn,) + h for h in hh]
            for k, v in core_counts(t, items).items():
                incore[k] = incore.get(k, 0) + v
        crowd.sort(key=lambda r: (-r[1], r[0]))
        keep.sort(key=lambda r: (-r[4], r[0], r[1][1]))
        lines = []
        for tn, n, c, mem in crowd:
            pts = _points(mem)
            fams = {}
            for m in mem:
                fams[m[0]] = fams.get(m[0], 0) + 1
            sx = max(m[2] for m in mem) - min(m[2] for m in mem)
            sy = max(m[3] for m in mem) - min(m[3] for m in mem)
            what = ", ".join(f"{m[1]} ({_f(m[2])},{_f(m[3])})" for m in mem[:8]) + (" ..." if len(mem) > 8 else "")
            lines.append(f"WARN {CHECK} {tn}: CROWD {n} FIRM sites at {len(pts)} points in one {2 * half:.2f}-um window "
                         f"about ({_f(c[2])},{_f(c[3])}) (span {sx:.2f} x {sy:.2f} um; "
                         f"{', '.join(f'{v} {k}' for k, v in sorted(fams.items()))}; limit {CROWD_K} sites at "
                         f"{CROWD_PTS} points with {CROWD_FOREIGN} of another family): {what}; risk OT_CLAND no legal site at "
                         f"place; fix: move the row-added site(s) >= {2 * half:.2f} um off the others")
        klines, hlines = [], []
        for tn, it, inst, h in halo:
            kind, name, x, y = it
            hlines.append(f"WARN {CHECK} {tn}: KEEPOUT {kind} {name} at ({_f(x)},{_f(y)}) window rows are blocked by the "
                          f"HALO-1 ring of {inst} (halo_um {_f(h)}; landing_place ignores halos: the kit keeps the window, place must grow it"
                          f"); fix: move it >= {_f(h + ROW_CUT_UM + half)} um off the core edge")
        for tn, it, nxy, inst, d in keep:
            kind, name, x, y = it
            if nxy is None:
                klines.append(f"WARN {CHECK} {tn}: KEEPOUT {kind} {name} at ({_f(x)},{_f(y)}) is inside hard core {inst} and "
                              f"no 4.32-um window clear of every core fits the outline: kit gen fails "
                              f"('no window clear of hard cores'); fix: re-site it outside the cores")
                continue
            if hlines:                                 # unplaceable first, then HALO-1 rows, then the longest moves
                klines += hlines
                hlines = []
            klines.append(f"WARN {CHECK} {tn}: KEEPOUT {kind} {name} at ({_f(x)},{_f(y)}) has no rows (inside hard core "
                          f"{inst}): kit gen moves it {d:.1f} um to ({_f(nxy[0])},{_f(nxy[1])}) (> {MOVE_WARN_UM:g}; "
                          f"its hops grow and it may land on other sites); fix: site it there or outside the core + "
                          f"{CLEAR_MARGIN_UM:g} um at plan time")
        klines += hlines
        # PRECHECK-R2 integration: moved / halo KEEPOUT is mostly inherited (QC 62, KV 95 on the 11-22 plans): counted in the
        # summary, listed on request; an unplaceable site (kit gen fails) is always listed
        if not kw.get("list_keepout", os.environ.get("OT_ADV_KEEPOUT_LIST", "0") == "1"):
            klines = [x for x in klines if "kit gen fails" in x]
        nc = min(len(lines), max(MAX_LINES // 2, MAX_LINES - len(klines)))
        out = lines[:nc] + klines[:MAX_LINES - nc]
        if crowd or keep or halo:
            out.append(f"WARN {CHECK} {len(crowd)} crowded window(s), {len(keep)} landing site(s) moved > {MOVE_WARN_UM:g} um "
                       f"or unplaceable out of hard cores, {len(halo)} in a HALO-1 ring; {nsites} sites in "
                       f"{time.time() - t0:.1f} s{' (first ' + str(len(out)) + ' listed)' if len(lines) + len(klines) > len(out) else ''}"
                       f"; not listed, inside a core box: "
                       f"{', '.join(f'{v} {k}' for k, v in sorted(incore.items())) or 'none'} (GEOM / relay rows)")
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

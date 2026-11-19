"""Explicit physical and timing roles for existing PHY clock pads.

No period is inferred from the digital die clock. This contract creates no
clock groups or landing-ring phase constraints.  By default it creates no
crossing exceptions either; an input pin may opt in with "cdc": "synchronized"
plus a "cdc_evidence" string (COORD ruling 10-31 (3): every crossing of that
plesiochronous PHY clock is synchronized), which emits exactly the asynchronous
crossing form CDC_RULE describes (no set_clock_groups: OpenSTA would then drop
the max delay).

Opt-in second clock entries (S81 RCK2-1109, COORD loopgap-155x-1109): an input pad
clock may declare "entries", each a plan-placed trunk from the pad pin (stations_um,
one `cell` per station, every hop <= ENTRY_HOP_UM, 12.1e reach) ending in an entry
driver at xy_um whose output net carries the sinks inside region_um plus the declared
macro sink_pins.  The PRE_CTS hook pad_clock_entry.tcl builds it, so TritonCTS sees
one local tree per entry (the pad net keeps the rest) under the same clock; SDC,
ports and RTL are unchanged.  Absent "entries" = kit byte-identical.

Core-clock regional entries (S81 LEAF-CLKENTRY-1109, opt-in clock.tap_entries): the same trunk form sourced at an
existing die-spine tap port ("tap": clk / clk_t<k>).  After the nearest-tap split (clock_taps.tcl) the entry driver's
net takes every std-cell clock sink inside region_um that sits on one of the "take_taps" ports, so a deep macro-field
channel that one or two far taps used to reach gets its own local tree behind a <= 405-um trunk.  No port, RTL, SDC,
reset-tree or die-top change; absent "tap_entries" = kit byte-identical.
"""
import math
import re

ENTRY_HOP_UM = 405.0         # METHODOLOGY 12.1e: plan 405 um per hop (repeaters <= 450)
ENTRY_KEYS = {'name', 'xy_um', 'stations_um', 'cell', 'region_um', 'sink_pins', 'evidence'}
# PLAN-READERS-1 11-14 (FABLE-PLAN-B6B 6.4): optional entry field min_early_ps (number >= 0): the entry's macro pins are clocked
# at least that long before the earliest register clock pin of the type, by the entry trunk itself (no delaybuf chain);
# written to rck_early.txt (write_contract) and reported by rck_early_report.tcl at the post-CTS gate (report only).
ENTRY_OPT = {'min_early_ps'}
EARLY_FILE = 'rck_early.txt'
TAP_ENTRY_CLEAR_UM = 2.16      # a trunk / driver point is a std cell: >= 8 rows off every hard core (not the 8.64 tap-pin halo)
TAP_ENTRY_KEYS = {'name', 'tap', 'take_taps', 'xy_um', 'stations_um', 'cell', 'region_um', 'evidence'}
PHY_EXPORT_SOURCE_SDC = 'if {[file exists /work/phy_clock_export_source.tcl]} {source /work/phy_clock_export_source.tcl}'

CDC_VALUES = ('synchronized',)
CDC_RULE = ('COORD 10-31 ruling (3): synchronized plesiochronous pad clock -> asynchronous crossing, '
            'max delay one pad period (latency ignored), no hold check')


def pins(P, tn):
    t = P.types[tn]
    c = t.get('clock', {}).get('pad_clock')
    if c is None:
        return []
    if not isinstance(c, dict) or set(c) != {'pins'} or not isinstance(c['pins'], list):
        raise ValueError(f'{tn}: pad_clock must contain exactly a pins list')
    pads = {p['name']: p for p in t.get('pads', []) if p.get('clock') is True}
    result, seen = [], set()
    data_seen = set()
    data_pads = {p['name']: p for p in t.get('pads', []) if p.get('clock') is not True}
    required = {'name', 'dir', 'period_ps', 'source', 'layer', 'xy_um'}
    periods = {}
    import gen_phys
    periods.update({n: float(P.die['period_ps']) for n, *_ in gen_phys.clock_pins(P, tn) + gen_phys.core_tap_pins(P, tn)})
    periods.update({n: float(P.die['period_ps']) * m for n, _x, _y, m in gen_phys.edge_clock_pins(P, tn)})
    for p in c['pins']:
        if not isinstance(p, dict) or required - set(p) or set(p) - required - {'source_clock_port', 'sink_pins', 'cdc', 'cdc_evidence', 'data_inputs', 'data_outputs', 'entries', 'star', 'die_trunk'}:
            raise ValueError(f'{tn}: pad_clock pin requires name/dir/period_ps/source/layer/xy_um')
        n = p['name']; pad = pads.get(n)
        if not isinstance(n, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', n) or n in seen:
            raise ValueError(f'{tn}: duplicate or invalid pad clock name {n!r}')
        seen.add(n)
        if not pad or int(pad['width']) != 1 or p['dir'] != pad['dir'] or p['dir'] not in ('in', 'out'):
            raise ValueError(f'{tn}.{n}: pad clock must match an existing scalar pads.clock role')
        per = p['period_ps']
        if isinstance(per, bool) or not isinstance(per, (int, float)) or not math.isfinite(per) or per <= 0:
            raise ValueError(f'{tn}.{n}: explicit positive finite PHY period_ps required')
        if not isinstance(p['source'], str) or not p['source'].strip():
            raise ValueError(f'{tn}.{n}: explicit PHY clock/period source required')
        xy = p['xy_um']; w, h = t['outline_um']
        if not isinstance(xy, list) or len(xy) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in xy):
            raise ValueError(f'{tn}.{n}: finite physical xy_um required')
        if not (0.096 <= xy[0] <= w - 0.096 and 0.096 <= xy[1] <= h - 0.096):
            raise ValueError(f'{tn}.{n}: full clock pin rectangle must fit the unchanged outline')
        if p['layer'] != P.layer_budget['partition_signal_max'] or p['layer'] not in P.layers:
            raise ValueError(f'{tn}.{n}: physical pad clock must use the partition top signal layer')
        if p['dir'] == 'out':
            src = p.get('source_clock_port')
            if src not in periods or abs(per - periods[src]) > 1e-6 or 'sink_pins' in p:
                raise ValueError(f'{tn}.{n}: output needs an actual same-period source_clock_port')
        elif 'source_clock_port' in p:
            raise ValueError(f'{tn}.{n}: external input cannot claim an internal source_clock_port')
        if 'cdc' in p or 'cdc_evidence' in p:
            ev = p.get('cdc_evidence')
            if p.get('cdc') not in CDC_VALUES or p['dir'] != 'in' or not isinstance(ev, str) or not ev.strip():
                raise ValueError(f'{tn}.{n}: cdc must be "synchronized" on an input pad clock with a non-empty cdc_evidence')
        for sink in p.get('sink_pins', []):
            if not isinstance(sink, dict) or set(sink) != {'module', 'pin'} or any(not isinstance(v, str) or not v for v in sink.values()):
                raise ValueError(f'{tn}.{n}: typed sink_pins require exact module/pin identities')
        if 'data_inputs' in p:
            rows = p['data_inputs']
            if p['dir'] != 'in' or not isinstance(rows, list) or not rows:
                raise ValueError(f'{tn}.{n}: data_inputs needs a nonempty list on an input pad clock')
            for row in rows:
                base = {'port', 'max_ps', 'min_ps', 'evidence'}
                if not isinstance(row, dict) or base - set(row) or set(row) - base - SAME_EDGE_KEYS:
                    raise ValueError(f'{tn}.{n}: data_inputs requires port/max_ps/min_ps/evidence')
                same_edge_row(tn, n, row, per)
                name = row['port']
                if not isinstance(name, str):
                    raise ValueError(f'{tn}.{n}: data input port must be a literal pad name')
                data = data_pads.get(name)
                if not data or data['dir'] != 'in' or name in data_seen:
                    raise ValueError(f'{tn}.{n}: data_inputs must uniquely select existing input data pads')
                data_seen.add(name)
                lo, hi = row['min_ps'], row['max_ps']
                if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
                       for v in (lo, hi)) or lo > hi:
                    raise ValueError(f'{tn}.{n}: data_inputs requires finite min_ps <= max_ps')
                if not isinstance(row['evidence'], str) or not row['evidence'].strip():
                    raise ValueError(f'{tn}.{n}: actual source-synchronous data-clock evidence required')
        if 'data_outputs' in p:
            rows = p['data_outputs']
            if p['dir'] != 'out' or not isinstance(rows, list) or not rows:
                raise ValueError(f'{tn}.{n}: data_outputs needs a nonempty list on an output pad clock')
            for row in rows:
                if not isinstance(row, dict) or set(row) != {'port', 'max_ps', 'min_ps', 'evidence'}:
                    raise ValueError(f'{tn}.{n}: data_outputs requires port/max_ps/min_ps/evidence')
                name = row['port']
                if not isinstance(name, str):
                    raise ValueError(f'{tn}.{n}: data output port must be a literal pad name')
                data = data_pads.get(name)
                if not data or data['dir'] != 'out' or name in data_seen:
                    raise ValueError(f'{tn}.{n}: data_outputs must uniquely select existing output data pads')
                data_seen.add(name)
                lo, hi = row['min_ps'], row['max_ps']
                if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
                       for v in (lo, hi)) or lo > hi:
                    raise ValueError(f'{tn}.{n}: data_outputs requires finite min_ps <= max_ps')
                if not isinstance(row['evidence'], str) or not row['evidence'].strip():
                    raise ValueError(f'{tn}.{n}: actual source-synchronous data-clock evidence required')
        if 'entries' in p:
            check_entries(tn, t, p, {q['name'] for q in t.get('pads', [])})
        result.append(dict(p))
    if seen != set(pads):
        raise ValueError(f'{tn}: pad_clock must cover every existing clock pad: {sorted(set(pads) - seen)}')
    return result


def _finite_xy(v):
    return (isinstance(v, list) and len(v) == 2
            and all(not isinstance(a, bool) and isinstance(a, (int, float)) and math.isfinite(a) for a in v))


def check_min_early(where, e):
    """min_early_ps, when present: a finite number >= 0 (not bool)."""
    if 'min_early_ps' not in e:
        return
    v = e['min_early_ps']
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
        raise ValueError(f'{where}: min_early_ps must be a finite number >= 0, got {v!r}')


def check_entries(tn, t, p, port_names):
    """Fail closed on a malformed second-entry declaration (see the module note)."""
    n = p['name']
    rows = p['entries']
    if p['dir'] != 'in' or not isinstance(rows, list) or not rows:
        raise ValueError(f'{tn}.{n}: entries needs a nonempty list on an input pad clock')
    w, h = t['outline_um']
    declared = [(s['module'], s['pin']) for s in p.get('sink_pins', [])]
    taken, names = set(), set()
    for e in rows:
        if not isinstance(e, dict) or not (ENTRY_KEYS <= set(e) <= ENTRY_KEYS | ENTRY_OPT):
            raise ValueError(f'{tn}.{n}: entry requires {sorted(ENTRY_KEYS)} and only the optional {sorted(ENTRY_OPT)}')
        en = e['name']
        check_min_early(f'{tn}.{n}.{en}', e)
        if (not isinstance(en, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', en) or en in names
                or en in port_names):
            raise ValueError(f'{tn}.{n}: duplicate, invalid or port-colliding entry name {en!r}')
        names.add(en)
        if not isinstance(e['cell'], str) or not re.fullmatch(r'[A-Za-z0-9_]+', e['cell']):
            raise ValueError(f'{tn}.{n}.{en}: entry cell must be one library cell name')
        if not isinstance(e['evidence'], str) or not e['evidence'].strip():
            raise ValueError(f'{tn}.{n}.{en}: entry evidence required')
        st = e['stations_um']
        if not isinstance(st, list) or not _finite_xy(e['xy_um']) or not all(_finite_xy(s) for s in st):
            raise ValueError(f'{tn}.{n}.{en}: entry xy_um / stations_um must be finite [x, y] points')
        chain = [p['xy_um']] + st + [e['xy_um']]
        for x, y in chain[1:]:
            if not (0.0 < x < w and 0.0 < y < h):
                raise ValueError(f'{tn}.{n}.{en}: trunk point ({x}, {y}) outside the outline')
        for a, b in zip(chain, chain[1:]):
            hop = abs(a[0] - b[0]) + abs(a[1] - b[1])
            if hop > ENTRY_HOP_UM + 1e-6:
                raise ValueError(f'{tn}.{n}.{en}: trunk hop {hop:.1f} um > {ENTRY_HOP_UM:g} um (12.1e)')
        reg = e['region_um']
        if (not isinstance(reg, list) or not reg or
                any(not isinstance(r, list) or len(r) != 4 or not all(_finite_xy(r[i:i + 2]) for i in (0, 2))
                    or not (r[0] < r[2] and r[1] < r[3]) for r in reg)):
            raise ValueError(f'{tn}.{n}.{en}: region_um must be a nonempty list of [x0, y0, x1, y1] (x0<x1, y0<y1)')
        sp = e['sink_pins']
        if not isinstance(sp, list) or any(not isinstance(s, dict) or set(s) != {'module', 'pin'} for s in sp):
            raise ValueError(f'{tn}.{n}.{en}: entry sink_pins require module/pin identities')
        for s in sp:
            key = (s['module'], s['pin'])
            if key not in declared or key in taken:
                raise ValueError(f'{tn}.{n}.{en}: entry sink pin {key} is not a declared pad sink or is claimed twice')
            taken.add(key)
    return rows


DIE_TRUNK_KEYS = {'from_xy_um', 'stations_um', 'layer', 'host', 'evidence'}
DIE_TRUNK_OPT = {'cell'}
DIE_TRUNK_HOSTS = ('die', 'type')


def die_trunks(P, tn):
    """[(pad clock name, row)] of the declared die-level trunks of the type's input pad clocks (FABLE-FIX-S81-SERDES 11-18,
    opt-in pad_clock pins[].die_trunk).  The row states how the die net of that pad clock reaches a pin that was moved into
    the type: {"from_xy_um": [x, y], "stations_um": [[x, y], ...], "layer": "M8", "host": "die" | "type", "evidence": ...,
    optional "cell"}, all in the TYPE frame (one row serves every instance; the die tool maps it by the instance transform).
    from_xy_um = where the die net arrives (the old pin / the type edge); the chain from_xy_um -> stations -> pin xy_um is the
    trunk, every hop <= ENTRY_HOP_UM.  stations_um may be empty: then the trunk is one unrepeated route on `layer` and its
    whole length must be <= ENTRY_HOP_UM.  With stations, `cell` (one repeater per station) is required.  host says who builds
    the repeaters: "die" = the die clock tool places them (the sites must be die-owned area), "type" = the kit builds them as
    its own cells.  Independent of the in-type clock form (single tree, regional roots, star).  This module only validates the
    row and hands it out; no kit file changes (absent or present = kit byte-identical) until a reader uses it."""
    out = []
    t = P.types[tn]
    w, h = t['outline_um']
    for p in pins(P, tn):
        if 'die_trunk' not in p:
            continue
        r = p['die_trunk']
        n = p['name']
        if p['dir'] != 'in':
            raise ValueError(f'{tn}.{n}: die_trunk needs an input pad clock')
        if not isinstance(r, dict) or not (DIE_TRUNK_KEYS <= set(r) <= DIE_TRUNK_KEYS | DIE_TRUNK_OPT):
            raise ValueError(f'{tn}.{n}: die_trunk requires {sorted(DIE_TRUNK_KEYS)} and only the optional {sorted(DIE_TRUNK_OPT)}')
        if not isinstance(r['evidence'], str) or not r['evidence'].strip():
            raise ValueError(f'{tn}.{n}: die_trunk evidence required')
        if r['host'] not in DIE_TRUNK_HOSTS:
            raise ValueError(f'{tn}.{n}: die_trunk host must be one of {DIE_TRUNK_HOSTS}')
        if r['layer'] not in P.layers:
            raise ValueError(f'{tn}.{n}: die_trunk layer {r["layer"]!r} is not a plan layer')
        st = r['stations_um']
        if not _finite_xy(r['from_xy_um']) or not isinstance(st, list) or not all(_finite_xy(x) for x in st):
            raise ValueError(f'{tn}.{n}: die_trunk from_xy_um / stations_um must be finite [x, y] points')
        if st and (not isinstance(r.get('cell'), str) or not re.fullmatch(r'[A-Za-z0-9_]+', r['cell'])):
            raise ValueError(f'{tn}.{n}: die_trunk with stations needs one repeater cell name')
        if not st and 'cell' in r:
            raise ValueError(f'{tn}.{n}: die_trunk without stations takes no cell')
        chain = [r['from_xy_um']] + st + [p['xy_um']]
        for x, y in chain[:-1]:
            if not (0.0 <= x <= w and 0.0 <= y <= h):
                raise ValueError(f'{tn}.{n}: die_trunk point ({x}, {y}) outside the outline')
        for a, b in zip(chain, chain[1:]):
            hop = abs(a[0] - b[0]) + abs(a[1] - b[1])
            if hop > ENTRY_HOP_UM + 1e-6:
                raise ValueError(f'{tn}.{n}: die_trunk hop {hop:.1f} um > {ENTRY_HOP_UM:g} um (12.1e)')
        out.append((n, r))
    return out


def port_xy(p):
    """Physical kit position of a pad clock port: from_xy_um when the kit builds the trunk (die_trunk host "type": the die net
    ends where it arrives and the kit carries the clock on), else the declared xy_um.  io_tcl places the port here."""
    r = p.get('die_trunk')
    return list(r['from_xy_um']) if isinstance(r, dict) and r.get('host') == 'type' else list(p['xy_um'])


TRUNK_FILE = 'pad_clock_trunk.tcl'


def trunk_tcl(P, tn):
    """PRE_CTS data + hook call of the kit-built trunks ('' when no die_trunk row has host "type" with stations):
    pad_clock_trunk.tcl places one `cell` per station and puts every load of the port net behind the last one; sourced after
    the other pad-clock hooks.  host "die" rows and station-less rows emit nothing (the die tool / a plain route owns them)."""
    rows = [(n, r) for n, r in die_trunks(P, tn) if r['host'] == 'type' and r['stations_um']]
    if not rows:
        return ''
    body = ''.join('  ' + _tcl_list([n, r['cell'], [[float(a) for a in s] for s in r['stations_um']]]) + '\n' for n, r in rows)
    return ('# GENERATED by tools/die_plan/gen.py phys (plan clock.pad_clock pins[].die_trunk, host type): port cell stations\n'
            'set ::pct_trunks {\n' + body + '}\nuplevel #0 {source /work/' + TRUNK_FILE + '}\n')


STAR_KEYS = {'evidence'}
STAR_OPT = {'max_sinks': (16, 4000), 'max_extent_um': (20.0, 1000.0), 'hop_um': (20.0, 100.0)}
STAR_DEFAULT = {'max_sinks': 200, 'max_extent_um': 100.0, 'hop_um': 92.0, 'cell': 'BUFx24_ASAP7_75t_R'}


def star(P, tn):
    """[(pad clock name, star row with defaults)] of the type's matched-leg star trunks (FABLE-FIX-S81-SERDES 11-18, opt-in
    pad_clock pins[].star = {"evidence": ..., optional max_sinks / max_extent_um / hop_um / cell}): the PRE_CTS hook rck_star.tcl
    cuts the PLACED sinks of that pad clock into compact regions and feeds one entry driver per region through its own leg of
    equal stage count and equal length (rck_star.py).  Nothing is plan-placed, so the same row
    serves every type of a family.  Fail closed: input pad clock only, not together with plan-placed entries, hop <= 100 um
    (the kit max-wire length: a longer hop would get an unplanned repeater), at most one star per type."""
    out = []
    for p in pins(P, tn):
        if 'star' not in p:
            continue
        r = p['star']
        n = p['name']
        if p['dir'] != 'in' or 'entries' in p:
            raise ValueError(f'{tn}.{n}: star needs an input pad clock without plan-placed entries')
        if not isinstance(r, dict) or not (STAR_KEYS <= set(r) <= STAR_KEYS | set(STAR_OPT) | {'cell'}):
            raise ValueError(f'{tn}.{n}: star requires evidence and only the optional {sorted(set(STAR_OPT) | {"cell"})}')
        if not isinstance(r['evidence'], str) or not r['evidence'].strip():
            raise ValueError(f'{tn}.{n}: star evidence required')
        for k, (lo, hi) in STAR_OPT.items():
            if k in r and (isinstance(r[k], bool) or not isinstance(r[k], (int, float)) or not math.isfinite(r[k])
                           or not lo <= r[k] <= hi):
                raise ValueError(f'{tn}.{n}: star {k} must be a number in {lo:g}..{hi:g}')
        if 'max_sinks' in r and not isinstance(r['max_sinks'], int):
            raise ValueError(f'{tn}.{n}: star max_sinks must be an integer')
        if 'cell' in r and (not isinstance(r['cell'], str) or not re.fullmatch(r'[A-Za-z0-9_]+', r['cell'])):
            raise ValueError(f'{tn}.{n}: star cell must be one library cell name')
        out.append((n, {**STAR_DEFAULT, **r}))
    if len(out) > 1:
        raise ValueError(f'{tn}: at most one star pad clock per type')
    return out


def star_exports(P, tn):
    """config.mk lines of the star trunk ([] when the key is absent)."""
    rows = star(P, tn)
    if not rows:
        return []
    n, r = rows[0]
    return ['# FABLE-FIX-S81-SERDES 11-18 (plan clock.pad_clock pins[].star): matched-leg star trunk on the placed sinks (rck_star.tcl)',
            f'export OT_RCK_STAR_PORT = {n}', f'export OT_RCK_STAR_MAX_SINKS = {int(r["max_sinks"])}',
            f'export OT_RCK_STAR_MAX_EXTENT_UM = {float(r["max_extent_um"]):g}', f'export OT_RCK_STAR_HOP_UM = {float(r["hop_um"]):g}',
            f'export OT_RCK_STAR_CELL = {r["cell"]}']


STAR_HOOK = 'uplevel #0 {source /work/rck_star.tcl}\n'
STAR_FILES = ("rck_star.tcl", "rck_star.py")


def entries(P, tn):
    """[(pad clock name, entry)] of every declared second entry of the type (validated), [] when none."""
    return [(p['name'], e) for p in pins(P, tn) for e in p.get('entries', [])]


def _tcl_list(v):
    return '{' + ' '.join(_tcl_list(x) if isinstance(x, (list, tuple)) else
                          (f'{x:.4f}' if isinstance(x, float) else str(x)) for x in v) + '}'


def _region_ok(r):
    return (isinstance(r, list) and len(r) == 4 and all(_finite_xy(r[i:i + 2]) for i in (0, 2))
            and r[0] < r[2] and r[1] < r[3])


def tap_entries(P, tn):
    """[(tap port, entry)] of the type's core-clock regional entries (clock.tap_entries, validated), [] when none.

    Fail closed: exact keys; a new identifier name that is no port, pad entry or other tap entry; `tap` and every
    take_taps port a grid / added tap of the type (gen_phys.clock_pins, the kit's snapped tap pins) with `tap` among
    take_taps; one library cell; trunk tap pin -> stations -> driver inside the outline, every hop <= ENTRY_HOP_UM
    (12.1e), every trunk point >= TAP_ENTRY_CLEAR_UM off every hard core (a std-cell row, not the tap-pin halo);
    nonempty, pairwise disjoint region rectangles; evidence."""
    t = P.types[tn]
    rows = t.get('clock', {}).get('tap_entries')
    if rows is None:
        return []
    if not isinstance(rows, list) or not rows:
        raise ValueError(f'{tn}: tap_entries needs a nonempty list')
    import gen_phys
    from placement_obstacles import placement_boxes
    taps = {n: (float(x), float(y)) for n, x, y in gen_phys.clock_pins(P, tn)}
    taken = set(taps) | {n for n, *_ in gen_phys.core_tap_pins(P, tn)} | {q['name'] for q in t.get('pads', [])}
    taken |= {b['name'] for b in t.get('buses', [])} | {e['name'] for _, e in entries(P, tn)}
    w, h = t['outline_um']
    eps = 1e-8
    boxes = list(placement_boxes(t, halo=TAP_ENTRY_CLEAR_UM).values())
    names, regs = set(), []
    for e in rows:
        if not isinstance(e, dict) or set(e) != TAP_ENTRY_KEYS:
            raise ValueError(f'{tn}: tap entry requires exactly {sorted(TAP_ENTRY_KEYS)}')
        en = e['name']
        if (not isinstance(en, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', en) or en in names
                or en in taken):
            raise ValueError(f'{tn}: duplicate, invalid or port-colliding tap entry name {en!r}')
        names.add(en)
        tk = e['take_taps']
        if (e['tap'] not in taps or not isinstance(tk, list) or not tk or len(set(tk)) != len(tk)
                or any(q not in taps for q in tk) or e['tap'] not in tk):
            raise ValueError(f'{tn}.{en}: tap / take_taps must be grid or added tap ports of the type, tap among them')
        if not isinstance(e['cell'], str) or not re.fullmatch(r'[A-Za-z0-9_]+', e['cell']):
            raise ValueError(f'{tn}.{en}: entry cell must be one library cell name')
        if not isinstance(e['evidence'], str) or not e['evidence'].strip():
            raise ValueError(f'{tn}.{en}: entry evidence required')
        st = e['stations_um']
        if not isinstance(st, list) or not _finite_xy(e['xy_um']) or not all(_finite_xy(q) for q in st):
            raise ValueError(f'{tn}.{en}: entry xy_um / stations_um must be finite [x, y] points')
        chain = [list(taps[e['tap']])] + st + [e['xy_um']]
        for x, y in chain[1:]:
            if not (0.0 < x < w and 0.0 < y < h):
                raise ValueError(f'{tn}.{en}: trunk point ({x}, {y}) outside the outline')
            if any(a + eps < x < c - eps and b + eps < y < d - eps for a, b, c, d in boxes):
                raise ValueError(f'{tn}.{en}: trunk point ({x}, {y}) within {TAP_ENTRY_CLEAR_UM} um of a hard core')
        for a, b in zip(chain, chain[1:]):
            hop = abs(a[0] - b[0]) + abs(a[1] - b[1])
            if hop > ENTRY_HOP_UM + 1e-6:
                raise ValueError(f'{tn}.{en}: trunk hop {hop:.1f} um > {ENTRY_HOP_UM:g} um (12.1e)')
        reg = e['region_um']
        if not isinstance(reg, list) or not reg or not all(_region_ok(r) for r in reg):
            raise ValueError(f'{tn}.{en}: region_um must be a nonempty list of [x0, y0, x1, y1] (x0<x1, y0<y1)')
        for r in reg:
            if any(r[0] < q[2] and q[0] < r[2] and r[1] < q[3] and q[1] < r[3] for q in regs):
                raise ValueError(f'{tn}.{en}: region {r} overlaps another tap entry region')
        regs += reg
    return [(e['tap'], e) for e in rows]


def entries_tcl(P, tn):
    """PRE_CTS data + hook call for the declared entries ('' when none): pad_clock_entry.tcl builds each trunk.
    Pad-clock entries keep their 7-field rows (RCK2); core-clock tap entries add the take_taps ports as an 8th field."""
    rows = entries(P, tn)
    trows = tap_entries(P, tn)
    if not rows and not trows:
        return ''
    body = ''.join('  ' + _tcl_list([port, e['name'], e['cell'], [[float(a) for a in s] for s in e['stations_um']],
                                     [float(a) for a in e['xy_um']], [[float(a) for a in r] for r in e['region_um']],
                                     [[s['module'], s['pin']] for s in e['sink_pins']]]) + '\n' for port, e in rows)
    body += ''.join('  ' + _tcl_list([port, e['name'], e['cell'], [[float(a) for a in s] for s in e['stations_um']],
                                      [float(a) for a in e['xy_um']], [[float(a) for a in r] for r in e['region_um']],
                                      [], list(e['take_taps'])]) + '\n' for port, e in trows)
    tap_note = ('# + plan clock.tap_entries (LEAF-CLKENTRY-1109): tap port, 8th field = take_taps ports\n'
                if trows else '')
    return ('# GENERATED by tools/die_plan/gen.py phys (plan clock.pad_clock pins[].entries, RCK2-1109): '
            'port entry cell stations entry_xy regions macro_sinks\n' + tap_note +
            'set ::pce_entries {\n' + body + '}\n'
            'uplevel #0 {source /work/pad_clock_entry.tcl}\n')


SAME_EDGE_KEYS = {'capture', 'eye_hold_extra_ps'}


def same_edge_row(tn, n, row, period_ps):
    """Optional same-edge eye capture of source-synchronous pad data (DIE-HEAD-74 11-06).

    When the capture clock tree is close to one pad period deep, the receiving
    flop samples the data launched by the SAME pad edge (inside its eye), not
    the previous one.  The SDC then states that relation exactly
    (set_multicycle_path 0 -setup: setup on the same edge, hold on the edge
    before), and the declared min budget is lowered by eye_hold_extra_ps, the
    measured TT-minus-FF capture insertion gap plus margin, so the FF-only hold
    sign-off also covers the TT eye edge.  Both fields are required together;
    absent fields keep the generated SDC byte-identical."""
    keys = SAME_EDGE_KEYS & set(row)
    if not keys:
        return False
    if keys != SAME_EDGE_KEYS or row['capture'] != 'same_edge':
        raise ValueError(f"{tn}.{n}: same-edge capture needs capture='same_edge' and eye_hold_extra_ps together")
    x = row['eye_hold_extra_ps']
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or not 0 < x < period_ps:
        raise ValueError(f'{tn}.{n}: eye_hold_extra_ps must be finite, > 0 and below the pad period')
    return True


def io_tcl(P, tn):
    import landing_contract as LC
    out = []
    for p in pins(P, tn):
        want = port_xy(p)
        xy = LC.on_track(P, p['layer'], *want)
        if any(abs(a-b) > 1e-6 for a, b in zip(xy, want)):
            raise ValueError(f"{tn}.{p['name']}: declared pad clock centre is off its layer track")
        out.append(f"place_pin -pin_name {{{p['name']}[0]}} -layer {p['layer']} -location {{{xy[0]:.4f} {xy[1]:.4f}}} "
                   "-pin_size {0.1920 0.1920} ;# explicit PHY pad clock")
    return '\n'.join(out) + ('\n' if out else '')


def sdc(P, tn, text):
    ps = pins(P, tn)
    if not ps:
        return text
    import gen_phys
    import landing_contract as LC
    exports = [p for p in ps if p['dir'] == 'out']
    if exports:
        # Collections are explicit OpenSTA port selectors, shared with the
        # existing landing helper; pad clocks are never labelled landing pins.
        selectors = ' '.join(LC.data_output_selectors(P, tn))
        text = 'set pad_data_outputs [get_ports {' + selectors + '}]\n' + text.replace('[all_outputs]', '$pad_data_outputs')
    # Define inputs before uncertainty is applied to [all_clocks].
    clocks = ''.join(f"create_clock -name {p['name']} -period {gen_phys.t_lib(p['period_ps']):.4f} [get_ports {{{p['name']}[0]}}]\n"
                     for p in ps if p['dir'] == 'in')
    text = clocks + text
    edge_names = {n for n, *_ in gen_phys.edge_clock_pins(P, tn)}
    for p in exports:
        master = p['source_clock_port'] if p['source_clock_port'] in edge_names else 'clk'
        text += (f"create_generated_clock -name {p['name']} -master_clock {master} "
                 f"-source [get_ports {{{p['source_clock_port']}}}] -divide_by 1 [get_ports {{{p['name']}[0]}}]\n")
    data = [(p['name'], row) for p in ps for row in p.get('data_inputs', [])]
    if data:
        # These pads belong to their recovered clock, not the die seam's
        # virtual insertion. Keep the exact declared delay budgets and keep
        # their real same-domain setup AND hold checks.
        selectors = ' '.join(row['port'] + '[*]' for _clock, row in data)
        marker = 'set non_clk_in [all_inputs -no_clocks]\n'
        if text.count(marker) != 1:
            raise ValueError(f'{tn}: native pad data needs the explicit generic input collection')
        text = text.replace(marker, marker +
            f'set pad_native_inputs [get_ports {{{selectors}}}]\n' +
            'set pad_seam_inputs {}\n' +
            'foreach pad_input $non_clk_in {\n' +
            '  if {[lsearch -exact $pad_native_inputs $pad_input] < 0} {lappend pad_seam_inputs $pad_input}\n' +
            '}\n')
        text = '\n'.join(line.replace('$non_clk_in', '$pad_seam_inputs')
                         if line.startswith('set_input_delay ') else line
                         for line in text.splitlines()) + '\n'
        for clock, row in data:
            same = row.get('capture') == 'same_edge'
            native_min = row['min_ps'] - (row['eye_hold_extra_ps'] if same else 0)
            text += (f'# OT_NATIVE_PAD_INPUT {clock} {row["port"]}[*] '
                     f'{gen_phys.t_lib(native_min):.4f} {gen_phys.t_lib(row["max_ps"]):.4f}\n')
            for kind in ('max', 'min'):
                budget = row[kind + '_ps'] - (row['eye_hold_extra_ps'] if same and kind == 'min' else 0)
                value = gen_phys.t_lib(budget)
                text += (f'set_input_delay -{kind} {value:.4f} -clock {clock} '
                         f'[get_ports {{{row["port"]}[*]}}]\n')
            if same:
                text += f'set_multicycle_path 0 -setup -from [get_ports {{{row["port"]}[*]}}]\n'
    output_data = [(p['name'], row) for p in exports for row in p.get('data_outputs', [])]
    if output_data:
        # Keep the existing loads on every data output. Only their generic
        # virtual-clock delays use the filtered explicit collection.
        native = {row['port'] for _clock, row in output_data}
        seam = [sel for sel in LC.data_output_selectors(P, tn)
                if sel.split('[', 1)[0] not in native]
        collection = '[get_ports {' + ' '.join(seam) + '}]' if seam else '{}'
        lines = []
        for line in text.splitlines():
            if line.startswith('set_output_delay ') and any(
                    name in line for name in ('$pad_data_outputs', '$cland_data_outputs')):
                if not seam:
                    continue
                line = line.replace('$pad_data_outputs', '$pad_seam_outputs').replace(
                    '$cland_data_outputs', '$pad_seam_outputs')
            lines.append(line)
        text = 'set pad_seam_outputs ' + collection + '\n' + '\n'.join(lines) + '\n'
        for clock in dict.fromkeys(clock for clock, _row in output_data):
            text += (f'set_clock_uncertainty {gen_phys.t_lib(gen_phys.unc_setup_ps()):.4f} '
                     f'-setup [get_clocks {clock}]\n'
                     f'set_clock_uncertainty {gen_phys.t_lib(gen_phys.unc_hold_ps()):.4f} '
                     f'-hold [get_clocks {clock}]\n')
        for clock, row in output_data:
            for kind in ('max', 'min'):
                value = gen_phys.t_lib(row[kind + '_ps'])
                text += (f'set_output_delay -{kind} {value:.4f} -clock {clock} '
                         f'[get_ports {{{row["port"]}[*]}}]\n')
    text += cdc_sdc(ps, text, gen_phys.t_lib)
    if any(p['name'] == 'pma_tck' and p['source_clock_port'] == 'clk' for p in exports):
        text += PHY_EXPORT_SOURCE_SDC + '\n'
    return text


def sdc_clock_names(text):
    """names of every create_clock / create_generated_clock in an SDC text, in order."""
    out = []
    for m in re.finditer(r'^\s*create_(?:generated_)?clock\b[^\n]*?-name\s+(\S+)', text, re.M):
        if m.group(1) not in out:
            out.append(m.group(1))
    return out


def cdc_sdc(ps, text, t_lib):
    """opt-in asynchronous crossing lines for declared synchronized input pad clocks against every other clock in
    text (empty without a declaration).  A pair of two declared pads is emitted once, at the first pad's period."""
    out, done = '', set()
    names = sdc_clock_names(text)
    for p in ps:
        if p.get('cdc') != 'synchronized':
            continue
        a, per = p['name'], t_lib(p['period_ps'])
        others = [b for b in names if b != a and frozenset((a, b)) not in done]
        if not others:
            continue
        out += f"# {CDC_RULE}: {a} (evidence: plan cdc_evidence / pad_clock.json)\n"
        for b in others:
            done.add(frozenset((a, b)))
            out += (f"set_max_delay -ignore_clock_latency {per:.4f} -from [get_clocks {a}] -to [get_clocks {b}]\n"
                    f"set_max_delay -ignore_clock_latency {per:.4f} -from [get_clocks {b}] -to [get_clocks {a}]\n"
                    f"set_false_path -hold -from [get_clocks {a}] -to [get_clocks {b}]\n"
                    f"set_false_path -hold -from [get_clocks {b}] -to [get_clocks {a}]\n")
    return out


def has_min_early(t):
    """True when the type declares min_early_ps on a pad-clock entry or an early core tap (cheap raw scan)."""
    ck = t.get('clock', {}) or {}
    pins_ = (ck.get('pad_clock') or {}).get('pins', []) if isinstance(ck.get('pad_clock'), dict) else []
    return (any('min_early_ps' in e for p in pins_ if isinstance(p, dict) for e in p.get('entries', []) or [])
            or any('min_early_ps' in tp for tp in ck.get('taps', []) or []))


def _module_insts(t, module):
    """instance names of the type's hard cores / contents of `module` (the bound physical identity when it has one)."""
    import gen_phys
    out = []
    for c in list(t.get('hard_cores', []) or []) + list(t.get('contents', []) or []):
        if c.get('module') == module and (c.get('inst') or c.get('physical_inst')):
            out.append(gen_phys.content_physical_identity(c)[0] if ('physical_inst' in c or 'physical_master' in c) else c['inst'])
    return sorted(set(out))


def early_rows(P, tn):
    """[(entry, inst, pin, min_early_ps)] of every pad-clock entry sink pin with min_early_ps (inst resolved from the type's
    hard_cores / contents by module; unresolved = ValueError, fail closed) and of every early core tap
    (clock.taps[] kind core) with min_early_ps (name = the tap, one row per core clock pin; the declared insertion must
    already deliver it: core_tap_early_ps >= min_early_ps, else ValueError).  Sorted, [] when none."""
    t = P.types[tn]
    rows = []
    for _port, e in entries(P, tn):
        if 'min_early_ps' not in e:
            continue
        for s in e['sink_pins']:
            insts = _module_insts(t, s['module'])
            if not insts:
                raise ValueError(f"{tn}.{e['name']}: min_early_ps sink module {s['module']} names no placed hard core / content inst")
            rows += [(e['name'], i, s['pin'], float(e['min_early_ps'])) for i in insts]
    import gen_phys
    import schema as S
    ck = t.get('clock', {}) or {}
    for tp in ck.get('taps', []) or []:
        if 'min_early_ps' in tp and (tp.get('kind') != 'core' or ck.get('core_taps') != 'early'):
            raise ValueError(f"{tn}.{tp['name']}: min_early_ps needs a kind core tap with clock.core_taps 'early'")
    for n, _x, _y, tp in S.core_taps(P, tn):
        if 'min_early_ps' not in tp:
            continue
        check_min_early(f"{tn}.{tp['name']}", tp)
        have = S.core_tap_early_ps(P, tp, 'TT', P.types[tn])
        if have + 1e-9 < float(tp['min_early_ps']):
            raise ValueError(f"{tn}.{tp['name']}: early core tap delivers {have:.1f} ps early (insertion_ps - die common latency), "
                             f"min_early_ps asks {tp['min_early_ps']}")
        for port, inst, pin, _e, _i in gen_phys.core_tap_rows(P, tn):
            if port == n:
                rows.append((tp['name'], inst, pin, float(tp['min_early_ps'])))
    return sorted(set(rows))


def early_text(rows):
    return ('# GENERATED by tools/die_plan/gen.py phys (plan min_early_ps, PLAN-READERS-1): entry inst pin min_early_ps\n'
            + ''.join(f'{e} {i} {p} {m:g}\n' for e, i, p, m in rows))


def write_contract(P, tn, kit):
    """Replace or remove exactly this generator-owned optional sidecar."""
    import json
    from pathlib import Path
    ep = Path(kit) / EARLY_FILE
    er = early_rows(P, tn)
    if er:
        ep.write_text(early_text(er))
    else:
        ep.unlink(missing_ok=True)
    path = Path(kit) / 'pad_clock.json'
    ps = pins(P, tn)
    if ps:
        path.write_text(json.dumps(dict(schema='opentallas.pad_clock.v1', pins=ps), indent=1) + '\n')
    else:
        path.unlink(missing_ok=True)
    owned = [Path(kit) / 'phy_clock_export.tcl', Path(kit) / 'phy_clock_export_source.tcl']
    export = next((p for p in ps if p['name'] == 'pma_tck' and p['dir'] == 'out'
                   and p['source_clock_port'] == 'clk'), None)
    if export is None:
        for f in owned:
            f.unlink(missing_ok=True)
    else:
        import shutil
        import gen_phys
        shutil.copyfile(Path(__file__).with_name('phy_clock_export.tcl'), owned[0])
        owned[1].write_text(
            '# Generator-owned typed pma_tck export; no IO, uncertainty or CDC policy changes.\n'
            'source [file join [file dirname [info script]] phy_clock_export.tcl]\n'
            'ot_phy_export_rebind [dict create target {pma_tck[0]} clock pma_tck master clk '
            f'declared_source clk period {gen_phys.t_lib(export["period_ps"]):.4f} period_ps {export["period_ps"]}]\n')

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
TAP_ENTRY_CLEAR_UM = 2.16      # a trunk / driver point is a std cell: >= 8 rows off every hard core (not the 8.64 tap-pin halo)
TAP_ENTRY_KEYS = {'name', 'tap', 'take_taps', 'xy_um', 'stations_um', 'cell', 'region_um', 'evidence'}
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
        if not isinstance(p, dict) or required - set(p) or set(p) - required - {'source_clock_port', 'sink_pins', 'cdc', 'cdc_evidence', 'data_inputs', 'data_outputs', 'entries'}:
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
        if not isinstance(e, dict) or set(e) != ENTRY_KEYS:
            raise ValueError(f'{tn}.{n}: entry requires exactly {sorted(ENTRY_KEYS)}')
        en = e['name']
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
        xy = LC.on_track(P, p['layer'], *p['xy_um'])
        if any(abs(a-b) > 1e-6 for a, b in zip(xy, p['xy_um'])):
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
    return text + cdc_sdc(ps, text, gen_phys.t_lib)


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


def write_contract(P, tn, kit):
    """Replace or remove exactly this generator-owned optional sidecar."""
    import json
    from pathlib import Path
    path = Path(kit) / 'pad_clock.json'
    ps = pins(P, tn)
    if ps:
        path.write_text(json.dumps(dict(schema='opentallas.pad_clock.v1', pins=ps), indent=1) + '\n')
    else:
        path.unlink(missing_ok=True)

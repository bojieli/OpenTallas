"""Explicit physical and timing roles for existing PHY clock pads.

No period is inferred from the digital die clock. This contract creates no
clock groups or landing-ring phase constraints.  By default it creates no
crossing exceptions either; an input pin may opt in with "cdc": "synchronized"
plus a "cdc_evidence" string (COORD ruling 10-31 (3): every crossing of that
plesiochronous PHY clock is synchronized), which emits exactly the asynchronous
crossing form CDC_RULE describes (no set_clock_groups: OpenSTA would then drop
the max delay).
"""
import math
import re

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
    required = {'name', 'dir', 'period_ps', 'source', 'layer', 'xy_um'}
    periods = {}
    import gen_phys
    periods.update({n: float(P.die['period_ps']) for n, *_ in gen_phys.clock_pins(P, tn) + gen_phys.core_tap_pins(P, tn)})
    periods.update({n: float(P.die['period_ps']) * m for n, _x, _y, m in gen_phys.edge_clock_pins(P, tn)})
    for p in c['pins']:
        if not isinstance(p, dict) or required - set(p) or set(p) - required - {'source_clock_port', 'sink_pins', 'cdc', 'cdc_evidence'}:
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
        result.append(dict(p))
    if seen != set(pads):
        raise ValueError(f'{tn}: pad_clock must cover every existing clock pad: {sorted(set(pads) - seen)}')
    return result


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

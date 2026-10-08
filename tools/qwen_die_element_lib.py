#!/usr/bin/env python3
"""Qwen ROM die: interface-timing Liberty views of the die's placeholder elements, for die-level OpenSTA.

Every die element boundary is register-to-register (owner rule 2026-10-06: inputs captured in a flop at the pin,
outputs launched from a flop at the pin, no logic between pin and flop), so an element's interface timing is one
flop: setup/hold at every input pin against the element clock pin, clock->Q plus the output drive at every output
pin.  This writes those views; the values are ASSUMED single-flop constants (ASAP7 DFFHQNx1 class at SS 0.63 V /
FF 0.77 V, scaled up for an output driver), NOT characterised element ETMs: no Qwen element has an ETM yet.  The
die STA they feed is therefore a die-WIRE audit (routed top-level RC between registered pins), not block sign-off.

Directions per bit: die_top_lint's registered stubs (inout ports: the bits the stub assigns from a flop are outputs),
real shells (ot_qwen_stream4_cdc_pc) through the die's abstract port names (qfd_cdc: ho/hi on hclk, co/ci on clk).
Clock pins (ck, ckx, cks, cku, ckd, clk, hclk) are clock inputs; forwarded-clock (fck_*) and PLL (pll_*) pins carry
no arcs (the STA creates its clocks on the PLL pins).

    python3 tools/qwen_die_element_lib.py --stubs LINTDIR/qwen_rom_lint_top_stubs.sv --lef CASE/elements.lef --out DIR
"""
import argparse
import re
from collections import defaultdict
from pathlib import Path

CLOCKS = ('ck', 'ckx', 'cks', 'cku', 'ckd', 'clk', 'hclk')
CORNERS = dict(  # setup, hold, clk->q base, ps/fF output slope, output transition base, ps/fF, input cap fF (ASSUMED)
    ss=dict(setup=30.0, hold=5.0, cq=75.0, k=0.9, tr=25.0, tk=1.6, cin=0.7, volt=0.63, temp=100),
    ff=dict(setup=12.0, hold=12.0, cq=32.0, k=0.35, tr=10.0, tk=0.7, cin=0.6, volt=0.77, temp=0))
# TT (owner option B setup corner): the SS constants, PESSIMISTIC and disclosed (no characterised TT placeholder exists)
CORNERS['tt'] = dict(CORNERS['ss'], volt=0.7, temp=25)
LOADS = (0.5, 5.0, 20.0, 80.0, 300.0, 1200.0)      # fF
SLEWS = (5.0, 20.0, 80.0, 300.0)                   # ps


IDX = set()     # (master, port) whose LEF pins carry an index ([0] even at width 1): Liberty bus


def lef_pins(path):
    """master -> {port: nbits} from the k=1 abstract LEF (pins 'p[i]' or 'p')."""
    out, cur, pin = defaultdict(dict), None, None
    for ln in Path(path).read_text().splitlines():
        t = ln.split()
        if not t:
            continue
        if t[0] == 'MACRO':
            cur = t[1]
        elif t[0] == 'PIN' and cur:
            m = re.match(r'([^\[]+)(?:\[(\d+)\])?$', t[1])
            pin = (m.group(1), m.group(2))
            p, i = pin
            out[cur][p] = max(out[cur].get(p, 0), (int(i) + 1) if i is not None else 1)
            if i is not None:
                IDX.add((cur, p))
        elif t[0] == 'USE' and pin and t[1].rstrip(';') in ('POWER', 'GROUND'):
            out[cur].pop(pin[0], None)          # supply pins: no Liberty signal pin
    return out


def stub_dirs(path):
    """module -> {port: (dir, width, {out bit set}, clock)} from die_top_lint's stubs."""
    mods, cur = {}, None
    for ln in Path(path).read_text().splitlines():
        m = re.match(r'\s*module (\S+)', ln)
        if m:
            cur = mods.setdefault(m.group(1), {})
            continue
        m = re.match(r'\s*(input|output|inout) wire \[(\d+):0\] (\w+)', ln)
        if m and cur is not None:
            cur[m.group(3)] = [m.group(1), int(m.group(2)) + 1, set()]
            continue
        m = re.search(r'assign (\w+)\[(\d+):(\d+)\] = r_', ln)
        if m and cur is not None and m.group(1) in cur:
            cur[m.group(1)][2].update(range(int(m.group(3)), int(m.group(2)) + 1))
    return mods


def bit_dirs(master, port, n, stubs):
    if master == 'qfd_cdc':
        return ['output' if port in ('ho', 'co') else 'input'] * n, ('hclk' if port in ('ho', 'hi') else 'clk')
    s = stubs.get(master, {}).get(port)
    if s is None:
        return ['input'] * n, None
    d, w, outs = s
    if d == 'inout':
        return ['output' if i in outs else 'input' for i in range(n)], None
    return [d] * n, None


def table(vals_fn, idx1, idx2=None):
    if idx2 is None:
        return ('index_1 ("%s"); values ("%s");' % (', '.join(f'{x:g}' for x in idx1),
                                                     ', '.join(f'{vals_fn(x):.2f}' for x in idx1)))
    rows = ', '.join('"%s"' % ', '.join(f'{vals_fn(a, b):.2f}' for b in idx2) for a in idx1)
    return ('index_1 ("%s"); index_2 ("%s"); values (%s);' % (', '.join(f'{x:g}' for x in idx1),
                                                              ', '.join(f'{x:g}' for x in idx2), rows))


def write_lib(corner, lef, stubs, path):
    c = CORNERS[corner]
    L = [f'library (qfd_elements_{corner}) {{',
         '  delay_model : table_lookup; time_unit : "1ps"; capacitive_load_unit (1, ff); voltage_unit : "1V";',
         '  current_unit : "1mA"; pulling_resistance_unit : "1kohm"; leakage_power_unit : "1nW";',
         f'  nom_process : 1; nom_voltage : {c["volt"]}; nom_temperature : {c["temp"]};',
         '  slew_lower_threshold_pct_rise : 10; slew_upper_threshold_pct_rise : 90;',
         '  slew_lower_threshold_pct_fall : 10; slew_upper_threshold_pct_fall : 90;',
         '  input_threshold_pct_rise : 50; input_threshold_pct_fall : 50;',
         '  output_threshold_pct_rise : 50; output_threshold_pct_fall : 50;',
         '  lu_table_template (load1) { variable_1 : total_output_net_capacitance; index_1 ("1, 2"); }',
         '  lu_table_template (slew1) { variable_1 : related_pin_transition; index_1 ("1, 2"); }',
         '  lu_table_template (cons2) { variable_1 : related_pin_transition; variable_2 : constrained_pin_transition;'
         ' index_1 ("1, 2"); index_2 ("1, 2"); }']
    widths = sorted({n for m, ps in lef.items() for p, n in ps.items() if n > 1 or (m, p) in IDX})
    for w in widths:
        L.append(f'  type (b{w}) {{ base_type : array; data_type : bit; bit_width : {w}; bit_from : {w - 1};'
                 f' bit_to : 0; downto : true; }}')
    cq = lambda load: c['cq'] + c['k'] * load            # noqa: E731
    trn = lambda load: c['tr'] + c['tk'] * load          # noqa: E731
    for master, ports in sorted(lef.items()):
        if master == 'ot_hbm3e_phy':
            continue                                    # real PHY: its own characterised .lib
        clocks = [p for p in ports if p in CLOCKS]
        L.append(f'  cell ({master}) {{ area : 0; dont_touch : true; dont_use : true;')
        for p, n in sorted(ports.items()):
            dirs, rel = bit_dirs(master, p, n, stubs)
            if p in CLOCKS:
                if (master, p) in IDX:
                    L.append(f'    bus ({p}) {{ bus_type : b{n}; direction : input; clock : true; capacitance : 2.0; }}')
                else:
                    L.append(f'    pin ({p}) {{ direction : input; clock : true; capacitance : 2.0; }}')
                continue
            rel = rel or ('ck' if 'ck' in clocks else (clocks[0] if clocks else None))
            if rel is not None and (master, rel) in IDX:
                rel = rel + '[0]'
            arcs = rel is not None and not p.startswith(('fck_', 'pll_'))

            def pin_body(d):
                if d == 'output':
                    b = ['direction : output; max_capacitance : 5000;']
                    if arcs:
                        b.append(f'timing () {{ related_pin : "{rel}"; timing_type : rising_edge; '
                                 f'cell_rise (load1) {{ {table(cq, LOADS)} }} cell_fall (load1) {{ {table(cq, LOADS)} }} '
                                 f'rise_transition (load1) {{ {table(trn, LOADS)} }} '
                                 f'fall_transition (load1) {{ {table(trn, LOADS)} }} }}')
                    return ' '.join(b)
                b = [f'direction : input; capacitance : {c["cin"]};']
                if arcs:
                    for tt, v in (('setup_rising', c['setup']), ('hold_rising', c['hold'])):
                        f = (lambda a, s_, v=v: v + 0.1 * s_)
                        b.append(f'timing () {{ related_pin : "{rel}"; timing_type : {tt}; '
                                 f'rise_constraint (cons2) {{ {table(f, SLEWS, SLEWS)} }} '
                                 f'fall_constraint (cons2) {{ {table(f, SLEWS, SLEWS)} }} }}')
                return ' '.join(b)
            if n == 1 and (master, p) not in IDX:
                L.append(f'    pin ({p}) {{ {pin_body(dirs[0])} }}')
            else:
                mixed = len(set(dirs)) > 1
                L.append(f'    bus ({p}) {{ bus_type : b{n}; direction : {"inout" if mixed else dirs[0]};')
                if mixed:
                    for i, d in enumerate(dirs):
                        L.append(f'      pin ({p}[{i}]) {{ {pin_body(d)} }}')
                else:
                    L.append(f'      {pin_body(dirs[0]).replace("direction : " + dirs[0] + ";", "")}')
                L.append('    }')
        L.append('  }')
    L.append('}')
    Path(path).write_text('\n'.join(L) + '\n')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--stubs', type=Path, required=True)
    ap.add_argument('--lef', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    lef, stubs = lef_pins(a.lef), stub_dirs(a.stubs)
    for corner in CORNERS:
        write_lib(corner, lef, stubs, a.out / f'qfd_elements_{corner}.lib')
    print(f'{len(lef)} masters -> {a.out}')


if __name__ == '__main__':
    main()

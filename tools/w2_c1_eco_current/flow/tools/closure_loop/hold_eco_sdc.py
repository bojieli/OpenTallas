#!/usr/bin/env python3
"""closure-loop HOLD-ECO: merge the two corners' EFFECTIVE sign-off SDCs (hold_eco_corner.tcl, write_sdc) into ONE
single-mode SDC for the two-corner ECO session, so each check sees the constraints it is signed off with:

  max side (setup, SS)  : the SS file as written (IO max delays, setup uncertainty, clock latencies).
  min side (hold, FF)   : the FF file's IO -min delays, hold uncertainties, hold-only exceptions and min delays.
                          The FF file may move a virtual clock's latency (vclk_corner_true.sdc: vclk at the FF minimum
                          insertion); the merged file keeps the SS latency and shifts the FF min delays by the latency
                          difference d = lat_FF - lat_SS so every hold check is unchanged:
                          input  min' = min + d   (launch at lat + min)
                          output min' = min - d   (required = lat + unc - min)
usage: hold_eco_sdc.py eff_ss.sdc eff_ff.sdc out.sdc
The ECO session validates the result (merged SS max / FF min worst slack == the corner sessions') before repairing."""
import re
import sys

LAT = re.compile(r'^set_clock_latency\s+(?P<v>-?[0-9.]+)\s+\[get_clocks \{(?P<c>[^}]+)\}\]\s*$')
IO = re.compile(r'^(?P<cmd>set_input_delay|set_output_delay)\s+(?P<v>-?[0-9.]+)\s+(?P<rest>.*)$')
CLK = re.compile(r'-clock \[get_clocks \{(?P<c>[^}]+)\}\]')


def latencies(lines):
    lat = {}
    for ln in lines:
        m = LAT.match(ln)
        if m:
            lat[m['c']] = float(m['v'])
    return lat


def has(ln, flag):
    return re.search(rf'(^|\s){re.escape(flag)}(\s|$)', ln) is not None


def side(ln, flag):
    """rewrite a both-sides line (no -min/-max, -setup/-hold) to one side"""
    cmd, rest = ln.split(None, 1)
    return f'{cmd} {flag} {rest}'


def is_min_side(ln):
    """lines whose effect is hold-only (or that carry a hold component)"""
    if ln.startswith(('set_input_delay', 'set_output_delay')):
        return 'min' if has(ln, '-min') else ('max' if has(ln, '-max') else 'both')
    if ln.startswith('set_clock_uncertainty'):
        return 'min' if has(ln, '-hold') else ('max' if has(ln, '-setup') else 'both')
    if ln.startswith(('set_false_path', 'set_multicycle_path')):
        return 'min' if has(ln, '-hold') else ('max' if has(ln, '-setup') else 'both')
    if ln.startswith('set_min_delay'):
        return 'min'
    if ln.startswith('set_max_delay'):
        return 'max'
    return None


def logical_lines(p):
    """write_sdc continues long commands with a trailing backslash: one entry per command"""
    return [ln.strip() for ln in re.sub(r'\\\n\s*', ' ', open(p).read()).splitlines()]


def main(ss_p, ff_p, out_p):
    ss = logical_lines(ss_p)
    ff = logical_lines(ff_p)
    lss, lff = latencies(ss), latencies(ff)
    out, notes = [], []
    for ln in ss:
        k = is_min_side(ln)
        if k == 'min':
            continue
        if k == 'both' and not ln.startswith(('set_false_path', 'set_multicycle_path')):
            ln = side(ln, '-max' if ln.startswith(('set_input', 'set_output')) else '-setup')
        elif k == 'both':
            ln = side(ln, '-setup')
        out.append(ln)
    out.append('# ---- FF (hold) side from the FF effective SDC ----')
    shifted = {}
    for ln in ff:
        k = is_min_side(ln)
        if k not in ('min', 'both'):
            continue
        if k == 'both':
            ln = side(ln, '-min' if ln.startswith(('set_input', 'set_output')) else '-hold')
        m = IO.match(ln)
        if m:
            c = CLK.search(m['rest'])
            if c and c['c'] in lff and abs(lff[c['c']] - lss.get(c['c'], lff[c['c']])) > 1e-9:
                d = lff[c['c']] - lss[c['c']]
                v = float(m['v']) + (d if m['cmd'] == 'set_input_delay' else -d)
                ln = f"{m['cmd']} {v:.4f} {m['rest']}"
                shifted[c['c']] = d
        out.append(ln)
    for c, d in shifted.items():
        notes.append(f'# {c}: FF latency {lff[c]:g} vs SS {lss[c]:g}: FF min IO delays shifted by {d:+g}')
    open(out_p, 'w').write('\n'.join(['# merged by hold_eco_sdc.py: SS max side + FF min side'] + notes + out) + '\n')
    print(f'OT_SDC_MERGE lines {len(out)} shifted {shifted}')


if __name__ == '__main__':
    main(*sys.argv[1:4])

#!/usr/bin/env python3
"""FP32 lane: per-boundary (= per pipeline stage, named by its capture register group) worst setup (TT) and hold (FF)
slack from fp32_lat4_sta.sh's `report_checks -format end` dumps, clk group only (reg->reg / in->reg / reg->out).
usage: stages.py <sta_dir>/<name> [...]   -> JSON on stdout"""
import json, re, sys, pathlib

def groups(path):
    out, grp = {}, None
    for ln in pathlib.Path(path).read_text().splitlines():
        m = re.match(r'^(max_delay/setup|min_delay/hold) group (\S+)', ln)
        if m:
            grp = m.group(2); continue
        m = re.match(r'^(\S+) \((\S+)\)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)', ln)
        if not m or grp != 'clk':
            continue
        ep = m.group(1)
        name = ep.split('/')[0] if '/' in ep else ep          # pin of a flop, or an output port
        name = name.replace('\\', '')
        name = re.sub(r'\$_.*$', '', name)                    # yosys flop suffix
        name = re.sub(r'\[\d+\]', '', name)                    # bit index
        name = re.sub(r'\.(g_r|g_rv)\.(r|rv|rd)$', '', name)   # cut-module generate regs -> the cut instance
        name = re.sub(r'\.g_b(\[\d+\])?$', '', name)
        s = float(m.group(5))
        out[name] = min(out.get(name, 1e9), s)
    return out

res = {}
for d in sys.argv[1:]:
    d = pathlib.Path(d)
    setup = groups(d / 'ends_TT_max.rpt'); hold = groups(d / 'ends_FF_min.rpt')
    log = (d / 'sta_TT_max.log').read_text()
    m = re.search(r'Design area ([\d.]+) um', log); cells = re.search(r'OT_CELLS (\d+) OT_REGS (\d+)', log)
    syn = d / 'orfs' / 'reports' / 'asap7' / d.name / 'base' / 'synth_stat.txt'
    sa = None
    if syn.exists():
        mm = re.search(r"Chip area for module '\\?fp32_sta_top': ([\d.]+)", syn.read_text()); sa = float(mm.group(1)) if mm else None
    res[d.name] = {
        'placed_area_um2': float(m.group(1)) if m else None, 'synth_area_um2': sa,
        'cells': int(cells.group(1)) if cells else None, 'regs': int(cells.group(2)) if cells else None,
        'wns_setup_tt_ps': min(setup.values()) if setup else None, 'wns_hold_ff_ps': min(hold.values()) if hold else None,
        'setup_tt_by_capture_group': dict(sorted(setup.items(), key=lambda kv: kv[1])),
        'hold_ff_by_capture_group': dict(sorted(hold.items(), key=lambda kv: kv[1])),
    }
json.dump(res, sys.stdout, indent=1)

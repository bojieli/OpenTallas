#!/usr/bin/env python3
"""Plan an A-only physical hold ECO; the emitted ODB is explicitly unqualified.

Only single-fanout routed HB2+BUF or HB2+HB2 pairs are eligible. Existing named pin pads,
clock/reset registers, all other sequential cells and mapped SRAM are retained.
The plan consumes the native TT ETM and exact FF per-input timing points, and
requires 30 ps measured FF margin after subtracting the removed path interval.
Actual TT/FF signoff, route, DRC and ETM export must follow in the canonical job.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hier_contract'))
import pinreg_audit as PA

CELL = 'qkd_ectl_a_tp8_epoch_direct'
HB = 'HB2xp67_ASAP7_75t_R'
BF = 'BUFx2_ASAP7_75t_R'

def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def netlist(path):
    cells, loads = {}, collections.defaultdict(list)
    text = Path(path).read_text()
    if not re.search(r'\bmodule\s+' + CELL + r'\b', text):
        raise ValueError('wrong top: A native controller only')
    for m in re.finditer(r'^\s*(\S+)\s+(\S+)\s*\((.*?)\);', text, re.M | re.S):
        master, name, body = m.groups()
        name = name.removeprefix('\\')
        ports = {k: v.strip().removeprefix('\\') for k, v in re.findall(r'\.(\w+)\(\s*([^()]*)\s*\)', body)}
        if name in cells:
            raise ValueError('duplicate cell ' + name)
        cells[name] = (master, ports)
        # Eligible pairs must have exactly one signal sink on each net. Any
        # unexpected input terminal is a real extra load, not silently ignored.
        for pin, net in ports.items():
            if pin not in ('Y', 'Q', 'QN'):
                loads[net].append((name, pin))
    return cells, loads

def timing_points(path):
    paths = collections.defaultdict(list)
    cur = None
    for line in Path(path).read_text().splitlines():
        x = line.split('\t')
        if x[0] == 'PATH':
            cur = {'endpoint': x[2], 'slack_ps': float(x[3]), 'points': {}}
            paths[x[1]].append(cur)
        elif x[0] == 'PT' and cur is not None:
            cur['points'][x[1]] = float(x[2])
        else:
            raise ValueError('invalid FF point row')
    return paths

def walk(pin, cells, loads):
    net, chain, seen = pin, [], set()
    for _ in range(100):
        if net in seen:
            raise ValueError('loop at ' + net)
        seen.add(net)
        if len(loads[net]) != 1:
            break
        name, term = loads[net][0]
        master, ports = cells[name]
        if term != 'A' or not re.match(r'^(HB|BUF)', master) or 'Y' not in ports:
            break
        chain.append(name)
        net = ports['Y']
    return chain

def choose(pin, capture, cells, loads, paths, margin=30.0):
    if not re.fullmatch(r'(rs\[\d+\]|cfg\[[0-4]\]|rst_n)', pin):
        raise ValueError('unexpected failing input ' + pin)
    chain = walk(pin, cells, loads)
    eligible = []
    for a, b in zip(chain, chain[1:]):
        am, ap = cells[a]; bm, bp = cells[b]
        if not re.fullmatch(r'hold\d+', a) or not re.fullmatch(r'hold\d+', b):
            continue
        if (am, bm) not in ((HB, BF), (HB, HB)) or ap['Y'] != bp['A']:
            continue
        if loads[ap['Y']] != [(b, 'A')] or len(loads[bp['Y']]) != 1:
            continue
        if pin != 'rst_n':
            # Normal data paths must still contain their original kept prepad.
            if not chain[0].startswith('ot_inhold_') or not chain[1].startswith('ot_ihdrv_'):
                raise ValueError('original pin pad missing at ' + pin)
        evidence = []
        for path in paths:
            pts = path['points']
            if a + '/A' not in pts or b + '/Y' not in pts:
                evidence = []; break
            removed = pts[b + '/Y'] - pts[a + '/A']
            remain = path['slack_ps'] - removed
            if removed <= 0 or remain < margin:
                evidence = []; break
            evidence.append({'endpoint': path['endpoint'], 'old_hold_ps': path['slack_ps'],
                             'removed_interval_ps': removed, 'estimated_hold_ps': remain})
        if evidence:
            eligible.append({'input': pin, 'old_capture_ps': capture, 'remove': [a, b],
                             'masters': [am, bm], 'keep_net': ap['A'], 'dead_nets': [ap['Y'], bp['Y']],
                             'sink': list(loads[bp['Y']][0]), 'FF_paths': evidence})
    # Later paths usually retain the original input slew and have lower delay.
    return max(eligible, key=lambda c: min(x['estimated_hold_ps'] for x in c['FF_paths']), default=None)

def q(s):
    if any(c in s for c in '{}\n\r'):
        raise ValueError('unsafe Tcl identifier')
    return '{' + s + '}'

def apply_tcl(plan):
    lines = ['# UNQUALIFIED physical ECO. Re-route, extract, TT/FF signoff, DRC and native export required.',
             '# Read the exact source ODB named by the hashed canonical recovery receipt before sourcing.',
             'if {![info exists ::env(ECTL_ECO_INPUT_ODB)]} {error "canonical source ODB path required"}',
             f'if {{[lindex [exec sha256sum $::env(ECTL_ECO_INPUT_ODB)] 0] ne {q(plan["input_odb_sha256"])}}} {{error "source ODB hash mismatch"}}',
             'set blk [ord::get_db_block]',
             'if {[$blk getName] ne ' + q(CELL) + '} {error "wrong A top"}',
             'set removed 0']
    # Validate the complete plan before making the first mutation.
    for c in plan['candidates']:
        a,b=c['remove']; n0,n1=c['dead_nets']; sn,st=c['sink']
        for name,master in zip((a,b),c['masters']):
            lines += [f'set i [$blk findInst {q(name)}]',
                      f'if {{$i eq "NULL" || [[$i getMaster] getName] ne {q(master)}}} {{error "ECO master mismatch"}}']
        lines += [f'set a [$blk findInst {q(a)}]; set b [$blk findInst {q(b)}]',
                  f'if {{[[[$a findITerm A] getNet] getName] ne {q(c["keep_net"])}}} {{error "ECO upstream net mismatch"}}',
                  f'if {{[[[$a findITerm Y] getNet] getName] ne {q(n0)} || [[[$b findITerm A] getNet] getName] ne {q(n0)}}} {{error "ECO pair not adjacent"}}',
                  f'set n [$blk findNet {q(n0)}]',
                  'if {[llength [$n getITerms]] != 2 || [llength [$n getBTerms]] != 0} {error "ECO pair fanout"}',
                  f'if {{[[[$b findITerm Y] getNet] getName] ne {q(n1)}}} {{error "ECO output net mismatch"}}',
                  f'set n [$blk findNet {q(n1)}]',
                  'if {[llength [$n getITerms]] != 2 || [llength [$n getBTerms]] != 0} {error "ECO output fanout"}',
                  f'set s [[$blk findInst {q(sn)}] findITerm {q(st)}]',
                  f'if {{[[$s getNet] getName] ne {q(n1)}}} {{error "ECO sink mismatch"}}']
    for c in plan['candidates']:
        a,b=c['remove'];sn,st=c['sink']
        lines += [f'set keep [$blk findNet {q(c["keep_net"])}]',
                  f'set s [[$blk findInst {q(sn)}] findITerm {q(st)}]',
                  '$s disconnect; $s connect $keep',
                  f'odb::dbInst_destroy [$blk findInst {q(a)}]',
                  f'odb::dbInst_destroy [$blk findInst {q(b)}]']
        for n in c['dead_nets']:
            lines += [f'set n [$blk findNet {q(n)}]',
                      'if {[llength [$n getITerms]] || [llength [$n getBTerms]]} {error "dead net still connected"}',
                      'odb::dbNet_destroy $n']
        lines += ['# The affected driver net must be physically re-routed, not published with stale wires.',
                  'set w [$keep getWire]; if {$w ne "NULL"} {odb::dbWire_destroy $w}',
                  'incr removed 2']
    lines += [f'if {{$removed != {2*len(plan["candidates"])}}} {{error "ECO count mismatch"}}',
              'puts "ECTL_NATIVE_HOLD_NORMALIZE removed=$removed UNQUALIFIED_REQUIRES_REROUTE"']
    return '\n'.join(lines)+'\n'

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input-odb-sha256', required=True)
    ap.add_argument('--netlist',type=Path,required=True);ap.add_argument('--view',type=Path,required=True)
    ap.add_argument('--ff-points',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    if not re.fullmatch('[0-9a-f]{64}', args.input_odb_sha256):raise ValueError('invalid source ODB hash')
    cells,loads=netlist(args.netlist);paths=timing_points(args.ff_points)
    lib=PA.parse_lib(args.view/f'{CELL}_tt.lib');ij=json.loads((args.view/'insertion.json').read_text())
    metrics=PA.pin_metrics(lib,PA.clock_refs(lib,ij,'tt'))
    candidates=[];unresolved=[]
    for pin,m in metrics.items():
        if m['dir']!='input' or m['inp'] is None or m['inp']<=190:continue
        c=choose(pin,m['inp'],cells,loads,paths[pin])
        if c:candidates.append(c)
        else:unresolved.append(pin)
    names=[n for c in candidates for n in c['remove']]
    if len(names)!=len(set(names)):raise ValueError('shared removal cell: plan is not independent')
    dead={n for c in candidates for n in c['dead_nets']}
    if dead & {c['keep_net'] for c in candidates}:raise ValueError('dependent removal nets')
    plan={'schema':'opentallas.qwen.ectl_native_hold_plan.v1','status':'UNQUALIFIED_PLAN_REQUIRES_CANONICAL_REROUTE',
          'cell':CELL,'input_odb_sha256':args.input_odb_sha256,'FF_margin_ps':30.0,'added_edges':0,'parameters':{'STATIC_QK':1,'ROW_RETURN_LAT':21,'QK_ISSUE_AGE':34,'HXK':13},
          'input_hashes':{str(p):digest(p) for p in (args.netlist,args.ff_points,args.view/f'{CELL}_tt.lib',args.view/'insertion.json')},
          'candidates':candidates,'unresolved':unresolved}
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    (args.out/'apply_unqualified.tcl').write_text(apply_tcl(plan))
    print(json.dumps({'planned_inputs':len(candidates),'removed_cells':len(names),'unresolved':unresolved,
                     'min_estimated_FF_hold_ps':min((p['estimated_hold_ps'] for c in candidates for p in c['FF_paths']),default=None)}))
    return bool(unresolved)

if __name__=='__main__':sys.exit(main())

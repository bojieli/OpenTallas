#!/usr/bin/env python3
"""Fail-closed internal timing evidence for the masters actually bound in a die kit.

ETM boundary timing never proves internal sequential timing. Census reads the
immutable die kit; replay reuses a retained CLOSED view's precise export sequence
and parasitics without modifying a clock, exception, route, or threshold. Run
replay on a fleet host via ot-run, never as an unadmitted local heavy command.
"""
import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

SCHEMA = 'opentallas.bound_leaf_internal.v1'

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def write(p, value):
    Path(p).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def census(kit):
    index = json.loads((kit / 'index.json').read_text())
    libs = {}
    for corner in ('ss', 'ff'):
        for name in (kit / f'libs_{corner}.txt').read_text().splitlines():
            p = Path(name)
            if not p.exists():
                continue
            for master in re.findall(r'\bcell\s*\(\s*"?([\w]+)"?\s*\)', p.read_text()):
                libs.setdefault(master, {})[corner] = {'path': str(p), 'sha256': sha(p)}
    rows = []
    for master, entry in sorted(index['masters'].items()):
        kind = entry['view']
        spec = None
        if libs.get(master, {}).get('ss'):
            spec_path = Path(libs[master]['ss']['path']).parent.parent.parent / 'spec.json'
            if spec_path.exists():
                d = json.loads(spec_path.read_text())
                source_root = Path((kit / 'src_root').read_text().strip())
                spec = {'sha256': sha(spec_path), 'top': d['top'], 'params': d.get('params', {}),
                        'sources': {n: sha(source_root / n) for n in d.get('sources', [])}}
        rows.append({'routed_spec': spec, 'master': master, 'instances': entry.get('instances', 0),
                     'kind': kind, 'libs': libs.get(master, {}),
                     'required': kind in ('closed', 'macro'),
                     'status': 'INTERNAL_EVIDENCE_REQUIRED' if kind == 'closed' else
                     'PLACEHOLDER' if kind in ('interim', 'partitioned') else 'HARD_IP_REVIEW_REQUIRED'})
    return {'schema': SCHEMA, 'scope': 'actual die-kit binding only', 'kit': str(kit),
            'kit_index_sha256': sha(kit / 'index.json'),
            'clock_delivery_sha256': sha(kit / 'clock_delivery.json'),
            'die_netlist_sha256': sha(kit / 'die.v'), 'masters': rows,
            'release_complete': False}

AUDIT = r'''
puts "OT_INTERNAL_BEGIN"
report_clock_properties
foreach c [all_clocks] {
 puts "OT_INTERNAL_CLOCK [get_full_name $c] [get_property $c period]"
}
set eps [all_registers -data_pins]
puts "OT_INTERNAL_DATA_COUNT [llength $eps]"
set regnames [dict create]
foreach p [all_registers -output_pins] {dict set regnames [get_full_name $p] 1}
set pairs 0
foreach ep $eps {
 foreach p [get_fanin -to $ep -flat -startpoints_only -trace_arcs all] {
  if {[dict exists $regnames [get_full_name $p]]} {
   incr pairs
   puts "OT_INTERNAL_STRUCTURAL_PAIR [get_full_name $p] [get_full_name $ep]"
  }
 }
}
puts "OT_INTERNAL_STRUCTURAL_PAIRS $pairs"
foreach mode {max min} {
 set missing 0
 set worst INF
 foreach ep $eps {
  set val [get_property $ep slack_$mode]
  if {![string is double -strict $val]} {
   incr missing
   puts "OT_INTERNAL_UNCONSTRAINED $mode [get_full_name $ep]"
  } elseif {$worst eq "INF" || $val < $worst} {set worst $val}
 }
 puts "OT_INTERNAL_COVERAGE $mode [llength $eps] $missing $worst"
 set paths [find_timing_paths -from [all_registers -output_pins] -to $eps -path_delay $mode -group_path_count 1000000 -endpoint_path_count 1]
 set worst INF
 foreach p $paths {
  set val [get_property $p slack]
  if {$worst eq "INF" || $val < $worst} {set worst $val}
 }
 puts "OT_INTERNAL_REG2REG $mode [llength $paths] $worst"
 report_checks -from [all_registers -output_pins] -to $eps -path_delay $mode -group_path_count 10 -format full_clock_expanded -digits 6
}
puts "OT_INTERNAL_MIN_PERIOD_BEGIN"
report_clock_min_period
puts "OT_INTERNAL_MIN_PERIOD_END"
puts "OT_INTERNAL_PERIOD_CHECKS_BEGIN"
report_check_types -min_period -min_pulse_width -violators -digits 6
puts "OT_INTERNAL_PERIOD_CHECKS_END"
check_setup -verbose
write_sdc -no_timestamp /out/replayed.sdc
puts "OT_INTERNAL_DONE"
exit
'''

def parse(log):
    coverage = {}
    reg2reg = {}
    for mode, count, missing, worst in re.findall(r'^OT_INTERNAL_COVERAGE (max|min) (\d+) (\d+) (\S+)$', log, re.M):
        coverage[mode] = {'endpoints': int(count), 'unconstrained': int(missing),
                          'worst_ps': float(worst) if worst != 'INF' else None}
    for mode, count, worst in re.findall(r'^OT_INTERNAL_REG2REG (max|min) (\d+) (\S+)$', log, re.M):
        reg2reg[mode] = {'endpoints': int(count), 'worst_ps': float(worst) if worst != 'INF' else None}
    clocks = {n: float(v) for n, v in re.findall(r'^OT_INTERNAL_CLOCK (\S+) (\S+)$', log, re.M)}
    periods = log.split('OT_INTERNAL_MIN_PERIOD_BEGIN\n')[-1].split('OT_INTERNAL_MIN_PERIOD_END')[0]
    checks = log.split('OT_INTERNAL_PERIOD_CHECKS_BEGIN\n')[-1].split('OT_INTERNAL_PERIOD_CHECKS_END')[0]
    matches = re.findall(r'^OT_INTERNAL_STRUCTURAL_PAIRS (\d+)$', log, re.M)
    return {'structural_reg2reg_pairs': int(matches[0]) if len(matches) == 1 else None, 'coverage': coverage, 'reg2reg': reg2reg, 'clocks_ps': clocks,
            'minimum_period_report': periods, 'period_pulse_violations_report': checks,
            'done': 'OT_INTERNAL_DONE' in log}

def replay(view, out):
    abstract = json.loads((view / 'abstract.json').read_text())
    if out.exists():
        raise ValueError('Replay output must be a fresh directory; never overwrite evidence')
    out.mkdir(parents=True)
    rec = {'schema': SCHEMA, 'master': abstract['name'], 'view': str(view),
           'abstract_sha256': sha(view / 'abstract.json'), 'corners': {},
           'libs': {}, 'artifacts': abstract.get('verdict', {}).get('files', {}),
           'source_binding': 'same exported lib and exact retained routed sequence',
           'scope': 'leaf internals, not die or behavioural qualification', 'passed': False}
    spec = Path(abstract.get('interface_sdc', {}).get('path', '')).parent / 'spec.json'
    if spec.exists():
        spec_data = json.loads(spec.read_text())
        source_root = next(Path(arg[:-len(':/src:ro')]) for arg in abstract['corners']['ss']['command'] if arg.endswith(':/src:ro'))
        rec['routed_spec'] = {'sha256': sha(spec), 'top': spec_data['top'], 'params': spec_data.get('params', {}),
            'sources': {name: sha(source_root / name) for name in spec_data.get('sources', [])}}
    for corner in ('ss', 'ff'):
        lib = view / f"{abstract['name']}_{corner}.lib"
        rec['libs'][corner] = sha(lib)
        cdir = out / corner
        cdir.mkdir()
        original = (view / f'export_{corner}.tcl').read_text()
        # Only remove output/report commands after the precisely recorded loading
        # sequence. Never reconstruct SDC and never overwrite clocks/exceptions.
        prefix = original.split('puts "OT_WS')[0]
        if 'read_db ' not in prefix or 'read_spef ' not in prefix:
            raise ValueError('No retained database/parasitics export sequence')
        for item in rec['artifacts'].values():
            p = Path(item['host'])
            if not p.exists() or sha(p) != item['sha256']:
                raise ValueError(f'Retained routed artifact mismatch: {p}')
        (cdir / 'internal.tcl').write_text(prefix + AUDIT)
        cmd = list(abstract['corners'][corner]['command'])
        for i, arg in enumerate(cmd):
            if arg.endswith(':/out'):
                cmd[i] = str(cdir) + ':/out'
        cmd[-1] = '/out/internal.tcl'
        run = subprocess.run(cmd, capture_output=True, text=True)
        log = run.stdout + run.stderr
        (cdir / 'internal.log').write_text(log)
        result = parse(log)
        result.update(returncode=run.returncode, command=cmd,
                      script_sha256=sha(cdir / 'internal.tcl'), log_sha256=sha(cdir / 'internal.log'))
        if (cdir / 'replayed.sdc').exists():
            result['sdc_sha256'] = sha(cdir / 'replayed.sdc')
        rec['corners'][corner] = result
        write(out / 'receipt.json', rec)
    # Separate gate performs domain matching and minimum-period review. Execution
    # success alone is deliberately insufficient to turn this into a release PASS.
    write(out / 'receipt.json', rec)
    return rec

def gate(manifest, receipts):
    rows = []
    for leaf in manifest['masters']:
        if not leaf['required']:
            continue
        receipt = receipts.get(leaf['master'])
        reasons = []
        if receipt is None:
            reasons.append('missing source-bound internal receipt')
        else:
            if receipt.get('libs', {}).get('ss') == receipt.get('libs', {}).get('ff'):
                reasons.append('SS and FF corner libraries are aliased')
            for corner, mode in [('ss', 'max'), ('ff', 'min')]:
                if receipt.get('libs', {}).get(corner) != leaf['libs'].get(corner, {}).get('sha256'):
                    reasons.append(f'{corner}: bound liberty hash mismatch')
                r = receipt.get('corners', {}).get(corner, {})
                if r.get('returncode') != 0 or not r.get('done'):
                    reasons.append(f'{corner}: replay did not complete')
                cov = r.get('coverage', {}).get(mode, {})
                paths = r.get('reg2reg', {}).get(mode, {})
                if not cov.get('endpoints') or cov.get('unconstrained') != 0:
                    reasons.append(f'{corner}: endpoint coverage incomplete')
                if cov.get('worst_ps') is None or not math.isfinite(cov['worst_ps']) or cov['worst_ps'] < 0:
                    reasons.append(f'{corner}: constrained endpoint slack missing or negative')
                if r.get('structural_reg2reg_pairs') != 0 and (not paths.get('endpoints') or paths.get('worst_ps') is None or not math.isfinite(paths['worst_ps']) or paths['worst_ps'] < 0):
                    reasons.append(f'{corner}: internal {mode} missing or negative')
                expected = leaf.get('expected_clocks_ps')
                if not expected or set(expected) != set(r.get('clocks_ps', {})) or any(
                        not math.isclose(v, r['clocks_ps'].get(k, -1), abs_tol=0.01) for k, v in (expected or {}).items()):
                    reasons.append(f'{corner}: actual clock domains not matched')
                # A textual minimum-period report must be reviewed against the
                # actual clocks; zero/missing ETM min_period earns no credit.
                review = receipt.get('minimum_period_review', {}).get(corner, {})
                if review.get('log_sha256') != r.get('log_sha256') or review.get('passed') is not True or not review.get('basis'):
                    reasons.append(f'{corner}: minimum-period/pulse review missing')
            if receipt.get('original_constraints_verified') is not True or not receipt.get('constraints_review_basis'):
                reasons.append('original uncertainty/waveform/exceptions review missing')
            if receipt.get('source_params_verified') is not True or receipt.get('routed_spec') != leaf.get('routed_spec'):
                reasons.append('routed source/parameter binding review missing')
        rows.append({'master': leaf['master'], 'instances': leaf['instances'],
                     'passed': not reasons, 'reasons': reasons})
    return {'schema': SCHEMA, 'scope': 'bound CLOSED leaf internals only',
            'passed': bool(rows) and all(r['passed'] for r in rows),
            'die_release_complete': False, 'leaves': rows}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='action', required=True)
    p = sub.add_parser('census'); p.add_argument('kit', type=Path); p.add_argument('output', type=Path)
    p = sub.add_parser('replay'); p.add_argument('view', type=Path); p.add_argument('output', type=Path)
    p = sub.add_parser('gate'); p.add_argument('manifest', type=Path); p.add_argument('receipts', type=Path); p.add_argument('output', type=Path)
    a = ap.parse_args()
    if a.action == 'census': write(a.output, census(a.kit))
    elif a.action == 'replay': replay(a.view, a.output)
    else:
        result = gate(json.loads(a.manifest.read_text()), json.loads(a.receipts.read_text()))
        write(a.output, result)
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result['passed'] else 1)
if __name__ == '__main__': main()

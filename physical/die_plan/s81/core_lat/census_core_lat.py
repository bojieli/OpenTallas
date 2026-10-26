#!/usr/bin/env python3
"""S81-CORE-LAT census: every S81 hard-core type -> declared core latency / early-tap
offset (die_plan clock taps + cores/views freeze.json) and measured insertion TT/FF
(view lib max/min_clock_tree_path, signoff.json pin-flop insertion).  Repo-relative,
reads git objects at REV (default HEAD) so evidence names its commit.
usage: census_core_lat.py [--rev REV] [--plan physical/die_plan/s81/die_plan.json] OUT.json"""
import argparse, collections, json, re, subprocess, sys
ap = argparse.ArgumentParser(); ap.add_argument('--rev', default='HEAD')
ap.add_argument('--plan', default='physical/die_plan/s81/die_plan.json'); ap.add_argument('out')
a = ap.parse_args()
def show(p):
    r = subprocess.run(['git', 'show', f'{a.rev}:{p}'], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None
rev = subprocess.run(['git', 'rev-parse', '--short=10', a.rev], capture_output=True, text=True).stdout.strip()
files = subprocess.run(['git', 'ls-tree', '-r', '--name-only', a.rev], capture_output=True, text=True).stdout.split('\n')
d = json.loads(show(a.plan))
MEM = re.compile(r'^ot_(rom|sram)_\d+x\d+')
cnt = collections.Counter(p['type'] for p in d['partitions'])
def ctp(lib):
    t = show(lib) if lib else None
    if not t: return None
    out = {}
    for kind in ('max', 'min'):
        m = re.search(kind + r'_clock_tree_path;\s*cell_rise\(scalar\)\s*\{\s*values\("([\d.]+)"', t)
        if m: out[kind] = float(m.group(1))
    return out or None
info = {}
for tn, tv in d['partition_types'].items():
    taps = {tp['name'].rsplit('.clk', 1)[0]: tp for tp in tv['clock'].get('taps', []) if tp.get('kind') == 'core'}
    for h in tv.get('hard_cores', []):
        m = h['module']
        i = info.setdefault(m, {'module': m, 'replicas': 0, 'parent_types': [], 'outline_um': h['outline_um'],
                                'obs_max': h.get('obs_max'), 'plan_lib': h.get('lib'), 'early_taps': []})
        i['replicas'] += cnt[tn]; i['parent_types'].append(tn)
        tp = taps.get(h['inst']) or taps.get(h['inst'] + '.u_view')
        if tp: i['early_taps'].append({'type': tn, 'inst': h['inst'], 'insertion_ps': tp['insertion_ps'], 'note': tp.get('note')})
rows = []
for m, i in sorted(info.items(), key=lambda x: -x[1]['replicas']):
    i['memory_macro'] = bool(MEM.match(m))
    libs = [i['plan_lib']] if i['plan_lib'] else sorted(f for f in files if f.endswith(f'/{m}_tt.lib'))
    i['lib_tt'] = libs[0] if libs else None
    tt = ctp(i['lib_tt']); ff = ctp(i['lib_tt'].replace('_tt.lib', '_ff.lib')) if i['lib_tt'] else None
    i['lib_insertion_tt'] = tt; i['lib_insertion_ff'] = ff
    fz = show(f'physical/die_plan/s81/cores/views/{m}/freeze.json'); so = show(f'physical/die_plan/s81/cores/views/{m}/signoff.json')
    i['declared_target_ps'] = json.loads(fz).get('insertion_ps') if fz else None
    if so:
        s = json.loads(so)['corners']
        i['signoff_pinflop_mean'] = {c: s[c]['insertion_pinflops']['mean'] for c in ('tt', 'ff') if c in s}
        i['signoff_all_minmax'] = {c: [s[c]['insertion_all']['min'], s[c]['insertion_all']['max']] for c in ('tt', 'ff') if c in s}
    i['parent_types'] = sorted(set(i['parent_types']))
    rows.append(i)
json.dump({'schema': 'opentallas.s81.core_lat_census.v1', 'rev': rev, 'plan': a.plan,
           'die_clock': {k: d['clock'][k] for k in ('insertion_ps', 'common_latency_ps', 'insertion_tol_ps')},
           'cores': rows}, open(a.out, 'w'), indent=1)
for i in rows:
    e = sorted({round(t['insertion_ps'], 1) for t in i['early_taps']})
    print(f"{i['module']:30s} rep={i['replicas']:5d} mem={int(i['memory_macro'])} early={e} lib_tt={i['lib_insertion_tt']} lib_ff={i['lib_insertion_ff']} decl={i['declared_target_ps']} so={i.get('signoff_pinflop_mean')}")

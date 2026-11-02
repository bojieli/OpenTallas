#!/usr/bin/env python3
"""R7 v2 named added-FF clock/reset/coordinate census (read-only, light).
Inputs (read-only): R7 bind_R7_v2/rtl, baseline codex-kv-wave-1131/bind/rtl, r7_geometry_proposal_v2.json,
actual_crossings.json, clock_clusters.json.  Writes only into --out dir."""
import json, re, sys, collections, hashlib, argparse
from pathlib import Path
ap = argparse.ArgumentParser()
ap.add_argument('--r7', default='/srv/opentallas-scratch2/claude/codex-kv-ei-startprep-1131')
ap.add_argument('--base', default='/srv/opentallas-scratch2/claude/codex-kv-wave-1131/bind/rtl')
ap.add_argument('--out', required=True)
a = ap.parse_args()
R7 = Path(a.r7); BASE = Path(a.base); OUT = Path(a.out)
KW = {'module', 'input', 'output', 'inout', 'wire', 'reg', 'assign', 'always', 'if', 'else', 'begin', 'end', 'localparam', 'parameter'}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def instances(path):
    t = Path(path).read_text()
    t = re.sub(r'/\*.*?\*/', ' ', t, flags=re.S)
    t = re.sub(r'//[^\n]*', ' ', t)
    t = re.sub(r'\(\*.*?\*\)', ' ', t, flags=re.S)  # strip generated (* keep *) attributes (Codex gotcha)
    out = {}
    for m in re.finditer(r'(?m)^\s*(\w+)\s+(?:#\s*\((?:[^()]|\([^()]*\))*\)\s*)?(\w+)\s*\(((?:[^;])*?)\)\s*;', t):
        mod, inst, body = m.group(1), m.group(2), m.group(3)
        if mod in KW: continue
        pins = {p: n.strip() for p, n in re.findall(r'\.(\w+)\s*\(\s*([^()]*?)\s*\)', body)}
        if not pins: continue
        assert inst not in out, ('duplicate instance', inst)
        out[inst] = (mod, pins)
    return out

r7f = R7 / 'bind_R7_v2/rtl/kv3_hub_Ei_part.sv'; bf = BASE / 'kv3_hub_Ei_part.sv'
I7 = instances(r7f); IB = instances(bf)
geo = json.loads((R7 / 'r7_geometry_proposal_v2.json').read_text())
rows = json.loads((R7 / 'actual_crossings.json').read_text())['rows']
cc = json.loads((R7 / 'clock_clusters.json').read_text())
cp = geo['clock_patch']
raw = {b['name']: b for b in cp['landing_raw_branches']}
rd = cp['landing_reader_start']['branches']; wr = cp['landing_writer_start']['branches']
links_in = collections.defaultdict(list); links_out = collections.defaultdict(list)
for r in rows:
    if r['dst'] == 'hub_Ei': links_in[r['dst_bus']].append(r['port'])
    if r['src'] == 'hub_Ei': links_out[r['src_bus']].append(r['port'])
# top-level clock net feeding part port clk
top = (R7 / 'bind_R7_v2/rtl/qwen_kvsys_bound_top.sv').read_text()
m = re.search(r'kv3_hub_Ei_part\s+hub_Ei\s*\((.*?)\);', top, re.S)
top_clk = re.search(r'\.clk\(\s*(\w+)\s*\)', m.group(1)).group(1)

added = sorted(set(I7) - set(IB)); removed = sorted(set(IB) - set(I7))
recs = []; gaps = []
for inst in added:
    mod, pins = I7[inst]
    rec = dict(hier='qwen_kvsys_bound_top/hub_Ei/' + inst, inst=inst, kind=mod, ff='q',
               clk_net=pins.get('clk'), clk_domain=None, reset_net=None, d_net=pins.get('d'), q_net=pins.get('q'),
               role=None, branch=None, stage=None, xy_um=None, links=[])
    rec['clk_domain'] = f"hub_Ei.clk <- top {top_clk}" if pins.get('clk') == 'clk' else 'NOT_LITERAL_CLK'
    if mod == 'ot_dp_landing_relay':
        rec['reset_net'] = pins.get('rst_raw_n')
        for role, br, links in (('reader_start', rd, links_in), ('writer_start', wr, links_out)):
            pre = 'u_cland_' + role + '_'
            if inst.startswith(pre):
                rest = inst[len(pre):]; bus, _, i = rest.rpartition('_')
                if bus in br:
                    rec.update(role=role, branch=bus, stage=int(i), links=links.get(bus, []))
                    st = br[bus]['stages']
                    if int(i) < len(st):
                        rec['xy_um'] = st[int(i)]['xy_um']; rec['planned_raw_reset'] = st[int(i)]['raw_reset']
    elif mod == 'ot_dp_rrelay':
        rec['reset_net'] = 'none (no reset pin; D carries raw reset transport)'
        pre = 'u_cland_raw_'
        if inst.startswith(pre):
            rest = inst[len(pre):]; name, _, j = rest.rpartition('_')
            if name in raw:
                b = raw[name]; j = int(j)
                rec.update(role='raw_copy', branch=name, stage=j, consumers=b['consumers'])
                if j < len(b['stages']):
                    rec['xy_um'] = b['stages'][j]['xy_um']; rec['original_relay'] = b['stages'][j]['original']
                c = b['consumers'][0]; mode, _, rest2 = c.partition(':')
                bus = rest2.rsplit(':', 1)[0] if mode in ('reader', 'writer') else rest2
                rec['links'] = (links_in if mode == 'reader' else links_out).get(bus, []) if mode in ('reader', 'writer', 'fstart') else []
    if rec['xy_um'] is None: gaps.append(inst)
    recs.append(rec)

# unchanged-source clock connectivity: every baseline instance kept, same module, same clock-type pins
clkpin = lambda p, n: p == 'clk' or 'clk' in p or 'fclk' in n or n.startswith('clk')
changed_clock = []; changed_other = collections.Counter(); changed_examples = []
for inst, (mod, pins) in IB.items():
    if inst not in I7: continue
    mod7, pins7 = I7[inst]
    if mod7 != mod: changed_clock.append((inst, 'module', mod, mod7)); continue
    for p in set(pins) | set(pins7):
        if pins.get(p) != pins7.get(p):
            if clkpin(p, pins.get(p, '') or '') or clkpin(p, pins7.get(p, '') or ''):
                changed_clock.append((inst, p, pins.get(p), pins7.get(p)))
            else:
                changed_other[(mod, p)] += 1
                if len(changed_examples) < 12: changed_examples.append((inst, p, pins.get(p), pins7.get(p)))
fclk_conn = lambda I: sorted((i, p, n) for i, (m_, ps) in I.items() for p, n in ps.items() if 'fclk' in n or 'fclk' in p)
fb = fclk_conn(IB); f7 = fclk_conn(I7)
added_fclk = [x for x in f7 if x[0] in set(added)]
# port-level assigns for fclk outputs unchanged?
def fclk_assigns(path):
    t = Path(path).read_text(); return sorted(l.strip() for l in t.splitlines() if 'fclk' in l and ('assign' in l or 'input' in l or 'output' in l))
fa_same = fclk_assigns(bf) == fclk_assigns(r7f)
kinds = collections.Counter(r['kind'] for r in recs)
roles = collections.Counter((r['kind'], r['role']) for r in recs)
perlink = collections.Counter(l for r in recs for l in r['links'])
nolink = [r['inst'] for r in recs if not r['links']]
literal = sum(1 for r in recs if r['clk_net'] == 'clk')
rawbr = collections.Counter(r['branch'] for r in recs if r['role'] == 'raw_copy')
base_ff = cc['total_grid_ff']; total = base_ff + len(recs)
summary = dict(
    status='READ_ONLY_CENSUS_SOURCE_LEVEL', generated_by='CODEX-PICKUP-KV/A (Claude)',
    inputs={str(r7f): sha(r7f), str(bf): sha(bf), str(R7 / 'r7_geometry_proposal_v2.json'): sha(R7 / 'r7_geometry_proposal_v2.json'),
            str(R7 / 'actual_crossings.json'): sha(R7 / 'actual_crossings.json'), str(R7 / 'clock_clusters.json'): sha(R7 / 'clock_clusters.json')},
    added_ff_total=len(recs), removed_baseline_instances=removed,
    per_kind=dict(kinds), per_kind_role={f'{k}/{r}': v for (k, r), v in roles.items()},
    clock={'literal_clk': literal, 'non_literal': len(recs) - literal, 'part_clk_from_top_net': top_clk,
           'domains': dict(collections.Counter(r['clk_domain'] for r in recs)),
           'added_forwarded_fclk_consumers': len(added_fclk)},
    reset_nets_landing=dict(collections.Counter(r['reset_net'] for r in recs if r['kind'] == 'ot_dp_landing_relay').most_common(5)),
    reset_landing_distinct=len({r['reset_net'] for r in recs if r['kind'] == 'ot_dp_landing_relay'}),
    raw_branches=len(rawbr), raw_branch_stage_counts=dict(collections.Counter(rawbr.values())),
    coordinates={'with_xy': len(recs) - len(gaps), 'gaps': len(gaps), 'gap_instances': gaps[:200]},
    per_link_ff=dict(sorted(perlink.items())), links_covered=len(perlink), ff_without_link=len(nolink), ff_without_link_examples=nolink[:20],
    unchanged_source_check={
        'baseline_instances': len(IB), 'r7_instances': len(I7), 'baseline_instances_kept': len(set(IB) & set(I7)),
        'baseline_clock_pin_changes': len(changed_clock), 'baseline_clock_pin_change_list': changed_clock[:50],
        'baseline_nonclock_pin_changes_by_module_pin': {f'{k[0]}.{k[1]}': v for k, v in changed_other.items()},
        'nonclock_change_examples': changed_examples,
        'fclk_connections_baseline': len(fb), 'fclk_connections_r7': len(f7), 'fclk_connections_identical': fb == f7,
        'fclk_port_decl_assign_lines_identical': fa_same,
        'baseline_forwarded_ff': cc['forwarded_ff_count'], 'baseline_forwarded_domains': len(cc['forwarded_domains_preserved']),
        'baseline_forwarded_source': 'clock_clusters.json (baseline mapped dump sha %s); not remeasured' % cc['source_dump_sha256'][:12],
        'other_files_differ_only': 'qwen_kvsys_bound_top.sv strap_ca_k_* values + kv3_hub_Ei_part.sv (checked by cmp)'},
    leaf_groups={'baseline_clk_ff': base_ff, 'source_delta_total_estimate': total, 'min_1500ff_leaf_groups': -(-total // 1500),
                 'note': 'source-delta estimate, not remeasured mapped count; requirement only, not CTS'},
)
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'R7_v2_named_clock_census.json').write_text(json.dumps({'summary': summary, 'ff': recs}, indent=0) + '\n')
(OUT / 'R7_v2_named_clock_census_SUMMARY.json').write_text(json.dumps(summary, indent=1) + '\n')
cols = ['hier', 'kind', 'clk_net', 'clk_domain', 'reset_net', 'role', 'branch', 'stage', 'x_um', 'y_um', 'links', 'd_net', 'q_net']
with open(OUT / 'R7_v2_named_clock_census.tsv', 'w') as f:
    f.write('\t'.join(cols) + '\n')
    for r in recs:
        xy = r['xy_um'] or ['GAP', 'GAP']
        f.write('\t'.join(str(v) for v in [r['hier'], r['kind'], r['clk_net'], r['clk_domain'], r['reset_net'], r['role'], r['branch'], r['stage'], xy[0], xy[1], ','.join(r['links']) or '-', r['d_net'], r['q_net']]) + '\n')
print(json.dumps({k: v for k, v in summary.items() if k not in ('per_link_ff', 'inputs')}, indent=1)[:6000])

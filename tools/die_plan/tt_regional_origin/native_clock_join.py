#!/usr/bin/env python3
"""Join TT regional-event homes to native clock terminals, without mutating a tree.

Inventory is exported from the *new* mapped source. Each exact model name must
identify one native ITerm and its complete clock path. This adapter emits review
metadata only: a separate guarded preCTS consumer must preserve that path.
"""
import argparse
import gzip
import json
import re
from pathlib import Path


def read(path):
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path, 'rt') as f:
        return json.load(f)



def source_expectation(name):
    """Finite generated-source identity map; never a guessed general RTL alias."""
    prefix='u_bound.u_cland_origin/'
    if name==prefix+'sf$_DFF_N_':
        return 'u_bound.u_cland_origin.g_on.sf','negedge','retained_namespace_only'
    if name==prefix+'s0$_SDFF_PN0_':
        return 'u_bound.u_cland_origin.g_on.s0','posedge','retained_namespace_only'
    match=re.fullmatch(re.escape(prefix)+r'g_on\.g_region\[([0-3])\]\.(s1|s2|pd)',name)
    if match:
        return 'u_bound.u_cland_origin.g_on.g_region['+match[1]+'].'+match[2],'posedge','regional_state'
    match=re.fullmatch(r'u_bound\.g_tt_raw_regions\.g_region\[([0-3])\]\.u_raw_copy/q',name)
    if match:
        return 'u_bound.g_tt_raw_regions.g_region['+match[1]+'].u_raw_copy.q','posedge','raw_same_depth_copy'
    return None


def join(proposal, inventory):
    if inventory.get('source_event') != 'tt_regional_origin_13ff':
        raise ValueError('Requires the newly generated regional source event, not the old checkpoint')
    if inventory.get('stage') != 'mapped_preCTS':
        raise ValueError('Requires mapped preCTS inventory; closed-leaf/CTS-open hooks are not this adapter')
    if not inventory.get('source_sha256') or not inventory.get('netlist_sha256'):
        raise ValueError('Missing actual source/netlist identity')
    ports = proposal['clock_ports']
    taps = inventory['ports']
    if len(ports) != 63 or set(taps) != set(ports):
        raise ValueError('Exactly the existing 63 clock input names must join')
    expected_xy=proposal.get('clock_port_xy_um')
    if not expected_xy or set(expected_xy)!=set(ports):
        raise ValueError('Missing exact existing 63 clock-entry coordinates')
    for name, p in taps.items():
        if len(p.get('xy_um',[]))!=2 or any(abs(a-b)>1e-6 for a,b in zip(p['xy_um'],expected_xy[name])):
            raise ValueError('Actual native clock-entry coordinate differs: '+name)
        if (p.get('cohort'), p.get('period_ps'), p.get('phase_ps'), p.get('polarity')) != ('clk', 833, 0, 1):
            raise ValueError('Clock cohort/period/phase/polarity mismatch: ' + name)
    records = inventory['sinks']
    by_name = {}
    native_seen = set()
    for r in records:
        name = r['model_name']
        if name in by_name or r['native_iterm'] in native_seen:
            raise ValueError('Duplicate native/model clock endpoint: ' + name)
        by_name[name] = r
        native_seen.add(r['native_iterm'])
    required = proposal['assignments'] + proposal['retained_other_cohorts']
    if set(by_name) != {r['name'] for r in required}:
        missing = {r['name'] for r in required} - set(by_name)
        extra = set(by_name) - {r['name'] for r in required}
        raise ValueError(f'Exact endpoint join failed: missing={len(missing)} extra={len(extra)}')
    ff_names={r['model_name']:r['native_name'] for r in inventory.get('ff_cells',[])}
    for a in required:
        r=by_name[a['name']]
        if '::' in a['name']:
            instance,pin=a['name'].split('::',1)
            if r['native_iterm']!=instance+'/'+pin:raise ValueError('Actual macro clock instance/pin identity differs: '+a['name'])
        elif ff_names and (a['name'] not in ff_names or r['native_iterm'].rsplit('/',1)[0]!=ff_names[a['name']]):
            raise ValueError('Clock ITerm does not belong to the joined native FF: '+a['name'])
    output = []
    for a in proposal['assignments']:
        r = by_name[a['name']]
        if '::' in a['name'] and (len(r.get('xy_um',[]))!=2 or any(abs(x-y)>1e-6 for x,y in zip(r['xy_um'],a['xy']))):
            raise ValueError('Actual macro clock ITerm geometry differs: '+a['name'])
        if r.get('cohort') != 'clk' or r['root_port'] not in taps:
            raise ValueError('Cross-root clock reassignment: ' + a['name'])
        if r.get('edge') not in ('posedge', 'negedge'):
            raise ValueError('Missing actual native clock edge: ' + a['name'])
        if not isinstance(r.get('path'), list):
            raise ValueError('Missing audited gate/inverter/buffer path: ' + a['name'])
        for cell in r['path']:
            if not all(cell.get(k) for k in ('instance', 'master', 'input_pin', 'output_pin', 'kind')):
                raise ValueError('Incomplete path member: ' + a['name'])
            if cell['kind'] not in ('buffer', 'inverter', 'clock_gate'):
                raise ValueError('Unclassified clock logic: ' + a['name'])
            if cell.get('polarity') not in (-1,1):
                raise ValueError('Missing actual clock-path pin polarity: ' + a['name'])
            if cell['kind'] in ('buffer','inverter') and cell['polarity'] != (1 if cell['kind']=='buffer' else -1):
                raise ValueError('Clock-path kind/polarity mismatch: ' + a['name'])
        expected=source_expectation(a['name'])
        if expected:
            signal,rtl_edge,kind=expected
            if r.get('rtl_signal')!=signal or r.get('rtl_edge')!=rtl_edge:
                raise ValueError('Exact regional source signal/edge join failed: '+a['name'])
            inversions=sum(c['polarity']==-1 for c in r['path'])
            native_negative=r['edge']=='negedge'
            if (native_negative ^ bool(inversions%2)) != (rtl_edge=='negedge'):
                raise ValueError('Regional clock inversion/edge path mismatch: '+a['name'])
        output.append(dict(model_name=a['name'], native_iterm=r['native_iterm'],
                           old_root_port=r['root_port'], target_root_port=a['parent_tap'],
                           edge=r['edge'], preserve_path=r['path'],
                           source_identity=expected,
                           capacity_override='nearest_parent_tap' in a))
    for a in proposal['retained_other_cohorts']:
        if by_name[a['name']]['root_port'] != a['logical_root']:
            raise ValueError('Other clock cohort changed: ' + a['name'])
    if sum(r['capacity_override'] for r in output) != proposal['reassociated_sinks']:
        raise ValueError('Explicit capacity overrides differ from this exact reviewed cohort')
    branches={}
    for row in output:
        for cell in row['preserve_path']:
            key=(cell['instance'],cell['input_pin'])
            branch=branches.setdefault(key,dict(instance=cell['instance'],input_pin=cell['input_pin'],master=cell['master'],kind=cell['kind'],targets=set(),sinks=0))
            if (branch['master'],branch['kind'])!=(cell['master'],cell['kind']):raise ValueError('Inconsistent actual shared clock-path identity')
            branch['targets'].add(row['target_root_port']);branch['sinks']+=1
    splits=[dict(**{k:v for k,v in b.items() if k!='targets'},target_root_ports=sorted(b['targets'])) for b in branches.values() if len(b['targets'])>1]
    gate_conflicts=[b for b in splits if b['kind']=='clock_gate']
    return dict(schema='opentallas.tt_native_clock_join.v1', status='HELD_SHARED_CLOCK_GATE_BRANCH' if gate_conflicts else 'JOINED_METADATA_ONLY',
                shared_stateless_branch_splits_required=[b for b in splits if b['kind']!='clock_gate'],
                gated_branch_conflicts=gate_conflicts,
                tree_applied=False, physical_release='HELD',
                source_sha256=inventory['source_sha256'], netlist_sha256=inventory['netlist_sha256'],
                clock_ports=ports,clock_port_xy_um=expected_xy,period_ps=833,assignments=output,
                retained_other_cohorts=proposal['retained_other_cohorts'],
                consumer_contract='Preserve each exact edge and full path; a shared gate branch with conflicting target roots requires a separate coherent branch-cut proposal. Never reconnect a gated/inverted sink directly to a port.')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--proposal', type=Path, required=True)
    ap.add_argument('--inventory', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    result = join(read(a.proposal), read(a.inventory))
    a.out.write_text(json.dumps(result, separators=(',', ':')) + '\n')
    print('TT_NATIVE_CLOCK_JOIN', result['status'], len(result['assignments']))

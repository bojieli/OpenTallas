#!/usr/bin/env python3
"""Trace native quarter-scorer key lines against a proposed physical plan.

This emits real source endpoints and physical scorer coordinates. It refuses to
substitute query ports for key lines, infer client count from hub count, or label
an unmapped replay buffer as bound. No plan is modified.
"""
import argparse, gzip, json, re
from collections import Counter
from pathlib import Path


def trace(native_top, plan, split_manifest):
    text = gzip.decompress(native_top.read_bytes()).decode() if native_top.suffix == '.gz' else native_top.read_text()
    scorers = []
    for line in text.splitlines():
        match = re.search(r'\b(ot_hbm_idx_score_quarter_static)\b.*?\b([\w]+)\s*\($', line)
        if not match:
            continue
        inst = match[2]
        begin = text.index(line)
        body = text[begin:text.index('\n  );', begin)]
        ports = dict(re.findall(r'\.(\w+)\(([^\n]*)\)', body))
        if not {'key_lines', 'half', 'first_ord'} <= ports.keys():
            raise ValueError('native scorer lacks required key/ordinal ports: '+inst)
        scorers.append(dict(instance=inst, module=match[1], half=ports['half'],
                            first_ord=ports['first_ord'], key_input=ports['key_lines'],
                            beat_v=ports['beat_v'], beat_index=ports['beat_index'],
                            key_bits=4396, keybuf_slices=4))
    if not scorers:
        raise ValueError('no native quarter scorers found; supply the actual composed native top')
    d = json.loads((plan/'die_plan.json').read_text())
    types = d['partition_types']
    leaves = []
    buffers = []
    for part in d['partitions']:
        t = types[part['type']]
        for core in t.get('hard_cores', []):
            if 'idx_score_hcol' in core['module']:
                leaves.append(dict(partition=part['name'], type=part['type'],
                                   instance=core['inst'], module=core['module'],
                                   partition_origin_um=part['origin_um'], partition_orient=part.get('orient','R0'),
                                   core_origin_um=core['origin_um'], outline_um=core['outline_um']))
            if core['module'] == 'ot_hnx_idxn_keybuf_slice':
                buffers.append(dict(partition=part['name'],instance=core['inst'],core_origin_um=core['origin_um']))
    proxy = []
    for tn,t in types.items():
        for station in t.get('internal_stations',[]):
            if 'keybuf' in str(station) and any(p in str(station) for p in ['__q_Q.kin','__q_Q.kout']):
                proxy.append(dict(type=tn,conn=station.get('conn'),launch=station.get('launch'),capture=station.get('capture')))
    # One canonical quarter consists of two engine rows, four chunks, four key
    # lanes and two head-column halves. A whole-client multiplicity is read from
    # the native top, independently of hub service replicas.
    split = json.loads(split_manifest.read_text())
    hcols_per_quarter = sum("ot_hidx_score_hcol" in c["module"] for c in split["cores"])
    if not hcols_per_quarter:raise ValueError("native split manifest has no hcol cores")
    expected_hcols = len(scorers)*hcols_per_quarter
    issues=[]
    if len(leaves) != expected_hcols:
        issues.append(dict(kind='SCORER_CARDINALITY',native_quarters=len(scorers),
                           required_hcol_instances=expected_hcols,plan_hcol_instances=len(leaves)))
    if proxy:
        issues.append(dict(kind='QUERY_PROXY_KEY_PORTS',count=len(proxy),
                           reason='ot_hbm_idx_query_static has no kin/kout; replay buffers feed scorer key_lines'))
    return dict(schema='opentallas.hbm.keybuf_native_contract.v1',status='UNBOUND' if issues else 'MAPPING_REQUIRED',
                native_scorers=scorers,hcols_per_native_quarter=hcols_per_quarter,
                required_slices_for_supplied_native_top=4*len(scorers),
                physical_slices=len(buffers),physical_scorer_hcols=len(leaves),
                hcols_per_partition=dict(Counter(c['partition'] for c in leaves)),
                physical_scorer_endpoints=leaves,physical_keybufs=buffers,query_proxies=proxy,issues=issues,
                note='Counts qualify the supplied native top only; no inference from hub count and no whole-die binding claim.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native-top',type=Path,required=True)
    p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--split-manifest',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();d=trace(a.native_top,a.plan,a.split_manifest)
    a.out.write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps({k:d[k] for k in ['status','required_slices_for_supplied_native_top','physical_slices','physical_scorer_hcols','hcols_per_partition','issues']},indent=2))
    return 1 if d['issues'] else 0

if __name__=='__main__':raise SystemExit(main())

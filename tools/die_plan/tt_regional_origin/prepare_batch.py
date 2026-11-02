#!/usr/bin/env python3
"""Prepare a disabled paired TT_C event; no live config, source or checkpoint changes."""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_gzip(path, obj):
    with gzip.GzipFile(filename=str(path), mode='wb', mtime=0) as f:
        f.write((json.dumps(obj, separators=(',', ':'))+'\n').encode())


def build(plan_path, sidecar_path, final, event_path, out):
    plan = json.loads(plan_path.read_text())
    sidecar = json.loads(sidecar_path.read_text())
    event = json.loads(event_path.read_text())
    original = copy.deepcopy(plan)
    typ = plan['partition_types']['tt_ctlm']
    if typ['outline_um'] != [777.6, 518.4] or typ['clock'].get('tap_mode') != 'density':
        raise ValueError('Requires the exact selected TT_C density source')
    if event['padw'] != 1 or event['price']['added_state_ff'] != 13 or event['enabled']:
        raise ValueError('Unexpected source mechanism or enabled candidate')
    changed = []
    for delta in json.loads((final/'macro_delta3_DISABLED.json').read_text()):
        name = delta['name'].replace('\\', '')
        matches = [m for m in typ['hard_cores'] if m['inst'] == name]
        if len(matches) != 1:
            raise ValueError('Missing exact selected macro: '+name)
        macro = matches[0]
        if macro['orient'] != 'R0' or macro['origin_um'][0] != delta['old_rect'][0]:
            raise ValueError('Stale macro source origin: '+name)
        old = list(macro['origin_um'])
        macro['origin_um'] = [round(old[0]+delta['dx'], 6), old[1]]
        changed.append(dict(instance=name, old=old, new=macro['origin_um']))
    # No schema extension is smuggled into the normal plan/sidecar. The local
    # source-model extension is separate until its guarded generator is joined.
    out.mkdir(parents=True, exist_ok=True)
    write_gzip(out/'plan_DISABLED.json.gz', plan)
    write_gzip(out/'sidecar_BASELINE_NOT_REDERIVED.json.gz', sidecar)
    origins = json.loads((final/'final_source_homes_DISABLED.json').read_text())
    raw = json.loads((final/'final_raw_homes_DISABLED.json').read_text())
    model = dict(schema='opentallas.tt_regional_paired_model.v1', enabled=False,
                 type='tt_ctlm', parent_source='rst_rl_85', retained_central_raw='rst_n_t0',
                 raw_depth=3, origin_padw=1, retain_sampling=['sf', 's0'],
                 qualified_regions=[dict(region=i, raw_leaf=next(r for r in raw if r['region']==i),
                                        states=[r for r in origins if r['region']==i],
                                        receivers=[n for n,v in event['receiver_regions'].items() if v==i]) for i in range(4)],
                 price=event['price'], source_files=event['source_files'],
                 clock_association='../composed_final/final_clock_association_DISABLED.json.gz',
                 physical_release='HELD', standard_global_derivation=False)
    (out/'regional_model_DISABLED.json').write_text(json.dumps(model, indent=1)+'\n')
    receipt=dict(schema='opentallas.tt_paired_batch_prep.v1', enabled=False,
                 selected_plan_sha256=digest(plan_path), selected_sidecar_sha256=digest(sidecar_path),
                 plan_delta=changed, clock_configuration_unchanged=original['partition_types']['tt_ctlm']['clock']==typ['clock'],
                 global_sidecar='BASELINE ONLY: not a new ClockLandings/global-reset receipt',
                 source_event=event['candidate_sha256'], native_clock_join_applied=False,
                 required_join_terms=[
                     'Optional source emitter must consume this same regional_model and preserve default OFF.',
                     'ClockLandings.manifest reset_placements.tt_ctlm.count_origin must model four same-edge s1/s2/pd regions, 37 exact receiver associations and four depth3 raw leaves, while retaining SF/S0 and central raw leaf.',
                     'Reset-tree/global count alignment must rederive on the composed current parent plan with the exact frozen 63 tap names/coordinates; no cached sidecar promotion.',
                     'All 2978 old FF homes and 16 replacement/new homes require native-name/row legalization; no old checkpoint adoption.',
                     'Map every new mapped clock ITerm to the existing same-phase root and preserve edge/gate/inverter path via native_clock_join.py; expose all 51 capacity overrides.',
                     'G0C differential0new, strictbind0, count/KEEP/ABI join, actual LOOK and existing parent/physical/corner holds remain required.'
                 ],next_stage='Source GEN and paired model derivation only after coherent adapter join; no CAD/full LEC.')
    (out/'batch_gate.json').write_text(json.dumps(receipt,indent=1)+'\n')
    return receipt


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','sidecar','final','event','out'):
        ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args()
    r=build(a.plan,a.sidecar,a.final,a.event,a.out)
    print('TT_PAIRED_BATCH_DISABLED',len(r['plan_delta']),'macro changes; source/model joins remain HELD')

#!/usr/bin/env python3
"""Join the exact selected generated TT_C source to its regional model, default OFF.

This standalone PREP adapter deliberately has no live Binder/ClockLandings hook.
It emits source and reset/origin records from one model; global derive/admission
still requires root-reviewed optional consumers of those records.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
try:
    from .prepare_event import build
except ImportError:
    from prepare_event import build
try:
    from .native_clock_join import source_expectation
except ImportError:
    from native_clock_join import source_expectation


def validate(wrapper, model):
    text=wrapper.read_text()
    if model.get('enabled') or model.get('type')!='tt_ctlm':
        raise ValueError('Only the disabled TT_C source-event model is supported')
    if (model.get('parent_source'),model.get('retained_central_raw'),model.get('raw_depth'),model.get('origin_padw'))!=('rst_rl_85','rst_n_t0',3,1):
        raise ValueError('Actual selected PADW/raw-parent/depth contract changed')
    for inst,d,q in [('84','rst_root_n','rst_rl_84'),('85','rst_rl_84','rst_rl_85'),('87','rst_rl_85','rst_n_t0')]:
        pattern=rf'ot_dp_rrelay\s+u_rrl_{inst}\s*\(\s*\.clk\(clk\),\s*\.d\({d}\),\s*\.q\({q}\)\s*\);'
        if len(re.findall(pattern,text))!=1:
            raise ValueError('Selected raw reset equation/depth drifted at u_rrl_'+inst)
    regions=model['qualified_regions']
    if [r['region'] for r in regions]!=[0,1,2,3]:
        raise ValueError('Requires four ordered nonempty regional groups')
    mapping={};homes=[];raw=[];slots=set()
    for region in regions:
        ri=region['region']
        if {s['stage'] for s in region['states']}!={'s1','s2','pd'} or len(region['states'])!=3:
            raise ValueError('Each region must model exactly s1/s2/pd')
        if not region['receivers']:raise ValueError('Empty region')
        for name in region['receivers']:
            if name in mapping:raise ValueError('Repeated receiver '+name)
            mapping[name]=ri
        for slot in region['states']+[region['raw_leaf']]:
            if slot['region']!=ri or len(slot['xy'])!=2:
                raise ValueError('Region/source slot mismatch')
            point=tuple(slot['xy'])
            if point in slots:raise ValueError('Aliased new state homes')
            slots.add(point)
        homes.extend(region['states']);raw.append(region['raw_leaf'])
    if len(mapping)!=37 or len(slots)!=16:raise ValueError('Requires all 37 receivers and 16 distinct state slots')
    if model['price']['added_state_ff']!=13 or model['price']['added_mission_cycles'] or model['price']['added_boot_cycles']:
        raise ValueError('Source-event price changed')
    return mapping,homes,raw


def prepare(wrapper,outer,model_path,out):
    model=json.loads(model_path.read_text())
    mapping,homes,raw=validate(wrapper,model)
    event=build(wrapper,mapping,homes,out,outer,raw)
    # All regional source signals are qualified against the same old raw path;
    # these replace the singular old S1/S2/PD model, not SF/S0 or central raw.
    record=dict(kind='regional_strap_source_PREP',enabled=False,physical_qualified=False,
                padw=1,raw_reset='rst_n_t0',raw_parent='rst_rl_85',raw_depth=3,
                retained_sampling=['u_cland_origin.sf','u_cland_origin.s0'],
                retained_central_leaf='u_rrl_87',old_replaced_states=['s1','s2','pd'],
                regions=model['qualified_regions'],same_edge=True,price=model['price'],
                clock='clk',source_sha256=event['candidate_sha256'],
                global_derive_complete=False,
                consumer_requirements=['count_origin regional consumer','land_slots and native placement paths','source verifier and KEEP/count ABI','global reset producer and 63clock name/phase join'])
    aliases=[]
    old_prefix='u_bound.u_cland_origin/'
    names=[old_prefix+'sf$_DFF_N_',old_prefix+'s0$_SDFF_PN0_']
    names += [old_prefix+f'g_on.g_region[{i}].{stage}' for i in range(4) for stage in ('s1','s2','pd')]
    names += [f'u_bound.g_tt_raw_regions.g_region[{i}].u_raw_copy/q' for i in range(4)]
    for name in names:
        signal,edge,kind=source_expectation(name)
        aliases.append(dict(model_name=name,rtl_signal=signal,rtl_edge=edge,join_kind=kind,
                            native_iterm='REQUIRES_ACTUAL_NEW_MAPPED_SOURCE',proof_cut_alias=False))
    record['source_name_joins']=aliases
    (out/'source_name_joins_PREP.json').write_text(json.dumps(aliases,indent=1)+'\n')
    (out/'count_origin_regional_PREP.json').write_text(json.dumps(record,indent=1)+'\n')
    return record


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('wrapper','outer','model','out'):ap.add_argument('--'+k,type=Path,required=True)
    a=ap.parse_args();r=prepare(a.wrapper,a.outer,a.model,a.out)
    print('TT_SOURCE_MODEL_JOIN_DISABLED',len(r['regions']),'regions; local source/model joined, global adapters HELD')

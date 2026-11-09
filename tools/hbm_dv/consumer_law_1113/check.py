#!/usr/bin/env python3
"""Gate private SFU absolute return parameters against actual regen records."""
import argparse
import copy
import json
from pathlib import Path


def check(regen,landing):
    if landing['errors'] or landing['contract'] != regen['record']['contract']:
        raise ValueError('landing/parameter contract differs')
    variants=regen['record']['variant_values']; rows=[]
    for side in ('NW','NE'):
        name='sfucore_'+side+'.__cut_ctl'
        family=next(x for x in landing['loops'] if x['family']=='SFU_VM_'+side)
        pairs=set()
        for loop in family['loops']:
            lg=loop['name']; v=variants[name+':'+lg]
            legs=loop['legs']
            if sum(legs.values()) != loop['rt_added']:
                raise ValueError('actual external loop total differs')
            ctl=sum(value for key,value in legs.items() if key.startswith('C_'))
            if v['ctl_legs']!=ctl:
                raise ValueError('consumer control legs differ')
            pair=(v['sfu_tap_read_return']+ctl,v['sfu_tap_write_return']+ctl)
            pairs.add(pair)
            rows.append(dict(consumer=name,variant=lg,external_read=pair[0],external_write=pair[1],
                native_read=2,native_write=2,absolute_read=pair[0]+2,absolute_write=pair[1]+2))
        if len(pairs)!=1:
            raise ValueError('LG variants do not share actual external return')
        external=next(iter(pairs)); expected=(external[0]+2,external[1]+2)
        chosen=variants[name]
        if (chosen['READ_RETURN'],chosen['WRITE_RETURN'])!=expected:
            raise ValueError('stale absolute SFU bridge parameters')
        for suffix,value in zip(('READ_RETURN','WRITE_RETURN'),expected):
            changed=[x for x in regen['changed'] if x['inst']==name and x['param']=='SFU_'+suffix]
            if len(changed)!=1 or changed[0]['bound']!=value:
                raise ValueError('actual emitted parameter record differs')
    return dict(schema='opentallas.hbm.absolute_sfu_consumer_gate.v1',status='PRIVATE_UNADOPTED_SOURCE_LAW_PASS',
        rows=rows,pad_cost=landing['summary'],
        max_pad_is_token_delta=False,final_LAT_integrated=False,
        FRRDX=dict(native_operand_loop=91,parts=[2,41,48],final_LAT_join='OPEN_SEPARATE_OPERAND_LOOP'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('evidence',type=Path);a=p.parse_args()
    reg=json.loads((a.evidence/'param_regen.json').read_text());land=json.loads((a.evidence/'landing_summary.json').read_text())
    result=check(reg,land); controls={}
    for label,pair in [('old145_142',(145,142)),('blanket_maxpad97',(224,221))]:
        bad=copy.deepcopy(reg)
        bad['record']['variant_values']['sfucore_NW.__cut_ctl'].update(READ_RETURN=pair[0],WRITE_RETURN=pair[1])
        try:check(bad,land)
        except ValueError as e:controls[label]='REJECTED: '+str(e)
        else:raise AssertionError('stale-law control accepted')
    result['controls']=controls
    (a.evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS actual8variant external125/122 + native2/2 = absolute127/124; two stale-law controls rejected')

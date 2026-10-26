#!/usr/bin/env python3
"""Opt-in native quant format-locality delta; no new register or data cycle.

Only remove the known FP32 low-half format zeros, after checking their literal
source value in the actual input netlist. All live write payload/control bits
retain their order. The original r2 registered output remains 281 bits/bank.
"""
import argparse
import json
from pathlib import Path
from b2_top import Die, parse_expr, slice_segs


def apply(delta, die):
    changed=[]
    for n in sorted(die.insts):
        if not n.startswith('hb_quant_NW__quant_NW') or not n.endswith('_lg'):
            continue
        i=die.insts[n]
        if i['master']!='ot_hgi_qdq_lg_port_group_r2' or i['params'].strip()!='.BANKS(2)':
            raise ValueError(f'{n}: unsupported quant leaf {i["master"]} {i["params"]}')
        if n in delta.get('remaster',{}) or 'wq_i' in delta.get('port_map',{}).get(n,{}):
            raise ValueError(f'{n}: already adapted')
        segs=parse_expr(i['conns']['wq_i'],die.widths)
        mapping=[]
        for b in range(2):
            mapping.append([b*281,b*281+7,b*153])
            for k in range(8):
                lo=b*281+8+32*k
                pad=slice_segs(segs,lo,lo+15)
                if len(pad)!=1 or pad[0]!=('c',16,0):
                    raise ValueError(f'{n}: format zero [{lo+15}:{lo}] is {pad}')
                mapping.append([lo+16,lo+31,b*153+8+16*k])
            mapping.append([b*281+264,b*281+280,b*153+136])
        delta.setdefault('remaster',{})[n]={'master':'ot_hgi_qdq_lg_bf16_r2','params':i['params']}
        delta.setdefault('port_map',{}).setdefault(n,{})['wq_i']=mapping
        changed.append(n)
    if len(changed)!=4:
        raise ValueError(f'Expected four native quant leaf groups, got {changed}')
    delta.setdefault('items',[]).append(dict(id='NATIVE-QUANT-BF16-LOCAL',
        status='source-local formatting; physical B1 interface adoption pending',
        instances=changed, removed_die_format_zero_bits=1024, added_cycles=0))
    return delta


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('delta');a.add_argument('--die',required=True);a.add_argument('--out',required=True)
    p=a.parse_args();d=apply(json.loads(Path(p.delta).read_text()),Die(p.die,[]))
    Path(p.out).write_text(json.dumps(d,indent=1)+'\n')
    print('QUANT_BF16_LOCAL',d['items'][-1])

if __name__=='__main__':main()

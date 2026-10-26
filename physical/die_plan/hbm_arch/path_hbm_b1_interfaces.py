#!/usr/bin/env python3
"""Fold proven VM observation / BF16 locality into the single D-HBM-B1 event.

These five blocks are soft contents of root / q_hub_nw, not standalone hard
cores. Geometry, face pins, output562 quant shape and mission cycles stay as
planned. Their changed source interfaces must be rebuilt with the master-plan
slice. Never treat this post-pass as a freeze or a standalone adoption.
"""
import argparse
import hashlib
import json
from pathlib import Path


def apply(raw):
    nw=raw['partition_types']['q_hub_nw']; changed=[]
    for c in nw['contents']:
        if c['inst'] not in [f'u_hb_quant_Q__quant_Q{k}_lg' for k in range(4)]:continue
        assert c['module']=='ot_hgi_qdq_lg_port_group_r2',c
        c['module']='ot_hgi_qdq_lg_bf16_r2';c['params']={'BANKS':2};c['status']='rework'
        c['note']+=' | D-HBM-B1 BF16 locality: wq_i562->306 live bits; low16 format expansion inside leaf; output562 / registers / 0addedcycles unchanged; physical slice rebuild owed'
        changed.append(dict(type='q_hub_nw',inst=c['inst'],module=c['module'],input_wq_bits_before=562,input_wq_bits_after=306,output_wq_bits=562,removed_die_constant_bits=256,added_cycles=0,outline_um=c['outline_um']))
    assert len(changed)==4
    root=raw['partition_types']['root'];obs=next(c for c in root['contents'] if c['inst']=='u_obs_C')
    assert obs['module'].startswith('ot_hbm_obs_leaf'),obs
    obs['module']='ot_hbm_obs_leaf';obs['params']={'N':144,'LID':0,'SYNC_MASK':"512'h0"};obs['status']='rework'
    # Conservative prebuild increment:73 FF(38sample+32sticky+3worddecode),
    #64sticky gates+64readword gates+14decode gates <=256 standard cells.
    oldcells=obs['cells'];obs['cells']=oldcells+256
    obs['note']+=' | D-HBM-B1 vmstat19 observed at bits125..143; original125-bit prefix/host ABI fixed; leaf3edges,0addedcycles; +256cell conservative topology reserve, remap/slice fit owed'
    changed.append(dict(type='root',inst='u_obs_C',input_obs_bits_before=125,input_obs_bits_after=144,host_data_bits=32,host_index_bits=8,leaf_cycles=3,added_cycles=0,cell_reserve_before=oldcells,cell_reserve_after=obs['cells'],outline_um=obs['outline_um']))
    raw['note']=raw.get('note','')+' | D-HBM-B1 interface candidate: proven BF16 local expansion in4 NW quant soft contents, root obs_C vmstat19; no plan freeze, master-plan fit/census/bind owed'
    return dict(changed_contents=changed,quant_removed_die_constant_bits=1024,external_partition_port_changes=0,added_cycles=0,
        neighbouring_output_contract='Quant wq_o562 unchanged; producer live BF16 fields retain original ordering; observation ring32data/8idx unchanged.',
        remaining=['regenerate native census/source module associations','master-plan root observer lot fit with new256cell reserve','rebuild changed soft contents inside their partition slice','q_hub_ne inherited NWquant budget entries remain conservative old-template allocations; native population reconciliation owed'])


def main():
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0]);ap.add_argument('plan');ap.add_argument('--out',required=True);ap.add_argument('--report',required=True);a=ap.parse_args()
    b=Path(a.plan).read_bytes();raw=json.loads(b);r=apply(raw);out=(json.dumps(raw,indent=1)+'\n').encode();Path(a.out).write_bytes(out);r.update(input_sha256=hashlib.sha256(b).hexdigest(),output_sha256=hashlib.sha256(out).hexdigest());Path(a.report).write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r,indent=1))

if __name__=='__main__':main()

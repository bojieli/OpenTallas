#!/usr/bin/env python3
"""Actual native owner/FIFO/SRAM leaves in the 17 service-band slot groups.

The wrappers materialize real leaf hardware. They do not manufacture old q/lq
ports, source bindings, pin plans, CTS results or inter-band timing closure.
"""
import argparse
import hashlib
import json
from pathlib import Path
import hbm_die_views as V

ROOT=Path(__file__).resolve().parents[1]
BASE=Path('rtl/hbm_accel/loader/service_native')
OUT=Path('physical/hbm_accel_die_views/svc/v15/native_bands')
LEAVES=dict(owner='ot_hbm_svc_prefetch_burst_owner',bank='ot_hbm_svc_prefetch_burst_bank')


def source(top,ids,leaves):
    ports=[]
    for role,leaf in leaves.items():
        for name,(direction,width) in leaf['ports'].items():
            if direction not in ('input','output'):raise ValueError('unknown native leaf direction')
            ports.append(f' {direction} wire [{width*len(ids)-1}:0] {role}_{name}')
    s=['`default_nettype none','// Native logical bank id is ordinal%32, not the DRAM PC hash.',
       '// Separate real clock/reset ports remain visible for every actual leaf.',f'module {top} (',',\n'.join(ports),');']
    for index,pid in enumerate(ids):
        for role,leaf in leaves.items():
            params=f'.PC(5\'d{pid}),.OWNER_AW(5)' if role=='owner' else f'.BANK(5\'d{pid}),.RESPONSE_DEPTH(8)'
            conns=','.join(f'.{name}({role}_{name}[{index*width}+:{width}])' for name,(_,width) in leaf['ports'].items())
            s.append(f" {leaf['top']} #({params}) u_{role}{pid} ({conns});")
    s+=['endmodule','`default_nettype wire','']
    return '\n'.join(s)


def build(write=False):
    inventory=Path('physical/hbm_accel_die_views/svc/v15/contract.json')
    d=json.loads((ROOT/inventory).read_text());leaves={}
    for role,top in LEAVES.items():
        path=BASE/(top+'.sv');parsed=V.L.parse_module(str(ROOT/path),top)
        leaves[role]=dict(top=top,source=str(path),sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),ports=parsed['ports'])
    records={};coverage={'SW':[],'SE':[]}
    for old,rec in d['actual_module_port_tables'].items():
        if not old.startswith(('hfd_svc_v15_SW_s','hfd_svc_v15_SE_s')):continue
        ids=rec['physical_pc_ids'];family=old.split('_')[3];coverage[family]+=ids
        top=old.replace('hfd_svc_v15_','hfd_svc_native_');text=source(top,ids,leaves);path=OUT/'rtl'/(top+'.sv')
        if write:(ROOT/path).parent.mkdir(parents=True,exist_ok=True);(ROOT/path).write_text(text)
        elif not (ROOT/path).exists() or (ROOT/path).read_text()!=text:raise ValueError('native source/pin inventory differs: '+str(path))
        ports=V.L.parse_module(str(ROOT/path),top)['ports']
        count={direction:sum(width for dr,width in ports.values() if dr==direction) for direction in ('input','output')}
        records[top]=dict(source=str(path),sha256=hashlib.sha256(text.encode()).hexdigest(),physical_PC_ids=ids,logical_ordinal_bank_ids=ids,instances=[top.replace('_SW_','_'+f+'_').replace('_SE_','_'+f+'_') for f in (['SW','NW'] if family=='SW' else ['SE','NE'])],ports={p:dict(direction=v[0],bits=v[1]) for p,v in ports.items()},port_counts=count,actual_SRAMs=len(ids),actual_FIFO_payload_words=8*len(ids),clock_sinks=dict(each_owner_hbm_root=1577,each_bank_FIFO_hbm_root=2294,each_bank_stream_root=213,each_bank_SRAM_clock_pins=1),slot_fit_measured=False,pin_plan=None)
    for family,ids in coverage.items():
        if sorted(ids)!=list(range(32)):raise ValueError('missing/duplicate PC or ordinal bank in '+family)
    return dict(schema='opentallas.actual-native-service-bands.v1',leaves=leaves,masters=records,instance_count=sum(len(v['instances']) for v in records.values()),dependency_sha256={str(inventory):hashlib.sha256((ROOT/inventory).read_bytes()).hexdigest()},native_leaf_hardware=True,qualified=False,remaining=['No new pin plan/physical hardened view/slot-fit proof','Native top descriptor/response crossbar/control joins not partitioned into timed registered interband edges','Separate leaf clock/reset inputs require actual parent clock and domain-local reset contracts','WB/SMpacked cache/loader/ATT sources are not silently substituted for these PF-only leaves'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--generate',action='store_true');p.add_argument('--require-qualified',action='store_true');a=p.parse_args();d=build(a.generate)
    o=ROOT/OUT/'contract.json';o.parent.mkdir(parents=True,exist_ok=True);o.write_text(json.dumps(d,indent=2)+'\n')
    print(f'Native hardware masters={len(d["masters"])} instances={d["instance_count"]} PC/bank coverage exact; qualified=False')
    if a.require_qualified:raise SystemExit(2)

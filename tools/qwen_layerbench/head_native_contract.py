#!/usr/bin/env python3
"""Validate explicit native HEAD source-bridge inputs; never emit instructions.

The known transformer layout is diagnostic context, not a HEAD allocation.
Missing maps/dates remain null in the template and fail validation. Even a
complete input does not qualify arithmetic, install BOOT, or emit a calendar.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import dv_lower as D

MAPS = ('x_base', 'rx_base', 'gain_base', 'ssq_pidx', 'apply_pidx')
DATES = ('x_ready_edge', 'gain_committed_edge', 'prog_committed_edge',
         'root_config_effective_edge', 'ssq_issue_edge', 'rstd_w1_edge',
         'rstd_vm_visible_edge', 'apply_issue_edge', 'apply_first_operand_edge')
AUTHORITIES = ('source_tree_sha', 'selected_recipe_sha256', 'allocation_source',
               'head_norm_isa_source', 'scalar_producer_source', 'dates_source',
               'native_arithmetic_gate')


def template():
    own = D.ownership(slice_rtl='s8')
    return dict(schema='opentallas.qwen.native-head-contract.v1', stage=37,
                rank=None, user=None, test_only=False,
                authorities={k:None for k in AUTHORITIES},
                memory_profile=dict(MEMORY_ALIGNMENT=3, MEMORY_READ_EXTRA=0),
                scalar=dict(producer='ROOT_FUSED_32_BLOCKS', root_slice=0,
                            k=None, eps_fp32_hex=None),
                slices=[dict(slice=s, blocks=b,
                             **{k:None for k in MAPS+DATES},
                             psum_root_arrival_edges=None,
                             protected_vm_ranges=None, protected_crom_ranges=None,
                             protected_prog_indices=None)
                        for s,b in enumerate(own['residual']['blocks_per_slice'])])


def validate(c):
    errors=[]
    def need(ok, msg):
        if not ok: errors.append(msg)
    need(c.get('schema')=='opentallas.qwen.native-head-contract.v1','schema')
    need(c.get('stage')==37,'stage must be37')
    for field, limit in [('rank',8),('user',4)]:
        need(type(c.get(field)) is int and 0<=c[field]<limit,field)
    for k in AUTHORITIES:
        need(isinstance(c.get('authorities',{}).get(k),str) and bool(c['authorities'][k].strip()),'authorities.'+k)
    need(c.get('memory_profile')==dict(MEMORY_ALIGNMENT=3,MEMORY_READ_EXTRA=0),'selected825 memory profile must be3/0')
    scalar=c.get('scalar',{})
    need(scalar.get('producer')=='ROOT_FUSED_32_BLOCKS','scalar.producer')
    need(scalar.get('root_slice')==0,'scalar.root_slice')
    need(type(scalar.get('k')) is int and scalar.get('k')==12,'scalar.k must describe4096-element norm')
    eps=scalar.get('eps_fp32_hex')
    need(isinstance(eps,str) and len(eps)==8 and all(ch in '0123456789abcdefABCDEF' for ch in eps),'scalar.eps_fp32_hex required from actual HEAD ISA')
    slices=c.get('slices',[])
    if not isinstance(slices,list) or len(slices)!=12 or not all(isinstance(s,dict) for s in slices):
        errors.append('exactly12 distinct slices required'); return errors
    ids=[s.get('slice') for s in slices]
    need(all(type(sid) is int for sid in ids) and set(ids)==set(range(12)),'exactly12 distinct slices required')
    known=D.ownership(slice_rtl='s8')['residual']['blocks_per_slice']
    for s in slices:
        sid=s.get('slice'); prefix=f'slice{sid}.'
        if type(sid) is not int or sid not in range(12): continue
        need(s.get('blocks')==known[sid],prefix+'blocks must match native s8 ownership')
        for k in MAPS+DATES:
            need(type(s.get(k)) is int and s[k]>=0,prefix+k)
        arr=s.get('psum_root_arrival_edges')
        need(isinstance(arr,list) and len(arr)==len(known[sid]) and all(type(v) is int and v>=0 for v in arr),prefix+'psum_root_arrival_edges')
        for k in ('protected_vm_ranges','protected_crom_ranges','protected_prog_indices'):
            need(isinstance(s.get(k),list),prefix+k+' explicit liveness inventory required')
        if not all(type(s.get(k)) is int for k in MAPS+DATES) or type(c.get('user')) is not int: continue
        user=c['user']; n=128*len(known[sid])
        vm=(s['x_base'],s['x_base']+n); rx=(s['rx_base'],s['rx_base']+1); cr=(s['gain_base'],s['gain_base']+n)
        for name,rng,lo,hi in [('X',vm,user*4096,(user+1)*4096),('RX',rx,user*4096,(user+1)*4096),('gain',cr,user*2048,(user+1)*2048)]:
            need(lo<=rng[0]<rng[1]<=hi,prefix+name+' crosses user bank')
        need(not(vm[0]<rx[1] and rx[0]<vm[1]),prefix+'RX overlaps X')
        need(s['gain_base']%16==0,prefix+'gain CROM must be row aligned')
        pidx=[s['ssq_pidx'],s['apply_pidx']]
        need(len(set(pidx))==2 and all(user*128<=p<(user+1)*128 for p in pidx),prefix+'PROG bank/duplicate')
        for label, spans in [('vm',[vm,rx]),('crom',[cr])]:
            for r in s.get('protected_'+label+'_ranges') or []:
                need(isinstance(r,list) and len(r)==2 and all(type(v) is int for v in r) and r[0]<r[1],prefix+'invalid protected '+label+' range')
                if not isinstance(r,list) or len(r)!=2 or not all(type(v) is int for v in r): continue
                need(not any(a<r[1] and r[0]<b for a,b in spans),prefix+'overwrites live '+label)
        need(not set(pidx).intersection(s.get('protected_prog_indices') or []),prefix+'overwrites live PROG')
        need(s['x_ready_edge']<s['ssq_issue_edge'],prefix+'SSQ precedes X publication')
        need(s['root_config_effective_edge']<s['ssq_issue_edge'],prefix+'SSQ precedes ROOT configuration')
        need(s['prog_committed_edge']<min(s['ssq_issue_edge'],s['apply_issue_edge']),prefix+'PROG not committed before issue')
        need(s['rstd_w1_edge']<=s['rstd_vm_visible_edge']<s['apply_first_operand_edge'],prefix+'RSTD not visible before operand read')
        need(s['gain_committed_edge']<s['apply_first_operand_edge'],prefix+'gain not committed before operand read')
        need(s['apply_issue_edge']<=s['apply_first_operand_edge'],prefix+'operand read precedes issue')
        if isinstance(arr,list) and arr and all(type(v) is int for v in arr):
            need(s['ssq_issue_edge']<min(arr) and max(arr)<s['rstd_w1_edge'],prefix+'PSUM/ROOT/RSTD dates inconsistent')
    arrivals=[v for s in slices for v in (s.get('psum_root_arrival_edges') or []) if type(v) is int]
    need(len(arrivals)==32 and len(set(arrivals))==32,'ROOT requires32 distinct PSUM arrival edges without scalar-port collisions')
    return errors


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--template',action='store_true')
    ap.add_argument('--contract',type=Path)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    if a.template:
        a.out.write_text(json.dumps(template(),indent=2)+'\n'); return
    if not a.contract: ap.error('--contract or --template required')
    c=json.loads(a.contract.read_text()); errors=validate(c)
    result=dict(status='BLOCKED' if errors else ('TEST_INPUT_VALIDATED' if c.get('test_only') else 'BRIDGE_INPUT_VALIDATED'),
                missing_or_invalid=errors, native_arithmetic='NOT_RUN_BY_BRIDGE',
                instruction_words='NOT_EMITTED',boot_transport='NOT_INSTALLED',calendar='NOT_EMITTED')
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    raise SystemExit(bool(errors))

if __name__=='__main__': main()

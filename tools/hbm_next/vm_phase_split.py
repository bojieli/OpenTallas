#!/usr/bin/env python3
"""Prepare exact row fragments for the owner-selected finite-VM phase alternative.

Splitting a consumer does not release already resident producer values. Therefore
this emits no executable image: actual producer spills, reload addresses and the
complete phase live set remain required. Byte traffic is counted from source
operands, never from an unrelated per-record fixed-latency sensitivity.
"""
import argparse,copy,hashlib,json,sys
from pathlib import Path


def prepare(record,rowx,IR,rows,workspace,carry,capacity=262144):
    if (record.unit,record.op)!=('SU','VOP')or rowx is None or rowx.rsel:
        raise ValueError('requires statically explicit SU row record')
    if set(record.desc)!={'A','B','R'}:raise ValueError('only explicit A/B -> R source shape supported')
    if not 1<=rows<rowx.n:raise ValueError('split must reduce resident row count')
    if workspace%8 or carry%8:raise ValueError('VM work/carry must be sector aligned')
    sizes={}
    for k,d in record.desc.items():
        if d.space!='VM'or any(getattr(d,f,0)for f in ('indexed','dyn_sel','n_sel','lstride','l1stride','ibcast')):
            raise ValueError('dynamic/broadcast operands need explicit source publication')
        size=d.n*max(d.m,1)
        if d.istride not in (0,1)or(max(d.m,1)>1 and d.stride!=d.n):
            raise ValueError('noncontiguous source operand')
        if rowx.rs.get(k,0)<size:raise ValueError('rows overlap')
        sizes[k]=size
    phases=[];orig=IR.expand(record,rowx)
    for start in range(0,rowx.n,rows):
        n=min(rows,rowx.n-start);r,x=copy.deepcopy(record),copy.deepcopy(rowx)
        x.n=n;x.slot0=rowx.slot0+start;r.slot=x.slot0&7
        a=workspace;b=a+n*sizes['A'];end=b+n*sizes['B']
        output=carry+start*rowx.rs['R'];out_end=output+(n-1)*rowx.rs['R']+sizes['R']
        if min(a,b,output)<0 or max(end,out_end)>capacity:raise ValueError('phase buffers outside old regular VM')
        if a<out_end and output<end:raise ValueError('phase inputs alias scalar carry')
        r.desc['A'].base=a;r.desc['B'].base=b;r.desc['R'].base=output
        x.rs['A']=sizes['A'];x.rs['B']=sizes['B']
        IR.check(r,x);IR.check_rows_independent(r,x)
        # The row operation/template/rounding stays exact; only explicit address
        # relocation and row grouping change. Compare the expanded source rows.
        expanded=IR.expand(r,x)
        pubs=[]
        for q,(slot,one) in enumerate(expanded):
            before_slot,before=orig[start+q]
            if slot!=before_slot:raise ValueError('row identity changed')
            for k,newbase in [('A',a+q*sizes['A']),('B',b+q*sizes['B']),('R',output+q*rowx.rs['R'])]:
                expected=copy.deepcopy(before);expected.desc[k].base=newbase
                if vars(one.desc[k])!=vars(expected.desc[k]):raise ValueError('expanded descriptor semantics changed')
            if one.sut!=before.sut or one.param!=before.param or one.imm_a!=before.imm_a or one.imm_b!=before.imm_b:
                raise ValueError('arithmetic/template changed')
        for k,dst in [('A',a),('B',b)]:
            pubs.append(dict(operand=k,source_vm_rows=[[record.desc[k].base+(start+q)*rowx.rs[k],sizes[k]]for q in range(n)],
                             reload_vm_base=dst,words=n*sizes[k],hbm_spill_address=None,
                             producer_store_required=True,reload_required=True))
        phases.append(dict(start_row=start,rows=n,input_work_words=end-workspace,input_work_range=[workspace,end],
                           scalar_carry_range=[output,out_end],native_record_hex=IR.encode(r,x).hex(),publication=pubs))
    words=sum(sum(p['words']for p in x['publication'])for x in phases)
    return dict(schema='opentallas.hbm.vm_finite_phase_preparation.v1',status='MISSING_PRODUCER_PUBLICATION',
                executable=False,full_programme_fits=None,phases=phases,capacity_words=capacity,
                source_input_words=words,chosen_spill_reload_bytes=2*words*4,
                chosen_dma_records=2*len(record.desc.keys()-{'R'})*len(phases),
                source_arithmetic_and_row_expansion_preserved=True,
                holds=['actual producer groups must be split/spilled before old VM exceeds capacity',
                       'provide real disjoint HBM scratch addresses and emit actual stores/reloads',
                       'complete phase live set includes other carried/scalar/table/gain operands',
                       'retime later R consumers to scalar carry and price bytes/drains/reloads on current model',
                       'consumer-only row split is not a storage reduction'])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('image','compiler-tools','out'):ap.add_argument('--'+k,required=k!='compiler-tools')
    ap.add_argument('--at',type=int,default=1470);ap.add_argument('--rows',type=int,default=2)
    ap.add_argument('--workspace',type=int,required=True);ap.add_argument('--carry',type=int,required=True)
    a=ap.parse_args()
    from isa_loader import load_isa
    IR,IC=load_isa(a.compiler_tools)
    raw=Path(a.image).read_bytes();rr=IC.decode_all(raw);off,r,rx,_=rr[a.at]
    out=prepare(r,rx,IR,a.rows,a.workspace,a.carry)
    out.update(image_sha256=hashlib.sha256(raw).hexdigest(),source_record_index=a.at,source_image_offset=off)
    Path(a.out).write_text(json.dumps(out,indent=1)+'\n')
    print(json.dumps({k:out[k]for k in ('status','chosen_spill_reload_bytes','chosen_dma_records','full_programme_fits')}))


if __name__=='__main__':main()

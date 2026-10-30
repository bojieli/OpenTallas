#!/usr/bin/env python3
"""Value-lifetime relocation of a bounded explicit-row native producer slice.

Descriptors sharing original words within an instruction retain their alias.
Every read joins the value versions it reads so each descriptor remains affine.
Boundary loads/retirements are explicit obligations, not assumed resident data.
"""
import argparse,copy,hashlib,json,sys
from pathlib import Path
import numpy as np
from vm_phase_region import merge_intervals,uncovered


def engine_span(record,operand):
    d=record.desc[operand]
    if any(getattr(d,k,0)for k in ('indexed','dyn_sel','n_sel','lstride','l1stride')):
        raise ValueError('dynamic operand requires actual runtime footprint')
    n=d.n
    if record.unit=='SU'and record.sut and record.sut.get('b_half')and operand in('B','D'):
        n=(n+1)//2
    step=0 if d.ibcast else(d.istride or 1)
    end=d.base+(max(1,d.m)-1)*d.stride+max(0,n-1)*step+1
    if end<=d.base:raise ValueError('negative or empty engine extent')
    return d.base,end


def infer_static_boundary(records,after,IR):
    written=[];needed=[];unresolved=[]
    for index in range(after+1,len(records)):
        _,r,x,_=records[index]
        if x and x.rsel and r.unit!='ATT':
            unresolved.append(dict(record=index,reason='runtime expert row table'));continue
        implicit=[]
        if x and x.rsel and r.unit=='ATT':implicit.append([x.rtab,x.rtab+32*IR.PLAN_WORDS])
        if(r.unit,r.op)==('CTL','LOOP')and r.param&(1<<17):implicit.append([r.imm_a,r.imm_a+1])
        for a,b in implicit:needed+=uncovered(a,b,written)
        for slot,row in IR.expand(r,x):
            wo=IR.written_operands(row);updates=[]
            for k,d in row.desc.items():
                if d.space!='VM':continue
                try:a,b=engine_span(row,k)
                except ValueError:
                    unresolved.append(dict(record=index,slot=slot,operand=k,reason='runtime descriptor'));continue
                if k in wo:updates.append([a,b])
                else:needed+=uncovered(a,b,written)
            written=merge_intervals(written+updates)
    return dict(after=after,known_boundary_intervals=merge_intervals(needed),unresolved_dynamic_count=len(unresolved),unresolved_examples=unresolved[:8],whole_programme_fit=None)


class UF:
    def __init__(self):self.p=[]
    def add(self):self.p.append(len(self.p));return len(self.p)-1
    def find(self,i):
        while self.p[i]!=i:self.p[i]=self.p[self.p[i]];i=self.p[i]
        return i
    def join(self,items):
        roots={self.find(int(i)) for i in items}
        if not roots:raise ValueError('empty value component')
        root=min(roots)
        for i in roots:self.p[i]=root
        return root


def build(records,first,last,start,count,IR,live_out,capacity=262144,placement_preference=None):
    current=np.full(1<<19,-1,np.int32);uf=UF();vals=[];ops=[];all_external=[]
    def new(a,b,t,kind,anchor):
        if not 0<=a<b<=len(current):raise ValueError('source VM interval exceeds actual ABI')
        i=uf.add();vals.append(dict(id=i,a=a,b=b,t0=t,t1=t,kind=kind,anchor=anchor));return i
    def read(a,b,t,anchor):
        missing=np.flatnonzero(current[a:b]<0)+a
        for block in np.split(missing,np.flatnonzero(np.diff(missing)!=1)+1):
            if not len(block):continue
            lo,hi=int(block[0]),int(block[-1])+1;i=new(lo,hi,t,'external',anchor);current[lo:hi]=i;all_external.append(i)
        ids=np.unique(current[a:b]).tolist()
        for i in ids:vals[i]['t1']=max(vals[i]['t1'],t)
        return ids
    t=0
    for index in range(first,last+1):
        t=index-first
        _,source,x,_=records[index]
        if x is None:
            if(source.unit,source.op)==('IDX','KVUNION'):
                if(source.param&15)+1!=count:raise ValueError('KVUNION physical lane count differs')
                if((source.param>>4)&15)!=start:continue
            elif(source.unit,source.op)not in(('DMA','LOAD'),('DMA','STORE'),('DMA','FENCE'),('CTL','NOP'),('CTL','ACCEPT'),('CTL','TOKX')):raise ValueError('unbounded shared control operation')
            expanded=IR.expand(source,x)
        elif x.rsel and source.unit=='ATT':
            if x.n!=count or x.emask:raise ValueError('requires bounded native attention plan')
            if x.slot0!=start:continue
            expanded=IR.expand(source,x)
        else:
            if x.rsel or start+count>x.n:raise ValueError('requires aligned explicit row records')
            expanded=IR.expand(source,x)[start:start+count]
        for slot,r in expanded:
            ports={};readivs=[];writeivs=[];writes=IR.written_operands(r)
            if x and x.rsel and source.unit=='ATT':
                a=x.rtab;b=a+32*IR.PLAN_WORDS;ids=read(a,b,t,(index,slot,'__rtab'));ports['__rtab']=uf.join(ids);readivs.append((a,b,ids))
            # Reads see the original value before this instruction writes.
            for k,d in r.desc.items():
                if d.space!='VM' or k in writes:continue
                a,b=engine_span(r,k);a=a//8*8;b=(b+7)//8*8;ids=read(a,b,t,(index,slot,k));ports[k]=uf.join(ids);readivs.append((a,b,ids))
            # Outputs get a new version; in-place read/output aliases retain one
            # translation by construction, as on the unchanged source engine.
            for k,d in r.desc.items():
                if d.space!='VM' or k not in writes:continue
                a,b=engine_span(r,k);lo=a//8*8;hi=(b+7)//8*8
                preserve=read(lo,hi,t,(index,slot,k))if(a!=lo or b!=hi)else[]
                a,b=lo,hi;i=new(a,b,t,'write',(index,slot,k));ids=[i]+preserve
                for lo,hi,other in readivs+writeivs:
                    if max(a,lo)<min(b,hi):ids+=other
                ports[k]=uf.join(ids);writeivs.append((a,b,[i]));current[a:b]=i
            ops.append(dict(source_record=index,slot=slot,record=copy.deepcopy(r),ports=ports,t=t))
    # Preserve the shared-weight SM row-array layout. These output values are
    # consumed together by the following COLLective; their source array stride
    # is retained, avoiding a serial reissue of the weight stream.
    for index in range(first,last+1):
        group=[op for op in ops if op['source_record']==index]
        if group and group[0]['record'].unit in('SM','ATT'):
            for k,d in group[0]['record'].desc.items():
                if d.space!='VM':continue
                ids=[op['ports'][k]for op in group if k in op['ports']]
                if ids:uf.join(ids)
    t=last-first+1
    # Only explicitly enumerated boundary values are retained after this slice.
    # Unknown dynamic boundary values remain unresolved in the parent packet.
    for a,b in live_out:
        for i in np.unique(current[a:b]).tolist():
            if i>=0:vals[i]['t1']=t
    objects={}
    for v in vals:
        root=uf.find(v['id']);o=objects.setdefault(root,dict(id=root,a=v['a'],b=v['b'],t0=v['t0'],t1=v['t1'],values=[]))
        o.update(a=min(o['a'],v['a']),b=max(o['b'],v['b']),t0=min(o['t0'],v['t0']),t1=max(o['t1'],v['t1']));o['values'].append(v['id'])
    hints={o['id']:list(placement_preference(o,vals))for o in objects.values()}if placement_preference else{}
    placed=[];high=0
    for o in sorted(objects.values(),key=lambda o:(not bool(hints.get(o['id'])), -(o['b']-o['a']),o['t0'])):
        size=o['b']-o['a'];candidate=o['a']%8
        occupied=sorted((p['base'],p['base']+p['b']-p['a'])for p in placed if not(p['t1']<o['t0']or o['t1']<p['t0']))
        preferred=next((int(c)for c in hints.get(o['id'],[])if c>=0 and c+size<=capacity and(c-o['a'])%8==0 and all(c+size<=lo or hi<=c for lo,hi in occupied)),None)
        if preferred is not None:candidate=preferred
        else:
            for lo,hi in occupied:
                if candidate+size<=lo:break
                if candidate<hi:candidate=hi+(o['a']-hi)%8
        if candidate+size>capacity and placement_preference:return build(records,first,last,start,count,IR,live_out,capacity,None)
        if candidate+size>capacity:raise ValueError(f'value phase needs {candidate+size} words > {capacity}')
        o['base']=candidate;placed.append(o);high=max(high,candidate+size)
    # Every source port stays in its joined component with one translation.
    blob=bytearray();manifest=[];relocated=[]
    for op in ops:
        q=copy.deepcopy(op['record'])
        for k,d in q.desc.items():
            if d.space=='VM':
                o=objects[uf.find(op['ports'][k])];d.base+=o['base']-o['a']
        relocated.append((op,q))
    for index in range(first,last+1):
        rows=[(op,q)for op,q in relocated if op['source_record']==index]
        source=records[index][1];original_x=records[index][2]
        if not rows:continue
        if original_x is None:
            for op,q in rows:
                encoded=IR.encode(q,None);manifest.append(dict(source_record=index,slots=[op['slot']],offset=len(blob),bytes=len(encoded),folded_rows=False,operand_objects=[{k:uf.find(i)for k,i in op['ports'].items()}]));blob.extend(encoded)
            continue
        q=copy.deepcopy(rows[0][1]);qx=copy.deepcopy(original_x);qx.n=count;qx.slot0=original_x.slot0 if source.unit=='ATT'and original_x.rsel else start+original_x.slot0;q.slot=qx.slot0&7
        if source.unit=='ATT'and original_x.rsel:
            obj=objects[uf.find(rows[0][0]['ports']['__rtab'])];qx.rtab=original_x.rtab+obj['base']-obj['a']
        if q.unit=='SM':q.param=(q.param&3)|((count-1)<<2)
        folded=True
        for k,d in q.desc.items():
            bases=[r.desc[k].base for _,r in rows]
            diffs={bases[i]-bases[i-1]for i in range(1,len(bases))}
            if len(diffs)>1:folded=False;break
            step=next(iter(diffs),0)
            if d.space=='HBM':
                if step%(1<<qx.hsh):folded=False;break
                step>>=qx.hsh
            qx.rs[k]=step
        if folded:
            try:
                IR.check(q,qx)
                if IR.check_rows_independent(q,qx):folded=False
                if folded:
                    ex=IR.expand(q,qx)
                    if [(s,vars(r))for s,r in ex]!=[(op['slot'],vars(r))for op,r in rows]:folded=False
            except(ValueError,IR.RangeFault):folded=False
        if source.unit=='ATT'and original_x.rsel and not folded:raise ValueError('attention plan lanes cannot be scalarized')
        emitted=[(q,qx,rows)]if folded else[(r,None,[(op,r)])for op,r in rows]
        for r,x,members in emitted:
            encoded=IR.encode(r,x)
            manifest.append(dict(source_record=index,slots=[op['slot']for op,_ in members],offset=len(blob),bytes=len(encoded),folded_rows=bool(x),operand_objects=[{k:uf.find(i)for k,i in op['ports'].items()}for op,_ in members]))
            blob.extend(encoded)
    boundary=[]
    for i in all_external:
        v=vals[i];o=objects[uf.find(i)];boundary.append(dict(source_words=[v['a'],v['b']],destination_words=[o['base']+v['a']-o['a'],o['base']+v['b']-o['a']],before_source_record=v['anchor'][0],source_slot=v['anchor'][1],source_anchor=v['anchor']))
    selected=np.zeros(len(current),bool)
    for a,b in live_out:selected[a//8*8:(b+7)//8*8]=True
    returns=[]
    for i in np.unique(current[selected]).tolist():
        if i<0 or vals[i]['kind']!='write':continue
        v=vals[i];o=objects[uf.find(i)]
        addrs=np.flatnonzero((current==i)&selected)
        for block in np.split(addrs,np.flatnonzero(np.diff(addrs)!=1)+1):
            if not len(block):continue
            a,b=int(block[0]),int(block[-1])+1
            if a%8 or b%8:raise ValueError('retirement lacks whole-sector ownership')
            returns.append(dict(source_words=[a,b],vm_words=[o['base']+a-o['a'],o['base']+b-o['a']],writer_anchor=v['anchor']))
    # Algebraic source-address equality plus object overlap/lifetime checks.
    for j,o in enumerate(placed):
        for p in placed[:j]:
            if not(p['t1']<o['t0']or o['t1']<p['t0']):
                if max(p['base'],o['base'])<min(p['base']+p['b']-p['a'],o['base']+o['b']-o['a']):raise ValueError('live value storage aliases')
    return bytes(blob),dict(start_row=start,rows=count,high_water_words=high,capacity_words=capacity,
                            objects=placed,records=manifest,boundary_loads=boundary,retirements=returns,
                            sector_granular_ownership=True,declared_live_out=live_out,instruction_count=len(manifest),expanded_row_count=len(ops),source_record_steps=t,
                            shared_weight_sm_rows_preserved=all(row['folded_rows']for row in manifest if records[row['source_record']][1].unit=='SM'),
                            whole_programme_fits=None,executable=False,
                            holds=['emit actual boundary loads/retirements and real scratch ownership',
                                   'resolve dynamic whole-programme live-out obligations',
                                   'price ungrouped DMA rows and emitted boundary drains before adoption'])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('image','compiler-tools','out-dir'):ap.add_argument('--'+k,required=k!='compiler-tools')
    ap.add_argument('--live-out');ap.add_argument('--infer-live-out',action='store_true')
    ap.add_argument('--first',type=int,default=1458);ap.add_argument('--last',type=int,default=1473);ap.add_argument('--rows',type=int,default=3)
    a=ap.parse_args()
    from isa_loader import load_isa
    IR,IC=load_isa(a.compiler_tools)
    raw=Path(a.image).read_bytes();rr=IC.decode_all(raw)
    if a.infer_live_out:boundary=infer_static_boundary(rr,a.last,IR)
    elif a.live_out:boundary=json.loads(Path(a.live_out).read_text())
    else:raise ValueError('provide declared live-out or request static inference (dynamic obligations remain unresolved)')
    live=boundary['known_boundary_intervals'];out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True);phases=[]
    n=max((x.slot0+x.n)if x else(((r.param>>4)&15)+(r.param&15)+1 if(r.unit,r.op)==('IDX','KVUNION')else 0)for _,r,x,_ in rr[a.first:a.last+1])
    for start in range(0,n,a.rows):
        blob,info=build(rr,a.first,a.last,start,min(a.rows,n-start),IR,live)
        name=f'value_{start}.hgi1r';(out/name).write_bytes(blob);info['fragment']=name;phases.append(info)
    packet=dict(schema='opentallas.hbm.vm_value_phase.v1',source_sha256=hashlib.sha256(raw).hexdigest(),source_record_range=[a.first,a.last],boundary=boundary,phases=phases)
    (out/'values.json').write_text(json.dumps(packet,indent=1)+'\n');print(json.dumps(dict(high_water=[p['high_water_words']for p in phases],instructions=[p['instruction_count']for p in phases])))

if __name__=='__main__':main()

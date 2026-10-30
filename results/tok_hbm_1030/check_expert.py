"""Original versus relocated native expert entry: actual UNION/rsel semantics."""
import copy,json,sys
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[2];tools=Path('/srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/tools')
sys.path[:0]=[str(root/'tools/hbm_next'),str(tools/'hbm_next'),str(tools),'/home/ubuntu/OpenTallas/tools']
import image_check as IC,isa_rows as IR,vm_expert_entry as E
from hgi_sim import machine as M
source=IC.decode_all(Path('/srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/a122.hgi1r').read_bytes())
blob,packet=E.lower(source);segments=packet['segments'];T=lambda n:E.translate(n,segments)
low=IC.decode_all(blob);rng=np.random.default_rng(1030)
profiles=[[[0,1,2,3,4,383]]*6,[list(range(i*6,(i+1)*6))for i in range(6)],[[0,7,11,19,i+30,383]for i in range(6)]]
profiles += [[sorted(rng.choice(384,6,replace=False).tolist())for _ in range(6)]for _ in range(61)]


def union(vm,r):
    a=r.desc['A'];rows=[vm[a.base+i*a.stride:a.base+i*a.stride+a.n].tolist()for i in range(a.m)]
    uni,tabs=IR.idx_union(rows,r.imm_a,r.imm_b)
    assert len(uni)<=r.desc['O'].n
    vm[r.desc['D'].base]=len(uni);vm[r.desc['O'].base:r.desc['O'].base+len(uni)]=uni
    for L,(c,entries)in enumerate(tabs):
        a=r.desc['R'].base+L*r.desc['R'].stride;vm[a:a+32]=0;vm[a]=c
        vm[a+1:a+1+c]=[IR.entry_word(*e)for e in entries]
    return uni,tabs


def check(data):
    lowered=IC.decode_all(data);compared=0
    for rows in profiles:
        old=((np.arange(1<<19,dtype=np.uint64)*2654435761)^0x9e3779b9).astype(np.uint32);new=np.zeros(262144,np.uint32)
        for i,ids in enumerate(rows):old[506112+8*i:506112+8*i+6]=ids
        for seg in segments:
            a,b=seg['source_words'];c,d=seg['vm_words'];new[c:d]=old[a:b]
        u,t=union(old,source[1559][1]);v,w=union(new,lowered[0][1]);assert u==v and t==w
        # Independent golden row order and combine-slot mapping.
        expected=sorted(set(x for row in rows for x in row));assert u==expected
        for L,expert in enumerate(expected):
            golden=[(rho,rho*7+row.index(expert))for rho,row in enumerate(rows)if expert in row]
            assert t[L]==(len(golden),golden)
        assert int(old[source[1561][1].imm_a])==int(new[lowered[2][1].imm_a])==len(expected),'runtime count differs'
        # Real HGI effective addressing preserves raw score bits for all six
        # indexed gathers, including ids at383. No floating conversion.
        hbm=M.Hbm();od=M.Die(0,hbm);nd=M.Die(0,hbm);od.vm=old;nd.vm=new;om=M.Machine([od]);nm=M.Machine([nd])
        for gather in(1560,1566,1567,1568,1569,1570):
          for (slot,r),(nslot,q)in zip(IR.expand(source[gather][1],source[gather][2]),IR.expand(lowered[gather-1559][1],lowered[gather-1559][2])):
            om.cur=r;nm.cur=q
            oa=om.eff(r.desc['A'],od,0)[0];na=nm.eff(q.desc['A'],nd,0)[0]
            assert old[oa]==new[na],'indexed gather differs';compared+=1
        for index in range(1559,1591):
            r,x=source[index][1:3];q,y=lowered[index-1559][1:3]
            if x and x.rsel:continue
            original=IR.expand(r,x);relocated=IR.expand(q,y)
            assert len(original)==len(relocated)
            for (slot,o),(nslot,n)in zip(original,relocated):
                assert slot==nslot
                expected=copy.deepcopy(o)
                for d in expected.desc.values():
                    if d.space=='VM':d.base=T(d.base)
                if(expected.unit,expected.op)==('CTL','LOOP'):expected.imm_a=T(expected.imm_a)
                assert vars(expected)==vars(n),'static arithmetic fields differ'
        for L in range(len(u)):
            for index in(1562,1563,1586):
                r,x=source[index][1:3];q,y=lowered[index-1559][1:3]
                a=IR.expand(r,x,old,L);b=IR.expand(q,y,new,L)
                assert len(a)==len(b)
                for(slot,orig),(nslot,rel)in zip(a,b):
                    assert slot==nslot
                    for k,d in orig.desc.items():
                        expected_base=T(d.base)if d.space=='VM'else d.base
                        assert rel.desc[k].base==expected_base,'rsel row/expert output mapping differs'
                        check=copy.deepcopy(rel.desc[k]);check.base=d.base;assert vars(check)==vars(d)
                        if d.space=='VM':assert 0<=rel.desc[k].base<262144
                        if d.space=='HBM'and d.indexed:
                            # I+L lookup is implicit in the real HGI engine.
                            origid=int(old[orig.desc['I'].base+L]);relid=int(new[rel.desc['I'].base+L]);assert origid==relid==u[L]
                            assert d.base+origid*d.dyn_mul==rel.desc[k].base+relid*rel.desc[k].dyn_mul
                        compared+=1
    return compared

n=check(blob);controls=[]
for label,mutate in [('union_pitch',lambda r,x:setattr(r[0][1],'imm_b',6)),('count_pointer',lambda r,x:setattr(r[2][1],'imm_a',r[2][1].imm_a+1)),('plan_pointer',lambda r,x:setattr(r[3][2],'rtab',r[3][2].rtab+32)),('expert_output_mask',lambda r,x:setattr(r[3][2],'emask',0)),('indexed_base',lambda r,x:setattr(r[1][1].desc['A'],'base',r[1][1].desc['A'].base+1))]:
    rec=IC.decode_all(blob);mutate(rec,None);bad=b''.join(IR.encode(r,x)for _,r,x,_ in rec)
    try:check(bad)
    except(AssertionError,ValueError,IndexError,IR.RangeFault,M.Fault):controls.append(label)
    else:raise AssertionError('mutant escaped: '+label)
print(json.dumps(dict(profiles=len(profiles),compared=n,high_water_words=packet['high_water_words'],controls=controls,numerical_matvec=False,whole_programme_executable=False)))

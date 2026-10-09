#!/usr/bin/env python3
"""Minimum metadata/host protocol gate; deliberately no arithmetic/RTL claim."""
import argparse,copy,json,tempfile
from pathlib import Path
import qwen_r25_native_bridge as B
import qwen_r25_decode_program as D

def gate(rom,dispatcher,provider):
    c=B.install(rom,dispatcher,provider);cases=[]
    def check(name,fn):fn();cases.append(dict(name=name,verdict='PASS'))
    def reject(name,fn):
        try:fn()
        except (ValueError,RuntimeError):cases.append(dict(name=name,verdict='MUTANT_REJECTED'));return
        raise AssertionError('accepted '+name)
    def ranges():
        expected={'prenorm':(0,4),'qknorm':(4,6),'rope':(10,6),'round_q':(16,1),'swiglu':(17,2),'softmax':(19,23)}
        for k,(pc,count) in expected.items():
            x=B.descriptor(c,k);assert (x['ROM_PC'],x['ROM_count'])==(pc,count)
        assert sum(count for _,count in expected.values())==42
    check('all actual ROM graph ranges cover 42 slots',ranges)
    def identities():
        for token in (0,131071,131072,151935):
            for position in (0,8191,8194,8223):
                r=B.launch(c,'softmax',token=token,position=position,job=0xffffffff,generation=15)
                o=r['launch_owner'];assert o&0xffffffff==0xffffffff and (o>>32)&15==15
                assert (o>>36)&((1<<18)-1)==token and o>>54==position
        r=B.launch(c,'softmax',token=151935,position=8191,job=73,generation=4,queries=4)
        assert r['launch_count']==23 and r['launch_queries']==4
    check('OWNER74 boundary tokens and query tails',identities)
    args=dict(token=151935,position=8191,job=73,generation=4,queries=4)
    for field,bad in [('token',151936),('token',-1),('job',1<<32),('generation',16),('position',8221),('queries',3)]:
        reject('invalid '+field+' '+str(bad),lambda field=field,bad=bad:B.launch(c,'softmax',**dict(args,**{field:bad})))
    reject('unresolved ME',lambda:B.descriptor(c,'qkv'))
    def registry():
        p={'batches':[{'name':'L0','operations':[dict(kernel=k,unit='SU' if k in B.ALIASES else 'SM',production_entry=None) for k in list(B.ALIASES)+['qkv']]}]}
        x=B.resolve(p,c);assert x['missing_production_entries']==['qkv'] and not x['full_decode_executable']
        assert p['batches'][0]['operations'][0]['production_entry'] is None
        reject('native ROM PC cannot be emitted as SM launch',lambda:D.link(x,{'prenorm':dict(unit='SU',production_dispatch=True,kernel_sha256='pin',entry_pc=0,sm_mask=1)}))
    check('resolved SU registry keeps unresolved graph failclosed',registry)
    class Pins:
        def __init__(self,mutation=None):self.mutation=mutation;self.t=0;self.drives=[]
        def snapshot(self):return dict(fault=self.mutation=='fault',launch_rdy=self.t>=3,finished_v=self.t>=6 or self.mutation=='stale')
        def stage_query(self,contract,kernel,request):
            if self.t<1:return None
            x=dict(owner=request['launch_owner'],queries=request['launch_queries'],visibility_checked=True,exclusive_dispatch=True,query_gate_installed=True)
            if self.mutation=='owner':x['owner']^=1<<32
            if self.mutation=='visibility':x['visibility_checked']=False
            if self.mutation=='query_gate':x['query_gate_installed']=False
            if self.mutation=='boolean':return True
            return x
        def drive(self,p):self.drives.append(p)
        def tick(self):self.t+=1
    def run(mutation=None):
        pins=Pins(mutation);h=B.NativeSUHost(pins,c,'softmax',**args)
        for _ in range(9):
            if h.step()=='DONE':break
        assert h.state=='DONE'
        held=[p for p in pins.drives if p['launch_v']]
        assert len(held)==2 and held[0]==held[1]
        assert pins.drives[-1]['finished_rdy']==1
    check('host holds actual launch under backpressure',run)
    for m in ('owner','visibility','query_gate','boolean','fault','stale'):reject('host '+m,lambda m=m:run(m))
    with tempfile.TemporaryDirectory() as tmp:
        dest=Path(tmp)
        for f in Path(rom).iterdir():
            if f.is_file():(dest/f.name).write_bytes(f.read_bytes())
        (dest/'Q2.hex').write_text('0\n'+(dest/'Q2.hex').read_text().split('\n',1)[1])
        reject('corrupted installed ROM',lambda:B.install(dest,dispatcher,provider))
    return dict(verdict='PASS',cases=cases,actual_quarter_RTL=False,full_decode_executable=False,physical_qualification=False,
                source_pins=c['source_pins'],ROM_sha256=c['ROM_sha256'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--dispatcher',type=Path,required=True);p.add_argument('--provider',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=gate(a.rom,a.dispatcher,a.provider);a.out.write_text(json.dumps(result,indent=2)+'\n');print('PASS',len(result['cases']),'metadata/protocol cases; no actual RTL arithmetic claim')
if __name__=='__main__':main()

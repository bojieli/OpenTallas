#!/usr/bin/env python3
"""Model-only variants of the credit17 Qwen ROM KV calendar (no repo writes).
Usage: run_variants.py <variant> <out.json>
variants: baseline | strict_refab | ecc | ecc_strict_refab | strict_refpb | ecc_strict_refpb
"""
import sys, json, math, time
from fractions import Fraction
WT='/tmp/claude-protref-wt'
sys.path.insert(0, WT+'/tools')
import uarch_model_qwen_kv_credit17 as M
A=M.A; S=A.S
variant=sys.argv[1]; out=sys.argv[2]
ECC='ecc' in variant
LOW='ecclow' in variant
# ECC latency edits (service edges at 1 GHz = 1000 ps; stream period 2500/3 ps)
ECC_EDITS={
 # return chain: +1 encode at raw capture, +1 SECDED check on return RAM/spill read, +1 check on context-bank read in lookup
 'col+25000+3000+2000+12000+link':'col+25000+4000+3000+13000+link',
 # request chain: +1 encode at request-RAM write, +1 check on request-RAM read before command
 'clock+3000+link+10000':'clock+3000+link+12000',
 # assembly pool: +1 stream period encode on quarter write, +1 check on pool read before tile fill
 'fill[lane]=max(fill[lane],at+4*period)+period':'fill[lane]=max(fill[lane],at+6*period)+period',
}
if LOW:
    ECC_EDITS={'col+25000+3000+2000+12000+link':'col+25000+3000+3000+12000+link','fill[lane]=max(fill[lane],at+4*period)+period':'fill[lane]=max(fill[lane],at+5*period)+period'}
if ECC:
    cal=M.cal
    for o,n in ECC_EDITS.items():
        if o not in cal: raise SystemExit('anchor missing '+o)
        cal=cal.replace(o,n)
    ns=dict(A.__dict__); exec(cal,ns); M.credit17_calendar=ns['credit17_calendar']

REFI=3900; RFC=350; RFCPB=200; NB=32
class Strict(S.PCService):
    """REFab issued at its due edge (bounded only by command-path legality), not at next arrival."""
    def __init__(self):
        super().__init__(); self.refs_issued=Counter_()
    def column(self,layer,st,sector,write,arrival_ps):
        pc=S.pc_of(sector); s=self.state(st,pc)
        now=math.ceil(arrival_ps/1000)
        while now>=s['nextref']:
            due=s['nextref']; e=due
            if any(s['opened']):
                pre=self.command(st,pc,'PREALL',max([due]+[s['pre'][b] for b in range(32) if s['opened'][b]]),sector)
                s['opened']=[False]*32; s['actok']=[max(v,pre+17) for v in s['actok']]; e=pre+17
            ref=self.command(st,pc,'REF',max(e,s['lastcol']+2,s['refblock']),sector)
            self.max_refresh_lateness=max(self.max_refresh_lateness,ref-due)
            s['nextref']+=REFI; s['refblock']=ref+RFC; s['actok']=[max(v,ref+RFC) for v in s['actok']]
        return super().column(layer,st,sector,write,arrival_ps)

class StrictPB(S.PCService):
    """Per-bank refresh: each bank refreshed once per tREFI (staggered tREFI/32 within the PC), tRFCpb=200,
    bank must be precharged; other banks keep serving. Issued at due edge (strict)."""
    def state(self,st,pc):
        new=(st,pc) not in self.states
        s=super().state(st,pc)
        if new:
            base=3900+(3900*pc)//32
            s['nextpb']=[base+(REFI*b)//NB for b in range(NB)]
            s['nextref']=10**15  # disable REFab
        return s
    def column(self,layer,st,sector,write,arrival_ps):
        pc=S.pc_of(sector); s=self.state(st,pc)
        now=math.ceil(arrival_ps/1000)
        while True:
            b=min(range(NB),key=lambda i:s['nextpb'][i]); due=s['nextpb'][b]
            if due>now: break
            e=due
            if s['opened'][b]:
                pre=self.command(st,pc,'PRE',max(due,s['pre'][b]),sector)
                s['opened'][b]=False; s['actok'][b]=max(s['actok'][b],pre+17); e=pre+17
            ref=self.command(st,pc,'REFPB',max(e,s['actok'][b]),sector)
            self.max_refresh_lateness=max(self.max_refresh_lateness,ref-due)
            s['actok'][b]=max(s['actok'][b],ref+RFCPB); s['nextpb'][b]+=REFI
        return super().column(layer,st,sector,write,arrival_ps)

from collections import Counter as Counter_
if 'strict_refab' in variant: S.PCService=Strict
elif 'strict_refpb' in variant: S.PCService=StrictPB
captured={}
Orig=S.PCService
class Cap(Orig):
    def __init__(self):
        super().__init__(); captured['svc']=self
S.PCService=Cap
t0=time.time()
r=M.build()
svc=captured['svc']
# end-of-token refresh debt: REFab (or REFpb) due before token end but never issued
end_edge=math.ceil(r['calendar']['total_conditional_s']*1e12/1000)
debt=0; debt_pb=0
for st in range(4):
    for pc in range(32):
        s=svc.state(st,pc)
        if 'nextpb' in s:
            for v in s['nextpb']:
                if v<=end_edge: debt_pb+=1+(end_edge-v)//REFI
        elif s['nextref']<=end_edge: debt+=1+(end_edge-s['nextref'])//REFI
res=dict(variant=variant,runtime_s=time.time()-t0,total_conditional_s=r['calendar']['total_conditional_s'],
    margin_to_3k_s=r['calendar']['margin_to_3k_s'],conditional_rate_gain_fraction=r['calendar']['conditional_rate_gain_fraction'],
    command_counts=r['controller']['command_counts'],max_refresh_lateness_edges=svc.max_refresh_lateness,
    end_edge=end_edge,unissued_REFab_due_before_token_end=debt,unissued_REFpb_due_before_token_end=debt_pb,
    rows=[{k:x[k] for k in ('layer','begin_ps','fill_ready_ps','all_grants_ps','compute_done_ps')} for x in r['calendar']['rows']],
    ecc_edits=ECC_EDITS if ECC else None)
json.dump(res,open(out,'w'),indent=1)
print(json.dumps({k:v for k,v in res.items() if k!='rows'}))

#!/usr/bin/env python3
"""Whole-service transport fixture for three safe mode-only class programmes.

Run only on admitted fleet, after selected executable chronology acceptance.
No arithmetic qualification; no result-producing command is offered.
"""
from pathlib import Path
import argparse,json,subprocess
import smb_unit as S
from hbm_svc_packed136_image import sector_address

def compile_fixture(mutation=''):
    store=S.Store(0);programmes=[]
    modes=(0,3,0) if mutation=='invalid_mode' else (0,4,0)
    for mode in modes:
        cmd=(0xa2<<184)|(mode<<181)
        programmes.append(store.add([S.svg_word(cmd & ((1<<83)-1),None,retire=True)],[cmd>>83]))
    if mutation=='command_class':
        # Preserve positive storage allocation and every descriptor; flip only
        # command mode[2] atXC programme bit100 (assembled bit183).
        store.xc[programmes[1][0]] ^= 1<<100
    ing=[];t=10
    for addr in range(store.top):
        for target,word,width in ((S.SVG_TGT,store.svg[addr],135),(S.XC_TGT,store.xc[addr],173)):
            ing.append((t,S.ingress(cfg=(((0 if addr<1024 else 2)<<10)|(addr&1023),S.prog_row(addr,word,width)),target=target)));t+=1
    dt=t;arm=dt+2*len(modes)+8;launch=arm+2;rc0=launch+S.OFF
    mem={};gos=(1000,1100,1200)
    for i,(mode,(pb,pl),go) in enumerate(zip(modes,programmes,gos)):
        metadata_mode=mode
        d=S.desc_row(i,row_base=i*8,landing=i,epoch=i+1,rows=1,tag_base=0,prog_base=pb,prog_limit=pl,go_at=go,row_off=0,loops=1,lstep=0,mode=metadata_mode,mrel=0,fl=0)
        for j,target in enumerate((S.SVG_TGT,S.XC_TGT)):
            # Mutate only SVG metadata so the real assembled-command guard,
            # rather than the earlier XC-local class guard, must reject it.
            target_d=d^((1<<197) if mutation=='descriptor_class' and i==1 and target==S.SVG_TGT else 0)
            ing.append((dt+2*i+j,S.ingress(cfg=((1<<10)|i,target_d),target=target)))
        alloc=dict(pcs=[0,1,2,3],row_base=i,stack_bytes=1<<35)
        for offset in range(8):
            address=sector_address(offset,alloc);assert address not in mem;mem[address]=0
    for j,target in enumerate((S.SVG_TGT,S.XC_TGT)):
        ing.append((arm+j,S.ingress(desc=(0,3,1),target=target)))
    ing.append((launch,S.ingress(launch=True)));ing.sort()
    return dict(ing=ing,xw=[],ids=[],mem=mem,n_end=rc0+gos[-1]+256),[(p[0],g) for p,g in zip(programmes,gos)],dict(literal_modes=(0,0,0) if mutation=='command_class' else modes,metadata_modes=modes,distinct_programmes=len(store.progs),resident_words=store.top,descriptors=3,sectors=24,launch=launch,run_origin=rc0,mutation_target=('SVG descriptor197 only; XC and literal commands unchanged' if mutation=='descriptor_class' else 'XC programme commandmode2 only; both descriptors and allocation unchanged' if mutation=='command_class' else 'Middle literal and both metadata modes3 with matched class0; globally invalid, no class mismatch' if mutation=='invalid_mode' else None))

def main():
    p=argparse.ArgumentParser();p.add_argument('--work',required=True);p.add_argument('--exe');p.add_argument('--out',required=True);p.add_argument('--service-build-revision',required=True);p.add_argument('--mut',choices=['','descriptor_class','command_class','invalid_mode'],default='');a=p.parse_args()
    c,expected,budget=compile_fixture(a.mut);work=Path(a.work).resolve();work.mkdir(parents=True,exist_ok=True);counts=S.write_events(c,work)
    report=dict(mutation=a.mut,budget=budget,expected_go=expected,event_sha256={p.name:S.sha(p) for p in work.glob('*.hex')},service_build_revision=a.service_build_revision,compiler_sha256=S.sha(Path(__file__)),scope='three mode-only drained programmes; actual transport qualification only, no arithmetic or general stateful splitting proof')
    if a.exe:
        exe=Path(a.exe).resolve();r=subprocess.run([str(exe),*(f'+{k}={work}/{v}.hex' for k,v in [('ING','ing'),('XW','xw'),('IDS','ids'),('MEM','mem')]),*(f'+{k}={v}' for k,v in counts.items())],capture_output=True,text=True,cwd=work)
        log=r.stdout+r.stderr;(work/'run.log').write_text(log);results,gos,runs,fault,done=S.parse(log)
        exact=[(g[1],g[2]) for g in gos]==expected
        positive=r.returncode==0 and exact and bool(done) and not fault and not results and len(runs)==1
        first_fault=next((line for line in log.splitlines() if line.startswith('FAULT ')),None)
        assembled_class_causal=bool(a.mut in ('descriptor_class','command_class') and first_fault and first_fault.startswith('FAULT svg ') and 'issuer 0 feed 0 ' in first_fault)
        invalid_mode_causal=bool(a.mut=='invalid_mode' and first_fault and any(first_fault.startswith('FAULT '+scope+' ') for scope in ['svg','xc','sm_arith','sm_schedule']))
        report.update(first_fault=first_fault,assembled_class_causal=assembled_class_causal,invalid_mode_causal=invalid_mode_causal,pass_=positive,rc=r.returncode,go_exact=exact,go_count=len(gos),done=done,fault=fault,run_count=len(runs),sm_results=len(results),executable_sha256=S.sha(exe),negative_causal_review_required=bool(a.mut))
    Path(a.out).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    if a.exe:raise SystemExit(0 if report['pass_'] else 1)
if __name__=='__main__':main()

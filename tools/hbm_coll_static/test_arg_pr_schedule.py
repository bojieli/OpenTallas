#!/usr/bin/env python3
"""Actual ARG compiler receipt against the proven +1 source publication contract.
Checks packed/unrolled capture+delivery edges, default bytes, and stale capture.
This is a compiler gate; native caller adoption remains a separate obligation.
"""
import importlib.util,json,subprocess,sys,types
from pathlib import Path
import argmax_rows as A

ROOT=Path(__file__).resolve().parents[2]

def load_baseline():
    src=subprocess.check_output(['git','show','5df2380a1e:tools/hbm_coll_static/argmax_rows.py'],cwd=ROOT,text=True)
    m=types.ModuleType('argmax_before');m.__file__=str(ROOT/'tools/hbm_coll_static/argmax_rows.py');exec(compile(src,m.__file__,'exec'),m.__dict__);return m

def configure(m,rows,vm,pr):
    m.set_rows(rows);m.set_npt(2);m.START_O=-1;m.LIDS.clear()
    if hasattr(m,'set_arg_pr_source'):m.set_arg_pr_source(pr)
    m.set_vm_rt(vm)

def events(m,words,meta):
    fields=json.loads(m.LAYOUT.read_text())['fields'];pc=0;counter={};cycle=0;out=[]
    while True:
        w=words[pc];md=m.dec_meta(meta[pc]);it=counter.get(md['lid'],0)
        def f(name):
            q=fields[name];return(w>>q['lsb'])&((1<<q['width'])-1)
        out.append((cycle,f('capture_arg'),(f('sink_slot')>>m.NPT)&1,(f('ar_high')>>(50-31))&1))
        if md['halt']:return out
        if md['count'] and it<md['count']-1:counter[md['lid']]=it+1;pc=md['target']
        else:
            if md['count']:counter[md['lid']]=0
            pc=md['next']
        cycle+=1
        if cycle>100000:raise AssertionError('unbounded programme')

def validate_source_receipt(ev,P,vm,extra):
    captures=[c for c,a,_,_ in ev if a]
    deliveries=[c for c,_,d,_ in ev if d]
    assert captures==[12+vm+32*p+32+extra for p in range(P)],('capture',captures)
    assert deliveries==[12+vm+32*p+33+extra for p in range(P)],('delivery',deliveries)


def main():
    old=load_baseline();receipt=[]
    for P,vm,rows in [(1,0,128),(6,0,128),(6,74,256),(96,0,128)]:
        configure(old,rows,vm,False);ow,om,oi=old.compile_program(0,P)
        configure(A,rows,vm,False);bw,bm,bi=A.compile_program(0,P)
        assert (ow,om,oi)==(bw,bm,bi),'default byte regression'
        configure(A,rows,vm,True);nw,nm,ni=A.compile_program(0,P)
        ne=events(A,nw,nm);oe=events(A,ow,om)
        validate_source_receipt(ne,P,vm,1)
        assert [c for c,_,_,pub in ne if pub]==[c for c,_,_,pub in oe if pub],'engine publication commands moved'
        assert ni['II']==oi['II']==32 and ni['halt']==oi['halt']+1 and ni['last_delivery']==oi['last_delivery']+1
        try:validate_source_receipt(oe,P,vm,1)
        except AssertionError:pass
        else:raise AssertionError('stale capture mutant survived')
        receipt.append(dict(P=P,vm_rt=vm,issuer_rows=rows,packed_rows=ni['rows'],II=32,source_capture_extra=1,last_delivery_extra=1,old_capture_mutant='REJECTED',default_bytes='IDENTICAL'))
    configure(old,64,0,False);default_old=old.compile_program(0,6)
    configure(A,64,0,False);assert A.compile_program(0,6)==default_old,'default64 bytes changed' 
    try:configure(A,64,0,True)
    except SystemExit as e:capacity=str(e)
    else:raise AssertionError('66 rows silently fit64')
    print(json.dumps(dict(status='COMPILER_PASS_NOT_NATIVE_ADOPTION',profiles=receipt,capacity_negative=capacity),indent=2))
if __name__=='__main__':main()

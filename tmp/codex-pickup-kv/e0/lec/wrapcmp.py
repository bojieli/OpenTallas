#!/usr/bin/env python3
"""Structural equivalence of two leaf-instance wrappers (leaves = blackboxes, params part of identity).
Instances matched by canonical signature, internal nets named by (driver signature, port, bit)."""
import json, subprocess, sys, os, tempfile, collections, hashlib
H=lambda x: hashlib.sha256(repr(x).encode()).hexdigest()[:16]
def load(wrap, leaves, top, ws):
    j=os.path.join(ws, os.path.basename(wrap)+'.json')
    ys=''.join(f'read_verilog -sv -lib {l}\n' for l in leaves)+f'read_verilog -sv {wrap}\nhierarchy -top {top}\nproc\nopt_clean\nwrite_json {j}\n'
    r=subprocess.run(['yosys','-q','-p',ys.replace('\n','; ')],capture_output=True,text=True)
    if r.returncode: sys.exit(r.stderr[-3000:])
    d=json.load(open(j)); m=d['modules'][top]
    dirs={n:{p:v['direction'] for p,v in mm['ports'].items()} for n,mm in d['modules'].items() if n!=top}
    bit2top={}
    for p,v in m['ports'].items():
        for i,b in enumerate(v['bits']): bit2top[b]=(v['direction'],p,i)
    cells={}
    for cn,c in m['cells'].items():
        ty=c['type'];
        prm=tuple(sorted((k,int(v,2) if set(v)<=set('01') else v) for k,v in c.get('parameters',{}).items()))
        cells[cn]=(ty,prm,c['connections'],dirs.get(ty) or c.get('port_directions',{}))
    return m,bit2top,cells
def canon(m,bit2top,cells):
    # signature by top-port connections
    def sig0(cn):
        ty,prm,con,dr=cells[cn]
        return (ty,prm,tuple(sorted((p,i,bit2top[b][1],bit2top[b][2]) for p,bs in con.items() for i,b in enumerate(bs) if b in bit2top)))
    sig={cn:sig0(cn) for cn in cells}
    for _ in range(6):
        if len(set(sig.values()))==len(sig): break
        d0={}
        for cn,(ty,prm,con,dr) in cells.items():
            for p,bs in con.items():
                if dr.get(p)=='output':
                    for i,b in enumerate(bs):
                        if isinstance(b,int): d0[b]=(sig[cn],p,i)
        rd=collections.defaultdict(list)
        for cn,(ty,prm,con,dr) in cells.items():
            for p,bs in con.items():
                if dr.get(p)!='output':
                    for i,b in enumerate(bs):
                        if isinstance(b,int): rd[b].append((sig[cn],p,i))
        ns={}
        for cn,(ty,prm,con,dr) in cells.items():
            ins=tuple(sorted((p,i,repr(d0.get(b))) for p,bs in con.items() if dr.get(p)!='output' for i,b in enumerate(bs) if isinstance(b,int) and b in d0))
            outs=tuple(sorted((p,i,repr(sorted(rd.get(b,[])))) for p,bs in con.items() if dr.get(p)=='output' for i,b in enumerate(bs) if isinstance(b,int)))
            ns[cn]=(sig[cn][0],sig[cn][1],H((sig[cn],ins,outs)))
        sig=ns
    if len(set(sig.values()))!=len(sig): sys.exit('ambiguous instance signature')
    drv={}
    for cn,(ty,prm,con,dr) in cells.items():
        for p,bs in con.items():
            if dr.get(p)=='output':
                for i,b in enumerate(bs):
                    if isinstance(b,int): drv[b]=(sig[cn],p,i)
    def name(b):
        if isinstance(b,str): return ('const',b)
        if b in bit2top and bit2top[b][0]=='input': return ('in',)+bit2top[b][1:]
        if b in drv: return ('drv',)+drv[b]
        return ('undriven',b in bit2top)
    out={}
    for cn,(ty,prm,con,dr) in cells.items():
        out[sig[cn]]={p:[name(b) for b in bs] for p,bs in con.items() if dr.get(p)!='output'}
    outs={}
    for p,v in m['ports'].items():
        if v['direction']=='output': outs[p]=[name(b) for b in v['bits']]
    ins={p:len(v['bits']) for p,v in m['ports'].items() if v['direction']=='input'}
    return out,outs,ins,{s[0]+str(dict(s[1])) for s in sig.values()}
a,b,top=sys.argv[1],sys.argv[2],sys.argv[3]; leaves=sys.argv[4:]
ws=tempfile.mkdtemp()
A=canon(*load(a,leaves,top,ws)); B=canon(*load(b,leaves,top,ws))
rep={'gold':a,'gate':b,'instances':sorted(A[3]),'instances_gate':sorted(B[3])}
rep['inst_set_equal']=A[3]==B[3]
diff=[]
for k in set(A[0])|set(B[0]):
    if A[0].get(k)!=B[0].get(k): diff.append(('inst_inputs',k[0]))
for p in set(A[1])|set(B[1]):
    if A[1].get(p)!=B[1].get(p): diff.append(('out',p))
rep['input_ports_only_gold']=sorted(set(A[2])-set(B[2])); rep['input_ports_only_gate']=sorted(set(B[2])-set(A[2]))
# extra input ports must be unused (no cell reads them)
used=lambda C: {n[1] for d in C[0].values() for bits in d.values() for n in bits if n[0]=='in'}|{n[1] for bits in C[1].values() for n in bits if n[0]=='in'}
rep['extra_inputs_used']=sorted((set(A[2])^set(B[2]))&(used(A)|used(B)))
rep['diffs']=diff[:50]; rep['n_diffs']=len(diff)
rep['verdict']='EQUIVALENT' if rep['inst_set_equal'] and not diff and not rep['extra_inputs_used'] else 'DIFFERENT'
print(json.dumps(rep,indent=1))

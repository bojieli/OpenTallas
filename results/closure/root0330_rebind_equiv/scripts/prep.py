import json,sys,subprocess,re,shlex,os
WT='/home/ubuntu/wt/root-0330-eqv'
CH={'ot_hbm_svc_stack_fault.sv':'rtl/hbm_accel/loader/service_native/ot_hbm_svc_stack_fault.sv',
    'ot_hbm_svc_wb_cutthrough_cdc.sv':'rtl/hbm_accel/loader/service_native/ot_hbm_svc_wb_cutthrough_cdc.sv',
    'qkd_pvw_die_t.sv':'rtl/qwen_sys/split_20261014/qkd_pvw_die_t.sv'}
NEWC='f722b4bbe'
def cat(blob): return subprocess.run(['git','-C',WT,'cat-file','blob',blob],capture_output=True,check=True).stdout
def rev(c,p): return subprocess.run(['git','-C',WT,'rev-parse',f'{c}:{p}'],capture_output=True,text=True).stdout.strip()
out={}
for t in open('/home/ubuntu/wt/root-0330-eqv.tiles').read().split():
    g=json.load(open(f'{WT}/physical/ref_tile/{t}/gate_result.json'))
    by={e['path']:e for e in g['source_binding']['files']}
    kpath=f'physical/ref_tile/{t}/kit.env'
    kit=cat(by[kpath]['git_blob']).decode()
    m=re.search(r"^SRCS='([^']*)'",kit,re.M); srcs=m.group(1).split()
    top=re.search(r'^TOP=(\S+)',kit,re.M).group(1)
    pm=re.search(r'^PARAMS=\((.*)\)',kit,re.M); ptok=shlex.split(pm.group(1)) if pm else []
    params=[ptok[i+1] for i in range(len(ptok)) if ptok[i]=='--param']
    defs=re.findall(r'^(?:DEFINES|VERILOG_DEFINES)=(.*)$',kit,re.M)
    d=f'/home/ubuntu/wt/r0330_scratch/kits/{t}'
    os.makedirs(d+'/src',exist_ok=True)
    rec={'tile':t,'top':top,'params':params,'kit_defines':defs,'kit_env_blob':by[kpath]['git_blob'],'srcs':[], 'changed':[]}
    texts=[]
    for i,s in enumerate(srcs):
        b=by[s]['git_blob']; data=cat(b); texts.append(data.decode(errors='replace'))
        fn=f'{i:02d}_'+os.path.basename(s); open(f'{d}/src/{fn}','wb').write(data)
        rec['srcs'].append({'path':s,'gate_git_blob':b,'file':fn})
    alltext='\n'.join(texts)
    for k,p in CH.items():
        if p not in by: continue
        ob=by[p]['git_blob']; nb=rev(NEWC,p)
        os.makedirs(d+'/old',exist_ok=True); os.makedirs(d+'/new',exist_ok=True)
        open(f'{d}/old/{k}','wb').write(cat(ob)); open(f'{d}/new/{k}','wb').write(cat(nb))
        mods=re.findall(r'^\s*module\s+(\w+)',cat(nb).decode()+cat(ob).decode(),re.M)
        rec['changed'].append({'path':p,'gate_git_blob':ob,'new_git_blob':nb,'in_srcs':p in srcs,
            'included_by_srcs':bool(re.search(r'`include\s+"[^"]*'+re.escape(k),alltext)),
            'modules':sorted(set(mods)),'modules_named_in_srcs':sorted(m for m in set(mods) if re.search(r'\b'+m+r'\b',alltext))})
    out[t]=rec
    print(t,top,params,defs,len(srcs),[(c['path'].split('/')[-1],c['in_srcs'],c['included_by_srcs'],c['modules_named_in_srcs'],c['gate_git_blob'][:7]) for c in rec['changed']])
json.dump(out,open('/home/ubuntu/wt/r0330_scratch/kits/index.json','w'),indent=1)
# --- includes: copy gate-bound blobs of `include files next to the sources (same basename)
for t,rec in out.items():
    g=json.load(open(f'{WT}/physical/ref_tile/{t}/gate_result.json'))
    by={e['path']:e for e in g['source_binding']['files']}
    d=f'/home/ubuntu/wt/r0330_scratch/kits/{t}'
    rec['includes']=[]
    todo=[s['path'] for s in rec['srcs']]; seen=set()
    while todo:
        p=todo.pop()
        if p in seen: continue
        seen.add(p)
        txt=cat(by[p]['git_blob']).decode(errors='replace')
        for inc in re.findall(r'^\s*`include\s+"([^"]+)"',txt,re.M):
            cand=os.path.normpath(os.path.join(os.path.dirname(p),inc))
            if cand not in by: cand=next((f for f in by if f.endswith('/'+inc)),None)
            if not cand: print('UNRESOLVED include',t,inc); continue
            os.makedirs(d+'/inc',exist_ok=True); open(f'{d}/inc/{os.path.basename(inc)}','wb').write(cat(by[cand]['git_blob']))
            rec['includes'].append({'path':cand,'gate_git_blob':by[cand]['git_blob']}); todo.append(cand)
json.dump(out,open('/home/ubuntu/wt/r0330_scratch/kits/index.json','w'),indent=1)
for t,rec in out.items():
    if rec['includes']: print(t,'includes',[i['path'] for i in rec['includes']])

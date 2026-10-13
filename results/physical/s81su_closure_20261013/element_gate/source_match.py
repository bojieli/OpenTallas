import json,subprocess,hashlib,re,sys
R='/home/ubuntu/OpenTallas'
def git(*a):
    r=subprocess.run(['git','-C',R,*a],capture_output=True)
    return r.stdout if r.returncode==0 else None
def blob(c,p):
    o=git('rev-parse',f'{c}:{p}'); return o.decode().strip() if o else None
def sha(c,p):
    o=git('show',f'{c}:{p}'); return hashlib.sha256(o).hexdigest() if o is not None else None
GATE='b132ae0da'
gj=json.loads(git('show','origin/codex/s81su-physical-20261013:results/physical/s81su_closure_20261013/smt_qualification/full_gate/run_full_dpi_m0_a0_h.json'))
gsha=gj['source_sha256']
TILES=[('smt','s81su_smt_hb1_ref','ab43f2fe0'),('smt','s81su_smt_hb2_ref','ab43f2fe0'),('swe','s81su_swe_spx_ref','1ec43dde7'),('swe','s81su_swe_gfix_ref','1065bcb90'),
('qnt','s81su_qnt_cb32_ref','c904b01fb'),('qne','s81su_qne_ref','8946ebc79'),('qnh','s81su_qnh_ref','8946ebc79'),('qnr','s81su_qnr_ref','8946ebc79'),('qnh','s81su_qnh_ref','46d62c427'),('qnr','s81su_qnr_ref','46d62c427'),
('kve','s81su_kve_ref','00167e741'),('kvp','s81su_kvp_ref','00167e741'),('kvr','s81su_kvr_ref','00167e741'),
('smc','s81su_smc_ref','47c31b637'),('smd','s81su_smd_ref','47c31b637'),('sml','s81su_sml_ref','47c31b637'),('smr','s81su_smr_ref','47c31b637'),('ctl','s81su_ctl_ref','cbafa4c7a')]
out=[]
for t,kit,c in TILES:
    sp=git('show',f'{c}:physical/ref_tile/{kit}/spec.json')
    if sp is None: print(t,kit,c,'NO SPEC'); continue
    sp=json.loads(sp)
    srcs=sp.get('rtl') or sp.get('sources') or sp.get('verilog')
    if srcs is None:
        print('keys',list(sp.keys())); srcs=[]
    srcs=[s for s in srcs if isinstance(s,str)]
    row=dict(tile='dsfd_su_t_'+t,kit=kit,routed_commit=c,top=sp.get('top') or sp.get('block'),params=sp.get('params') or sp.get('parameters') or sp.get('defparams'),files=[])
    for p in srcs:
        s_r=sha(c,p); b_r=blob(c,p); b_g=blob(GATE,p)
        row['files'].append(dict(path=p,sha256_routed=s_r,equal_gate_commit=(b_r==b_g and b_r is not None),in_gate_build=(p in gsha),gate_build_sha_equal=(gsha.get(p)==s_r) if p in gsha else None))
    out.append(row)
    f=row['files']
    print(t,kit,c,'top',row['top'],'params',row['params'],'n',len(f),'neq_commit',[x['path'].split('/')[-1] for x in f if not x['equal_gate_commit']],'not_in_gate_build',[x['path'].split('/')[-1] for x in f if not x['in_gate_build']],'gate_sha_neq',[x['path'].split('/')[-1] for x in f if x['gate_build_sha_equal'] is False])
json.dump(out,open('/tmp/s81su_price/srcmatch.json','w'),indent=1)

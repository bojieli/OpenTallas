import argparse,ast,json,hashlib,subprocess,re
from pathlib import Path
root=Path(__file__).resolve().parents[1];p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.work.mkdir(parents=True,exist_ok=True)
if a.out.exists():raise SystemExit('immutable output exists')
# Execute only the immutable launch expansion function: no model/checkpoint
# import, arithmetic simulation or oracle-derived token generation.
original=root/'tools/gpu_sys/v41_dspark.py';tree=ast.parse(original.read_text());fun=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='expand');scope={'B':5,'PMAX':8,'L_NONE':63,'NOISE':129279};exec(compile(ast.Module(body=[fun],type_ignores=[]),str(original),'exec'),scope)
sources=['rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv','rtl/hbm_accel/control/ot_hbm_native_mtp_operation_backend_mx1.sv','rtl/test/hbm_accel/tb_hbm_native_mtp_operation_backend_mx1.sv']
cases=[];vectors=[(0,0,6,1048570,0,0),(0,39,6,524288,0,0),(1,0,6,1048570,0,0),(2,0,6,1048570,0,0),(3,0,5,1048570,0,0),(3,2,5,524288,0,0),(4,0,5,1048570,0,0),(5,4,1,1048575,0,0),(0,0,1,1,0,1),(0,40,1,1,0,0),(3,0,5,1048571,0,0),(6,0,1,1,0,0)]
for n,(op,idx,col,pos,ecc,missing) in enumerate(vectors):
 exe=a.work/f'gate{n}.vvp';params={'OP':op,'IDX':idx,'NCOL':col,'POS':pos,'ECC':ecc,'MISSING':missing}
 b=subprocess.run(['iverilog','-g2012','-s','tb_hbm_native_mtp_operation_backend_mx1',*[f'-Ptb_hbm_native_mtp_operation_backend_mx1.{k}={v}' for k,v in params.items()],'-o',str(exe),*[str(root/s) for s in sources]],capture_output=True,text=True)
 if b.returncode:raise RuntimeError(b.stderr)
 r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
 launches=[(int(k),int(t),int(p),int(pc0),int(pc1)) for k,t,p,pc0,pc1 in re.findall(r'LAUNCH kind=(\d+) token=(\d+) pos=(\d+) pc0=(\d+) pc1=(\d+)',r.stdout)]
 invalid=ecc==2 or missing or op>5 or (op==0 and idx>=40) or (op in (3,4) and pos+6>1048576)
 expected=[]
 if not invalid:
  command=dict(op=('VLAYER','VHEAD','SEED','DSTAGE','DHEAD','MARKOV')[op],idx=idx,ncol=col,pos=pos,tok1=131071,toks=[131071-i for i in range(col)])
  kinds=('swapin','swapout','embed','layer','head','seed','demb','dsa','dsb','dhead','markov')
  expected=[(kinds.index(k),t,p,100*(kinds.index(k)+1),100*(kinds.index(k)+1)+1) for k,t,p in scope['expand'](command)]
 end=re.search(r'COMPLETE fault=(\d+) launches=(\d+)',r.stdout);ok=r.returncode==0 and end and bool(int(end[1]))==bool(invalid) and (invalid or launches==expected)
 cases.append(dict(params=params,verdict='PASS' if ok else 'FAIL',returncode=r.returncode,invalid_rejected=invalid,expected_launches=expected,actual_launches=launches,output=r.stdout))
rec=dict(schema='opentallas.hbm.native_mtp_operation_mx1.rtl.v1',verdict='PASS' if all(c['verdict']=='PASS' for c in cases) else 'FAIL',cases=cases,source_sha256={s:hashlib.sha256((root/s).read_bytes()).hexdigest() for s in sources+[str(original.relative_to(root))]},scope='actual two16SM CP cores; full201 command ordering/widths plainflopentry/code storage MX1 no controlECC/resetepoch; synthetic SM arithmetic completion only; fullshape linked kernels still require source registration')
a.out.write_text(json.dumps(rec,indent=2)+'\n');print(rec['verdict']);raise SystemExit(rec['verdict']!='PASS')

#!/usr/bin/env python3
"""Admitted AR-only real N256/M64 minimum-component gate; no DPI or whole die.
Run under host guard128GiB after prior full-quarter frontend has terminated.
Compiler source d5225192c, arithmetic parent5449dfcc4, plain AR successor must be source-pinned must be in pinned SRC.
"""
import argparse,json,subprocess,sys
from pathlib import Path
SOURCES='''rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv
rtl/hdc/ot_hdc_cg.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_ring.sv
rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv
rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv
rtl/hdc/ot_hdc_fastfp_lat_c12.sv rtl/hdc/ot_hdc_fp32_f12.sv
rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv
rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv
rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/v41x/ot_dsrom_su_f12.sv
rtl/hdc/v41/ot_hdc_fsqrt_c12.sv
rtl/hdc/v41x/ot_hdc_v41x_sfu_c12.sv rtl/hdc/v41x/ot_hdc_v41x_vec_lane_c12.sv
rtl/hdc/v41x/ot_hdc_v41x_vec_side_c12.sv rtl/hdc/v41x/ot_hdc_v41x_vec_red_c12.sv
rtl/hdc/v41x/ot_hdc_v41x_vec_c12.sv
rtl/qwen_r25_su_dispatch/ot_qwen_r25_su_quarter_ar.sv
rtl/qwen_r25_su_dispatch/tb_qwen_r25_su_quarter_ar.sv'''.split()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--prepare-only',action='store_true');a=p.parse_args()
 root=Path(__file__).resolve().parents[1];out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 sys.path.insert(0,str(root/'tools'))
 import qwen_r25_native690 as B
 import qwen_r25_native690_fixture as F
 S,R,C,I=B.load(root/'tools');compiler=B.Compiler(S,R,C,I).build();compiler.write(out/'rom')
 cases=[]
 for stage,queries in [('rmsnorm4096',1),('softmax8x8224',1)]:
  directory=out/stage;directory.mkdir();counts=[]
  mem,_=F.fixture(stage,root/'tools',valid=8192,quarter=0)
  C.write_hex(directory/'VM.hex',mem.vm,32)
  for q in range(queries):
   _,checks=F.fixture(stage,root/'tools',valid=8192+q,quarter=0)
   flat=[]
   for addr,want in checks:
    flat.extend(((addr+j)<<32)|int(word) for j,word in enumerate(want))
   C.write_hex(directory/f'expected{q}.hex',flat,64);counts.append(len(flat))
  assert len(set(counts))==1
  spec=compiler.stages[stage]
  args=[f'+PROGRAM={out}/rom/Q0.hex',f'+META={out}/rom/META.hex',f'+VM={directory}/VM.hex',f'+EXPECTED={directory}/expected',f'+START={spec["pc"]}',f'+NOPS={spec["count"]}',f'+QUERIES={queries}',f'+POSITION=8191',f'+NCHECK={counts[0]}']
  cases.append((stage,args,'PASS_QWEN_NATIVE_QUARTER_AR_REAL_FP'))
 cases.extend([('rms_stalls',cases[0][1]+['+STALL=3'],'PASS_QWEN_NATIVE_QUARTER_AR_REAL_FP'),('foreign_reply',cases[0][1]+['+NEGATIVE=1'],'PASS_QWEN_NATIVE_QUARTER_FOREIGN_REPLY_FENCE')])
 manifest=dict(source_dependencies={'compiler':'d5225192c','arithmetic_parent':'5449dfcc4','selected_AR_source':'pinned launch source manifest'},N=256,M=64,OWNER_W=74,TOKEN18=151935,DPI=False,queries=1,dispatcher=False,query_release=False,control_mirror=False,lease_epoch=False,CP_binding_credit=False,vm_words=262144,CONST0=262143,cases=cases,compile_admission_gib=128,workers=8)
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 if a.prepare_only:return
 cmd=['verilator','--binary','--timing','-Wno-fatal','--top-module','tb_qwen_r25_su_quarter_ar','-I'+str(root/'rtl/test'),'--Mdir',str(out/'obj'),'--output-split','20000','--output-split-cfuncs','20000','-CFLAGS','-O1','-j','8',*[str(root/s) for s in SOURCES]]
 with (out/'build.log').open('w') as f:
  rc=subprocess.call(cmd,cwd=root,stdout=f,stderr=subprocess.STDOUT)
 if rc:
  (out/'build_failed.json').write_text(json.dumps(dict(returncode=rc,manifest=manifest))+'\n');raise SystemExit(rc)
 results=[]
 for name,args,marker in cases:
  log=out/(name+'.log')
  with log.open('w') as f:rc=subprocess.call([str(out/'obj/Vtb_qwen_r25_su_quarter_ar'),*args],stdout=f,stderr=subprocess.STDOUT,cwd=root)
  verdict='PASS' if rc==0 and marker in log.read_text() else 'FAIL'
  rec=dict(name=name,returncode=rc,verdict=verdict,log=log.name);results.append(rec)
  (out/(name+'.json')).write_text(json.dumps(rec,indent=2)+'\n')
  if verdict!='PASS':break
 (out/'verdict.json').write_text(json.dumps(dict(verdict='PASS' if len(results)==len(cases) and all(r['verdict']=='PASS' for r in results) else 'FAIL',manifest=manifest,results=results),indent=2)+'\n')
 if len(results)!=len(cases) or any(r['verdict']!='PASS' for r in results):raise SystemExit(1)
if __name__=='__main__':main()

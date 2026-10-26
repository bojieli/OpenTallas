#!/usr/bin/env python3
"""Exact current VP pin-to-r0c0 store/output mechanism; run via ot-run."""
import argparse,hashlib,json,re,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
RTL=['rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_fp32_f12.sv','rtl/hdc/ot_hdc_prefix.sv','rtl/hdc/ot_hdc_delay.sv','rtl/hdc/v41x/ot_dsrom_su_add6.sv','rtl/hdc/v41x/ot_dsrom_su_hcpost.sv','rtl/hdc/v41x/ot_dsrom_su_hcpost_lane_pr.sv','rtl/lib/ot_rst_relay.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r0c0/ot_sram_1r1w_512x128_m4_r0c0.v','tools/s81_dv/vp_local_1026/tb_vp_local.sv']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--entry-rows',type=Path,required=True);a.add_argument('--params',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a=a.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 image=json.loads(a.entry_rows.read_text()); audit=json.loads(a.params.read_text())
 required=dict(ML=7,AL=6,HPL=33,CS_HI_D=0,CS_HI_GS=0,CS_HO_D=0,CS_HO_GS=0,CS_H_G=4,HQX=0)
 assert len(audit['units'])==80 and all(p==required for p in audit['units'].values())
 assert image['die_sha256']==audit['source_top_sha256']
 rows=[w for w in image['writes'] if w['sid']==0 and w['leaf']==0]
 assert len(rows)==49 and sorted(w['row'] for w in rows)==list(range(32))+list(range(64,80))+[1008]
 (a.out/'selected_rows.json').write_text(json.dumps(dict(source_image_sha256=sha(a.entry_rows),fixture_meta_sha256=image['fixture_meta_sha256'],rows=rows),indent=2)+'\n')
 (a.out/'vp_params.source_audit.json').write_bytes(a.params.read_bytes())
 (a.out/'expect.memh').write_text(''.join(f'{w["row"]:04x}{w["data128"]}\n' for w in rows))
 result=dict(schema='opentallas.s81.vp_local_gate.v1',status='RUNNING',source_sha256={p:sha(ROOT/p) for p in RTL},parameters=required,source_asbuilt_sha256=audit['source_asbuilt_sha256'],source_top_sha256=audit['source_top_sha256'],clock_period_ps=833,source_event='Input changes 5ps after rising edge N; age is destination rising edge minus N. SRAM commit sampled from actual macro write pins at the active edge; outputs sampled2ps after edge.',scope='Current VP pins -> two real r0c0 SRAM macros -> HLOAD16 HW, GAIN8 WL, RDOUT low128. No XRT/ring/route/VN capture or composed token-rate qualification.')
 def save():(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 save();v=str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator');obj=a.out/'obj'
 argv=[v,'--binary','--timing','-O1','-fno-dfg','--unroll-count','4','-Wno-fatal','-Wno-WIDTH','--top-module','tb_vp_local','-Mdir',str(obj),'-j','2',*[str(ROOT/p) for p in RTL],'-CFLAGS','-O1']
 t=time.time();r=subprocess.run(['/usr/bin/time','-v',*argv],capture_output=True,text=True);(a.out/'build.log').write_text(r.stdout+r.stderr);result['build_seconds']=time.time()-t
 if r.returncode:result.update(status='FAIL',reason='build',exit_code=r.returncode);save();return r.returncode
 checks={}
 for name,mut in [('positive',0),('negative_payload',1)]:
  r=subprocess.run([str(obj/'Vtb_vp_local'),f'+MUT={mut}'],cwd=a.out,capture_output=True,text=True);log=r.stdout+r.stderr;(a.out/(name+'.log')).write_text(log)
  checks[name]=dict(exit_code=r.returncode,passed=(r.returncode!=0 and 'VP_LOCAL FAIL' in log) if mut else (r.returncode==0 and 'VP_LOCAL PASS' in log))
  if not mut:
   result['commit_edges']=[int(x) for x in re.findall(r'^AGE COMMIT .* age=(\d+)$',log,re.M)]
   result['output_edges']={k:int(x) for k,x in re.findall(r'^AGE (HLOAD|GAIN|RDOUT) .* age=(\d+)$',log,re.M)}
 result['checks']=checks;result['status']='PASS' if all(c['passed'] for c in checks.values()) and len(result.get('commit_edges',[]))==49 else 'FAIL';save();print(json.dumps(result));return 0 if result['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())

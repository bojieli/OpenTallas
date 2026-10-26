#!/usr/bin/env python3
"""Current-source scheduled SFU candidate. Run in an exact staged tree via ot-run."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
P='rtl/hbm_accel/generic/peers/'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--r',type=int,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--split48',action='store_true');ap.add_argument('--positive-only',action='store_true');ap.add_argument('--jobs',type=int,default=8);a=ap.parse_args()
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 fixture=ROOT/'results/rtl/hbm_hc_sfu_static_1015/qswiglu'
 subprocess.run(['python3','tools/hbm_static/make_qswiglu_gate.py',str(fixture),str(out/'data')],cwd=ROOT,check=True)
 env=dict(os.environ,SFU_LG_PATH=str(a.r+1))
 subprocess.run(['python3','tools/hbm_static/make_qswiglu_io_calendar.py',str(out/'data')],env=env,cwd=ROOT,check=True)
 io=json.loads((out/'data/io_manifest.json').read_text())
 sources=(ROOT/'results/arch/hbm_native_1013/sfu_native_quarter/r2_sources.txt').read_text().splitlines()
 sources += [P+n+'.sv' for n in ['ot_hgi_sfu_static_quarter','ot_hgi_sfu_scheduled_engine','ot_hgi_sfu_io_calendar_static','ot_hgi_sfu_vm_programmed_engine','ot_hgi_sfu_vm_static_bridge','ot_hgi_sfu_programmed_engine','ot_hgi_sfu_calendar_paged_static','ot_hgi_sfu_program_stripe_static','ot_hgi_sfu_static_engine','ot_hgi_sfu_static_operand_store','ot_hgi_su_unit','ot_hgi_sfu_lg_pair_leaf']]
 sources += ['rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_tap.sv','rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv']
 for macro in ['1024x256_m2_r2c2','256x256_m2_r2c2','128x256_m1_r2c2']:
  n='ot_sram_1r1w_'+macro;sources.append('physical/asap7_memory_macros/'+n+'/'+n+'.v')
 sources += ['rtl/hbm_accel/die_glue/hbfd_rly_masters.sv','rtl/hbm_accel/die_glue/ot_hbm_rly.sv','rtl/lib/ot_rst_relay.sv']
 relay=(ROOT/'rtl/test/hbm_sfu_relay_0330/ot_hgi_sfu_lg_hbfd_relay.sv').read_text()
 if a.split48:
  relay=relay.replace('hbfd_rly_624_EW','hbfd_rly_624_split48_candidate')
  sources.append('rtl/test/hbm_sfu_relay_0330/hbfd_rly_624_split48_candidate.sv')
 (out/'relay_binding.sv').write_text(relay)
 split=(ROOT/(P+'ot_hgi_sfu_split_engine.sv')).read_text()
 old='ot_hgi_sfu_lg_relay #(.R(RG))';assert split.count(old)==1
 (out/'split_binding.sv').write_text(split.replace(old,'ot_hgi_sfu_lg_hbfd_relay #(.R(RG))'))
 tb=(ROOT/'rtl/test/hbm_accel/generic/tb_hgi_sfu_qswiglu_scheduled.sv').read_text()
 monitor="""integer cyc=0,launch=-1,finish_io=-1,last_bank=-1,last_ack=-1,commits=0;
 always @(posedge clk)begin
  cyc=cyc+1;#0.01;
  if(io_start_v && launch<0)launch=cyc;
  if(launch>=0)begin
   if(io_done)finish_io=cyc;
   for(integer k=0;k<8;k=k+1)if(bdone[k])begin last_bank=cyc;commits=commits+1;end
   if(|dut.c_done)last_ack=cyc;
  end
 end
 """
 tb=tb.replace(' initial begin\n  $readmemh',monitor+' initial begin\n  $readmemh')
 tb=tb.replace('  $finish;', '  $display("SFU_COST R=%0d launch=%0d io_done_delta=%0d last_bank_delta=%0d last_ack_delta=%0d sector_commits=%0d",`SFU_LG_R,launch,finish_io-launch,last_bank-launch,last_ack-launch,commits);\n  $finish;')
 (out/'tb_binding.sv').write_text(tb)
 generated=[out/'relay_binding.sv',out/'split_binding.sv',out/'tb_binding.sv']
 pins=list(dict.fromkeys(sources+[P+'ot_hgi_sfu_split_engine.sv','rtl/test/hbm_sfu_relay_0330/ot_hgi_sfu_lg_hbfd_relay.sv','rtl/test/hbm_accel/generic/tb_hgi_sfu_qswiglu_scheduled.sv']))
 manifest=dict(generating_source='a89a10d1fc2200a6f6d556dda2efc905cecbac77',fixture_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture.iterdir() if p.is_file()},compiler_hashes={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in ['tools/hbm_static/make_qswiglu_gate.py','tools/hbm_static/make_qswiglu_io_calendar.py','tools/hbm_static/sfu_control_image.py','tools/hbm_static/sfu_vector_calendar.py']},R=a.r,LG_PATH=a.r+1,split48=a.split48,source_hashes={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in pins},generated_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in generated},scope='SFU component exact loaded programme; no physical/native/full-die qualification')
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 defs=[f'-DSFU_IMAGE="{out}/data/image.hex"',f'-DSFU_DATA_DIR="{out}/data"',f'-DSFU_LG_R={a.r}',f'-DSFU_IO_ROWS={io["rows"]}',f'-DSFU_SCALAR_EDGE={io["scalar_prefetch_edge"]}']
 cmd=['verilator','--binary','--timing','-O2','-j',str(a.jobs),'-CFLAGS','-O0','-Wno-fatal','-Wno-TIMESCALEMOD','--output-split','20000','--top-module','tb_hgi_sfu_qswiglu_scheduled','--Mdir',str(out/'obj')]+defs+sources+[str(p) for p in generated]
 with (out/'build.log').open('w') as f:subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
 rows=[]
 for case in (['positive'] if a.positive_only else ['positive','MUT_IO','MUT_LG_CLOCK']):
  p=subprocess.run([str(out/'obj/Vtb_hgi_sfu_qswiglu_scheduled')]+([] if case=='positive' else ['+'+case]),cwd=ROOT,capture_output=True,text=True)
  log=p.stdout+p.stderr;(out/(case+'.log')).write_text(log)
  ok=(p.returncode==0 and 'PASS canonical Qswiglu' in log) if case=='positive' else (p.returncode!=0 and ('VM_QSWIGLU_WORD' in log or 'SCHEDULED_ENGINE_FAULT' in log))
  rows.append(dict(case=case,exit=p.returncode,passed=ok))
  if not ok:raise RuntimeError(case+' failed; see logs')
 (out/'receipt.json').write_text(json.dumps(dict(manifest=manifest,cases=rows),indent=2)+'\n');print('SFU_SCHEDULED_CANDIDATE PASS')
if __name__=='__main__':main()

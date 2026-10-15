#!/usr/bin/env python3
"""Full default SU calendar component proof: 4096x1024, 128 actual SRAM models.

Run in an ot-run allocation. References supply external configuration and check
answers; DUT instruction reads always traverse the real mapped SRAM models.
"""
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
FILES=[
 'rtl/dsrom_sys/s81_suhc/test/tb_s81_su_calendar_store_full.sv',
 'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_calendar_store.sv',
 'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_calendar_ctl.sv',
 'rtl/hdc/ot_sram_bank.sv',
 'physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v',
 'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_calendar_ctl_p.sv']
TOP='tb_s81_su_calendar_store_full'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--pinctl',action='store_true');a=p.parse_args()
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
 sources={s:sha(ROOT/s) for s in FILES}
 # Each mutation changes the copied target RTL, never an oracle or waveform force.
 variants={
  'base':(0,None),
  'bad_ready':(1,None),
  'half_swap':(0,(FILES[1],'.q(calendar_word[512*b+:512])','.q(calendar_word[512*(1-b)+:512])')),
  'bank_select':(0,(FILES[3],'bs <= ra >> 6;','bs <= (ra >> 6) ^ 1;')),
  'control_row':(0,(FILES[2],'rq_row<=calendar_word[239:16];',"rq_row<=calendar_word[239:16]^224'd1;")),
  'ready_bypass':(1,(FILES[2],'!up_rdy ||',"1'b0 ||")),
 }
 if a.pinctl:variants['pin_word']=(0,(FILES[5],'q_calendar_word<=calendar_word;',"q_calendar_word<=calendar_word^1024'd1;"))
 receipts={}
 for name,(bad_ready,mutation) in variants.items():
  d=out/name;d.mkdir(exist_ok=True);paths=[]
  for rel in FILES:
   target=d/Path(rel).name;shutil.copy2(ROOT/rel,target)
   if mutation and rel==mutation[0]:
    text=target.read_text();assert text.count(mutation[1])==1,(name,'mutation did not bind')
    target.write_text(text.replace(mutation[1],mutation[2]))
   paths.append(target)
  cmd=['iverilog','-g2012','-s',TOP,f'-P{TOP}.BAD_READY={bad_ready}',f'-P{TOP}.PINCTL={int(a.pinctl)}','-o',str(d/'dut'),*map(str,paths)]
  with (d/'build.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
  if r.returncode:raise SystemExit('BUILD FAIL '+name)
  with (d/'run.log').open('w') as f:r=subprocess.run(['vvp',str(d/'dut')],stdout=f,stderr=subprocess.STDOUT)
  log=(d/'run.log').read_text();positive=mutation is None
  ok=(r.returncode==0 and 'PASS CALENDAR_FULL128' in log) if positive else (r.returncode!=0 and any(s in log for s in ['mismatch','full calendar failure']))
  receipts[name]=dict(expected_pass=positive,returncode=r.returncode,ok=ok,mutation=mutation,
   compiled_sha256={x.name:sha(x) for x in paths},log_sha256=sha(d/'run.log'),tail=log[-1500:])
  print(name,'PASS' if ok else 'FAIL',flush=True)
  if not ok:break
 assert all(sha(ROOT/s)==h for s,h in sources.items()),'source changed during proof'
 result=dict(schema='opentallas.s81.su-calendar-full128.v1',sources=sources,
  shape=dict(depth=4096,width=1024,macros=128,macro_shape='64x512',words_per_edge=1,input_pipeline=int(a.pinctl),startup_edges=2+int(a.pinctl)),
  scope='Mapped programme store and actual fixed controller component only; SU arithmetic parent, clock delivery and physical placement remain open.',
  variants=receipts,pass_gate=len(receipts)==len(variants) and all(x['ok'] for x in receipts.values()))
 (out/'gate.json').write_text(json.dumps(result,indent=1)+'\n')
 if not result['pass_gate']:raise SystemExit(1)
 print('PASS SU_CALENDAR_FULL128 exact4096x1024 real_mutants%d availability_fault_reset pinctl%d'%(len(variants)-2,int(a.pinctl)),flush=True)
if __name__=='__main__':main()

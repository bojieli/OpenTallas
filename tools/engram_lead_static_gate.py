#!/usr/bin/env python3
"""Actual released token-map masks -> fixed-slot Engram history lead, no stalls."""
import argparse,hashlib,json,os,shutil,subprocess
from pathlib import Path
from engram_token_map_image import prepare
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);a=p.parse_args();w=a.work.resolve();w.mkdir(exist_ok=False)
 model=prepare(w/'images');model.update(implementation='ot_dsrom_engram_lead_static',compiler_schedule=True,normal_flow_control=False,producer_inflight_entries=3,producer_context_bits=3*57,token_issue_minimum_cycles=1,output_pulse_only=True,slot_sample_to_output_capture_edges=3,cold_reset_clears_history_and_count=True,rollback_conflict_horizon=3,physical_qualified=False)
 src=[R/'rtl/dsrom_sys/engram'/f for f in ['ot_dsrom_engram_token_map.sv','ot_dsrom_engram_idwin.sv','ot_dsrom_engram_lead_static.sv']]+[R/'physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v',R/'rtl/test/tb_dsrom_engram_lead_static.sv',R/'rtl/test/hdc_v41_tb_harness.cpp']
 vl=os.environ.get('VL',str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'));top='tb_dsrom_engram_lead_static'
 cmd=[vl,'--timing','--cc','--exe','--build','-j','8','-O2','-Wno-fatal','-Wno-WIDTH','--top-module',top,'-Mdir',str(w/'obj'),*map(str,src),'-CFLAGS',f'-O1 -DVTOP=V{top}']
 with (w/'build.log').open('w')as f:subprocess.run(cmd,check=True,stdout=f,stderr=subprocess.STDOUT)
 cases=[]
 def run(mode,image,name,expected):
  r=subprocess.run([str(w/'obj'/('V'+top)),f'+MODE={mode}',f'+OT_ROM_DIR={image}'],capture_output=True,text=True);(w/(name+'.log')).write_text(r.stdout+r.stderr)
  ok=(r.returncode==0 and ('ENGRAM_STATIC_PASS' if mode==0 else 'ENGRAM_STATIC_NEG')in r.stdout) if expected=='PASS'else r.returncode!=0 and 'static lead window/context mismatch'in r.stdout
  cases.append(dict(name=name,expected=expected,returncode=r.returncode,gate=ok));assert ok,(name,r.stdout)
 for m in range(5):run(m,w/'images',f'mode{m}','PASS')
 shutil.copytree(w/'images',w/'mutant_images');f=w/'mutant_images/tmap7.viamap.hex';rows=f.read_text().splitlines();rows[455]=f'{int(rows[455],16)^(1<<415):0144x}';f.write_text('\n'.join(rows)+'\n');run(0,w/'mutant_images','actual_rom_mask_mutant','FAIL')
 rec=dict(gate='PASS',scope='Component arithmetic/history/control correctness; not physical or whole native token',old_entry='ot_dsrom_engram_lead_producer ready/busy/output hold historical',successor='ot_dsrom_engram_lead_static fixed compiler slots, actual eight released ROMs and history flops',model=model,cases=cases,sources={str(f.relative_to(R)):sha(f)for f in src},tool_sha256=sha(Path(__file__)))
 (w/'report.json').write_text(json.dumps(rec,indent=2)+'\n');print('ENGRAM_STATIC_GATE PASS 130624 exact windows (all129280released token IDs), four faults, actual ROM mutant rejected')
if __name__=='__main__':main()

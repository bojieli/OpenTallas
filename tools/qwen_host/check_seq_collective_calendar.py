#!/usr/bin/env python3
"""Actual qfd_seq_su PW/start leaf mechanism, four-state omissions and mutant."""
from pathlib import Path
import tempfile,subprocess,json,hashlib
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['rtl/test/tb_qfd_seq_su_collective_calendar.sv','rtl/qwen_split/qfd_seq_su_collective_calendar.sv','rtl/rom/ot_coll_cmd_issue.sv','rtl/qwen_sys/static_schedule_20261014/ot_qwen_fixed_issue.sv']
def main():
 out=ROOT/'results/rtl/qwen_q_export_1014/seq_collective_calendar';out.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='q_seq_coll_')as td:
  exe=Path(td)/'sim';cmd=['iverilog','-g2012','-s','tb_qfd_seq_su_collective_calendar','-o',str(exe)]
  subprocess.run(cmd+SOURCES,cwd=ROOT,check=True)
  for name,args in [('actual_dh_PW944',[]),('free_fault_fixed_timeline',['+BLOCK=1']),('missing_header',['+OMIT=1']),('missing_tag_fixed_timeline',['+OMIT=2'])]:
   r=subprocess.run(['vvp',str(exe)]+args,cwd=ROOT,capture_output=True,text=True);(out/(name+'.log')).write_text(r.stdout+r.stderr)
   if r.returncode or 'PASS 'not in r.stdout:raise RuntimeError(name+':'+r.stdout+r.stderr)
  mutant=Path(td)/'mutant.sv';mutant.write_text((ROOT/SOURCES[1]).read_text().replace('dh[117:108]','dh[116:107]'))
  subprocess.run(cmd+[SOURCES[0],str(mutant)]+SOURCES[2:],cwd=ROOT,check=True)
  r=subprocess.run(['vvp',str(exe)],cwd=ROOT,capture_output=True,text=True);(out/'wrong_actual_PW_face_mutant.log').write_text(r.stdout+r.stderr)
  if not r.returncode or 'FATAL:'not in r.stdout:raise RuntimeError('actual PW face mutation escaped')
 out.joinpath('status.json').write_text(json.dumps(dict(scope='actual sequencer dh PW/start leaf, actual issuer and fixed issue core; full sequencer body not simulated by this mechanism test; production layer calendar/physical D_seq remain open',sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in SOURCES+['rtl/qwen_split/qfd_seq_su_static.sv','tools/qwen_static_schedule/collective.py']},command_issue_cycle=8,stop_cycle=12,PW_window=[944,960],native=False),indent=2)+'\n')
 print('PASS actual seq PW/start calendar, fault-only free, missing halves and rejected wrong-face mutant')
if __name__=='__main__':main()

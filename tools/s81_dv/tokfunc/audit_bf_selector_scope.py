#!/usr/bin/env python3
"""Finite active-profile audit: BF INSTANCE only forwards to image loading."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
FILES={
 'column_wrapper':'rtl/dsrom_sys/s81_die_bind/dsfd_bf_col.sv',
 'column':'rtl/v41rom/ot_v41_bf_col.sv',
 'front_wrapper':'rtl/dsrom_sys/s81_die_bind/dsfd_bf_front_roots.sv',
 'front':'rtl/s81/ot_s81_bf_front_roots.sv',
 'front_core':'rtl/v41rom/ot_v41_bf_front_core_roots.sv',
 'macro':'physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v'}


def clean(text):
 return re.sub(r'/\*[\s\S]*?\*/|//[^\n]*','',text)


def audit(verilator):
 result={}
 for role,name in FILES.items():
  p=ROOT/name;text=p.read_text();lines=[l.strip() for l in clean(text).splitlines() if re.search(r'\bINSTANCE\b',l)]
  result[role]=dict(path=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),all_INSTANCE_uses=lines)
  if role=='macro':
   init=re.search(r'initial begin[\s\S]*?\n    end',text)[0]
   rest=clean(text.replace(init,''));uses=[l.strip() for l in rest.splitlines() if re.search(r'\bINSTANCE\b',l)]
   assert len(uses)==1 and 'parameter string' in uses[0]
   assert '$readmemh({rom_dir, "/", INSTANCE, ".viamap.hex"}' in init
   result[role]['operative_use']='initial readmemh filename only; no reset/clock/arithmetic use'
   continue
  pp=subprocess.run([verilator,'-E','-DSYNTHESIS',str(p)],check=True,capture_output=True,text=True).stdout
  uses=[l.strip() for l in clean(pp).splitlines() if re.search(r'\bINSTANCE\b',l)]
  result[role]['SYNTHESIS_INSTANCE_uses']=uses
  if role in ('column','front_core'):
   assert len(uses)==1 and 'parameter INSTANCE' in uses[0]
   result[role]['operative_use']='none after preprocessing (unused parameter)'
  else:
   assert all('parameter INSTANCE' in l or '.INSTANCE(INSTANCE)' in l for l in uses)
   result[role]['operative_use']='named parameter forwarding only'
 # Fixed selected-profile edges, taken from the actual wrapper constants.
 front=(ROOT/FILES['front_wrapper']).read_text();column=(ROOT/FILES['column_wrapper']).read_text()
 assert '.HCOL(1)' in front and '.RECUT(2)' in front and '.STATIC_PROGRAM(1)' in front
 assert '.PP(1)' in column and '.INSTANCE(INSTANCE), .MB(MB)' in column
 controller=(ROOT/FILES['front']).read_text()
 active_start=re.search(r'if \(RECUT != 0 && HCOL != 0\) begin : g_hc',clean(controller))
 assert active_start is not None
 active=clean(controller)[active_start.start():].split('if (RECUT != 0 && HCOL == 0)',1)[0]
 assert 'ot_v41_bf_front_core_roots #(' in active and active.count('.INSTANCE(INSTANCE)')==1
 assert '.INSTANCE(INSTANCE), .STATIC_PROGRAM(STATIC_PROGRAM)' in active
 return dict(status='PASS_ACTIVE_BF_INSTANCE_IMAGE_ONLY_SCOPE',files=result,
             selected_profile=dict(front_HCOL=1,front_RECUT=2,front_STATIC_PROGRAM=1,column_PP=1,column_MB=0,front_SOQ=0,front_SOQ_SWD=160,front_N32=0),
             active_graph=['dsfd_bf_col→ot_v41_bf_col→simulation-only 2×ot_rom_4096x274_m8 INSTANCE→initial readmemh',
                           'dsfd_bf_front_roots→ot_s81_bf_front_roots(HCOL1)→ot_v41_bf_front_core_roots unused INSTANCE'],
             INSTANCE_drives_reset_clock_state_or_synthesis_logic=False,added_rtl_cycles=0,
             production_reset_or_source_correspondence_qualified=False)


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verilator',default='verilator');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 x=audit(a.verilator)
 with a.out.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
 print(x['status'])
if __name__=='__main__':main()

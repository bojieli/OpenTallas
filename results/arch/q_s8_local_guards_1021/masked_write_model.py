#!/usr/bin/env python3
"""Exact source-transform and four-state procedural write proof; no simulation."""
from pathlib import Path
import hashlib,itertools,json,re,subprocess,sys
R=Path(__file__).resolve().parents[3];sys.path.insert(0,str(R/'tools/qwen_dv'))
import s8_landing_masks as M
sym='01XZ'
def AND(a,b):return '0' if '0' in (a,b) else '1' if a==b=='1' else 'X'
def OR(a,b):return '1' if '1' in (a,b) else '0' if a==b=='0' else 'X'
checks=0;causal=0
# Arbitrary independent binary/X/Z selectors and arbitrary data/previous state.
for enables in itertools.product(sym,repeat=3):
 any_en=OR(OR(enables[0],enables[1]),enables[2])
 for data,previous in itertools.product(sym,repeat=2):
  masked=data if any_en=='1' else '0' if any_en=='0' else '0' if data=='0' else 'X'
  for e in enables:
   old=data if e=='1' else previous
   new=masked if e=='1' else previous
   assert old==new;checks+=1
   bad_en=AND(AND(enables[0],enables[1]),enables[2])
   mutant=data if bad_en=='1' else '0' if bad_en=='0' else '0' if data=='0' else 'X'
   causal+=old!=(mutant if e=='1' else previous)
assert causal>0
bindings={}
for top,D in [('qfd_dv_s8',4),('qfd_dv_s8b',8)]:
 rel=f'rtl/qwen_dv/s5/s8/lp/{top}_lp.sv'
 old=subprocess.check_output(['git','-C',str(R),'show','363295685:'+rel],text=True)
 new=(R/rel).read_text();assert M.transform(old)==new
 # Remove only 23 changed writer lines, generated combinational block and helper modules;
 # the entire original parent, including all readers/clocks/resets/MUT logic, is unchanged.
 prefix=top+'_lp_flags_mask';a=new.index('    // Shared real flag gates');b=new.index('    // ---- LANDING 0:',a)
 restored=new[:a]+new[b:];restored=restored[:restored.index('\n\nmodule '+prefix+'_local_w')]
 original_lines={re.search(r'u_lpl_(\d+)_w',line)[1]:line for line in old.splitlines() if 'ot_pl_land_n32_chunk_w #' in line}
 n=0;lines=[]
 for line in restored.splitlines():
  if prefix+'_chunk_w #' in line:
   number=re.search(r'u_lpl_(\d+)_w',line)[1];line=original_lines[number];n+=1
  lines.append(line)
 assert n==23;assert '\n'.join(lines)+'\n'==old
 # The custom local writer keeps all original state declarations, always/NBA statements,
 # OH instances, valid/epoch equations; only dq RHS uses combinational slot_i.
 src=(R/'rtl/common/landed_parent/ot_pl_land_n32.sv').read_text()
 original=M.module(src,'ot_pl_land_n32_local_w')
 helper=M.module(new,prefix+'_local_w')
 state=lambda s:re.findall(r'\breg\b[^;]*;',re.sub(r'//[^\n]*','',s))
 assert state(original)==state(helper)
 statements=lambda s:re.findall(r'\balways\b.*?;',s,re.S)
 expected=statements(original)
 actual=statements(helper)
 assert len(expected)==len(actual)
 assert [s.replace('dq <= slot_i','dq <= i[LO +: GW]') for s in actual]==expected
 assert 'assign flags_oh=oh[(FLO/GB)*D+:D];' in helper
 assert '.rq(rq), .oh(oh[g*D +: D])' in helper
 # Selected fields all fit one original chunk and one original kept OH group.
 for W,FLO,FW in [(132,128,4),(66,64,2)]:
  c=FLO//24;lo=FLO%24;CW=min(24,W-c*24)
  assert lo+FW<=CW and lo//12==(lo+FW-1)//12
 bindings[rel]={'old_sha256':hashlib.sha256(old.encode()).hexdigest(),'new_sha256':hashlib.sha256(new.encode()).hexdigest(),'writer_instances':n,'full_original_parent_restoration':True,'local_state_declarations_and_all_always_statements_unchanged_except_dq_rhs':True,'D':D,'raw_input_alias_contract':M.alias_contract(old),'source_input_gate_loads':3*D,'rs_s_source_input_loads_with_existing_direct_consumer':3*D+1}
out={'scope':'Four-state procedural RTL write mechanism plus exact generated-source restoration; not executed full RTL or mapped-native qualification','four_state_write_comparisons':checks,'AND_instead_of_OR_mutant_counterexamples':causal,'independent_selectors':True,'reset_or_phase_correlation_assumed':False,'new_state_or_capture_edges':0,'max_group_writers':3,'target_fields':{'rss/rsn':[128,129,130,131],'nb':[64,65]},'source_binding':bindings,'selector_load_note':'One added real OR input per selected original OH slot; mask output <=3 writer D cones. Actual mapped census including selector/control loads remains required.'}
Path(__file__).with_name('MASKED_WRITE_MODEL.json').write_text(json.dumps(out,indent=2)+'\n')
print(f'MASKED_WRITE_MODEL PASS {checks} independent four-state writes; mutant differs {causal}; both whole-parent restoration and exact local state/always identity PASS')

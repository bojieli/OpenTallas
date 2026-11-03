#!/usr/bin/env python3
"""Prepare owned UNAPPLIED PVQ data cut from exactly original or approved PMEM preimage."""
from pathlib import Path
import re,json,hashlib,argparse,difflib,shutil
ALLOWED={'61c902f184b49e231c34de041d0f1832a4117749592f81fa3bf42d6ff4df504a':'original_T7','04a554300de8e3c87737a889aa4462dece93e4f5221c77ce98b04913cea94544':'approved_PMEM_data_cut'}
P='w_u_rsv_14_u_u_att_';G='g_u_rsv_14_u_u_att_src_26dc491f45cf101b7ca4_q';Q=P+'src_26dc491f45cf101b7ca4_Q';D=P+'src_37314bb8933e4a98116c_Y'
PORTS={'RD_ADDR':P+'driver_pvr_Q[2:0]','RD_DATA':P+'pvq_RD_DATA','WR_ADDR':P+'driver_pvw_Q[2:0]','WR_CLK':'clk','WR_DATA':'{'+P+'u_eng_src_26cc0285b4c5b801b801_Q[7:0], '+P+'u_eng_src_378b62d9249ca62f488b_Q[2047:0], '+P+'u_eng_src_6870e5b5454840c8a2c3_Q[63:0]}','WR_EN':P+'src_8c9e9eb60b3aae42c23f_Y[2119:0]'}
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def header(s):return s[s.index('module '):s.index(');',s.index('module '))+2]
def transform(s):
 if sha(s) not in ALLOWED:raise ValueError('unapproved preimage hash')
 lines=s.splitlines();inst=[l for l in lines if 'ot_bind_native_9c28130c03bbd6a26f6fd9a5 g_u_rsv_14_u_u_att_pvq (' in l]
 if len(inst)!=1:raise ValueError('PVQ instance count')
 ports=dict(re.findall(r'\.(\w+)\((.*?)\)(?=,|\);)',inst[0]))
 if ports!=PORTS:raise ValueError('PVQ port identity')
 old=[l for l in lines if re.search(r'\b'+G+r'\b',l)]
 if len(old)!=3 or not any('always @(posedge clk)' in l for l in old):raise ValueError('capture consumer/driver count')
 # Only consider backwards cone of original capture D and native array read data.
 assigns={};decl={}
 for l in lines:
  m=re.match(r'\s*assign (\w+) = (.*);',l)
  if m:assigns[m[1]]=(l,m[2])
  mcell=re.match(r'\s*ot_bind_native_1d3023bdc8bf230da3726274 .*\.A\((.*?)\), \.B\((.*?)\), \.Y\((\w+)\)\);',l)
  if mcell:assigns[mcell[3]]=(l,mcell[1]+' '+mcell[2])
  m=re.match(r'\s*wire (?:\[[^]]+\] )?(\w+);',l)
  if m:decl[m[1]]=l
 cone=set();stack=[D,P+'pvq_RD_DATA']
 while stack:
  n=stack.pop()
  if n in cone:continue
  cone.add(n)
  if n in assigns:stack.extend(re.findall(r'\bw_\w+\b',assigns[n][1]))
 remove=set(old+[inst[0]])
 # Delete only now-unobserved wire+continuous-assignment nodes in that cone.
 while True:
  progress=False;remain='\n'.join(l for l in lines if l not in remove)
  for n in sorted(cone):
   if n==Q or n not in decl:continue
   own=[decl[n]]+([assigns[n][0]] if n in assigns else [])
   if all(l in remove for l in own):continue
   rest='\n'.join(l for l in lines if l not in remove and l not in own)
   if not re.search(r'\b'+n+r'\b',rest):remove.update(own);progress=True
  if not progress:break
 child=['    // UNAPPLIED PVQ data-cut: all original queue/control/reset lines retained.',
 '    ot_t7_pvq_capture_candidate g_u_rsv_14_u_u_att_pvq_capture (',
 '        .clk(clk), .dr_on('+P+'driver_dr_on_Q[0]), .p_i('+P+'driver_p_i_Q[2:0]),',
 '        .ra('+PORTS['RD_ADDR']+'), .wa('+PORTS['WR_ADDR']+'),',
 '        .wd('+PORTS['WR_DATA']+'), .wm('+PORTS['WR_EN']+'),',
 '        .provenance('+P+'u_pv_identity_provenance[47:0]), .out('+Q+'[512:0]));']
 out=[]
 for l in lines:
  if l==inst[0]:out.extend(child)
  elif l not in remove:out.append(l)
 new='\n'.join(out)+'\n'
 assert header(new)==header(s)
 assert G not in new and 'ot_bind_native_9c28130c03bbd6a26f6fd9a5' not in new
 assert P+'pvq_RD_DATA' not in new and P+'src_f2d8531b2b64cd0f0ac6_Y' not in new
 assert len(remove)==23
 assert all(l in new for l in lines if l not in remove)
 return new,[l for l in lines if l in remove]
def prepare(parent,out):
 if out.exists():raise FileExistsError('fresh owned output required')
 s=parent.read_text();new,removed=transform(s);out.mkdir(parents=True);name='s81p_svc_lo_dsdv_svc_rs__t7_bound.sv'
 (out/name).write_text(new);shutil.copyfile(Path(__file__).parent/'ot_t7_pvq_capture_candidate.sv',out/'ot_t7_pvq_capture_candidate.sv')
 (out/'bound_cut.patch').write_text(''.join(difflib.unified_diff(s.splitlines(True),new.splitlines(True),fromfile='before/'+name,tofile='UNAPPLIED/'+name)))
 r=dict(status='UNAPPLIED_OWN_SOURCE_NOT_ELABORATED',preimage=ALLOWED[sha(s)],before_sha256=sha(s),after_sha256=sha(new),removed_lines=removed,removed_line_count=len(removed),original_capture_FF_removed=513,new_dynamic_provenance_FF=48,new_mode_FF=3,external_FF_delta=-462,macro_clock_delta=34,reset_load_delta=0,cycle_delta=0,top_header_identical=True,all_other_original_lines_identical_in_order=True,original_queue_control_ready_fault_reset_unchanged=True,normal_child_no_mutant_or_test_state=True,native_component_gate='3b5e9b338',fresh_bound_integration_native_proof=False,physical_cohort_adopted=False)
 (out/'transform.json').write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--parent',type=Path,required=True);a.add_argument('--out',type=Path,required=True);x=a.parse_args();print(json.dumps(prepare(x.parent,x.out),indent=2))

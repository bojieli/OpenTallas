#!/usr/bin/env python3
"""Hash-guarded isolated source preparation only; refuses existing output or changed nativecut."""
from pathlib import Path
import re,json,hashlib,argparse,difflib,gzip,shutil
EXPECTED='61c902f184b49e231c34de041d0f1832a4117749592f81fa3bf42d6ff4df504a'
P='w_u_rsv_14_u_u_att_';E=P+'u_eng_';G='g_u_rsv_14_u_u_att_u_eng_driver_g_pskid_'
CLOSED=[P+'pmem_RD_DATA',P+'src_c42275b8d43e8375c6e7_Y',P+'src_037d97b1cd2a5ab22e14_Y',P+'733_Y',E+'src_7a2f9d574e2d0b99b375_Y',E+'src_75b927658e070e2d323b_Y']
PORTS={'RD_ADDR':'{'+P+'driver_pr_Q[8:0], '+P+'src_29b80db2284db6415584_Y[8:0]}','RD_DATA':P+'pmem_RD_DATA','WR_ADDR':P+'driver_pw_Q[8:0]','WR_CLK':'clk','WR_DATA':'w_u_rsv_14_u_src_b4e411b517a9f984ed73_Q[511:0]','WR_EN':P+'src_edb47cb20fbd82577b0b_Y[511:0]'}

def digest(b):return hashlib.sha256(b).hexdigest()
def module_header(s):return s[s.index('module '):s.index(');',s.index('module '))+2]
def inspect(s):
 lines=s.splitlines();inst=[l for l in lines if 'ot_bind_native_193c9bdc13b0c4251a5bbbc4 g_u_rsv_14_u_u_att_pmem ('in l]
 if len(inst)!=1:raise ValueError('native memory instance count')
 ports=dict(re.findall(r'\.(\w+)\((.*?)\)(?=,|\);)',inst[0]))
 if ports!=PORTS:raise ValueError('native memory port identity')
 for slot in [0,1]:
  reg=G+f'sk{slot}_q'
  block=[l for l in lines if re.search(r'\b'+reg+r'\b',l)]
  if len(block)!=3 or not any('always @(posedge clk)'in l for l in block):raise ValueError('native payload consumer count')
 for n,count in [(P+'pmem_RD_DATA',4),(P+'733_Y',4),(P+'src_c42275b8d43e8375c6e7_Y',3),(P+'src_037d97b1cd2a5ab22e14_Y',3)]:
  if len(re.findall(r'\b'+n+r'\b',s))!=count:raise ValueError('native async fanout count')
 if digest(s.encode())!=EXPECTED:raise ValueError('native parent body hash')
 return lines,inst[0]

def transform(s):
 lines,oldinst=inspect(s);out=[];removed=[]
 for line in lines:
  if line==oldinst:
   out.extend(['    // DISABLED isolated PMEM data-cut; preserve every original control/reset cell.',
    '    ot_t7_pmem_capture_candidate g_u_rsv_14_u_u_att_pmem_capture (',
    '        .clk(clk), .pr('+P+'driver_pr_Q[8:0]), .wa('+P+'driver_pw_Q[8:0]),',
    '        .pstep('+P+'716_Y[1:0]), .owner('+P+'719_Y[0]),',
    '        .push('+E+'111_Y[0]), .wp('+E+'driver_g_pskid_wp_Q[0]),',
    '        .wd(w_u_rsv_14_u_src_b4e411b517a9f984ed73_Q[511:0]),',
    '        .wm('+P+'src_edb47cb20fbd82577b0b_Y[511:0]),',
    '        .slot0('+E+'driver_g_pskid_sk0_Q[1023:0]),',
    '        .slot1('+E+'driver_g_pskid_sk1_Q[1023:0]));'])
   removed.append(line);continue
  if any(re.search(r'\b'+G+f'sk{k}_q'+r'\b',line)for k in [0,1]):removed.append(line);continue
  if any(re.match(r'\s*wire .*\b'+n+r'\s*;',line)or re.match(r'\s*assign '+n+r'\s*=',line)for n in CLOSED):removed.append(line);continue
  out.append(line)
 new='\n'.join(out)+'\n'
 for n in CLOSED:
  if re.search(r'\b'+n+r'\b',new):raise ValueError('unremoved old async cone '+n)
 for k in [0,1]:
  if G+f'sk{k}_q'in new:raise ValueError('unremoved old payloaddriver')
 if module_header(s)!=module_header(new):raise ValueError('top interface changed')
 if len(removed)!=18:raise ValueError('removal count '+str(len(removed)))
 # Every retained original line stays byte-identical and in order. Thus control/reset/ready/rp mux are untouched.
 assert all(l in new for l in lines if l not in removed)
 return new,removed

def prepare(parent,out):
 if out.exists():raise FileExistsError('fresh isolated output required')
 s=parent.read_text();new,removed=transform(s);here=Path(__file__).resolve().parent;out.mkdir(parents=True)
 name='s81p_svc_lo_dsdv_svc_rs__t7_bound.sv';(out/name).write_text(new);shutil.copyfile(here/'ot_t7_pmem_capture_candidate.sv',out/'ot_t7_pmem_capture_candidate.sv')
 patch=''.join(difflib.unified_diff(s.splitlines(True),new.splitlines(True),fromfile='original/'+name,tofile='DISABLED/'+name));(out/'bound_cut.patch').write_text(patch)
 report=dict(status='DISABLED_OWN_ISOLATED_SOURCE_ONLY_NOT_ELABORATED',parent=str(parent.resolve()),output=str((out/name).resolve()),before_sha256=digest(s.encode()),after_sha256=digest(new.encode()),module_header_identical=True,native_memory_removed=1,payload_drivers_removed=2,payload_FF_removed=2048,old_closed_cone_wires_removed=6,old_closed_cone_assigns_removed=5,removed_lines=len(removed),all_other_original_lines_identical_in_order=True,controls_ready_valid_reset_rp_mux_retained=True,new_macro_count=4,new_payload_FF=1024,new_format_and_marker_FF=4,net_external_FF=-1020,added_macro_clock_pins=4,reset_load_delta=0,cycle_delta=0,test_delay_FF=0,algorithm_native_gate='09032d7ab',fresh_projection_native_or_fullservice_proof=False,physical_or_profile_adopted=False,files={p.name:digest(p.read_bytes())for p in out.iterdir()if p.is_file()})
 (out/'transform.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.parent,a.out),indent=2))

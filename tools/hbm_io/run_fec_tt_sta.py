#!/usr/bin/env python3
"""Source-bound ideal-wire TT characterization, never a physical timing signoff."""
import argparse, hashlib, json, pathlib, subprocess, time
from fec_bit_graph import CLOCKS

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--map',type=pathlib.Path,required=True);ap.add_argument('--libs',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);ap.add_argument('--sta',default=str(pathlib.Path.home()/'.local/opentallas-tools/opensta-be771a0/bin/sta'));a=ap.parse_args()
 mapped=a.map.resolve();libs=a.libs.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 r=json.loads((mapped/'receipt.json').read_text());assert r['yosys_exit']==0
 assert sha(mapped/'mapped.v')==r['mapped_verilog_sha256']
 assert {p.name:sha(p) for p in libs.glob('*.lib')}==r['libraries_sha256']
 # An abstract common phase gives an upper-bound feasibility screen for the
 # numerical profile. Delivered phases, reset recovery and skew are unqualified.
 period=885.4166666666666
 bind={'scope':'ACTUAL_STANDALONE_FEC_RVT_TT_IDEAL_WIRE_COMMON_PHASE_CHARACTERIZATION','mapping_receipt_sha256':sha(mapped/'receipt.json'),'mapped_verilog_sha256':r['mapped_verilog_sha256'],'libraries_sha256':r['libraries_sha256'],'runner_sha256':sha(pathlib.Path(__file__)),'period_ps':period,'clock_ports':CLOCKS,'abstract_clock_phase_ps':0,'external_input_delay_ps':0,'external_output_delay_ps':0,'external_driver_model':None,'external_load_model':None,'reset_case':'rst_n=1 functional mode','spef':None,'cts':False,'physical_qualified':False,'timing_signoff':False,'limits':['No delivered clock phase/skew or wire parasitics','Zero external delays are ideal boundary assumptions','No qualified input slew/output load','No asynchronous reset recovery/removal qualification','Standalone hierarchy excludes joined PMA/outer CDC/endpoint state']}
 (out/'binding.json').write_text(json.dumps(bind,indent=2)+'\n')
 lines=[f'read_liberty {{{p}}}' for p in sorted(libs.glob('*.lib'))]
 lines += [f'read_verilog {{{mapped/"mapped.v"}}}',f'link_design {r["top"]}','set_units -time ps']
 lines += [f'create_clock -name {c} -period {period:.12f} [get_ports {{{c}}}]' for c in CLOCKS]
 lines += ['set_case_analysis 1 [get_ports rst_n]','set data_inputs {}']
 lines += ['foreach p [all_inputs] { if {[lsearch -exact {'+' '.join(CLOCKS+['rst_n'])+'} [get_full_name $p]] < 0} { lappend data_inputs $p } }']
 lines += ['set_input_delay 0 -clock clk $data_inputs','set_output_delay 0 -clock clk [all_outputs]','check_setup -verbose',f'report_checks -path_delay max -group_path_count 64 -format full_clock_expanded -fields {{capacitance slew fanout input_pin net}} -digits 4 > {{{out/"max_paths.txt"}}}',f'report_checks -path_delay min -group_path_count 16 -format full_clock_expanded -fields {{capacitance slew fanout input_pin net}} -digits 4 > {{{out/"min_paths.txt"}}}',f'report_checks -unconstrained -group_path_count 16 -digits 4 > {{{out/"unconstrained.txt"}}}','report_worst_slack -max','report_worst_slack -min','report_tns','exit']
 (out/'sta.tcl').write_text('\n'.join(lines)+'\n');started=time.monotonic()
 with (out/'sta.log').open('w') as log:cp=subprocess.run([a.sta,'-no_init','-exit',str(out/'sta.tcl')],stdout=log,stderr=subprocess.STDOUT)
 log=(out/'sta.log').read_text();success=cp.returncode==0 and not any(x in log for x in ['Error:','Error '])
 result=dict(bind,sta_exit=cp.returncode,tool_execution_pass=success,elapsed_seconds=time.monotonic()-started,sta_log_sha256=sha(out/'sta.log'),sta_script_sha256=sha(out/'sta.tcl'))
 for name in ['max_paths.txt','min_paths.txt','unconstrained.txt']:
  if (out/name).exists():result[name+'_sha256']=sha(out/name)
 assert sha(mapped/'mapped.v')==r['mapped_verilog_sha256']
 (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return 0 if success else 1
if __name__=='__main__':raise SystemExit(main())

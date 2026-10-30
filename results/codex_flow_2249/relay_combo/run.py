import json, pathlib, subprocess
import face_guard
src=pathlib.Path('top.sv').read_text()
land={'st':{'form':'origin_start','origin':'origin','copies':['copy0','copy1']}}
results={}
for mode in ['base','wrong_reset','extra_cycle','wrong_type']:
 s=src
 if mode=='wrong_reset': s=s.replace('copy0(.clk(clk),.rst_raw_n(reset_q)','copy0(.clk(clk),.rst_raw_n(rst_n)')
 if mode=='extra_cycle': s=s.replace('copy0(.clk(clk),.rst_raw_n(reset_q),.d(st)','copy0(.clk(clk),.rst_raw_n(reset_q),.d(mission)')
 if mode=='wrong_type':
  relay=src[:src.index('module top')].replace('module ot_dp_landing_relay','module unrelated_relay')
  s=relay+src.replace('ot_dp_landing_relay copy0','unrelated_relay copy0')
 pathlib.Path(mode+'.sv').write_text(s)
 cp=subprocess.run(['yosys','-Q','-p',f'read_verilog -sv {mode}.sv; synth -top top; opt_clean; write_verilog -noattr -noexpr {mode}.v'],capture_output=True,text=True)
 pathlib.Path(mode+'.log').write_text(cp.stdout+cp.stderr);assert cp.returncode==0
 r=face_guard.guard(pathlib.Path(mode+'.v').read_text(),'top',land=land)
 pathlib.Path(mode+'.json').write_text(json.dumps(r,indent=1)+'\n')
 print(mode,r['verdict'],r.get('fail_counts'),r.get('ring_start'))
 assert (r['verdict']=='PASS') == (mode=='base')
 results[mode]={'verdict':r['verdict'],'fails':r['fail_counts']}
pathlib.Path('result.json').write_text(json.dumps(results,indent=1)+'\n')

"""Universal wiring equivalence to the full selector with each quarter's8missing records invalid0.
The same arbitrary original sequential selector is used on both sides. Wrong-quarter control must fail.
"""
from pathlib import Path
import subprocess,json,sys,re
root=Path(__file__).resolve().parents[2];out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
s=(root/'physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/index/ot_hbm_idx_selector_static_sel.sv').read_text();a=s.index('module ot_hbm_idx_selector_static_sel #(');b=re.search(r'^\s*\);\s*$',s[a:],re.M).end()+a;stub='(* blackbox *) '+s[a:b]+'\nendmodule\n'
gate=(root/'rtl/hbm_next/bind/ot_hnx_selector_eightwide.sv').read_text();gate=gate.replace('ot_hbm_idx_selector_static_sel_eightwide','gate',1)
head=gate[gate.index('module gate'):gate.index(');')+2].replace('module gate','module gold')
ports=['clk_ctl','clk_q','clk_mem','rst_n','op','pass','addr','k','in_line','selected_v','selected_line','fault']
conn="{296'd0,in_line[1183:888],296'd0,in_line[887:592],296'd0,in_line[591:296],296'd0,in_line[295:0]}"
gold=head+'\n ot_hbm_idx_selector_static_sel #(.MUT(MUT)) u_ref ('+','.join('.'+x+'('+ (conn if x=='in_line' else x)+')' for x in ports)+');\nendmodule\n'
rs=[]
for mode in ['exact','wrong_quarter']:
 g=gate if mode=='exact' else gate.replace("{296'd0,in_line[296+:296]}","{296'd0,in_line[0+:296]}")
 f=out/(mode+'.sv');f.write_text(stub+gold+g)
 r=subprocess.run(['yosys','-Q','-T','-p',f'read_verilog -sv {f}; proc; opt_clean; equiv_make gold gate equiv; hierarchy -top equiv; equiv_struct; equiv_simple; equiv_status -assert'],capture_output=True,text=True)
 (out/(mode+'.log')).write_text(r.stdout+r.stderr);ok=(r.returncode==0)==(mode=='exact');rs.append(dict(mode=mode,returncode=r.returncode,accepted=ok));print(mode,r.returncode,ok)
(out/'receipt.json').write_text(json.dumps(dict(checks=rs,pass_all=all(x['accepted'] for x in rs),added_cycles=0),indent=2)+'\n')
raise SystemExit(not all(x['accepted'] for x in rs))

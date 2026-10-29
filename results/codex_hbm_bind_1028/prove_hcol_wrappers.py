"""Universal unchangednativeHCOL wiring proof,HALF0seed andHALF1 realchain. Wrongseedmutantmustfail."""
from pathlib import Path
import subprocess,json,sys,re
root=Path(__file__).resolve().parents[2];out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True);d=json.loads(Path(__file__).with_name('hcol_wrapper_ports.json').read_text());ports=d['ports']
stub='(* blackbox *) module ot_hidx_score_hcol #(parameter integer HALF=0,MUT=0,DELIVERED_RESET=0)(\n'+',\n'.join(x['direction']+' wire '+(f"[{x['width']-1}:0] " if x['width']>1 else '')+x['port'] for x in ports)+'\n);endmodule\n';src=(root/'rtl/hbm_next/bind/ot_hnx_idx_hcol_plan.sv').read_text();rs=[]
for half in [0,1]:
 mod=f'ot_hbm_idx_score_hcol_h{half}';m=re.search(r'module '+mod+r'\b.*?\nendmodule',src,re.S);cand=m[0].replace(mod,'gate',1);h=cand[:cand.index(');')+2].replace('module gate','module gold',1)
 gold=h+f'\n ot_hidx_score_hcol #(.HALF({half}),.MUT(MUT),.DELIVERED_RESET(DELIVERED_RESET)) u_ref ('+','.join('.'+x['port']+'('+ ("32'd0" if half==0 and x['port']=='cs_in' else "1'b0" if half==0 and x['port']=='cf_in' else x['port'])+')' for x in ports)+');\nendmodule\n'
 for mode in (['exact','seed1'] if half==0 else ['exact']):
  gate=cand if mode=='exact' else cand.replace(".cf_in(1'b0)",".cf_in(1'b1)");f=out/f'h{half}_{mode}.sv';f.write_text(stub+gold+gate)
  r=subprocess.run(['yosys','-Q','-T','-p',f'read_verilog -sv {f}; proc; opt_clean; equiv_make gold gate equiv; hierarchy -top equiv; equiv_struct; equiv_simple; equiv_status -assert'],capture_output=True,text=True);(out/f'h{half}_{mode}.log').write_text(r.stdout+r.stderr)
  ok=(r.returncode==0)==(mode=='exact');rs.append(dict(half=half,mode=mode,returncode=r.returncode,accepted=ok));print(half,mode,r.returncode,ok)
(out/'receipt.json').write_text(json.dumps(dict(checks=rs,pass_all=all(x['accepted'] for x in rs),added_cycles=0,delivered_reset_forwarded=True),indent=2)+'\n');raise SystemExit(not all(x['accepted'] for x in rs))

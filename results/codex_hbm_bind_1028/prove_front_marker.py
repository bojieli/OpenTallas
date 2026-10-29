"""Universal unchanged-master wiring proof; wrongreservedmarkercontrolmustfail."""
from pathlib import Path
import re,json,subprocess,sys
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools'));import die_port_bind as D
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True);mod='ot_hbm_sm_attn_front_static';s=(root/'rtl/hbm_accel/sm/attn'/f'{mod}.sv').read_text();a=s.index('module '+mod);z=re.search(r'^\s*\);\s*$',s[a:],re.M).end()+a;stub='(* blackbox *) '+s[a:z]+'\nendmodule\n'
gate=(root/'rtl/hbm_next/bind/ot_hnx_sm_front_nomarker.sv').read_text().replace(mod+'_nomarker','gate',1);a=gate.index('module gate');z=re.search(r'^\s*\);\s*$',gate[a:],re.M).end()+a;h=gate[a:z].replace('module gate','module gold',1);m=next(x for x in D.parse_modules(s,mod) if x.name==mod);ps=[x for x in m.params if x not in m.localparams]
full="{command[190:116],1'b0,command[115:0]}";gold=h+'\n'+mod+' #('+','.join('.'+x+'('+x+')' for x in ps)+') u_ref ('+','.join('.'+p+'('+ (full if p=='command' else p)+')' for p in m.ports)+');\nendmodule\n'
rs=[]
for mode in ['exact','marker1']:
 g=gate if mode=='exact' else gate.replace("1'b0","1'b1");f=out/(mode+'.sv');f.write_text(stub+gold+g)
 r=subprocess.run(['yosys','-Q','-T','-p',f'read_verilog -sv {f}; proc; opt_clean; equiv_make gold gate equiv; hierarchy -top equiv; equiv_struct; equiv_simple; equiv_status -assert'],capture_output=True,text=True);(out/(mode+'.log')).write_text(r.stdout+r.stderr)
 ok=(r.returncode==0)==(mode=='exact');rs.append(dict(mode=mode,returncode=r.returncode,accepted=ok));print(mode,r.returncode,ok)
(out/'receipt.json').write_text(json.dumps(dict(checks=rs,pass_all=all(x['accepted'] for x in rs),added_cycles=0),indent=2)+'\n');raise SystemExit(not all(x['accepted'] for x in rs))

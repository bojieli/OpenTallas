"""Universal unchanged-master wiring proof and exact D0 wire proof, with controls."""
from pathlib import Path
import json,re,subprocess,sys
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools'));import die_port_bind as D
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
native=(root/'rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_lane_pinreg.sv').read_text()
source=(root/'rtl/hbm_next/bind/ot_hnx_su_boundaries.sv').read_text();m=next(x for x in D.parse_modules(native[:native.index('\n);')+3]+'\nendmodule','native') if x.name=='ot_hbm_su_static_lane_pinreg')
start=native.index('module ot_hbm_su_static_lane_pinreg');end=native.index('\n);',start)+3
stub='(* blackbox *) '+native[start:end]+'\nendmodule\n'
gate=re.search(r'module ot_hnx_su_pinreg_noside\b.*?\nendmodule',source,re.S)[0].replace('module ot_hnx_su_pinreg_noside','module gate',1)
header=gate[:gate.index('\n);')+3].replace('module gate','module gold',1)
gold=header+'\n ot_hbm_su_static_lane_pinreg #('+','.join('.'+p+'('+p+')' for p in m.params)+') u_native ('+','.join('.'+p+'('+ ("32'd0" if p=='side_y' else p)+')' for p in m.ports)+');\nendmodule\n'
rows=[]
def run(name,sv,command,positive):
    path=out/(name+'.sv');path.write_text(sv)
    r=subprocess.run(['yosys','-Q','-T','-p',f'read_verilog -sv {path}; '+command],capture_output=True,text=True);(out/(name+'.log')).write_text(r.stdout+r.stderr)
    rows.append(dict(name=name,returncode=r.returncode,accepted=(r.returncode==0)==positive))
for kind in (0,1):
    for ln in (3,7):
        for mutant in (False,True):
            cand=gate.replace(".side_y(32'd0)",".side_y(32'd1)") if mutant else gate
            run(f'kind{kind}_ln{ln}_'+('mutant' if mutant else 'exact'),stub+gold+cand,
                f'chparam -set KIND {kind} -set LN {ln} -set MLAT 4 -set ALAT 4 gold gate; proc; opt_clean; equiv_make gold gate equiv; hierarchy -top equiv; equiv_struct; equiv_simple; equiv_status -assert',not mutant)
delay=(root/'rtl/hdc/ot_hdc_delay.sv').read_text()
wire=re.search(r'module ot_hnx_delay_wire\b.*?\nendmodule',source,re.S)[0].replace('module ot_hnx_delay_wire','module gate',1)
ref='''module gold #(parameter W=569,D=0,RESET=0)(input wire[W-1:0]d,output wire[W-1:0]q);
ot_hdc_delay #(.W(W),.D(D),.RESET(RESET)) u(.clk(1'b0),.rst_n(1'b0),.d(d),.q(q));endmodule
'''
for mutant in (False,True):
    cand=wire.replace('assign q=d;','assign q=~d;') if mutant else wire
    run('delay_wire_'+('mutant' if mutant else 'exact'),delay+ref+cand,'chparam -set W 569 gold gate; hierarchy; proc; flatten gold gate; opt_clean; equiv_make gold gate equiv; hierarchy -top equiv; equiv_struct; equiv_simple; equiv_status -assert',not mutant)
record=dict(checks=rows,pass_all=all(x['accepted'] for x in rows),added_cycles=0,source_requirements='SIDE=0 at enumerated KIND0/1 paths, D=RESET=0 at enumerated delay paths; full KIND2 is explicitly rejected')
(out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=1));sys.exit(0 if record['pass_all'] else 1)

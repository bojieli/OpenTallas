"""Focused actual bridge full-boundary 4-state coupon; physical child is isolated, no count/PNR claim."""
import json,pathlib,re,subprocess,tempfile
from pin_plan import ROOT,ports
HERE=pathlib.Path(__file__).parent;B=ROOT/'physical/die_plan/hbm_arch_cores/wrappers';full='ot_hnx_su_plain4__7dd6a1bbbf47_rst3__id44';physical=full+'__nocoll';bridge=physical+'__native_bridge';top='ot_hnx_su_plain4__7dd6a1bbbf47_rst3';P=ports(top);outs=[(n,w)for d,n,w in P if d=='output'];stub='module '+physical+'(\n'+',\n'.join(d+' wire '+f'[{w-1}:0] '+('strap_lane_lane_id'if n=='lane_lane_id'else n)for d,n,w in P if n!='lane_coll')+'\n);\n';expr={}
for i,(n,w)in enumerate(outs):
 ex="4'b0000"if n=='lane_coll'else 'cmd0_D['+str((i*17)%(1382-w+1))+'+:'+str(w)+']';expr[n]=ex
 if n!='lane_coll':stub+='assign '+n+'='+ex+';\n'
stub+='endmodule\n';src=(B/(bridge+'.sv')).read_text();mut=src.replace('module '+bridge+'(', 'module '+bridge+'__wrong(').replace("assign lane_coll = 4'b0000;", "assign lane_coll = 4'b0001;")
tb='`timescale 1ns/1ps\nmodule tb;integer c,hits=0;\n'
for d,n,w in P:
 if d=='input':tb+='reg '+f'[{w-1}:0] '+n+';\n'
 else:
  for tag in ['a','m']:tb+='wire '+f'[{w-1}:0] '+tag+'_'+n+';\n'
for tag,mod in [('a',bridge),('m',bridge+'__wrong')]:tb+=mod+' '+tag+'('+','.join('.'+n+'('+((tag+'_'+n)if d=='output'else n)+')'for d,n,w in P)+');\n'
tb+='initial begin\n'
for d,n,w in P:
 if d=='input':tb+=n+"='0;\n"
tb+="rst_n=1;#1;rst_n=0;\nfor(c=0;c<64;c=c+1)begin\ncmd0_D={44{$random}};if(c%7==0)cmd0_D[37]=1'bx;if(c%11==0)cmd0_D[103]=1'bz;rst_n=(c>4&&!(c>30&&c<35));bank_clk=~bank_clk;#1;\n"
a='{'+','.join('a_'+n for n,w in outs)+'}';m='{'+','.join('m_'+n for n,w in outs)+'}';g='{'+','.join(expr[n]for n,w in outs)+'}'
tb+='if('+a+'!=='+g+')$fatal(1,"bridge full1540output mismatch");if('+m+'!=='+g+')hits=hits+1;\nend\nif(hits==0)$fatal(1,"wrongTIE1notcaught");$display("PASS bridge full1540output 64fourstatevectors truePOR/warm; wrongTIE1=%0d",hits);$finish;end\nendmodule\n'
with tempfile.TemporaryDirectory(dir=HERE)as tmp:
 t=pathlib.Path(tmp);(t/'stub.sv').write_text(stub);(t/'mut.sv').write_text(mut);(t/'tb.sv').write_text(tb)
 r=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(t/'a'),str(B/(bridge+'.sv')),str(t/'stub.sv'),str(t/'mut.sv'),str(t/'tb.sv')],capture_output=True,text=True);assert r.returncode==0,r.stderr
 r=subprocess.run(['vvp',str(t/'a')],capture_output=True,text=True);assert r.returncode==0,r.stdout+r.stderr
(HERE/'constant_bridge_coupon_receipt.json').write_text(json.dumps(dict(status='PASS',scope='Actual generated parent bridge, full1540output comparison, physicalchild isolated withsymbolicpayloadfunction; nativeconstant induction separatelyproven, no arithmetic/count/PNR claim',four_state_vectors=64,wrong_TIE1_mutant_detected=True,output=r.stdout+r.stderr),indent=1)+'\n');print(r.stdout)

from pathlib import Path
import re,sys,subprocess,json
base=Path(sys.argv[1]);old=(base/'qkd_hr_core_prompt_vJ2/rtl/qkd_hr_core_prompt.v').read_text();new=(base/'qkd_hr_core_prompt_vK/rtl/qkd_hr_core_prompt.v').read_text();out=base/'fault_pin_proof';out.mkdir(exist_ok=True)
def blocks(s):
 pat=r'always @\(posedge ck, negedge (rr_p_l\d+)\)\s+if \(!\1\) (hrfp_u_program__fault_0_internal_state|u_program__fault) <= 1\x27h0;\s+else \2 <= [^;]+;'
 z=re.findall(pat,s);assert len(z)==2
 return '\n'.join(m.group(0) for m in re.finditer(pat,s))
def module(s,name):return 'module '+name+'(input ck,rst,d,output reg u_program__fault,hrfp_u_program__fault_0_internal_state);\nwire rr_p_l3=rst,rr_p_l5=rst;wire _3129_=d;\n'+blocks(s)+'\nendmodule\n'
bench='''module tb;
reg ck=0,rst=0,d=0;wire oq,os,nq,ns;integer count=0,errors=0;reg expected=0;
always #5 ck=~ck;
old_ref o(ck,rst,d,oq,os);candidate n(ck,rst,d,nq,ns);
always @(posedge ck) begin
 if(!rst)expected=0; else expected=oq;
 #1;
 if(nq!==expected || ns!==os) begin errors=errors+1; if(errors<4)$display("DIFF cycle%0d old%0b new%0b expected%0b state%0b/%0b",count,oq,nq,expected,os,ns);end
 count=count+1;
end
initial begin
 // First fault, sticky fault, deasserted fault, reset during active fault, and repeated reset pulses.
 #2;rst=0;#11;rst=1;d=1;#20;d=1;#20;d=0;#20;d=1;#7;rst=0;#1;
 if(nq!==0 || ns!==0)begin $display("ASYNC RESET FAIL");$fatal;end
 #6;rst=1;d=1;#30;
 repeat(256)begin @(negedge ck);d=$random;if((count%31)==0)rst=0;else rst=1;end
 @(negedge ck);rst=0;#1;if(nq!==0 || ns!==0)$fatal;
 #20;$display("LOCKSTEP cycles%0d errors%0d",count,errors);if(errors)$fatal; $finish;
end
endmodule
'''
results={}
for mode,s in [('new',new),('bypass_mutant',new.replace('else u_program__fault <= hrfp_u_program__fault_0_internal_state;','else u_program__fault <= _3129_;'))]:
 v=out/(mode+'.v');v.write_text(module(old,'old_ref')+module(s,'candidate')+bench);exe=out/(mode+'.out');subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(v)],check=True);r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);(out/(mode+'.log')).write_text(r.stdout+r.stderr);results[mode]={'rc':r.returncode,'log':r.stdout};print(mode,r.returncode,r.stdout.strip())
assert results['new']['rc']==0
assert results['bypass_mutant']['rc']!=0
(out/'result.json').write_text(json.dumps(results,indent=2)+'\n')

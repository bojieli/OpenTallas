from pathlib import Path
import re,subprocess,json
q=Path(__file__).resolve().parents[3]
s=(q/'rtl/common/ot_dp_clk_landing_ca.sv').read_text()
m=re.search(r'module ot_dp_landing_relay\s*\(.*?endmodule',s,re.S).group()
o=Path(__file__).resolve().parent/'miter';o.mkdir(exist_ok=True)
(o/'relay.sv').write_text(m+'\n')
tb='''module tb;
reg clk=0;always #5 clk=~clk;
reg raw=0,d=0;wire baseline,face0,face1;reg previous=0;reg [31:0] r=32'h8c392ef1;
ot_dp_landing_relay ref0(clk,raw,d,baseline);
wire copy_d = MUTANT==1 ? baseline : d;
wire copy_raw = MUTANT==2 ? 1'b1 : raw;
ot_dp_landing_relay copy0(clk,copy_raw,copy_d,face0);
ot_dp_landing_relay copy1(clk,raw,d,face1);
integer checks=0;parameter MUTANT=0;
initial begin
 for(integer i=0;i<4096;i=i+1)begin
  @(negedge clk);r=r^(r<<13);r=r^(r>>17);r=r^(r<<5);
  raw=(i>3)&&(i%37>2);d=r[0];
  @(posedge clk);#1;
  if(face0!==baseline||face1!==baseline)begin
   $display("MUTANT_CAUGHT %0d edge=%0d",MUTANT,i);$finish_and_return(86);
  end
  checks=checks+2;
 end
 $display("PASS checks=%0d added_cycles=0",checks);$finish;
end
endmodule
'''
(o/'tb.sv').write_text(tb)
r=[]
for mutant in (0,1,2):
 exe=o/f'm{mutant}';subprocess.run(['iverilog','-g2012',f'-Ptb.MUTANT={mutant}','-o',str(exe),str(o/'relay.sv'),str(o/'tb.sv')],check=True)
 c=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);r.append(dict(mutant=mutant,rc=c.returncode,output=c.stdout.strip()));assert c.returncode==(0 if mutant==0 else 86),r[-1]
(o/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))

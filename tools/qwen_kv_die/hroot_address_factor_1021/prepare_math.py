#!/usr/bin/env python3
"""Source-bound arithmetic proof fixtures; no shipping wrapper or cell models."""
from pathlib import Path
import hashlib,json,re,sys
src=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
s=src.read_text();f='\n'.join(re.findall(r'    function automatic \[31:0\] af_.*?    endfunction',s,re.S));assert len(re.findall('function automatic',f))==3
(out/'binding.json').write_text(json.dumps({'production_source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'extracted_helper_sha256':hashlib.sha256(f.encode()).hexdigest(),'scope':'universal binary arithmetic + 4-state boundary vectors; does not qualify native copied engine'},indent=2)+'\n')
for kind,expr in [('add','a+b'),('mul3','a*b[2:0]'),('mul5','a*b[4:0]')]:
 call={'add':'af_add32(a,b)','mul3':'af_mul3(a,b[2:0])','mul5':'af_mul5(a,b[4:0])'}[kind]
 body='module m(input [31:0] a,b,output ok);\n'+f+'\nwire[31:0] got='+call+'; wire[31:0] refv='+expr+'; assign ok=(got==refv); endmodule\n'
 (out/(kind+'.sv')).write_text(body)
# Causal wrong carry output: universal positive must pass; this must fail.
(out/'negative.sv').write_text((out/'add.sv').read_text().replace('assign ok=(got==refv)','assign ok=((got ^ 32\'h80000000)==refv)'))
tb='''module tb;
reg[31:0] a,b; integer n,i,t; reg[31:0] refv; reg[31:0] got; reg[31:0] base_a,base_b; integer checks=0;
'''+f+'''
task check;
begin
 refv=a+b;got=af_add32(a,b);if(got!==refv)$fatal(1,"ADD a=%h b=%h got=%h ref=%h",a,b,got,refv);
 refv=a*b[2:0];got=af_mul3(a,b[2:0]);if(got!==refv)$fatal(1,"MUL3 a=%h b=%h got=%h ref=%h",a,b,got,refv);
 refv=a*b[4:0];got=af_mul5(a,b[4:0]);if(got!==refv)$fatal(1,"MUL5 a=%h b=%h got=%h ref=%h",a,b,got,refv);
 checks=checks+3;
end endtask
initial begin
for(n=0;n<8;n=n+1)begin
 case(n)0:begin a=0;b=0;end 1:begin a=-1;b=-1;end 2:begin a='h7fffffff;b=1;end 3:begin a='h80000000;b='h80000000;end 4:begin a='haaaaaaaa;b='h55555555;end 5:begin a=0;b=-1;end 6:begin a=-1;b=0;end 7:begin a=1;b='h80000000;end endcase
 check; base_a=a; base_b=b;
 for(i=0;i<32;i=i+1)begin
  for(t=0;t<4;t=t+1)begin
   a=base_a;b=base_b;
   case(t)0:a[i]=1'bx;1:a[i]=1'bz;2:b[i]=1'bx;3:b[i]=1'bz;endcase
   check;
  end
 end
end
for(n=0;n<1024;n=n+1)begin a=$random;b=$random;check;end
$display("ADDRESS_4STATE PASS checks=%0d",checks);$finish;
end endmodule
'''
(out/'fourstate.sv').write_text(tb)

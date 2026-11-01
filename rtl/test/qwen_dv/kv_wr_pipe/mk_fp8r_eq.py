import re,sys
s=open(sys.argv[1]).read()
def fn(name):
    m=re.search(r'    function automatic \[31:0\] '+name+r'\(.*?endfunction\n',s,re.S); return m.group(0)
body=fn('fp8r')+fn('fp8r_pre')+fn('fp8r_fin')
open(sys.argv[2],'w').write('module eqv(input wire [31:0] v, output wire [31:0] a, output wire [31:0] b, output wire ok);\n'+body+
 '    assign a = fp8r(v);\n    assign b = fp8r_fin(fp8r_pre(v));\n    assign ok = (a == b);\nendmodule\n')
open(sys.argv[3],'w').write('''module tb;
  reg [31:0] v; wire [31:0] a,b; wire ok; integer i, bad, k; reg [7:0] ex;
  eqv u(.v(v),.a(a),.b(b),.ok(ok));
  initial begin
    bad=0;
    for (i=0;i<4000000;i=i+1) begin
      v=$random; if (i%2) begin ex = 110 + ($random & 31); v[30:23]=ex; end
      if (i%7==0) v[19:0] = (i%3==0) ? 20'd0 : ((i%3==1) ? 20'h80000 : 20'hFFFFF);
      #1; if (!ok) begin bad=bad+1; if (bad<10) $display("MISMATCH v=%h a=%h b=%h",v,a,b); end
    end
    for (k=0;k<256;k=k+1) begin v={1'b0,k[7:0],23'd0}; #1; if(!ok) bad=bad+1; v={1'b1,k[7:0],23'h7FFFFF}; #1; if(!ok) bad=bad+1;
      v={1'b0,k[7:0],23'h400000}; #1; if(!ok) bad=bad+1; v={1'b0,k[7:0],23'h580000}; #1; if(!ok) bad=bad+1; end
    $display("RANDOM_EQ vectors=%0d mismatches=%0d", 4000000+1024, bad); $finish;
  end
endmodule
''')

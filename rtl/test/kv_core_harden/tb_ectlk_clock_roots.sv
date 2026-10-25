`timescale 1ns/1ps
// Smallest clock-binding vehicle. The two .ck expressions below are exactly
// the extracted ECTLK wrapper's old and restored bindings. All source pins are
// the same related die clock; arbitrary dependent registered data must keep
// every edge. A half-cycle wrong root must be caught.
module ectkk_clock_probe(input wire [2:0] ck,input wire rn,input wire [47:0] d,output wire [47:0] q);
  reg [15:0] a,b,c;
  always @(posedge ck[0] or negedge rn)if(!rn)a<=0;else a<=d[15:0];
  always @(posedge ck[1] or negedge rn)if(!rn)b<=0;else b<=d[31:16]^a;
  always @(posedge ck[2] or negedge rn)if(!rn)c<=0;else c<=d[47:32]^b;
  assign q={c,b,a};
endmodule
module tb_ectlk_clock_roots;
  reg ck0=0;always #0.5 ck0=~ck0;
  reg rn=0;reg [47:0] d=0;
`ifdef KVG3_ECTLK_CKMUT
  wire [2:0] ck={~ck0,ck0,ck0};
`else
  wire [2:0] ck={ck0,ck0,ck0};
`endif
  wire [47:0] a,b;
  ectkk_clock_probe ref_core(.ck({ck[0], ck[0], ck[0]}),.rn(rn),.d(d),.q(a));
  ectkk_clock_probe new_core(.ck(ck[2:0]),.rn(rn),.d(d),.q(b));
  integer i,mismatches=0;
  initial begin
    repeat(5)@(negedge ck0);#0.1;rn=1;
    for(i=0;i<6000;i=i+1)begin
      @(negedge ck0);#0.1;d={$urandom,$urandom};rn=(i%197!=0);
      @(posedge ck0);#0.05;if(a!==b)mismatches=mismatches+1;
    end
    if(mismatches==0)$display("PASS ectlk_clock_roots edges=6000 cycles_added=0");
    else $display("FAIL ectlk_clock_roots mismatches=%0d",mismatches);
    $finish;
  end
endmodule

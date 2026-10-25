`timescale 1ns/1ps
module tb_astk_fault_face;
    reg ck=0;always #0.5 ck=~ck;
    reg rn=0,a=0,b=0;
    wire q;
    qkd_astk_fault_join #(.PORT_REGS(1)) dut(.ck(ck),.rst_n(rn),.a(a),.b(b),.q(q));
    reg prior_b=0,expected=0;
    integer i,mismatches=0;
    initial begin
       repeat(5)@(negedge ck);rn=1;
       for(i=0;i<6000;i=i+1)begin
          @(negedge ck);a=$urandom;b=$urandom;rn=(i%197!=0);
          // Contract: a is reported on its original next edge, b one edge later.
          expected=rn ? (a|prior_b) : 1'b0;
          prior_b=rn ? b : 1'b0;
          @(posedge ck);#0.01;
          if(q!==expected)mismatches=mismatches+1;
       end
       if(mismatches==0)$display("PASS astk_fault_face edges=6000 local_cycles=1 external_cycles=2");
       else $display("FAIL astk_fault_face mismatches=%0d",mismatches);
       $finish;
    end
endmodule

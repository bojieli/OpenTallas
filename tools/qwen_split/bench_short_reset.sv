`timescale 1ns/1ps
// Actual short landing, distinct source/receiver resets, exact cycle oracle.
// K is static. A calendar mutant restores the historical G=R0 strap.
module short_case #(parameter integer G=16, R0=20) (output integer errors, output integer checks);
    reg cs=0, cd=0; always #5 cs=~cs;
    initial begin #2; forever #5 cd=~cd; end
    integer es=0, ed=0;
    reg en=1, rs=1;
    initial begin #0.1; en=0; rs=0; end
    reg [15:0] data=0;
    wire [15:0] result; wire fault;
    localparam integer L=3, E=L-1;
`ifdef CALENDAR_MUTANT
    localparam [2:0] K=E;
`else
    localparam [2:0] K=(E+G-R0)&7;
`endif
    function automatic [15:0] word(input integer e); word=16'(e*40503+(e>>3)+7); endfunction
    always @(posedge cs) begin es<=es+1; data<=word(es); en<=(es>=G); end
    always @(posedge cd) begin ed<=ed+1; rs<=(ed>=R0); end
    ot_qfd_land #(.W(16),.FIRST(1)) dut(.ckf(cs),.ea(en),.i(data),.ck(cd),.rs(rs),.k(K),.o(result),.fault(fault));
    integer expected_edge;
    initial begin errors=0;checks=0; end
    always @(negedge cd) begin
        expected_edge=ed-1-L;
        if(ed>R0+16 && ed>G+16) begin
            checks=checks+1;
            if(result !== word(expected_edge) || fault !== 1'b0) begin errors=errors+1; if(errors<2) $display("DBG G %0d R0 %0d ed %0d result %h exp %h fault %b wc %0d rc %0d",G,R0,ed,result,word(expected_edge),fault,dut.wc,dut.rc);end
        end
    end
endmodule
module tb;
    wire integer e[0:5],c[0:5];
    short_case #(.G(16),.R0(20)) c0(e[0],c[0]);
    short_case #(.G(20),.R0(16)) c1(e[1],c[1]);
    short_case #(.G(16),.R0(28)) c2(e[2],c[2]);
    short_case #(.G(28),.R0(16)) c3(e[3],c[3]);
    short_case #(.G(16),.R0(16)) c4(e[4],c[4]);
    short_case #(.G(420),.R0(16)) c5(e[5],c[5]);
    integer errors=0,checks=0,j;
    initial begin #12000; for(j=0;j<6;j=j+1) begin errors+=e[j];checks+=c[j];end
      $display("SHORT_RESET errors %0d checks %0d",errors,checks);
      if(errors || checks<5000) $fatal(1,"SHORT_RESET FAIL");
      $display("SHORT_RESET PASS");$finish;end
endmodule

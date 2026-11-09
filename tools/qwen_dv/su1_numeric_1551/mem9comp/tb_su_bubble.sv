`timescale 1ns/1ps
// QC-MEM9-COMP: SU sequencer issue spacing. Two ops, second go N edges after the first. Reports first-emit distance and su_fault.
module tb_su_bubble;
  reg ck=0,rst_n=0,start=0; reg [456:0] si=0; wire [243:0] gb; wire [2:0] gv; wire [7:0] lv1; wire [767:0] pd1; wire su_nr,su_idle,su_fault; wire [15:0] su_prog,su_rows;
  qfd_dv_s5_su8 dut(.ck(ck),.rst_n(rst_n),.start(start),.si(si),.l_retire(1'b0),.l_last(1'b0),.l_fault(8'd0),.kv_we(8'd0),.rd_v(1'b0),.red_busy(1'b0),.red_fault(1'b0),.lvm_we(8'd0),.gb(gb),.gv(gv),.lv1(lv1),.pd1(pd1),.su_nr(su_nr),.su_idle(su_idle),.su_fault(su_fault),.su_prog(su_prog),.su_rows(su_rows));
  always #1 ck=~ck;
  function [456:0] word(input integer nin); begin word=0; word[18:1]=18'd1; word[36:19]=18'(nin); end endfunction
  reg [456:0] w_in=0, dl[0:3]; always @(negedge ck) begin dl[0]<=w_in; dl[1]<=dl[0]; dl[2]<=dl[1]; dl[3]<=dl[2]; si<=dl[3]; end
  task go(input integer nin); begin @(negedge ck); w_in=word(nin); start=1; @(negedge ck); start=0; end endtask
  integer t=0, first[0:1], n, emits, prev, gap;
  task run(input integer nin1, input integer nin2, input integer d);
    integer sf,k,edges[0:63],ne,seen_nr;
    begin
      @(negedge ck); rst_n=0; repeat(6) @(negedge ck); rst_n=1; repeat(12) @(negedge ck);
      ne=0; seen_nr=0;
      fork
        begin go(nin1); repeat(d-2) @(negedge ck); go(nin2); end
        begin for(k=0;k<80;k=k+1) begin @(posedge ck); #0.1; if(gv[2]) begin if(ne<64) edges[ne]=t; ne=ne+1; end if(su_nr===1'b1) seen_nr=1; t=t+1; end end
      join
      gap=-1; for(k=1;k<ne;k=k+1) if(edges[k]!=edges[k-1]+1) gap=edges[k]-edges[0];
      $display("CASE nvec1=%0d nvec2=%0d go_dist=%0d emits=%0d second_op_first_emit_minus_first=%0d su_nr=%0d su_fault=%b",nin1/8,nin2/8,d,ne,gap,seen_nr,su_fault);
    end
  endtask
  initial begin
    run(72,64,9); run(72,64,10); run(64,64,9); run(64,64,8); run(8,64,3); run(8,64,2); $finish;
  end
endmodule

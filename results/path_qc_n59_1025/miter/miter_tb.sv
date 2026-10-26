`timescale 1ns/1ps
// PATH-QC-N59 10-25 miter: qfd_native59_qbank (main, per-bit 512-bit write mask macro) vs the same block with
// ot_sram_1r1w_32x512_m1 regenerated at mask_gran 32 (16 lane write enables).  Same random stimulus into both;
// every output compared every edge AND the eight SRAM arrays compared word by word every edge.
module miter_tb #(parameter integer QB_ALIGN=0, QB_LOCAL32=0, integer CYCLES=200000, integer SEED=1);
 reg ck=0, rst_n=0;
 reg[547:0]dd_i; reg lcv; reg[5:0]stage; reg qs; reg[4:0]qbeat;
 wire[547:0]dd_o_a,dd_o_b; wire lcv_a,lcv_b,qv_a,qv_b,full_a,full_b,com_a,com_b,bad_a,bad_b;
 wire[5:0]st_a,st_b; wire[4:0]bt_a,bt_b; wire[511:0]row_a,row_b;
 old_qfd_native59_qbank #(.QB_ALIGN(QB_ALIGN),.QB_LOCAL32(QB_LOCAL32)) u_old(.ck(ck),.rst_n(rst_n),.dd_i(dd_i),.layer_context_v(lcv),
  .command_stage(stage),.q_slot(qs),.q_slot_beat(qbeat),.dd_o(dd_o_a),.lcv_o(lcv_a),.stage_o(st_a),.qb_v(qv_a),.qb_beat(bt_a),
  .qb_row(row_a),.qb_full(full_a),.qb_committed(com_a),.qb_bad(bad_a));
 qfd_native59_qbank #(.QB_ALIGN(QB_ALIGN),.QB_LOCAL32(QB_LOCAL32)) u_new(.ck(ck),.rst_n(rst_n),.dd_i(dd_i),.layer_context_v(lcv),
  .command_stage(stage),.q_slot(qs),.q_slot_beat(qbeat),.dd_o(dd_o_b),.lcv_o(lcv_b),.stage_o(st_b),.qb_v(qv_b),.qb_beat(bt_b),
  .qb_row(row_b),.qb_full(full_b),.qb_committed(com_b),.qb_bad(bad_b));
 wire[7:0]arr_neq;
 genvar w;
 generate for(w=0;w<8;w=w+1)begin:g_cmp
  reg neq; integer r;
  always @* begin neq=0; for(r=0;r<32;r=r+1) if(u_old.u_qseat.g_writer[w].u_mem.arr[r]!==u_new.u_qseat.g_writer[w].u_mem.arr[r]) neq=1; end
  assign arr_neq[w]=neq;
 end endgenerate
 integer cyc=0, errs=0, arr_errs=0, out_errs=0, writes=0, reads=0, rows_nz=0, k;
 reg[63:0]xs;   // xorshift64 (every bit usable; $random's low bits are periodic)
 function automatic [31:0] rnd(); begin xs=xs^(xs<<13); xs=xs^(xs>>7); xs=xs^(xs<<17); rnd=xs[63:32]; end endfunction
 reg[8:0]e;
 always #1 ck=~ck;
 initial begin
  xs=64'h9E3779B97F4A7C15^64'(SEED);
  dd_i=0; lcv=0; stage=0; qs=0; qbeat=0;
  repeat(5) @(negedge ck); rst_n=1;
  for(cyc=0;cyc<CYCLES;cyc=cyc+1) begin
   @(negedge ck);
   if(arr_neq!=0 || {dd_o_a,lcv_a,st_a,qv_a,bt_a,row_a,full_a,com_a,bad_a}!=={dd_o_b,lcv_b,st_b,qv_b,bt_b,row_b,full_b,com_b,bad_b}) begin
    errs=errs+1; if(arr_neq!=0) arr_errs=arr_errs+1; if(row_a!==row_b || {dd_o_a,lcv_a,st_a,qv_a,bt_a,full_a,com_a,bad_a}!=={dd_o_b,lcv_b,st_b,qv_b,bt_b,full_b,com_b,bad_b}) out_errs=out_errs+1;
    if(errs<=5) $display("MISMATCH cyc %0d arr_neq %b row_eq %0d outs_eq %0d", cyc, arr_neq, row_a===row_b,
      {dd_o_a,lcv_a,st_a,qv_a,bt_a,full_a,com_a,bad_a}==={dd_o_b,lcv_b,st_b,qv_b,bt_b,full_b,com_b,bad_b});
   end
   if(qv_a && row_a!=0) rows_nz=rows_nz+1;
   // stimulus: Q writes (dd valid, kind 0, writer mask), elements {beat, lane}, random data; rare slot begins; reads
   for(k=0;k<18;k=k+1) dd_i[32*k+:32]=rnd();
   dd_i[547]=rnd()%4!=0; dd_i[546:545]=(rnd()%4==0)?2'd1:2'd0;
   for(k=0;k<8;k=k+1) begin
    e=rnd(); dd_i[345+24*k+:9]=e;
    dd_i[345+24*k+9+:15]=((rnd()%64)==0)?15'(rnd()):15'd0;
   end
   lcv=(rnd()%200)==0; stage=rnd(); qs=rnd(); qbeat=rnd();
   if(dd_i[547]&&dd_i[546:545]==0&&dd_i[544:537]!=0) writes=writes+1;
   if(qs) reads=reads+1;
  end
  $display("MITER QB_ALIGN=%0d QB_LOCAL32=%0d cycles %0d q_write_cycles %0d read_cycles %0d nonzero_rows %0d mismatch_cycles %0d (array %0d, outputs %0d) => %s",
   QB_ALIGN, QB_LOCAL32, CYCLES, writes, reads, rows_nz, errs, arr_errs, out_errs, errs==0?"EQUIVALENT":"DIFFERENT");
  $finish;
 end
endmodule

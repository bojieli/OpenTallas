`timescale 1ns/1ps
module tb_issuer_rel_class #(parameter integer CMUT=0);
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,desc_we=0,run_v=0,ids_v=0,program_done=0;
 reg[7:0]desc_addr=0,run_base=248,run_layer=3,ids_layer=3;
 reg[8:0]run_count=8;reg[255:0]desc_data=0;
 reg[53:0]ids=0;reg[15:0]ids_cohort=0;
 reg reserve_ready=1;reg[3:0]block_ready=15;reg[1:0]cache_ready=3,cache_owned=0;
 wire[1:0]running,run_done,fault,reserve_v,start_v,program_start_v;
 wire[31:0]reserve_base[0:1];wire[14:0]reserve_row_base[0:1];wire[11:0]reserve_total[0:1];
 wire[1:0]reserve_bank[0:1],start_bank[0:1];wire[15:0]reserve_epoch[0:1],start_epoch[0:1];
 wire[6:0]reserve_rows[0:1];wire[9:0]reserve_tag_base[0:1];
 wire[10:0]program_start_base[0:1];wire[11:0]program_start_limit[0:1];
 wire[15:0]program_start_loops[0:1];wire[46:0]program_start_ctx[0:1];
 `define CONN(I) .clk(clk),.rst_n(rst_n),.desc_we(desc_we),.desc_addr(desc_addr),.desc_data(desc_data), \
 .run_v(run_v),.run_base(run_base),.run_count(run_count),.run_layer(run_layer), \
 .ids_v(ids_v),.ids_layer(ids_layer),.ids(ids),.ids_cohort(ids_cohort), \
 .running(running[I]),.run_done(run_done[I]),.fault(fault[I]), \
 .reserve_v(reserve_v[I]),.reserve_ready(reserve_ready),.reserve_base(reserve_base[I]),.reserve_row_base(reserve_row_base[I]), \
 .reserve_total(reserve_total[I]),.reserve_bank(reserve_bank[I]),.reserve_epoch(reserve_epoch[I]), \
 .reserve_rows(reserve_rows[I]),.reserve_tag_base(reserve_tag_base[I]), \
 .block_ready(block_ready),.cache_ready(cache_ready),.cache_owned(cache_owned), \
 .start_v(start_v[I]),.start_bank(start_bank[I]),.start_epoch(start_epoch[I]), \
 .program_start_v(program_start_v[I]),.program_start_base(program_start_base[I]), \
 .program_start_limit(program_start_limit[I]),.program_start_loops(program_start_loops[I]),.program_done(program_done)
 ot_hbm_svc_sm_issuer_rel #(.ID_COHORT(1))reference_825(`CONN(0),.program_start_ctx(program_start_ctx[0][45:0]));
 assign program_start_ctx[0][46]=0;
 ot_hbm_svc_sm_issuer_rel_class #(.ID_COHORT(1),.CLASS_MUT(CMUT))candidate(`CONN(1),.program_start_ctx(program_start_ctx[1]));
 `undef CONN
 integer cycles=0,go_i=0,res_i=0,total_go=0,total_done=0,cohort_expected=0,checks=0,j;
 reg fresh_seen=0;reg[7:0]done_pipe=0;
 function[2:0]mode_for;input integer i;begin
  case(i%8)0:mode_for=0;1:mode_for=4;2:mode_for=6;3:mode_for=7;
   4:mode_for=2;5:mode_for=4;6:mode_for=1;default:mode_for=6;endcase
 end endfunction
 function[255:0]descriptor;input integer i;reg[255:0]w;begin
  w=0;w[255:240]=16'h5d15;w[239:232]=8'(248+i);
  w[46:32]=15'(i*8);w[48:47]=2'(i%4);w[64:49]=16'(21+i);
  w[71:65]=7'(1+7*i);w[81:72]=10'(64*i);
  w[91:82]=10'(8*i);w[102:92]=11'(8*i+8);w[118:103]=16'(1+i);
  w[142:119]=24'(80+40*i);w[157:143]=15'(i+3);w[172:158]=15'(i+1);
  w[176:173]=i%2?4'd1:4'd0;w[188:177]=12'(17*i);
  w[194:191]=4'(i%5);w[197:195]=mode_for(i);w[198]=1;w[199]=i%2==0;
  descriptor=w;
 end endfunction
 always @(negedge clk)if(rst_n)reserve_ready=(cycles%5)!=1;
 always @(posedge clk)begin
  cycles=cycles+1;
  if(!rst_n)begin done_pipe<=0;program_done<=0;go_i=0;res_i=0;cohort_expected=0;fresh_seen=0;end
  else begin
   done_pipe<={done_pipe[6:0],program_start_v[0]};program_done<=done_pipe[7];
   if({running[0],run_done[0],fault[0],reserve_v[0],start_v[0],program_start_v[0]}!==
      {running[1],run_done[1],fault[1],reserve_v[1],start_v[1],program_start_v[1]})$fatal(1,"ISSUER_CLASS_FAIL handshake cycle%0d",cycles);
   if(reserve_v[0]&&{reserve_base[0],reserve_row_base[0],reserve_total[0],reserve_bank[0],reserve_epoch[0],reserve_rows[0],reserve_tag_base[0]}!==
      {reserve_base[1],reserve_row_base[1],reserve_total[1],reserve_bank[1],reserve_epoch[1],reserve_rows[1],reserve_tag_base[1]})$fatal(1,"ISSUER_CLASS_FAIL reserve");
   if(start_v[0]&&{start_bank[0],start_epoch[0]}!=={start_bank[1],start_epoch[1]})$fatal(1,"ISSUER_CLASS_FAIL start");
   if(program_start_v[0])begin
    if({program_start_base[0],program_start_limit[0],program_start_loops[0],program_start_ctx[0][45:0]}!==
       {program_start_base[1],program_start_limit[1],program_start_loops[1],program_start_ctx[1][45:0]})$fatal(1,"ISSUER_CLASS_FAIL low46/programme");
    if(program_start_ctx[1][46]!==((mode_for(go_i)&4)!=0))$fatal(1,"ISSUER_CLASS_FAIL independent class oracle mut%0d index%0d mode%0d got%0d",CMUT,go_i,mode_for(go_i),program_start_ctx[1][46]);
    go_i=go_i+1;total_go=total_go+1;
   end
   if(reserve_v[0])begin
    if(res_i%2!=0&&!fresh_seen)$fatal(1,"ISSUER_CLASS_FAIL stale IDs escaped reserve");
    res_i=res_i+1;
   end
   if(run_v)begin go_i=0;res_i=0;fresh_seen=0;cohort_expected=cohort_expected+1;end
   if(ids_v&&running[0]&&!run_v&&ids_cohort==16'(cohort_expected)&&ids_layer==run_layer&&!fresh_seen)fresh_seen=1;
   if(run_done[0])total_done=total_done+1;
   checks=checks+1;
  end
 end
 task idle;input integer n;begin repeat(n)@(negedge clk);end endtask
 task clear;begin @(negedge clk);rst_n=0;run_v=0;ids_v=0;idle(3);rst_n=1;idle(3);end endtask
 task launch;begin @(negedge clk);run_v=1;@(negedge clk);run_v=0;end endtask
 task send_ids;input[15:0]c;input[7:0]l;begin
  @(negedge clk);ids_v=1;ids_cohort=c;ids_layer=l;
  @(negedge clk);ids_v=0;
 end endtask
 task expect_fault;input integer label_id;begin
  idle(4);if(fault!==2'b11)$fatal(1,"ISSUER_CLASS_FAIL expected cohort fault case%0d got%b",label_id,fault);
  $display("ISSUER_COHORT_REJECT case=%0d",label_id);
 end endtask
 initial begin
  for(j=0;j<6;j=j+1)ids[j*9+:9]=9'(3*j+3);
  clear;
  for(j=0;j<8;j=j+1)begin @(negedge clk);desc_we=1;desc_addr=8'(248+j);desc_data=descriptor(j);@(negedge clk);desc_we=0;end
  idle(5);
  launch;idle(8);send_ids(1,3);wait(!running[0]);idle(4);
  if(fault!=0||go_i!=8||res_i!=8)$fatal(1,"ISSUER_CLASS_FAIL first run");
  // Same layer, second token: prior IDs must be invalidated before new cohort.
  launch;idle(8);send_ids(2,3);wait(!running[0]);idle(4);
  if(fault!=0||go_i!=8||res_i!=8)$fatal(1,"ISSUER_CLASS_FAIL second run");
  launch;idle(8);send_ids(2,3);expect_fault(1); // stale previous-token cohort
  clear;launch;idle(8);send_ids(1,4);expect_fault(2); // wrong layer
  clear;launch;idle(8);send_ids(1,3);idle(2);send_ids(1,3);expect_fault(3); // duplicate
  clear;launch;idle(150);expect_fault(4); // absent IDs miss fixed routed deadline
  $display("ISSUER_CLASS_PASS mut=%0d cycles=%0d checks=%0d total_go=%0d completed=%0d low46_mismatches=0 class_mismatches=0",CMUT,cycles,checks,total_go,total_done);
  $finish;
 end
 initial begin repeat(4000)@(posedge clk);$fatal(1,"ISSUER_CLASS_FAIL exceeded two360edge runs and four bounded cohort cases");end
endmodule

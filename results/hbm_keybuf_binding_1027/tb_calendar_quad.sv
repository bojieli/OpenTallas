`timescale 1ps/1ps
module tb_calendar_quad;
 reg clk=0; initial forever begin #416 clk=1;#417 clk=0;end
 reg rst_n=0,program_we=0,start=0;
 reg[7:0]program_addr=0;reg[255:0]program_data=0;
 reg[11:0]length=0,pitch=0;reg[4:0]n_rows=6;
 wire row_start,ow,oq,qv,key_v,pre_v,lc,lf,le,done,calendar_fault;
 wire[6:0]oi;wire[4:0]qh,key_row,lr,er;wire[7:0]key_index,pre_index;
 wire[3:0]eg;wire[15:0]sop;wire[7:0]sps;wire[31:0]sad;
 ot_hnx_idxn_calendar #(.K(8),.S(4)) calendar(.clk(clk),.clk_mem(clk),.rst_n(rst_n),
 .program_we(program_we),.program_addr(program_addr),.program_data(program_data),
 .start(start),.length(length),.n_rows(n_rows),.pitch(pitch),.row_start(row_start),
 .opr_weight(ow),.opr_query(oq),.opr_index(oi),.qem_v(qv),.qem_head(qh),
 .key_v(key_v),.key_index(key_index),.key_row(key_row),.pre_v(pre_v),.pre_index(pre_index),
 .sel_op(sop),.sel_pass(sps),.sel_addr(sad),.lin_clear(lc),.lin_flush(lf),.lin_row(lr),
 .lout_emit(le),.lout_group(eg),.lout_row(er),.done(done),.fault(calendar_fault));
 wire live_v=key_v&&key_row==0,replay_v=key_v&&key_row!=0;
 reg[17583:0]key_in=0;
 wire[17583:0]key_out,gold_out;wire[3:0]fault,gold_fault;
 ot_hnx_idxn_quad_key_replay dut(.clk(clk),.rst_n(rst_n),.clear({4{start}}),
 .live_v({4{live_v}}),.live_index({4{key_index}}),.pre_v({4{pre_v}}),.pre_index({4{pre_index}}),
 .replay_v({4{replay_v}}),.replay_index({4{key_index}}),.key_in(key_in),.key_out(key_out),.fault(fault));
 for(genvar q=0;q<4;q=q+1)begin:gref
  localparam integer S=q/2,H=q%2;
  ot_hnx_idxn_keybuf #(.NP(4),.RS(0)) gold(.clk(clk),.rst_n(rst_n),.clear(start),.pbase(3'(4*H)),
   .live_v(live_v),.live_index(key_index),.pre_v(pre_v),.pre_index(pre_index),
   .replay_v(replay_v),.replay_index(key_index),.key_in(key_in[S*8792+H*4396+:4396]),
   .key_out(gold_out[S*8792+H*4396+:4396]),.fault(gold_fault[q]));
 end
 integer checks=0,errors=0,live_beats=0,replay_beats=0,cycles=0,done_cycle=-1;
 reg active=0;reg[255:0]program_mem[0:255];string dir;integer words=0;
 always @(negedge clk)if(active)begin
  checks=checks+1;cycles=cycles+1;
  if(key_out!==gold_out||fault!==gold_fault)begin errors=errors+1;if(errors<4)$display("CALENDAR_KEYBUF_MISMATCH cycle=%0d row=%0d beat=%0d",cycles,key_row,key_index);end
  if(calendar_fault||(|gold_fault))begin errors=errors+1;if(errors<4)$display("NATIVE_CALENDAR_FAULT cycle=%0d cal=%b gold=%b",cycles,calendar_fault,gold_fault);end
  if(live_v)live_beats=live_beats+1;
  if(replay_v)replay_beats=replay_beats+1;
  if(done&&done_cycle<0)done_cycle=cycles;
  // Unrelated changing live traffic during replay catches bypass/aliasing errors.
  for(integer z=0;z<17584;z=z+1)key_in[z]=$random;
  for(integer s=0;s<2;s=s+1)for(integer p=0;p<8;p=p+1)
   key_in[s*8792+p*1099+:11]={10'(p*128+int'(key_index)),1'b1};
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR required");
  if(!$value$plusargs("LENGTH=%d",length))$fatal(1,"LENGTH required");
  if(!$value$plusargs("PITCH=%d",pitch))$fatal(1,"PITCH required");
  if(!$value$plusargs("WORDS=%d",words))$fatal(1,"WORDS required");
  $readmemh({dir,"/program.mem"},program_mem,0,words-1);
  repeat(4)@(negedge clk);rst_n=1;
  for(integer i=0;i<words;i=i+1)begin program_we=1;program_addr=8'(i);program_data=program_mem[i];@(negedge clk);end
  program_we=0;repeat(4)@(negedge clk);
  if($test$plusargs("MUT_TAG"))force dut.gq[1].keybuf.gp[0].pc=3'd0;
  start=1;@(negedge clk);start=0;active=1;
  // Bound is derived from the finite static programme and row-launch schedule.
  repeat(length+5*pitch+40)@(negedge clk);
  active=0;
  $display("NATIVE_CALENDAR_QUAD_KEYBUF checks=%0d errors=%0d live=%0d replay=%0d done_cycle=%0d length=%0d pitch=%0d rows=6 clock_ps=833",checks,errors,live_beats,replay_beats,done_cycle,length,pitch);
  if(errors||live_beats!=171||replay_beats!=855||done_cycle<0)$fatal(1,"FAIL");
  $display("NATIVE_CALENDAR_QUAD_KEYBUF PASS");$finish;
 end
endmodule

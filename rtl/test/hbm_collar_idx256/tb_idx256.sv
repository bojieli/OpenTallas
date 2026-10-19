`timescale 1ns/1ps
module tb_idx256;
 parameter integer MUT=0, FAN32=1;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0,cfg_v=0,desc_v=0,launch_v=0;
 reg [11:0] cfg_addr=0;reg[255:0]cfg_data=0;
 wire[0:0]we0,we1;wire[11:0]a0,a1;wire[255:0]d0,d1;
 wire[1535:0]p0,p1;wire s0,s1;wire[1:0]g0,g1;wire[220:0]r0,r1;
 wire rd0,rd1,ac0,ac1,f0,f1;
 ot_hbm_static_cfg_collar #(.PAGE_W(1),.NS(1),.NPR(6),.NREC(8),.NGO(2),.NB(2),.NF(5)) legacy(
 .clk(clk),.clk_in(clk),.rst_n(rst_n),.tgt(8'd120),.cfg_v(cfg_v),.cfg_target(8'd120),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.launch_v(launch_v),.c_busy(2'b0),.c_done(1'b0),.c_fault(5'b0),.pw_we(we0),.pw_addr(a0),.pw_data(d0),.prm(p0),.start_v(s0),.go(g0),.rec(r0),.ready(rd0),.active(ac0),.fault(f0));
 ot_hbm_static_cfg_collar_idx256 #(.PAGE_W(1),.NS(1),.NPR(6),.NREC(8),.NGO(2),.NB(2),.NF(5),.MUT(MUT),.FAN32(FAN32)) guarded(
 .clk(clk),.clk_in(clk),.rst_n(rst_n),.tgt(8'd120),.cfg_v(cfg_v),.cfg_target(8'd120),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.launch_v(launch_v),.c_busy(2'b0),.c_done(1'b0),.c_fault(5'b0),.pw_we(we1),.pw_addr(a1),.pw_data(d1),.prm(p1),.start_v(s1),.go(g1),.rec(r1),.ready(rd1),.active(ac1),.fault(f1));
 bit compare=0,operands_ready=0,forbid_write=0,forbid_start=0;
 integer checks=0,writes=0,launches=0,cases=0,legacy_aliases=0,records=0;
 always @(posedge clk) begin
  #1;
  if(compare)begin
   checks++;
   if({we0,s0,g0,rd0,ac0,f0} !== {we1,s1,g1,rd1,ac1,f1}) $fatal(1,"IDX256_FAIL legacy control identity MUT%0d",MUT);
   if(we1 && {a0,d0} !== {a1,d1}) $fatal(1,"IDX256_FAIL legacy write identity");
   if(operands_ready && p0!==p1)$fatal(1,"IDX256_FAIL operand identity");
   if(|g1 && r0!==r1)$fatal(1,"IDX256_FAIL record identity");
  end
  if(we0 && a0>=256)legacy_aliases++;
  if(we1)begin writes++;if(a1>=256)$fatal(1,"IDX256_FAIL aliased write addr%0d MUT%0d",a1,MUT);end
  if(s1)launches++;
  if(|g1)records++;
  if(forbid_write && we1)$fatal(1,"IDX256_FAIL bad install wrote");
  if(forbid_start && s1)$fatal(1,"IDX256_FAIL bad install launched");
 end
 task automatic edges(input integer n); repeat(n)begin @(posedge clk);#2;end endtask
 task automatic reset_case;
  @(negedge clk);compare=0;operands_ready=0;forbid_write=0;forbid_start=0;rst_n=0;cfg_v=0;desc_v=0;launch_v=0;
  edges(6);@(negedge clk);rst_n=1;edges(6);
 endtask
 task automatic frame(input[11:0]a,input[255:0]d);
  @(negedge clk);cfg_addr=a;cfg_data=d;cfg_v=1;
  @(negedge clk);cfg_v=0;edges(3);
 endtask
 task automatic arm;
  @(negedge clk);desc_v=1;@(negedge clk);desc_v=0;edges(4);
 endtask
 task automatic launch;
  @(negedge clk);launch_v=1;@(negedge clk);launch_v=0;edges(4);
 endtask
 task automatic install256;
  for(integer j=0;j<256;j++) frame(12'(j),{8{32'(j^32'h12345678)}});
 endtask
 initial begin
  // Exact low-range installation, operands, records and two launches across resets.
  for(integer trial=0;trial<2;trial++)begin
   reset_case();compare=1;
   for(integer j=0;j<6;j++)frame(12'h800+12'(j),{8{32'(trial*100+j)}});
   operands_ready=1;
   for(integer j=0;j<8;j++)frame(12'hc00+12'(j),{221'({7{32'(trial*1000+j+1)}}),2'(1+j%3),1'b1,32'(trial==0?(j<4?j:(j<6?j+4:j+11)):(j<2?j:(j<6?j+252:j+504)))});
   frame(12'he00,256'd0);install256();frame(12'he01,256'd256);arm();
   if(!rd1||f1)$fatal(1,"IDX256_FAIL valid256 not ready");launch();edges(trial==0?32:530);
   if(f1||ac1)$fatal(1,"IDX256_FAIL valid256 completion");
   frame(12'd0,256'habc);frame(12'he01,256'd1);arm();launch();edges(trial==0?32:530);cases++;
  end
  reset_case();install256();forbid_write=1;frame(12'd256,256'hbad);
  if(!f1)$fatal(1,"IDX256_FAIL missing row256 rejection MUT%0d",MUT);
  if(legacy_aliases!=1||f0)$fatal(1,"IDX256_FAIL original alias counterexample missing");cases++;
  reset_case();frame(12'he00,256'd256);
  if(!f1)$fatal(1,"IDX256_FAIL missing page rejection MUT%0d",MUT);
  if(f0)$fatal(1,"IDX256_FAIL original page counterexample missing");cases++;
  for(integer k=0;k<4;k++)begin
   reset_case();case(k)
   0:frame(12'he01,256'd257);1:frame(12'he01,256'd4096);
   2:frame(12'he01,256'd65536);3:frame(12'he01,256'hffffffff);
   endcase
   if(!f1)$fatal(1,"IDX256_FAIL missing need rejection MUT%0d k%0d",MUT,k);
   if(f0)$fatal(1,"IDX256_FAIL original need counterexample missing");cases++;
  end
  // An invalid update concurrent with launch must not exploit the old armed state.
  reset_case();for(integer j=0;j<6;j++)frame(12'h800+12'(j),256'd0);
  install256();frame(12'he01,256'd256);arm();forbid_start=1;forbid_write=1;
  @(negedge clk);cfg_addr=12'd256;cfg_data=256'hbad;cfg_v=1;launch_v=1;
  @(negedge clk);cfg_v=0;launch_v=0;edges(5);
  if(!f1)$fatal(1,"IDX256_FAIL concurrent update rejection");cases++;
  if(records!=32)$fatal(1,"IDX256_FAIL record calendar count%0d",records);
  $display("IDX256_PASS cases=%0d identity_edges=%0d writes=%0d launches=%0d legacy_aliases=%0d records=%0d MUT=%0d FAN32=%0d",cases,checks,writes,launches,legacy_aliases,records,MUT,FAN32);$finish;
 end
endmodule

`timescale 1ns/1ps
// Local32-row weight ROM: two real macros alternate beats so q survives to
// a capture TWO edges after read.512useful words total; no ECC/parity.
module ot_dsrom_markov_weight32 #(parameter INSTANCE="mk")(
 input wire clk,rst_n,input wire req_valid,output wire req_ready,input wire[4:0] row,
 output wire out_valid,input wire out_ready,output wire[255:0] out_data,
 output wire[3:0] out_beat,output wire out_last);
 reg busy;reg[4:0] saved_row;reg[4:0] issue_beat;
 reg[3:0] reserved,count;reg[2:0] wp,rp;reg[2:0] v;
 reg[3:0] bp[0:2];reg[255:0] data[0:7];reg[3:0] beats[0:7];
 reg re0,re1;reg[11:0] addr;
 wire[273:0] q0,q1;
 wire issue=busy&&issue_beat<16&&reserved<8;
 wire consume=out_valid&&out_ready;
 assign req_ready=!busy;assign out_valid=count!=0;assign out_data=data[rp];
 assign out_beat=beats[rp];assign out_last=out_beat==15;
 ot_rom_4096x274_m8
`ifndef SYNTHESIS
 #(.INSTANCE($sformatf("%s_0",INSTANCE)))
`endif
 m0(.clk(clk),.ce_in(re0),.addr_in(addr),.rd_out(q0));
 ot_rom_4096x274_m8
`ifndef SYNTHESIS
 #(.INSTANCE($sformatf("%s_1",INSTANCE)))
`endif
 m1(.clk(clk),.ce_in(re1),.addr_in(addr),.rd_out(q1));
 integer i;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin busy<=0;saved_row<=0;issue_beat<=0;reserved<=0;count<=0;wp<=0;rp<=0;v<=0;re0<=0;re1<=0;addr<=0;end
  else begin
   re0<=issue&&!issue_beat[0];re1<=issue&&issue_beat[0];
   if(req_valid&&req_ready)begin busy<=1;saved_row<=row;issue_beat<=0;end
   if(issue)begin addr<={4'b0,saved_row,issue_beat[3:1]};issue_beat<=issue_beat+1;end
   v<={v[1:0],issue};bp[0]<=issue_beat[3:0];for(i=1;i<3;i=i+1)bp[i]<=bp[i-1];
   if(v[2])begin data[wp]<=bp[2][0]?q1[255:0]:q0[255:0];beats[wp]<=bp[2];wp<=wp+1;end
   if(consume)begin rp<=rp+1;if(out_last)busy<=0;end
   case({issue,consume})2'b10:reserved<=reserved+1;2'b01:reserved<=reserved-1;default:;endcase
   case({v[2],consume})2'b10:count<=count+1;2'b01:count<=count-1;default:;endcase
  end
 end
endmodule

// Successor's actual rowstream interface. Embedding row captured once and reused
// across32row-congruent fullK Markov dots; head rows cannot be backpressured,
// therefore a finite2-seat logit queue detects overflow rather than dropping rows.
module ot_dsrom_markov_head_driver #(
 parameter bit ENABLE=0,parameter[8:0] CUT=511,parameter integer SPLIT9=1,
 parameter integer CACHE_PINREG=0,parameter integer VALID_ROWS=32,parameter integer PINREG=0,parameter integer MUTANT_FOLD=0,parameter INSTANCE="mk"
)(input wire clk,rst_n,input wire start,output wire start_ready,
 input wire[16:0] row0,input wire[31:0] transaction,
 input wire embed_valid,output wire embed_ready,input wire[255:0] embed_data,
 input wire[3:0] embed_beat,input wire[31:0] embed_id,input wire embed_last,
 output reg head_go,input wire head_valid,input wire[31:0] head_bits,input wire head_fault,
 output reg joined_valid,output reg[31:0] joined_bits,output reg[16:0] joined_row,
 output reg done,output wire best_valid,output reg[16:0] best_row,output reg[31:0] best_bits,output reg fault);
 reg busy,vector_ready;reg[4:0] embed_next;reg[31:0] identity;reg[16:0] base;
 reg[255:0] vector[0:15];reg[31:0] hq[0:1];reg[4:0] rq[0:1];
 reg hw,hr;reg[1:0] hn;reg[5:0] emitted,completed,valid_count;
 reg active;reg[4:0] active_row;reg[3:0] read_beat;
 wire mk_ready,mk_in_ready,mk_valid,mk_fault;wire[31:0] mk_bits;
 wire wr_ready,wv,wl;wire[255:0] wd;wire[3:0] wb;
 wire launch=ENABLE&&busy&&vector_ready&&!active&&hn!=0&&mk_ready&&wr_ready&&!fault;
 wire wtake=wv&&mk_in_ready;
 assign start_ready=ENABLE&&!busy&&!fault;
 assign best_valid=have&&!fault;
 wire push_head=head_valid&&busy&&vector_ready&&emitted<valid_count&&!fault;
 assign embed_ready=busy&&!vector_ready&&!fault&&embed_next<16;
 wire embed_take=embed_valid&&embed_ready;
 wire embed_good=embed_take&&embed_id==identity&&embed_beat==embed_next&&embed_last==(embed_next==15);
 reg[255:0] embed_q,embed_d;reg[3:0] embed_beat_q;reg embed_last_q,embed_last_d,cache_v;
 (* keep *) reg[16*16-1:0] bank_enable;
 integer ce_bank,ce_rep;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin cache_v<=0;bank_enable<=0;embed_last_q<=0;embed_last_d<=0;embed_beat_q<=0;end
  else begin
   cache_v<=embed_good;embed_beat_q<=embed_beat;embed_last_q<=embed_last;embed_last_d<=embed_last_q;
   for(ce_bank=0;ce_bank<16;ce_bank=ce_bank+1)for(ce_rep=0;ce_rep<16;ce_rep=ce_rep+1)
    bank_enable[ce_bank*16+ce_rep]<=CACHE_PINREG&&cache_v&&embed_beat_q==ce_bank;
  end
 end
 always @(posedge clk)begin embed_q<=embed_data;embed_d<=embed_q;end
 wire cache_commit=CACHE_PINREG&&(|bank_enable);
 integer cache_bank,cache_bit;
 ot_dsrom_markov_weight32 #(.INSTANCE(INSTANCE)) weights(.clk(clk),.rst_n(rst_n),
  .req_valid(launch),.req_ready(wr_ready),.row(rq[hr]),.out_valid(wv),.out_ready(mk_in_ready),.out_data(wd),.out_beat(wb),.out_last(wl));
 ot_dsrom_markov_row #(.K(256),.PINREG(PINREG),.CUT(CUT),.SPLIT9(SPLIT9),.MUTANT_FOLD(MUTANT_FOLD)) dot(
  .clk(clk),.rst_n(rst_n),.start(launch),.start_ready(mk_ready),.head_logit(hq[hr]),
  .in_valid(wv),.in_ready(mk_in_ready),.weight_bf16(wd),.embed_bf16(vector[read_beat]),
  .out_valid(mk_valid),.out_ready(1'b1),.out_bits(mk_bits),.fault(mk_fault));
 wire[31:0] canon=mk_bits == 32'h80000000 ? 32'b0 : mk_bits;
 wire[31:0] key=canon[31]?~canon:{1'b1,canon[30:0]};
 reg[31:0] best_key;reg have;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin busy<=0;vector_ready<=0;embed_next<=0;identity<=0;base<=0;head_go<=0;
   hw<=0;hr<=0;hn<=0;emitted<=0;completed<=0;valid_count<=0;active<=0;active_row<=0;read_beat<=0;
   joined_valid<=0;joined_bits<=0;joined_row<=0;done<=0;best_row<=0;best_bits<=0;best_key<=0;have<=0;fault<=0;
  end else begin
   head_go<=0;joined_valid<=0;
   if(start&&!start_ready)fault<=1;
   if(start&&start_ready)begin
    begin busy<=1;valid_count<=row0>=129280?0:((129280-row0)<VALID_ROWS?129280-row0:VALID_ROWS);vector_ready<=0;embed_next<=0;identity<=transaction;base<=row0;
     hw<=0;hr<=0;hn<=0;emitted<=0;completed<=0;done<=0;have<=0;end
   end
   if(embed_valid&&embed_ready)begin
    if(embed_id!=identity || embed_beat!=embed_next || embed_last!=(embed_next==15))fault<=1;
    else begin embed_next<=embed_next+1;
     if(!CACHE_PINREG)begin vector[embed_next]<=embed_data;
      if(embed_last)begin vector_ready<=1;head_go<=1;end
     end
    end
   end
   if(CACHE_PINREG)begin
    for(cache_bank=0;cache_bank<16;cache_bank=cache_bank+1)for(cache_bit=0;cache_bit<256;cache_bit=cache_bit+1)
     if(bank_enable[cache_bank*16+cache_bit/16])vector[cache_bank][cache_bit]<=embed_d[cache_bit];
    if(cache_commit&&embed_last_d&&!fault)begin vector_ready<=1;head_go<=1;end
   end
   if(head_valid)begin
    if(!busy||!vector_ready||emitted>=32 || (push_head&&hn==2&&!launch))fault<=1;
    else begin emitted<=emitted+1;if(push_head)begin hq[hw]<=head_bits;rq[hw]<=emitted[4:0];hw<=!hw;end end
   end
   if(launch)begin hr<=!hr;active<=1;active_row<=rq[hr];read_beat<=0;end
   case({push_head,launch})2'b10:hn<=hn+1;2'b01:hn<=hn-1;default:;endcase
   if(wtake)begin if(wb!=read_beat||wl!=(read_beat==15))fault<=1;read_beat<=read_beat+1;end
   if(head_fault||mk_fault)fault<=1;
   if(mk_valid)begin
    if(!active||mk_bits[30:23]==8'hff||fault)fault<=1;
    else begin
     joined_valid<=1;joined_bits<=mk_bits;joined_row<=base+active_row;completed<=completed+1;active<=0;
     if(!have||key>best_key||(key==best_key&&base+active_row<best_row))begin
      have<=1;best_key<=key;best_bits<=mk_bits;best_row<=base+active_row;
     end

    end
   end
   if(busy&&vector_ready&&emitted==32&&completed==valid_count&&hn==0&&!active&&!fault)begin done<=1;busy<=0;end
   if(fault)begin joined_valid<=0;done<=0;head_go<=0;end
  end
 end
endmodule

// Existing A remains source-pinned. This successor consumes its actual l_v/l_d;
// its original local argmax is superseded by the post-Markov argmax above.
module ot_dsrom_markov_head_A #(
 parameter bit ENABLE=0,parameter[8:0] CUT=511,parameter integer SPLIT9=1,
 parameter integer CACHE_PINREG=0,parameter integer VALID_ROWS=32,parameter integer PINREG=0,parameter integer MUTANT_FOLD=0,parameter HEAD_INSTANCE="ha",MARKOV_INSTANCE="mk"
)(input wire clk,rst_n,input wire start,output wire start_ready,
 input wire[16:0] row0,input wire[31:0] transaction,
 input wire embed_valid,output wire embed_ready,input wire[255:0] embed_data,
 input wire[3:0] embed_beat,input wire[31:0] embed_id,input wire embed_last,
 input wire[255:0] x,input wire b_v,input wire[31:0] b_d,
 output wire head_go,output wire root_valid,output wire[31:0] root_bits,
 output wire joined_valid,output wire[31:0] joined_bits,output wire[16:0] joined_row,
 output wire done,output wire best_valid,output wire[16:0] best_row,output wire[31:0] best_bits,output wire fault);
 reg[16:0] row0_q;always @(posedge clk)if(start&&start_ready)row0_q<=row0;
 wire hv,hf;wire[31:0] hb;
 ot_dsrom_head_elem #(.LV(8),.PAD(0),.JOIN(1),.ROWS(32),.CUT(CUT),.SPLIT9(SPLIT9),.INSTANCE(HEAD_INSTANCE),.SAFE(1)) head(
 .clk(clk),.rst_n(rst_n),.go(head_go),.row0(row0_q),.x(x),.b_v(b_v),.b_d(b_d),
 .o_v(root_valid),.o_d(root_bits),.l_v(hv),.l_d(hb),.done(),.best_row(),.best_bits(),.best_key(),.fault(hf));
 ot_dsrom_markov_head_driver #(.ENABLE(ENABLE),.CACHE_PINREG(CACHE_PINREG),.VALID_ROWS(VALID_ROWS),.PINREG(PINREG),.CUT(CUT),.SPLIT9(SPLIT9),.MUTANT_FOLD(MUTANT_FOLD),.INSTANCE(MARKOV_INSTANCE)) driver(
 .clk(clk),.rst_n(rst_n),.start(start),.start_ready(start_ready),.row0(row0),.transaction(transaction),
 .embed_valid(embed_valid),.embed_ready(embed_ready),.embed_data(embed_data),.embed_beat(embed_beat),.embed_id(embed_id),.embed_last(embed_last),
 .head_go(head_go),.head_valid(hv),.head_bits(hb),.head_fault(hf),
 .joined_valid(joined_valid),.joined_bits(joined_bits),.joined_row(joined_row),.done(done),.best_valid(best_valid),.best_row(best_row),.best_bits(best_bits),.fault(fault));
endmodule

// Minimum concrete successor with actual token lookup wired to actual A rowstream.
// For a full shard the embedding response is broadcast to its337successors;
// duplicating this506macro lookup per A is NOT the selected die architecture.
module ot_dsrom_markov_head_lookup_A #(
 parameter bit ENABLE=0,parameter integer CACHE_PINREG=0,parameter integer VALID_ROWS=32,parameter integer PINREG=0,parameter integer MUTANT_FOLD=0
)(input wire clk,rst_n,input wire start,output wire start_ready,
 input wire[16:0] d_i,row0,input wire[31:0] transaction,
 input wire[255:0] x,input wire b_v,input wire[31:0] b_d,
 output wire head_go,root_valid,output wire[31:0] root_bits,
 output wire joined_valid,output wire[31:0] joined_bits,output wire[16:0] joined_row,
 output wire done,output wire best_valid,output wire[16:0] best_row,output wire[31:0] best_bits,output wire fault);
 wire dr,er,ev,econsume,el,ef,hf;wire[255:0] ed;wire[3:0] eb;wire[31:0] ei,efid;
 reg lookup_fault;
 wire fire=start&&start_ready;
 assign start_ready=ENABLE&&dr&&er&&!lookup_fault;
 always @(posedge clk or negedge rst_n)if(!rst_n)lookup_fault<=0;else if(ef)lookup_fault<=1;
 assign fault=lookup_fault||hf;
 ot_dsrom_markov_embed_rom #(.ENABLE(ENABLE)) lookup(.clk(clk),.rst_n(rst_n),
 .req_valid(fire),.req_ready(er),.req_token(d_i),.req_id(transaction),.fault_valid(ef),.fault_id(efid),
 .out_valid(ev),.out_ready(econsume),.out_data(ed),.out_id(ei),.out_beat(eb),.out_last(el));
 ot_dsrom_markov_head_A #(.ENABLE(ENABLE),.CACHE_PINREG(CACHE_PINREG),.VALID_ROWS(VALID_ROWS),.PINREG(PINREG),.MUTANT_FOLD(MUTANT_FOLD)) successor(
 .clk(clk),.rst_n(rst_n),.start(fire&&d_i<129280),.start_ready(dr),.row0(row0),.transaction(transaction),
 .embed_valid(ev),.embed_ready(econsume),.embed_data(ed),.embed_beat(eb),.embed_id(ei),.embed_last(el),
 .x(x),.b_v(b_v),.b_d(b_d),.head_go(head_go),.root_valid(root_valid),.root_bits(root_bits),
 .joined_valid(joined_valid),.joined_bits(joined_bits),.joined_row(joined_row),.done(done),.best_valid(best_valid),.best_row(best_row),.best_bits(best_bits),.fault(hf));
endmodule

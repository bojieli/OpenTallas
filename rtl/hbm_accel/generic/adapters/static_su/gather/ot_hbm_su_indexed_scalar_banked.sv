`timescale 1ns/1ps
`default_nettype none
// Same sampled start/read/write phases as the released engine. Requests are
// produced by 32 local headers, rather than clearing/registering 32 wide buses.
module ot_hbm_su_indexed_scalar_banked #(
 parameter integer READ_SAMPLE=9,WRITE_COMMIT=5,SEGMENTED96=0,MUT_PHASE=0
)(input wire clk,rst_n,start,start_aux,input wire[23:0]index_word,score_base,score_limit,dest_word,dyn_mul,
 input wire[71:0]extra_bases,input wire[8223:0]rr,
 output wire[543:0]rq,output wire[8991:0]wq,output reg busy,done,fault);
 localparam SI=READ_SAMPLE+2,SS=2*READ_SAMPLE+2,WI=2*READ_SAMPLE+4,END=WI+WRITE_COMMIT;
 wire[8:0]rrst;
 ot_rst_relay #(.REGIONS(9),.SYNC_STAGES(2),.TREE_STAGES(1)) reset_tree(.clk(clk),.rst_n_in(rst_n),.rst_n(rrst));
 localparam PW=$clog2(END+2);
 reg[PW-1:0]phase;reg[23:0]ix,base,limit,dst,mul,score_address;reg[71:0]bases;
 wire[31:0]index_value;wire[31:0]value[0:1];wire[1023:0]bank_words;wire[31:0]return_valid;
 wire[31:0]returned_word;wire[4:0]ix_expected;wire[4:0]score_expected[0:1];
 wire[23:0]segmented_address;
 for(genvar c=0;c<3;c=c+1)begin:segment_chunk
  ot_hbm_gather_segment_byte #(.N(c)) addr(.index_value(index_value),.base(base),.bases(bases),.q(segmented_address[c*8+:8]));
 end
 wire[55:0]product=SEGMENTED96!=0?56'(segmented_address):56'(index_value)*56'(mul)+56'(base);
 function automatic[4:0]bank_of(input[23:0]a);bank_of={a[17:16],a[5:3]};endfunction
 wire[PW-1:0]local_phase[0:5];
 for(genvar c=0;c<6;c=c+1)begin:phasecopy
  ot_hbm_gather_phase_copy #(.PW(PW)) counter(.clk(clk),.rst_n(rrst[1+c]),.start(c<3?start:start_aux),.busy(running[2]),.q(local_phase[c]));
 end
 wire[2:0]running;
 for(genvar c=0;c<3;c=c+1)begin:busycopy
  ot_hbm_gather_busy_copy copy(.clk(clk),.rst_n(rrst[0]),.start(c==0?start:start_aux),.finish(phase==END),.q(running[c]));
 end
 wire rd_fire,wr_fire;
 ot_hbm_gather_phase_fire #(.SI(SI),.WI(WI)) fire(.phase(16'(local_phase[0])),.busy(busy),.rd(rd_fire),.wr(wr_fire));
 wire[23:0]read_address;
 for(genvar c=0;c<3;c=c+1)begin:read_mux
  ot_hbm_gather_read_byte #(.PW(PW)) mux(.phase(local_phase[0]),.ix(ix[c*8+:8]),.score(score_address[c*8+:8]),.q(read_address[c*8+:8]));
 end
 for(genvar b=0;b<32;b=b+1)begin:bank
  ot_hbm_gather_bank_header #(.B(b)) head(.clk(clk),.rst_n(rrst[1+b/4]),
   .rd_fire(rd_fire),.wr_fire(wr_fire),.read_bank(bank_of(read_address)),.write_bank(bank_of(dst)),
   .read_sector(read_address[18:3]),.write_sector(dst[18:3]),.word_lane(dst[2:0]),.read_word_lane(read_address[2:0]),.value(value[b/16]),
   .rr(rr[b*257+:257]),.returned_word(bank_words[b*32+:32]),.return_valid(return_valid[b]),
   .rq(rq[b*17+:17]),.wq(wq[b*281+:281]));
 end
 for(genvar bit_n=0;bit_n<32;bit_n=bit_n+1)begin:word_or
  wire[31:0]column;
  for(genvar b=0;b<32;b=b+1)begin:bankbit assign column[b]=bank_words[b*32+bit_n];end
  assign returned_word[bit_n]=|column;
 end
 for(genvar b=0;b<4;b=b+1)begin:capture
  ot_hbm_gather_sample_byte #(.EDGE(READ_SAMPLE+MUT_PHASE)) index_capture(.clk(clk),.busy(running[0]),.phase(16'(local_phase[1])),.d(returned_word[b*8+:8]),.q(index_value[b*8+:8]));
  for(genvar c=0;c<2;c=c+1)begin:vcopy
   ot_hbm_gather_sample_byte #(.EDGE(SS)) value_capture(.clk(clk),.busy(running[c]),.phase(16'(local_phase[2+2*c+b/2])),.d(returned_word[b*8+:8]),.q(value[c][b*8+:8]));
  end
 end
 // Descriptor data remains stable for the entire scheduled transaction. Raw
 // local captures avoid a hundreds-of-bits shared load-enable node.
 always @(posedge clk)begin
  ix<=index_word;base<=score_base;limit<=score_limit;dst<=dest_word;mul<=dyn_mul;bases<=extra_bases;
  score_address<=product[23:0];
 end
 ot_hbm_gather_bank_identity_copy ix_copy(.clk(clk),.d(bank_of(index_word)),.q(ix_expected));
 for(genvar c=0;c<2;c=c+1)begin:scorecopy
  ot_hbm_gather_bank_identity_copy score_copy(.clk(clk),.d(bank_of(product[23:0])),.q(score_expected[c]));
 end
 integer k;
 always @(posedge clk or negedge rrst[0])begin
  if(!rrst[0])begin busy<=0;done<=0;fault<=0;phase<=0;end
  else begin
   done<=0;phase<=phase+1;
   if(start)begin
    if(busy)fault<=1;
    else begin
     busy<=1;phase<=0;
     if(index_word>=262144||score_base>=score_limit||score_limit>262144||dest_word>=262144||dyn_mul!=1)fault<=1;
     if(SEGMENTED96!=0 && (score_base+25'd96>score_limit ||
        {1'b0,extra_bases[23:0]}+25'd96>score_limit || {1'b0,extra_bases[47:24]}+25'd96>score_limit ||
        {1'b0,extra_bases[71:48]}+25'd96>score_limit))fault<=1;
    end
   end
   if(busy)begin
    for(k=0;k<32;k=k+1)
     if(return_valid[k]!==((phase==READ_SAMPLE&&k==ix_expected)||(phase==SS&&k==score_expected[k/16])))fault<=1;
    if(phase==READ_SAMPLE+1)begin
     if(product>=56'(limit)||product>=262144 || (SEGMENTED96==0&&product<56'(base)) ||
        (SEGMENTED96!=0&&index_value>=384))fault<=1;
    end
    if(phase==END)begin busy<=0;done<=1;end
   end
  end
 end
endmodule

(* keep_hierarchy *) module ot_hbm_gather_phase_fire #(parameter SI=11,WI=22)(
 input wire[15:0]phase,input wire busy,output wire rd,wr);
 assign rd=busy&&((phase==0)||(phase==SI));assign wr=busy&&(phase==WI);
endmodule

(* keep_hierarchy *) module ot_hbm_gather_bank_header #(parameter integer B=0)(
 input wire clk,rst_n,rd_fire,wr_fire,input wire[4:0]read_bank,write_bank,
 input wire[15:0]read_sector,write_sector,input wire[2:0]word_lane,read_word_lane,input wire[31:0]value,
 input wire[256:0]rr,output wire[31:0]returned_word,output wire return_valid,
 output wire[16:0]rq,output wire[280:0]wq);
 wire rv,wv;wire[3:0]ret_hit;
 wire rd_hit=rd_fire&&(read_bank==5'(B));wire wr_hit=wr_fire&&(write_bank==5'(B));
 ot_hbm_gather_valid_bit rv0(.clk(clk),.rst_n(rst_n),.d(rd_hit),.q(rv));
 ot_hbm_gather_valid_bit wv0(.clk(clk),.rst_n(rst_n),.d(wr_hit),.q(wv));
 for(genvar c=0;c<4;c=c+1)begin:hitcopy
  ot_hbm_gather_valid_bit rv1(.clk(clk),.rst_n(rst_n),.d(rd_hit),.q(ret_hit[c]));
 end
 reg[15:0]rs,ws;reg[2:0]lane,read_lane_cap;reg[31:0]word_q;
 wire[1:0]response;
 for(genvar c=0;c<2;c=c+1)begin:responsecopy
  ot_hbm_gather_reserve_bit v(.clk(clk),.d(rr[256]),.q(response[c]));
 end
 assign return_valid=response[0];
 for(genvar n=0;n<16;n=n+1)begin:readnibble
  ot_hbm_gather_return_nibble #(.N(n)) ret(.clk(clk),.hit(ret_hit[n/4]),.lane(read_lane_cap),
    .rr(rr[255:0]),.v(response[n/8]),.q(returned_word[n*2+:2]));
 end
 // Bank identity sector bits are local constants, avoiding a second global
 // bank-address fanout into each header's data capture.
 always @(posedge clk)begin
  rs<={read_sector[15],2'(B/8),read_sector[12:3],3'(B%8)};
  ws<={write_sector[15],2'(B/8),write_sector[12:3],3'(B%8)};
  lane<=word_lane;read_lane_cap<=read_word_lane;word_q<=value;
 end
 assign rq={rv,rv?rs:16'd0};
 // Invalid request payloads are unqualified; the real bank samples only v=1.
 assign wq={wv,wv?ws:16'd0,{8{word_q}},wv?(8'd1<<lane):8'd0};
endmodule
(* keep_hierarchy *) module ot_hbm_gather_valid_bit(input wire clk,rst_n,d,output reg q);
 always @(posedge clk or negedge rst_n)if(!rst_n)q<=0;else q<=d;
endmodule
(* keep_hierarchy *) module ot_hbm_gather_sample_byte #(parameter integer EDGE=10)(
 input wire clk,busy,input wire[15:0]phase,input wire[7:0]d,output reg[7:0]q);
 always @(posedge clk)if(busy&&phase==EDGE)q<=d;
endmodule
(* keep_hierarchy *) module ot_hbm_gather_return_nibble #(parameter integer N=0)(
 input wire clk,hit,input wire[2:0]lane,input wire[255:0]rr,input wire v,output wire[1:0]q);
 reg[2:0]held_lane;reg[1:0]word_q;
 always @(posedge clk)begin
  if(hit)held_lane<=lane;
  word_q<=rr[held_lane*32+N*2+:2];
 end
 assign q=word_q&{2{v}};
endmodule
(* keep_hierarchy *) module ot_hbm_gather_bank_identity_copy(input wire clk,input wire[4:0]d,output reg[4:0]q);
 always @(posedge clk)q<=d;
endmodule
(* keep_hierarchy *) module ot_hbm_gather_read_byte #(parameter PW=5)(input wire[PW-1:0]phase,input wire[7:0]ix,score,output wire[7:0]q);
 assign q=phase==0?ix:score;
endmodule
(* keep_hierarchy *) module ot_hbm_gather_segment_byte #(parameter N=0)(input wire[31:0]index_value,input wire[23:0]base,input wire[71:0]bases,output wire[7:0]q);
 wire[1:0]rank=index_value<96?0:index_value<192?1:index_value<288?2:3;
 wire[31:0]offset=index_value-(rank==0?0:rank==1?96:rank==2?192:288);
 wire[23:0]selected=rank==0?base:rank==1?bases[23:0]:rank==2?bases[47:24]:bases[71:48];
 wire[31:0]address={8'b0,selected}+offset;
 assign q=address[N*8+:8];
endmodule
(* keep_hierarchy *) module ot_hbm_gather_phase_copy #(parameter PW=5)(input wire clk,rst_n,start,busy,output wire[PW-1:0]q);
 (* keep *) reg[PW-1:0]held;
 always @(posedge clk or negedge rst_n)if(!rst_n)held<=0;else if(start&&!busy)held<=0;else held<=held+1'b1;
 assign q=held;
endmodule
(* keep_hierarchy *) module ot_hbm_gather_busy_copy(input wire clk,rst_n,start,finish,output reg q);
 always @(posedge clk or negedge rst_n)if(!rst_n)q<=0;else begin
  if(start&&!q)q<=1;
  if(q&&finish)q<=0;
 end
endmodule
`default_nettype wire

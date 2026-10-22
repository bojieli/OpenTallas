`timescale 1ns/1ps
`default_nettype none
// Same sampled start/read/write phases as the released engine. Requests are
// produced by 32 local headers, rather than clearing/registering 32 wide buses.
module ot_hbm_su_indexed_scalar_banked_routed #(
 parameter integer READ_SAMPLE=9,WRITE_COMMIT=5,SEGMENTED96=0,MUT_PHASE=0,OUTBOUND_EDGES=0,RETURN_EDGES=0
)(input wire clk,rst_n,start,start_aux,input wire[23:0]index_word,score_base,score_limit,dest_word,dyn_mul,
 input wire[71:0]extra_bases,input wire reserve0,reserve1,input wire[8223:0]rr,
 output wire[31:0]bank_reserve,
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
  wire[82:0]header_in={rd_fire,wr_fire,bank_of(read_address),bank_of(dst),read_address[18:3],dst[18:3],dst[2:0],read_address[2:0],value[b/16],b<16?reserve0:reserve1};
  wire[82:0]header_out;
  ot_hbm_gather_transport_bundle #(.W(83),.EDGES(OUTBOUND_EDGES),.RESET_RELAY(1)) outward(.clk(clk),.rst_n(rrst[1+b/4]),.d(header_in),.q(header_out));
  wire rd_h,wr_h;wire[4:0]rb_h,wb_h;wire[15:0]rs_h,ws_h;wire[2:0]wl_h,rl_h;wire[31:0]value_h;
  assign {rd_h,wr_h,rb_h,wb_h,rs_h,ws_h,wl_h,rl_h,value_h,bank_reserve[b]}=header_out;
  wire[32:0]return_in,return_out;
  ot_hbm_gather_transport_bundle #(.W(33),.EDGES(RETURN_EDGES),.RESET_RELAY(0)) inward(.clk(clk),.rst_n(rrst[1+b/4]),.d(return_in),.q(return_out));
  assign {return_valid[b],bank_words[b*32+:32]}=return_out;
  ot_hbm_gather_bank_header #(.B(b)) head(.clk(clk),.rst_n(rrst[1+b/4]),
   .rd_fire(rd_h),.wr_fire(wr_h),.read_bank(rb_h),.write_bank(wb_h),
   .read_sector(rs_h),.write_sector(ws_h),.word_lane(wl_h),.read_word_lane(rl_h),.value(value_h),
   .rr(rr[b*257+:257]),.returned_word(return_in[31:0]),.return_valid(return_in[32]),
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
`default_nettype wire

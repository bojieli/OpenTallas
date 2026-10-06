`timescale 1ns/1ps
// DEFAULT OFF. Logical W15 separate score/ID word planes, one actual borrowed
// checked512b port. No implicit TOPK->VM copy, cache, extra SRAM or host packing.
// Model before RTL: 593baf8aa, hbm_index_w15_planemajor_model.py.
// N96/NPER512: scores BASEword+rank*32; IDs BASEword+3072+rank*32.
// These are 64-B WORD addresses; installer byte bounds require checked /64.
// The enclosing owner MUST supply the REAL gathered extent and exclusive lease.
module ot_hbm_accel_index_w15_planemajor_formatter #(
 parameter integer ENABLE=0,N=96,NPER=512,AW=32
)(
 input wire clk,por_n,start,output wire start_ready,
 input wire [31:0] source_job,input wire [3:0] source_gen,input wire [19:0] source_pos,
 input wire [AW-1:0] gather_base,input wire [AW:0] gather_limit,
 input wire gather_exclusive,gather_writers_drained,
 output wire retained,output reg fault,
 // The ordered adapter's existing eight-pair request and full source tuple.
 input wire pair_v,output wire pair_r,
 input wire [31:0] pair_job,input wire [3:0] pair_gen,input wire [19:0] pair_pos,
 input wire [6:0] pair_rank,input wire [5:0] pair_word,input wire [15:0] pair_tag,
 output wire pairs_v,input wire pairs_r,output wire [511:0] pairs,
 output wire [31:0] pairs_job,output wire [3:0] pairs_gen,output wire [19:0] pairs_pos,
 output wire [6:0] pairs_rank,output wire [5:0] pairs_word,output wire [15:0] pairs_tag,
 output wire pairs_checked,output wire pairs_uncorrectable,
 // Exactly one outstanding read. Addresses are VM WORDS (not bytes).
 output wire read_v,input wire read_r,output wire [AW-1:0] read_addr,
 output wire read_id,output wire [6:0] read_rank,output wire [15:0] read_tag,
 output wire [31:0] read_job,output wire [3:0] read_gen,output wire [19:0] read_pos,
 input wire rsp_v,output wire rsp_r,input wire [511:0] rsp_data,
 input wire [AW-1:0] rsp_addr,input wire rsp_id,input wire [6:0] rsp_rank,
 input wire [15:0] rsp_tag,input wire [31:0] rsp_job,input wire [3:0] rsp_gen,
 input wire [19:0] rsp_pos,input wire rsp_checked,rsp_uncorrectable,
 // Release only when the enclosing ordered pipeline has actual terminal debt.
 input wire release_v,output wire release_r,
 input wire [31:0] release_job,input wire [3:0] release_gen,input wire [19:0] release_pos,
 input wire publication_done,source_reverse_done
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:disabled
 assign start_ready=0;assign retained=0;assign pair_r=0;assign pairs_v=0;assign pairs=0;
 assign pairs_job=0;assign pairs_gen=0;assign pairs_pos=0;assign pairs_rank=0;assign pairs_word=0;assign pairs_tag=0;
 assign pairs_checked=0;assign pairs_uncorrectable=0;
 assign read_v=0;assign read_addr=0;assign read_id=0;assign read_rank=0;assign read_tag=0;
 assign read_job=0;assign read_gen=0;assign read_pos=0;assign rsp_r=0;assign release_r=0;
 always @*fault=0;
 end else begin:enabled
 initial if(N<1||N>96||NPER<16||NPER>512||NPER%16!=0||AW<13||AW>32)
  $fatal(1,"Bounded W15 source geometry/address width required");
 localparam integer PLANE_WORDS=NPER/16,RANK_WORDS=2*PLANE_WORDS,EXTENT_WORDS=N*RANK_WORDS;
 localparam [3:0] UNBOUND=0,READY=1,SREQ=2,SRSP=3,IREQ=4,IRSP=5,PACK=6,SETTLE=7,RETURN=8,FAIL=9;
 reg [71:0] control_code;
 wire [65:0] control=decode64(control_code);
 wire [3:0] state=control[3:0];wire [1:0] settling=control[5:4];
 reg [71:0] owner_lo,owner_hi,span_lo,span_hi;
 wire [65:0] ol=decode64(owner_lo),oh=decode64(owner_hi);
 wire [65:0] sl=decode64(span_lo),sh=decode64(span_hi);
 wire [127:0] owner={oh[63:0],ol[63:0]},span={sh[63:0],sl[63:0]};
 // owner128={zero43,job32,gen4,pos20,rank7,word6,tag16}
 assign pairs_job=owner[84:53];assign pairs_gen=owner[52:49];assign pairs_pos=owner[48:29];
 assign pairs_rank=owner[28:22];assign pairs_word=owner[21:16];assign pairs_tag=owner[15:0];
 // span128={zero63,limit33,base32}, all address arithmetic33b until checked.
 wire [32:0] held_limit=span[64:32];wire [31:0] held_base=span[31:0];
 wire [32:0] input_end={1'b0,32'(gather_base)}+33'(EXTENT_WORDS);
 wire initial_bounds=input_end<=33'(gather_limit)&&input_end<=(33'd1<<AW);
 reg [71:0] score_code[0:7],id_code[0:7],pair_code[0:7];
 wire [65:0] score_dec[0:7],id_dec[0:7],pair_dec[0:7];
 wire [511:0] score_data,id_data;
 wire [32:0] address_ext={1'b0,held_base}+33'(pairs_rank)*33'(PLANE_WORDS)+
  33'(pairs_word>>1)+(read_id?33'(N*PLANE_WORDS):33'b0);
 wire address_valid=address_ext<held_limit&&address_ext<(33'd1<<AW);
 reg bad;
 always @*begin
  bad=control[65]||ol[65]||oh[65]||sl[65]||sh[65];
  for(integer k=0;k<8;k=k+1)bad=bad||score_dec[k][65]||id_dec[k][65]||pair_dec[k][65];
 end
 for(genvar k=0;k<8;k=k+1)begin:stripes
  assign score_dec[k]=decode64(score_code[k]);assign id_dec[k]=decode64(id_code[k]);assign pair_dec[k]=decode64(pair_code[k]);
  assign score_data[64*k+:64]=score_dec[k][63:0];assign id_data[64*k+:64]=id_dec[k][63:0];
  assign pairs[64*k+:64]=pair_dec[k][63:0];
 end
 assign retained=state!=UNBOUND||bad;
 assign start_ready=state==UNBOUND&&!fault&&!bad&&gather_exclusive&&gather_writers_drained&&initial_bounds;
 wire pair_frame=pair_job==pairs_job&&pair_gen==pairs_gen&&pair_pos==pairs_pos;
 wire pair_bounds=pair_rank<N&&pair_word<NPER/8;
 assign pair_r=state==READY&&!fault&&!bad&&gather_exclusive&&pair_frame&&pair_bounds;
 assign read_id=state==IREQ||state==IRSP;
 assign read_addr=address_ext[AW-1:0];assign read_rank=pairs_rank;assign read_tag=pairs_tag;
 assign read_job=pairs_job;assign read_gen=pairs_gen;assign read_pos=pairs_pos;
 assign read_v=(state==SREQ||state==IREQ)&&!fault&&!bad&&gather_exclusive&&address_valid;
 wire rsp_match=rsp_addr==read_addr&&rsp_id==read_id&&rsp_rank==read_rank&&rsp_tag==read_tag&&
  rsp_job==read_job&&rsp_gen==read_gen&&rsp_pos==read_pos;
 assign rsp_r=(state==SRSP||state==IRSP)&&!fault&&!bad&&gather_exclusive&&address_valid&&rsp_match&&rsp_checked&&!rsp_uncorrectable;
 assign pairs_v=state==RETURN&&!fault&&!bad&&gather_exclusive;
 assign pairs_checked=!bad&&!fault&&state==RETURN;
 assign pairs_uncorrectable=bad;
 wire release_match=release_job==pairs_job&&release_gen==pairs_gen&&release_pos==pairs_pos;
 assign release_r=state==READY&&!fault&&!bad&&gather_exclusive&&release_match&&publication_done&&source_reverse_done;
 integer k;
 reg [127:0] next_owner,next_span;
 function automatic [71:0] ctrl(input [3:0] s,input [1:0] c);
  ctrl=encode64({58'b0,c,s});
 endfunction
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin
   control_code<=ctrl(UNBOUND,0);owner_lo<=encode64(0);owner_hi<=encode64(0);
   span_lo<=encode64(0);span_hi<=encode64(0);fault<=0;
   for(k=0;k<8;k=k+1)begin score_code[k]<=encode64(0);id_code[k]<=encode64(0);pair_code[k]<=encode64(0);end
  end else if(bad||(retained&&!gather_exclusive))begin fault<=1;control_code<=ctrl(FAIL,0);end
  else case(state)
   UNBOUND:if(start)begin
    if(!start_ready)begin fault<=1;control_code<=ctrl(FAIL,0);end
    else begin
     next_owner={43'b0,source_job,source_gen,source_pos,7'b0,6'b0,16'b0};
     next_span={63'b0,33'(gather_limit),32'(gather_base)};
     owner_lo<=encode64(next_owner[63:0]);owner_hi<=encode64(next_owner[127:64]);
     span_lo<=encode64(next_span[63:0]);span_hi<=encode64(next_span[127:64]);
     control_code<=ctrl(READY,0);
    end
   end
   READY:begin
    if(release_v)begin
     if(!release_match)begin fault<=1;control_code<=ctrl(FAIL,0);end
     else if(release_r)control_code<=ctrl(UNBOUND,0);
    end else if(pair_v)begin
     if(!pair_frame||!pair_bounds)begin fault<=1;control_code<=ctrl(FAIL,0);end
     else if(pair_r)begin
      next_owner={43'b0,pair_job,pair_gen,pair_pos,pair_rank,pair_word,pair_tag};
      owner_lo<=encode64(next_owner[63:0]);owner_hi<=encode64(next_owner[127:64]);control_code<=ctrl(SREQ,0);
     end
    end
   end
   SREQ:if(!address_valid)begin fault<=1;control_code<=ctrl(FAIL,0);end
    else if(read_v&&read_r)control_code<=ctrl(SRSP,0);
   IREQ:if(!address_valid)begin fault<=1;control_code<=ctrl(FAIL,0);end
    else if(read_v&&read_r)control_code<=ctrl(IRSP,0);
   SRSP,IRSP:if(rsp_v)begin
    if(!rsp_match||!rsp_checked||rsp_uncorrectable)begin fault<=1;control_code<=ctrl(FAIL,0);end
    else if(rsp_r)begin
     for(k=0;k<8;k=k+1)
      if(state==SRSP)score_code[k]<=encode64(rsp_data[64*k+:64]);
      else id_code[k]<=encode64(rsp_data[64*k+:64]);
     control_code<=ctrl(state==SRSP?IREQ:PACK,0);
    end
   end
   PACK:begin
    for(k=0;k<8;k=k+1)pair_code[k]<=encode64({id_data[32*(k+(pairs_word[0]?8:0))+:32],score_data[32*(k+(pairs_word[0]?8:0))+:32]});
    control_code<=ctrl(SETTLE,0);
   end
   SETTLE:if(settling==2)control_code<=ctrl(RETURN,0);
    else control_code<=ctrl(SETTLE,settling+1);
   RETURN:if(pairs_v&&pairs_r)control_code<=ctrl(READY,0);
   default:control_code<=ctrl(FAIL,0);
  endcase
 end
 end endgenerate
endmodule

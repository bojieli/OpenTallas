`timescale 1ns/1ps
// Correctness-only opt-in DS20 SM0 borrower. Model: main6647d7c8e.
// No memory allocation, new backing RAM, implicit TOPK store, or timing credit.
// The installer loads the compiler's eight private CMD64 words, then supplies
// real occupied/free-book validation. The shared arbiter owns grant/drain.
// Native collective producers MUST hold requests under req_r refusal. Original
// ot_w15_coll_dma GW1 has no scalar write-ready: it cannot attach unchanged.
module ot_hbm_integrated_gather_bridge #(
 parameter integer ENABLE=0, VM_AW=0
)(
 input wire clk,por_n,
 input wire desc_v, output wire desc_r, input wire [2:0] desc_index,
 input wire [63:0] desc_data,
 input wire start_v, output wire start_r, input wire installed_book_valid,
 input wire [31:0] job, input wire [3:0] gen,
 input wire [16:0] token, input wire [19:0] pos,
 output wire borrow_v, input wire borrow_granted,borrow_fault,
 output wire retained,arena_visible,sink_visible,fault,
 output wire [31:0] bound_arena_base,bound_arena_limit,
 // All addresses here are BYTE addresses. kind: 0 source read, 1 score
 // store, 2 ID store, 3 formatter read, 4 final ID sink store.
 input wire req_v, output wire req_r, input wire [2:0] req_kind,
 input wire [31:0] req_addr, input wire [15:0] req_tag,
 input wire [6:0] req_rank, input wire [5:0] req_word,
 input wire [511:0] req_data,
 input wire [31:0] req_job, input wire [3:0] req_gen,
 input wire [16:0] req_token, input wire [19:0] req_pos,
 output wire rsp_v, input wire rsp_r, output wire [511:0] rsp_data,
 output wire [31:0] rsp_addr, output wire [15:0] rsp_tag,
 output wire [2:0] rsp_kind, output wire rsp_checked,
 output wire [31:0] held_job, output wire [3:0] held_gen,
 output wire [16:0] held_token, output wire [19:0] held_pos,
 // Connect to shared borrower's existing SM-side AW3 CDC, not a new port.
 output wire m_req_v, input wire m_req_rdy, output wire m_req_we,
 output wire [31:0] m_req_addr, output wire [255:0] m_req_wdata,
 output wire [31:0] m_req_wstrb, output wire [15:0] m_req_tag,
 input wire m_rsp_v, output wire m_rsp_rdy, input wire m_rsp_we,
 input wire [255:0] m_rsp_data, input wire [15:0] m_rsp_tag,
 input wire release_v, output wire release_r,
 input wire [31:0] release_job, input wire [3:0] release_gen,
 input wire [16:0] release_token, input wire [19:0] release_pos,
 input wire result_published,source_reverse_done,
 output wire borrow_release,input wire borrow_release_ack
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(ENABLE==0)begin:off
 assign desc_r=0;assign start_r=0;assign borrow_v=0;assign retained=0;
 assign arena_visible=0;assign sink_visible=0;assign fault=0;
 assign bound_arena_base=0;assign bound_arena_limit=0;
 assign req_r=0;assign rsp_v=0;assign rsp_data=0;assign rsp_addr=0;
 assign rsp_tag=0;assign rsp_kind=0;assign rsp_checked=0;
 assign held_job=0;assign held_gen=0;assign held_token=0;assign held_pos=0;
 assign m_req_v=0;assign m_req_we=0;assign m_req_addr=0;
 assign m_req_wdata=0;assign m_req_wstrb=0;assign m_req_tag=0;
 assign m_rsp_rdy=0;assign release_r=0;assign borrow_release=0;
 end else begin:on
 initial if(VM_AW<13||VM_AW>26)$fatal(1,"Installer-derived W15 aperture required");
 // 35 protected rows = 2520 FF, below 4104 estimate; no extra raw payload FF.
 // Rows: descriptor8, valid1, frame2, control1, request1, counts1, sequence1,
 // two 96-rank seen sets4, request5128, return5128. Common transport holds the sector before capture.
 reg [71:0] code[0:34]; wire [65:0] dec[0:34];
 wire [63:0] d[0:34]; reg bad;
 for(genvar k=0;k<35;k=k+1)begin:rows
  assign dec[k]=decode64(code[k]);assign d[k]=dec[k][63:0];
 end
 always @*begin bad=0;for(integer k=0;k<35;k=k+1)bad=bad||dec[k][65];end
 localparam [3:0] IDLE=0,ADMIT=1,READY=2,ENC=3,SEND=4,WAIT_RSP=5,
   DEC=6,NEXT=7,RETURN=8,RELEASE1=9,RELEASE2=10,FAIL=15;
 wire [3:0] state=d[11][3:0];wire [3:0] ticks=d[11][7:4];
 wire sector=d[11][8],verify=d[11][9];
 wire [3:0] next_tick=ticks+4'd1;
 wire [31:0] base=d[2][31:0],limit=d[2][63:32];
 assign bound_arena_base=base;assign bound_arena_limit=limit;
 wire [31:0] sink_base=d[3][31:0],sink_limit=d[3][63:32];
 wire [32:0] capacity=d[4][32:0];
 wire [31:0] score_src=d[1][31:0],id_src=d[1][63:32];
 wire [32:0] base_end={1'b0,base}+33'd393216;
 wire [32:0] sink_end={1'b0,sink_base}+33'd2048;
 wire [32:0] score_end={1'b0,score_src}+33'd2048,id_end={1'b0,id_src}+33'd2048;
 function automatic overlap(input [32:0] a,b,c,e);overlap=(a<e&&c<b);endfunction
 wire bounds=d[8][7:0]==8'hff&&d[5]==(64'd96|(64'd512<<16)|(64'd32<<32))&&
  d[6]==0&&d[7]==0&&d[4][63:33]==0&&capacity>0&&capacity<=(33'd1<<32)&&
  {base[5:0],limit[5:0],sink_base[5:0],sink_limit[5:0],score_src[5:0],id_src[5:0]}==0&&
  base_end=={1'b0,limit}&&sink_end=={1'b0,sink_limit}&&
  base_end<=capacity&&sink_end<=capacity&&score_end<=capacity&&id_end<=capacity&&
  base_end<=(33'd1<<(VM_AW+6))&&sink_end<=(33'd1<<(VM_AW+6))&&
  score_end<=(33'd1<<(VM_AW+6))&&id_end<=(33'd1<<(VM_AW+6))&&
  !overlap({1'b0,base},base_end,{1'b0,sink_base},sink_end)&&
  !overlap({1'b0,base},base_end,{1'b0,score_src},score_end)&&
  !overlap({1'b0,base},base_end,{1'b0,id_src},id_end)&&
  !overlap({1'b0,sink_base},sink_end,{1'b0,score_src},score_end)&&
  !overlap({1'b0,sink_base},sink_end,{1'b0,id_src},id_end)&&
  !overlap({1'b0,score_src},score_end,{1'b0,id_src},id_end);
 wire [127:0] frame={d[10],d[9]};
 assign held_job=frame[31:0];assign held_gen=frame[35:32];
 assign held_token=frame[52:36];assign held_pos=frame[72:53];
 wire frame_match=req_job==held_job&&req_gen==held_gen&&req_token==held_token&&req_pos==held_pos;
 wire release_match=release_job==held_job&&release_gen==held_gen&&release_token==held_token&&release_pos==held_pos;
 wire [11:0] score_count=d[13][11:0],id_count=d[13][23:12];
 wire [5:0] sink_count=d[13][29:24];
 wire [95:0] score_seen={d[16][31:0],d[15]},id_seen={d[18][31:0],d[17]};
 assign arena_visible=score_count==3072&&id_count==3072&&!fault;
 assign sink_visible=sink_count==32&&!fault;
 wire [32:0] req_end={1'b0,req_addr}+33'd64;
 wire source_range=({1'b0,req_addr}>={1'b0,score_src}&&req_end<=score_end)||
  ({1'b0,req_addr}>={1'b0,id_src}&&req_end<=id_end);
 wire [32:0] score_expected={1'b0,base}+33'(req_rank)*2048+33'(score_count/96)*64;
 wire [32:0] id_expected={1'b0,base}+196608+33'(req_rank)*2048+33'(id_count/96)*64;
 wire [32:0] sink_expected={1'b0,sink_base}+33'(sink_count)*64;
 reg legal;
 always @*begin
  legal=0;
  if(req_addr[5:0]==0&&req_end<=capacity&&req_end<=(33'd1<<(VM_AW+6)))
   case(req_kind)
    0:legal=source_range&&!arena_visible;
    1:legal=score_count<3072&&req_rank<96&&32'(req_word)==32'(score_count)/96&&
       !score_seen[req_rank]&&{1'b0,req_addr}==score_expected;
    2:legal=score_count==3072&&id_count<3072&&req_rank<96&&32'(req_word)==32'(id_count)/96&&
       !id_seen[req_rank]&&{1'b0,req_addr}==id_expected;
    3:legal=arena_visible&&{1'b0,req_addr}>={1'b0,base}&&req_end<=base_end;
    4:legal=arena_visible&&sink_count<32&&{1'b0,req_addr}==sink_expected;
    default:legal=0;
   endcase
 end
 assign fault=bad||state==FAIL||borrow_fault;
 assign retained=state!=IDLE||bad;
 assign desc_r=state==IDLE&&!fault&&!start_v;
 assign borrow_v=start_v&&state==IDLE&&bounds&&installed_book_valid&&!fault;
 assign start_r=borrow_v&&borrow_granted;
 assign req_r=state==READY&&borrow_granted&&!fault&&frame_match&&legal&&d[14]<65532;
 wire [31:0] addr=d[12][31:0];wire [15:0] tag=d[12][47:32];
 wire [2:0] kind=d[12][50:48];wire [6:0] rank=d[12][57:51];
 wire is_write=kind==1||kind==2||kind==4;
 wire [511:0] write_data,read_data;
 for(genvar k=0;k<8;k=k+1)begin:payload
  assign write_data[64*k+:64]=d[19+k];assign read_data[64*k+:64]=d[27+k];
 end
 assign m_req_v=state==SEND&&borrow_granted&&!fault;
 assign m_req_we=is_write&&!verify;
 assign m_req_addr=addr+(sector?32'd32:0);
 assign m_req_wdata=sector?write_data[511:256]:write_data[255:0];
 assign m_req_wstrb=m_req_we?32'hffffffff:0;
 // Independent sector sequence; caller's logical tag retained separately.
 assign m_req_tag=d[14][15:0];
 wire rsp_match=m_rsp_tag==m_req_tag&&m_rsp_we==m_req_we;
 assign m_rsp_rdy=state==WAIT_RSP&&borrow_granted&&!fault&&rsp_match;
 assign rsp_v=state==RETURN&&borrow_granted&&!fault;
 assign rsp_data=read_data;assign rsp_addr=addr;assign rsp_tag=tag;assign rsp_kind=kind;
 // checked means local W6 capture + write/readback comparison, NOT HBM ECC proof.
 assign rsp_checked=rsp_v;
 assign release_r=state==READY&&sink_visible&&release_match&&result_published&&source_reverse_done&&!fault;
 assign borrow_release=state==RELEASE2&&!fault;
 function automatic [71:0] ctrl(input [3:0] s,input [3:0] t,input sec,v);
  reg [63:0] raw;
  begin
   raw=64'b0;raw[3:0]=s;raw[7:4]=t;raw[8]=sec;raw[9]=v;
   ctrl=encode64(raw);
  end
 endfunction
 integer k;reg [95:0] seen;reg [127:0] new_frame;
 wire [255:0] captured=sector?read_data[511:256]:read_data[255:0];
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin for(k=0;k<35;k=k+1)code[k]<=encode64(0);end
  else if(fault||(retained&&!borrow_granted&&state!=RELEASE2))code[11]<=ctrl(FAIL,0,0,0);
  else case(state)
   IDLE:begin
    if(desc_v&&desc_r)begin code[integer'(desc_index)]<=encode64(desc_data);code[8]<=encode64(d[8]|(64'd1<<desc_index));end
    if(start_v)begin
     if(!bounds||!installed_book_valid)code[11]<=ctrl(FAIL,0,0,0);
     else if(start_r)begin
      new_frame={55'b0,pos,token,gen,job};code[9]<=encode64(new_frame[63:0]);code[10]<=encode64(new_frame[127:64]);
      code[13]<=encode64(0);code[14]<=encode64(0);code[15]<=encode64(0);code[16]<=encode64(0);code[17]<=encode64(0);code[18]<=encode64(0);
      code[11]<=ctrl(ADMIT,0,0,0);
     end
    end
   end
   ADMIT:if(ticks==15)code[11]<=ctrl(READY,0,0,0);else code[11]<=ctrl(ADMIT,next_tick,0,0);
   READY:begin
    if(release_v)begin
     if(!release_match)code[11]<=ctrl(FAIL,0,0,0);
     else if(release_r)code[11]<=ctrl(RELEASE1,0,0,0);
    end else if(req_v)begin
     if(!frame_match||!legal)code[11]<=ctrl(FAIL,0,0,0);
     else if(req_r)begin
      code[12]<=encode64({req_word,req_rank,req_kind,req_tag,req_addr});
      for(k=0;k<8;k=k+1)code[19+k]<=encode64(req_data[64*k+:64]);
      code[11]<=ctrl(ENC,0,0,0);
     end
    end
   end
   ENC:if(ticks==1)code[11]<=ctrl(SEND,0,sector,verify);else code[11]<=ctrl(ENC,next_tick,sector,verify);
   SEND:if(m_req_v&&m_req_rdy)code[11]<=ctrl(WAIT_RSP,0,sector,verify);
   WAIT_RSP:if(m_rsp_v)begin
    if(!rsp_match)code[11]<=ctrl(FAIL,0,sector,verify);
    else if(m_rsp_rdy)begin
     if(!is_write||verify)
      for(k=0;k<4;k=k+1)code[27+4*integer'(sector)+k]<=encode64(m_rsp_data[64*k+:64]);
     code[11]<=ctrl(DEC,0,sector,verify);
    end
   end
   DEC:if(ticks==2)begin
    if(is_write&&verify&&captured!=(sector?write_data[511:256]:write_data[255:0]))code[11]<=ctrl(FAIL,0,sector,verify);
    else begin
     code[14]<=encode64(d[14]+1);code[11]<=ctrl(NEXT,0,sector,verify);
    end
   end else code[11]<=ctrl(DEC,next_tick,sector,verify);
   NEXT:begin
    // Both write ACKs precede both readbacks; visibility advances only after
    // all four matched sector responses and full original-payload comparison.
    if(!sector)code[11]<=ctrl(ENC,0,1,verify);
    else if(is_write&&!verify)code[11]<=ctrl(ENC,0,0,1);
    else begin
     if(kind==1)begin
      code[13]<=encode64(d[13]+1);seen=score_seen|(96'd1<<rank);
      if(score_count%96==95)seen=0;
      code[15]<=encode64(seen[63:0]);code[16]<=encode64({32'b0,seen[95:64]});
     end else if(kind==2)begin
      code[13]<=encode64(d[13]+(64'd1<<12));seen=id_seen|(96'd1<<rank);
      if(id_count%96==95)seen=0;
      code[17]<=encode64(seen[63:0]);code[18]<=encode64({32'b0,seen[95:64]});
     end else if(kind==4)code[13]<=encode64(d[13]+(64'd1<<24));
     code[11]<=ctrl(RETURN,0,0,0);
    end
   end
   RETURN:if(rsp_v&&rsp_r)code[11]<=ctrl(READY,0,0,0);
   RELEASE1:code[11]<=ctrl(RELEASE2,0,0,0);
   RELEASE2:if(borrow_release_ack)begin code[11]<=ctrl(IDLE,0,0,0);code[8]<=encode64(0);end
   default:code[11]<=ctrl(FAIL,0,0,0);
  endcase
 end
 end endgenerate
endmodule

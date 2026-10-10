`timescale 1ns/1ps
`default_nettype none
// ot_hgi_quant_vm_transport_p: the pipelined (accelerator-style) successor of ot_hgi_quant_vm_transport
// (hgi-1010/d5, 2026-10-10).  Same ports, same CP sector ABI (req 337 / rsp 273, rsp[256] = WRITE_ECHO), same
// transaction semantics; only the cycle at which things happen moves.  Selected by ot_hgi_quant_unit PIPE=1
// (opt-in; the historical module stays byte-identical).
//
// Why (placement STA of hgi_quant_vm_pd50-f4b0ce450-serial, 3_4_place_resized, TT): 20,202 reg2reg endpoints < 0, of
// which 16,380 are the 32 x 512 flop result array (vo -> tail decode -> 16k enables, -453 ps), 1,024 the x lanes
// (response tag compare -> 1,024 enables / lane muxes, -898 ps), 300 the request staging cone (read_row == m ->
// burst / last / step -> address adds -> seat, -803..-854 ps), cmd[0] -> 1,409 cq enables (IO -630 ps), and the
// parallel span multiplier (-1,098 ps; that route never passed SERIAL_SHAPE=1).  Async reset reached 1,363 payload
// flops (-397 ps recovery).  Root causes, and the structure here:
//   1. command station: cq captures cmd every edge with no enable and no reset; only cq_v = ready & cmd[0] is a
//      control flop (the pin flop is a plain D flop at the pin);
//   2. span check: the serial one-add-per-edge products only (SERIAL_SHAPE=1 behaviour; no multiplier);
//   3. result store: a first-word-fall-through FIFO on one ot_sram_1r1w_64x512_m1_r2c2 macro (ot_fifo_sram_fwft)
//      instead of 16,384 flops; queued counts pushed-not-popped entries (fault drain empties it);
//   4. request staging: the next read request and the next write request (address, step, last / final flags, write
//      data, next stream state) are computed from registered state one cycle ahead into p_* registers; a stage
//      only selects one of the two precomputed descriptors and copies its next state (a stage invalidates the
//      precompute for one cycle: p_ok).  The seat already restaged at most every second cycle, so the request rate
//      is unchanged;
//   5. response lanes: the response edge (R1) registers per-lane write enable / zero / source lane plus a copy of the
//      data; the lanes update at R2 and the decode launch moves one edge later (launch_q -> launch), so the decoder
//      still samples a complete beat;
//   6. payload registers (cq, response data, x, rd2) carry no reset: every one is qualified by a reset control valid.
// Added latency: +1 edge a beat (launch), +1 edge per FIFO landing, +1 edge to the first request of a record.
// MUTANT (bench): 1..4 as the historical module; 5 = launch not delayed (decoder samples x before R2 lands);
// 6 = the write precompute trusts the entry count instead of the landed FIFO head (queued != 0, head not yet read out
// of the macro); both must FAIL the exact gates.  (A stage-validity mutant is not observable: the seat cannot restage
// on the edge after a stage, so p_ok is always fresh -- kept as a structural guard.)
module ot_hgi_quant_vm_transport_p #(parameter ENABLE=0, DEPTH=32, MUTANT=0)(
 input wire clk,rst_n,input wire [1408:0] cmd,
 output wire ready,output reg done,output reg fault,output wire drained,
 output wire req_v,input wire req_r,output wire [336:0] req,
 input wire rsp_v,output wire rsp_r,input wire [272:0] rsp,
 input wire provider_fault
);
 localparam CW=$clog2(DEPTH+1);
 // registered reset: async assert, release two edges after rst_n
 reg [1:0] rq; always @(posedge clk or negedge rst_n) if(!rst_n) rq<=2'b00; else rq<={rq[0],1'b1};
 wire rn=rq[1];
 // ---------------------------------------------------------------- command station (1)
 reg cq_v; reg [1408:0] cq;
 always @(posedge clk) cq<=cmd;
 wire [127:0] incoming_header=cq[1+:128];
 wire [255:0] ca=cq[385+:256],co=cq[1153+:256];
 reg [255:0] a,o;reg validating; reg val2, val3, val4; reg [63:0] aspan_q,ospan_q;
 reg shape_active, val_sum; reg [4:0] shape_bit;
 reg [63:0] ar_acc,ac_acc,or_acc,oc_acc;
 reg [63:0] ar_mc,ac_mc,or_mc,oc_mc;
 reg [19:0] ar_count,ac_count,or_count,oc_count;
 wire [127:0] ch=header;
 reg busy,bad;
 reg seat_v;reg [336:0] seat;
 reg response_v;reg [272:0] response;
 reg [127:0] header;
 reg [19:0] n,m,read_row,read_col,write_row,write_col;
 reg [39:0] launched,returned,finished;
 reg [31:0] read_addr,write_addr,read_rowbase,write_rowbase,rs,ws;
 reg [15:0] ri,wi;
 reg [5:0] read_part,write_part;
 reg [15:0] next_tag;
 reg [1023:0] x;
 reg launch, launch_q;
 reg [CW-1:0] reserved,queued;
 wire vo,qfault,decode_fault;wire [511:0] y;
 ot_hgi_quant_decode quant(.clk(clk),.rst_n(rn),.v(launch),
 .generic_enable(1'b1),.legacy_fp4(1'b0),.header(header),.x(x),
 .vo(vo),.y(y),.fault(qfault),.decode_fault(decode_fault));
 wire [15:0] air=a[5]?16'd0:(a[135:120]==0?16'd1:a[135:120]);
 wire [15:0] oir=o[135:120]==0?16'd1:o[135:120];
 wire same_geometry=a[47:8]==o[47:8] && air==oir && a[119:88]==o[119:88];
 wire fields_ok=ch[127:124]==4 && ch[123:118]>=4 && ch[123:118]<=6 &&
 ch[99:93]==7'b0010001 && !ch[92] &&
 (ch[123:118]!=6 || ch[71:64]==16) && a[1:0]==1 && o[1:0]==1 &&
 a[4:2]==0 && (o[4:2]==0 || o[4:2]==1) && !o[5] &&
 a[87:68]!=0 && a[87:68]==o[87:68] && a[67:48]!=0 && a[67:48]==o[67:48] &&
 (ch[123:118]==6 ? a[51:48]==0 : a[52:48]==0);
 reg fields_q, same_q, nalias_q, shape_q; reg [63:0] aend_q, oend_q;
 wire shape_ok=fields_q && (aend_q<64'd262144) && (oend_q<64'd262144) &&
 (!same_q || nalias_q) && (same_q || (aend_q<{24'd0,o[47:8]}) || (oend_q<{24'd0,a[47:8]}));
 reg [63:0] orow_q;
 assign ready=ENABLE&&rn&&!busy&&!cq_v;
 // ---------------------------------------------------------------- result store (3)
 wire hv, fovf; wire [511:0] fhead;
 wire push=vo&&!bad&&MUTANT!=1;
 wire pop;
 ot_fifo_sram_fwft #(.W(512),.DEPTH(DEPTH),.MACRO(0)) u_res(.clk(clk),.rst_n(rn),.push(push),.wdata(y),.pop(pop),
  .hv(hv),.head(fhead),.ovf(fovf));
 // ---------------------------------------------------------------- in-flight descriptors (in request order)
 localparam integer DW=1+4+3+6+1+1+1+16;
 reg [DW-1:0] pd [0:3]; reg [1:0] pd_h,pd_t; reg [2:0] pd_n; reg [DW-1:0] seat_d;
 wire pending=pd_n!=0;
 assign drained=!busy&&!pending&&reserved==0;
 assign req_v=ENABLE&&rn&&seat_v&&!bad;
 assign req=seat;
 assign rsp_r=ENABLE&&rn;                     // never back-pressured: one response a cycle is processed
 wire take_req=req_v&&req_r,take_rsp=response_v;
 wire [DW-1:0] dsc=(MUTANT==4)?pd[pd_t-2'd1]:pd[pd_h];
 wire d_we=dsc[DW-1]; wire [3:0] d_step=dsc[DW-2-:4]; wire [2:0] d_lane=dsc[DW-6-:3]; wire [5:0] d_part=dsc[DW-9-:6];
 wire d_lastr=dsc[18]; wire d_lastw=dsc[17]; wire d_final=dsc[16]; wire [15:0] d_tag=dsc[15:0];
 wire reply_ok=response[272:257]==d_tag && response[256]==d_we;
 // ---------------------------------------------------------------- request precompute (4): from registered state only
 wire r_burst=ri==1 && read_addr[2:0]==0 && n-read_col>=8 && 32-read_part>=8;
 wire [3:0] r_step=r_burst?4'd8:4'd1;
 wire r_rowend=read_col+r_step==n;
 wire r_last=read_part+r_step==32 || r_rowend;
 wire w_burst=wi==1 && write_addr[2:0]==0 && n-write_col>=8 && 32-write_part>=8;
 wire [3:0] w_step=w_burst?4'd8:4'd1;
 wire w_rowend=write_col+w_step==n;
 wire w_last=write_part+w_step==32 || w_rowend;
 wire w_final=w_last&&write_row+1==m&&w_rowend;
 reg [255:0] wd;
 always @* begin
  wd=0;
  if(w_burst)for(integer j=0;j<8;j=j+1)
    wd[j*32+:32]={fhead[(write_part+j)*16+:16],16'd0};
  else wd[write_addr[2:0]*32+:32]={fhead[write_part*16+:16],16'd0};
 end
 wire [31:0] wmask=w_burst?32'hffffffff:(32'hf<<(write_addr[2:0]*4));
 reg p_ok,pw_ok,p_rdone;
 reg [31:0] p_r_addr,p_w_addr; reg [3:0] p_r_step,p_w_step; reg p_r_last,p_w_last,p_w_final;
 reg [5:0] p_r_part,p_w_part,p_r_part_n,p_w_part_n;
 reg [19:0] p_r_row_n,p_r_col_n,p_w_row_n,p_w_col_n;
 reg [31:0] p_r_addr_n,p_r_rowbase_n,p_w_addr_n,p_w_rowbase_n;
 reg [255:0] p_wd; reg [31:0] p_wmask;
 wire wsel=pw_ok && (p_rdone || (reserved>=DEPTH && MUTANT!=3));
 wire rsel=!p_rdone && (p_r_part!=0 || (reserved<DEPTH || MUTANT==3));
 wire ctl_run=busy&&!validating&&!val_sum&&!val2&&!val3&&!val4;
 wire stage=ctl_run&&!bad&&!launch&&!launch_q&&p_ok&&(wsel||rsel)&&!seat_v&&pd_n<3'd4;
 wire stw=wsel;
 wire reserve_read=stage&&!stw&&p_r_part==0;
 wire retire_write=take_rsp&&reply_ok&&d_we&&d_lastw&&!bad;
 assign pop=(stage&&stw&&p_w_last) || (bad&&hv);
 always @(posedge clk) begin                  // payload registers of the precompute: no reset (qualified by p_ok)
  p_r_addr<=read_addr; p_r_step<=r_step; p_r_last<=r_last; p_r_part<=read_part;
  p_r_part_n<=r_last?6'd0:read_part+r_step;
  if(r_rowend)begin p_r_row_n<=read_row+1;p_r_col_n<=0;p_r_rowbase_n<=read_rowbase+rs;p_r_addr_n<=read_rowbase+rs;end
  else begin p_r_row_n<=read_row;p_r_col_n<=read_col+r_step;p_r_rowbase_n<=read_rowbase;p_r_addr_n<=read_addr+(r_burst?{ri,3'd0}:{3'd0,ri});end
  p_w_addr<=write_addr; p_w_step<=w_step; p_w_last<=w_last; p_w_final<=w_final; p_w_part<=write_part;
  p_w_part_n<=w_last?6'd0:write_part+w_step;
  if(w_rowend)begin p_w_row_n<=write_row+1;p_w_col_n<=0;p_w_rowbase_n<=write_rowbase+ws;p_w_addr_n<=write_rowbase+ws;end
  else begin p_w_row_n<=write_row;p_w_col_n<=write_col+w_step;p_w_rowbase_n<=write_rowbase;p_w_addr_n<=write_addr+(w_burst?{wi,3'd0}:{3'd0,wi});end
  p_wd<=wd; p_wmask<=wmask;
 end
 // ---------------------------------------------------------------- response lanes (5): R1 decides, R2 writes
 reg [255:0] rd2; reg [31:0] xe_q,xz_q; reg [95:0] xs_q;
 always @(posedge clk) rd2<=response[255:0];
 always @(posedge clk) response<=rsp;         // payload: qualified by response_v
 always @(posedge clk or negedge rn)begin
  if(!rn)begin xe_q<=0;xz_q<=0;xs_q<=0;end
  else for(integer lane=0;lane<32;lane=lane+1)begin
   xe_q[lane]<=0;xz_q[lane]<=0;
   if(take_rsp&&reply_ok&&!d_we&&!bad)begin
    if(d_step==8 && lane>=d_part && lane<d_part+8)begin xe_q[lane]<=1;xs_q[lane*3+:3]<=lane-d_part;end
    else if(d_step==1 && lane==d_part)begin xe_q[lane]<=1;xs_q[lane*3+:3]<=d_lane;end
    else if(d_part==0)begin xe_q[lane]<=1;xz_q[lane]<=1;end
   end
  end
 end
 for(genvar lane=0;lane<32;lane=lane+1)begin:g_input_lane
  always @(posedge clk)
   if(xe_q[lane]) x[lane*32+:32]<=xz_q[lane]?32'd0:rd2[xs_q[lane*3+:3]*32+:32];
 end
 // ---------------------------------------------------------------- control
 always @(posedge clk or negedge rn)begin
  if(!rn)begin
   shape_active<=0;val_sum<=0;shape_bit<=0;
   ar_acc<=0;ac_acc<=0;or_acc<=0;oc_acc<=0;
   ar_mc<=0;ac_mc<=0;or_mc<=0;oc_mc<=0;
   ar_count<=0;ac_count<=0;or_count<=0;oc_count<=0;
   cq_v<=0;val2<=0;val3<=0;val4<=0;aspan_q<=0;ospan_q<=0;orow_q<=0;
   fields_q<=0;same_q<=0;nalias_q<=0;shape_q<=0;aend_q<=0;oend_q<=0;
   a<=0;o<=0;validating<=0;busy<=0;bad<=0;seat_v<=0;seat<=0;response_v<=0;header<=0;n<=0;m<=0;
   read_row<=0;read_col<=0;write_row<=0;write_col<=0;
   read_addr<=0;write_addr<=0;read_rowbase<=0;write_rowbase<=0;rs<=0;ws<=0;ri<=0;wi<=0;
   launched<=0;returned<=0;finished<=0;
   read_part<=0;write_part<=0;next_tag<=0;seat_d<=0;
   launch<=0;launch_q<=0;reserved<=0;queued<=0;done<=0;fault<=0;pd_h<=0;pd_t<=0;pd_n<=0;
   p_ok<=0;pw_ok<=0;p_rdone<=0;
  end else begin
   done<=0;launch<=launch_q;launch_q<=0;
   response_v<=rsp_v;
   cq_v<=ready&&cmd[0];
   // precompute validity: the stream state did not change at this edge
   p_ok<=!stage&&!cq_v; pw_ok<=(MUTANT==6?queued!=0||push:hv)&&!pop&&!stage&&!cq_v; p_rdone<=read_row==m;
   if(cq_v)begin
    a<=ca;o<=co;header<=incoming_header;validating<=1;busy<=1;bad<=0;fault<=0;
    n<=ca[67:48];m<=ca[87:68];
    read_addr<=ca[39:8];write_addr<=co[39:8];read_rowbase<=ca[39:8];write_rowbase<=co[39:8];
    read_row<=0;read_col<=0;write_row<=0;write_col<=0;rs<=ca[119:88];ws<=co[119:88];
    ri<=ca[5]?16'd0:(ca[135:120]==0?16'd1:ca[135:120]);
    wi<=co[135:120]==0?16'd1:co[135:120];
    launched<=0;returned<=0;finished<=0;read_part<=0;write_part<=0;
    reserved<=0;
   end
   if(busy&&validating)begin
    if(!shape_active)begin                  // operand station; invalid zero shapes still reject in fields_ok
     shape_active<=1;shape_bit<=0;
     ar_acc<=0;ac_acc<=0;or_acc<=0;oc_acc<=0;
     ar_mc<={32'd0,a[119:88]};ac_mc<={48'd0,air};
     or_mc<={32'd0,o[119:88]};oc_mc<={48'd0,oir};
     ar_count<=a[87:68]-20'd1;ac_count<=a[67:48]-20'd1;
     or_count<=o[87:68]-20'd1;oc_count<=o[67:48]-20'd1;
    end else begin                          // four parallel, one-add-per-edge unsigned products
     ar_acc<=ar_acc+(ar_count[0]?ar_mc:64'd0);
     ac_acc<=ac_acc+(ac_count[0]?ac_mc:64'd0);
     or_acc<=or_acc+(or_count[0]?or_mc:64'd0);
     oc_acc<=oc_acc+(oc_count[0]?oc_mc:64'd0);
     ar_mc<=ar_mc<<1;ac_mc<=ac_mc<<1;or_mc<=or_mc<<1;oc_mc<=oc_mc<<1;
     ar_count<=ar_count>>1;ac_count<=ac_count>>1;or_count<=or_count>>1;oc_count<=oc_count>>1;
     shape_bit<=shape_bit+1'b1;
     if(shape_bit==19)begin shape_active<=0;validating<=0;val_sum<=1;end
    end
   end
   if(busy&&val_sum)begin
    val_sum<=0;val2<=1;aspan_q<=ar_acc+ac_acc;ospan_q<=or_acc+oc_acc;orow_q<=oc_acc;
   end
   if(busy&&val2)begin
    val2<=0;val3<=1;
    fields_q<=fields_ok;same_q<=same_geometry;nalias_q<=(o[87:68]==1 || o[119:88]>orow_q);
    aend_q<={24'd0,a[47:8]}+aspan_q;oend_q<={24'd0,o[47:8]}+ospan_q;
   end
   if(busy&&val3)begin val3<=0;val4<=1;shape_q<=shape_ok;end
   if(busy&&val4)begin
    val4<=0;
    if(!shape_q)begin bad<=1;fault<=1;busy<=0;done<=1;end
   end
   if(ctl_run)begin
    if(take_req&&!stage)seat_v<=0;
    if(bad)seat_v<=0;
    if(provider_fault||decode_fault||fovf)begin bad<=1;fault<=1;end
    // ---- stage: select a precomputed descriptor and commit its next stream state
    if(stage)begin
     seat_v<=1;next_tag<=next_tag+1;
     if(stw)begin
      seat<={1'b1,{p_w_addr[29:3],5'd0},p_wd,p_wmask,next_tag};
      seat_d<={1'b1,p_w_step,p_w_addr[2:0],p_w_part,1'b0,p_w_last,p_w_final,next_tag};
      write_part<=p_w_part_n;write_row<=p_w_row_n;write_col<=p_w_col_n;write_rowbase<=p_w_rowbase_n;write_addr<=p_w_addr_n;
     end else begin
      seat<={1'b0,{p_r_addr[29:3],5'd0},256'd0,32'hffffffff,next_tag};
      seat_d<={1'b0,p_r_step,p_r_addr[2:0],p_r_part,p_r_last,1'b0,1'b0,next_tag};
      read_part<=p_r_part_n;read_row<=p_r_row_n;read_col<=p_r_col_n;read_rowbase<=p_r_rowbase_n;read_addr<=p_r_addr_n;
     end
    end
    // ---- responses, in request order
    if(take_rsp)begin
     pd_h<=pd_h+2'd1;
     if(!reply_ok)begin bad<=1;fault<=1;end
     else if(!bad)begin
      if(d_we)begin
       if(d_lastw)finished<=finished+1;
      end else if(d_lastr)begin
       if(MUTANT==5)launch<=1; else launch_q<=1;
       launched<=launched+1;
      end
     end
    end
    if(take_req)begin pd[pd_t]<=seat_d;pd_t<=pd_t+2'd1;end
    pd_n<=pd_n+{2'd0,take_req}-{2'd0,take_rsp};
    if(vo)begin
     returned<=returned+1;
     if(!bad && MUTANT!=1 && qfault)begin bad<=1;fault<=1;end
    end
    if(!bad)begin
     case({reserve_read,retire_write})
      2'b10:reserved<=reserved+1;2'b01:reserved<=reserved-1;
     endcase
    end
    case({push,pop})
     2'b10:queued<=queued+1;2'b01:queued<=queued-1;
    endcase
    if(bad&&!pending&&!seat_v&&!launch&&!launch_q&&returned==launched&&queued==0&&!push)begin
     busy<=0;reserved<=0;done<=1;fault<=1;
    end else if(!bad && take_rsp&&reply_ok&&d_we&&d_lastw&&(d_final || MUTANT==2))begin busy<=0;done<=1;end
   end
  end
 end
 // bench visibility (historical names)
 wire [4:0] head=0, tail=0;
 initial if(DEPTH<24)$fatal(1,"QDQ result reservations require23 inflight+assembly");
endmodule
`default_nettype wire

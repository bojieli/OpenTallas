`timescale 1ns/1ps
// Actual single-query consumer completion fence. No new authentication,
// epoch scheme or hypothetical fault encoding: the frame is the source's
// existing owner/op/PC/query/session identity, and captures are actual hub FFs.
// The caller supplies the real VM lease grant and binds the separate local
// PV/SV consumer before acknowledging whole-query release.
module ot_hbm_collective_publication_receipt #(parameter ENABLE=0,FRAME_W=176)(
 input wire clk,rst_n,begin_valid,output wire begin_ready,
 input wire[FRAME_W-1:0] begin_frame,
 input wire publication_published,publication_quiet,publication_pending,publication_fault,
 input wire[1:0] captured_valid,input wire[31:0] captured_index,
 input wire[2*FRAME_W-1:0] captured_frame,
 input wire release_valid,input wire[FRAME_W-1:0] release_frame,
 output wire release_ready,output wire release_lease,
 output wire receipt_valid,input wire receipt_ready,
 output wire[FRAME_W-1:0] receipt_frame,
 output wire[9:0] receipt_count,output wire active,output wire fault
);
 generate if(ENABLE)begin:g_on
 localparam IDLE=0,CAPTURE=1,DRAIN=2,DONE=3;
 reg[1:0] state;reg bad;reg[255:0] seen;
 reg[9:0] count;reg[FRAME_W-1:0] frame;
 wire cap0=captured_valid[0],cap1=captured_valid[1];
 wire[15:0] idx0=captured_index[15:0],idx1=captured_index[31:16];
 wire invalid0=cap0 && (idx0>=256 || captured_frame[0+:FRAME_W]!=frame || seen[idx0[7:0]]);
 wire invalid1=cap1 && (idx1>=256 || captured_frame[FRAME_W+:FRAME_W]!=frame || seen[idx1[7:0]]);
 wire invalid_capture=(|captured_valid) && (state!=CAPTURE || !publication_published ||
 invalid0 || invalid1 || (cap0 && cap1 && idx0==idx1));
 assign begin_ready=state==IDLE && !bad && !publication_fault;
 assign release_ready=state==CAPTURE && publication_published && count==256 && (&seen) &&
 !publication_pending && !(|captured_valid) && !bad && !publication_fault;
 assign release_lease=release_valid && release_ready && release_frame==frame;
 assign receipt_valid=state==DONE && !bad && !publication_fault;
 assign receipt_frame=frame;assign receipt_count=count;
 assign active=state!=IDLE;
 assign fault=bad || publication_fault;
 always@(posedge clk or negedge rst_n)begin
 if(!rst_n)begin state<=IDLE;bad<=0;seen<=0;count<=0;frame<=0;end
 else if(!bad)begin
 if(publication_fault || invalid_capture)bad<=1;
 if(begin_valid && !begin_ready)bad<=1;
 if(release_valid && (state!=CAPTURE || release_frame!=frame))bad<=1;
 case(state)
 IDLE:if(begin_valid && begin_ready)begin
 frame<=begin_frame;seen<=0;count<=0;state<=CAPTURE;end
 CAPTURE:begin
 if(!invalid_capture)begin
 if(cap0)seen[idx0[7:0]]<=1;
 if(cap1)seen[idx1[7:0]]<=1;
 count<=count+(cap0?10'd1:10'd0)+(cap1?10'd1:10'd0);
 end
 if(release_lease)state<=DRAIN;
 end
 DRAIN:if(publication_quiet && !publication_pending && !(|captured_valid))state<=DONE;
 DONE:if(receipt_valid && receipt_ready)state<=IDLE;
 endcase
 end end
 end else begin:g_off
 assign begin_ready=0;assign release_ready=0;assign release_lease=0;
 assign receipt_valid=0;assign receipt_frame=0;assign receipt_count=0;
 assign active=0;assign fault=0;
 end endgenerate
endmodule

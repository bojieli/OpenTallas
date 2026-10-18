`timescale 1ns/1ps
// KVJ-SMALL (a) 2026-10-17: qkd_attn_result_face -- the attention service RESULT FACE of the split KV die, i.e. the
// producer of qkd_native_attention_programme.result_valid / result_beat / result_data / result_epoch / result_layer /
// result_done / service_fault (static-join gap item 9).  request_ready is qkd_attn_service_root.request_ready (boot
// count only, an assertion input of the programme: it never moves a slot).
//
// Behaviour = the "fixed result emission" block of ot_qwen_tp8_attention_native_service_w16(_sr), moved out of the
// service the same way KVJ-B moved the calendar control into qkd_attn_service_root:
//   * the final join (ot_qwen_tp8_pv256_finalize_static_cal) presents out_valid / out_data / out_epoch on its fixed
//     capture slot, service age RESULT_AGE = PV_START + max(P0, P1, R) + 16 (calendar fields of the accepted command);
//   * the face captures the 16,384-bit vector on that edge and shifts it out as 32 beats x 512 b on the next 32
//     edges (beat b on service age RESULT_AGE+1+b), then raises result_done for one edge (age RESULT_AGE+33);
//   * epoch / layer are the root's held command identity.
// Two structural changes, both exact on the emitted timeline:
//   * the per-edge "fvalid exactly on RESULT_AGE" check compares against a target registered on the start_qk edge
//     (cal is the root's held calendar from that edge), instead of the 16-bit max + 2 adds in front of the compare;
//   * the service's result_ready input is removed: the programme reserves the 32 result slots statically
//     (qkd_native_attention_static_ctl result_reserved) and checks result_valid against its own reservation, so a
//     ready would only be a backpressure path (owner rule 10-14: none).
// RESULT_RELAY registered relay edges carry the whole face (valid, beat, data, epoch, layer, done, service_fault) to
// the programme; the compiler places compiled_tx_first = (request edge) + 1 + RESULT_AGE + 1 + RESULT_RELAY.
// service_fault = sticky result-identity fault | root local / io faults | the service units' sticky faults
// (unit_fault: stacks, hub, PV pairs, finalize, V request, e-read identity, rz-late, K identity), never a stall.
// MUT (diagnostic, bench only): 1 = emission starts one edge late, 2 = result_done one edge early,
//   3 = unit_fault not folded into service_fault.
module qkd_attn_result_face #(
 parameter integer NF=10,
 parameter integer RESULT_RELAY=0,
 parameter integer MUT=0
)(
 input wire ck,rst_n,
 // from qkd_attn_service_root (held command context)
 input wire running,start_qk,
 input wire [15:0] age,
 input wire [15:0] ep,input wire [5:0] layer,
 input wire [175:0] cal,
 input wire root_local_fault,root_io_fault,
 // from ot_qwen_tp8_pv256_finalize_static_cal
 input wire f_valid,input wire [16383:0] f_data,input wire [15:0] f_epoch,
 // sticky faults of the other service units
 input wire [NF-1:0] unit_fault,
 // to qkd_native_attention_programme
 output wire result_valid,output wire [4:0] result_beat,output wire [511:0] result_data,
 output wire [15:0] result_epoch,output wire [5:0] result_layer,
 output wire result_done,output wire service_fault,
 output reg result_fault
);
 // calendar fields: R [175:160], P1 [159:144], P0 [143:128], PV_START [127:112]
 wire [15:0] c_pv=cal[127:112],c_p0=cal[143:128],c_p1=cal[159:144],c_r=cal[175:160];
 wire [15:0] c_last=(c_p0>c_p1)?((c_p0>c_r)?c_p0:c_r):((c_p1>c_r)?c_p1:c_r);
 reg [15:0] res_t;                // RESULT_AGE of the running command
 reg [16383:0] rbuf;reg [5:0] rbeat;reg emitting,done_r,f_valid_d;
 wire fire=(MUT==1)?f_valid_d:f_valid;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin emitting<=0;rbeat<=0;done_r<=0;result_fault<=0;res_t<=16'hffff;f_valid_d<=0;end
  else begin
   done_r<=0;f_valid_d<=f_valid;
   if(start_qk)res_t<=c_pv+c_last+16'd16;
   if(f_valid!=(running&&!start_qk&&age==res_t))result_fault<=1;
   if(fire)begin rbeat<=0;emitting<=1;if(f_epoch!=ep)result_fault<=1;end
   else if(emitting)begin
    rbeat<=rbeat+1'b1;
    if(rbeat==((MUT==2)?30:31))begin emitting<=0;done_r<=1;end
   end
  end
 end
 always @(posedge ck)
  if(fire)rbuf<=f_data;
  else if(emitting)rbuf<={512'd0,rbuf[16383:512]};
 wire sf=result_fault|root_local_fault|root_io_fault|((MUT==3)?1'b0:(|unit_fault));
 wire [541:0] face={emitting,rbeat[4:0],rbuf[511:0],ep,layer,done_r,sf};
 generate if(RESULT_RELAY==0)begin:g0
  assign {result_valid,result_beat,result_data,result_epoch,result_layer,result_done,service_fault}=face;
 end else begin:gr
  reg [541:0] rl[0:RESULT_RELAY-1];
  always @(posedge ck or negedge rst_n)
   if(!rst_n)begin for(integer j=0;j<RESULT_RELAY;j=j+1)rl[j]<=0;end
   else begin rl[0]<=face;for(integer j=1;j<RESULT_RELAY;j=j+1)rl[j]<=rl[j-1];end
  assign {result_valid,result_beat,result_data,result_epoch,result_layer,result_done,service_fault}=rl[RESULT_RELAY-1];
 end endgenerate
endmodule

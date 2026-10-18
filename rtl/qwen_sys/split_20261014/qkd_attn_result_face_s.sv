`timescale 1ns/1ps
// KV-PLAN-FIN 2026-10-17: qkd_attn_result_face_s -- qkd_attn_result_face with a 512-b BEAT-STREAM input from the
// stream final join qkd_pv_fin_s (die element pvfin, results/arch/qwen_kv_pvfin_1017/plan.json), instead of the
// 16,384-b word of ot_qwen_tp8_pv256_finalize_static_cal.  Everything the programme sees is unchanged: beat b of the
// result is presented on service age RESULT_AGE + 1 + b, result_done on RESULT_AGE + 33, the same epoch / layer /
// service_fault, the same RESULT_RELAY face relay.
//   * RESULT_AGE = PV_START + max(P0, P1) + 16 + F_DLY: F_DLY = the fixed edges the stream adds (qkd_pv_fin_s pin stage
//     1 + the die relay edges pvfin -> this face; compiler-priced from the die plan, like RESULT_RELAY);
//   * beat b must arrive exactly on age RESULT_AGE + b with f_beat == b and the command epoch: the per-beat window,
//     beat-index and epoch checks replace the one-edge capture check; a missing, extra or misordered beat sets
//     result_fault (sticky), never a stall;
//   * the 16,384-b capture / shift register (rbuf) is gone: the face registers one 512-b beat.
// MUT (diagnostic, bench only): 1 = emission one edge late, 2 = result_done one edge early, 3 = unit_fault not folded.
module qkd_attn_result_face_s #(
 parameter integer NF=10,
 parameter integer RESULT_RELAY=0,
 parameter integer F_DLY=1,
 parameter integer MUT=0
)(
 input wire ck,rst_n,
 // from qkd_attn_service_root (held command context)
 input wire running,start_qk,
 input wire [15:0] age,
 input wire [15:0] ep,input wire [5:0] layer,
 input wire [175:0] cal,
 input wire root_local_fault,root_io_fault,
 // from qkd_pv_fin_s (beat stream)
 input wire f_valid,input wire [4:0] f_beat,input wire [511:0] f_data,input wire [15:0] f_epoch,
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
 wire [15:0] c_last=(c_p0>c_p1)?c_p0:c_p1;     // the stream join waits for the later pair; R is held before
 reg [15:0] res_t;                // RESULT_AGE of the running command (beat 0 arrival)
 reg [511:0] rdata;reg [4:0] rbeat;reg emitting,done_r;
 reg fv_d;reg [4:0] fb_d;reg [511:0] fd_d;
 wire fire=(MUT==1)?fv_d:f_valid;
 wire [4:0] fbeat=(MUT==1)?fb_d:f_beat;
 wire [15:0] boff=age-res_t;
 wire in_win=running&&!start_qk&&(age>=res_t)&&(boff<16'd32);
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin emitting<=0;rbeat<=0;done_r<=0;result_fault<=0;res_t<=16'hffff;fv_d<=0;end
  else begin
   done_r<=0;fv_d<=f_valid;
   if(start_qk)res_t<=c_pv+c_last+16'd16+16'(F_DLY);
   if(f_valid!=in_win)result_fault<=1;
   if(f_valid&&(f_beat!=boff[4:0]||f_epoch!=ep))result_fault<=1;
   if(fire)begin rbeat<=fbeat;emitting<=1;end
   else if(emitting)begin
    if(rbeat==((MUT==2)?5'd30:5'd31))begin emitting<=0;done_r<=1;end
    else result_fault<=1;              // a gap inside the 32-beat run
   end
  end
 end
 always @(posedge ck)begin
  fb_d<=f_beat;fd_d<=f_data;
  if(fire)rdata<=(MUT==1)?fd_d:f_data;
 end
 wire sf=result_fault|root_local_fault|root_io_fault|((MUT==3)?1'b0:(|unit_fault));
 wire [541:0] face={emitting,rbeat[4:0],rdata,ep,layer,done_r,sf};
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

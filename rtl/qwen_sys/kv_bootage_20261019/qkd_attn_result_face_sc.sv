`timescale 1ns/1ps
// KV-BOOTAGE 2026-10-19 (coordinator decision, lanes/KVR-DERIVE.md "SPEC for the ONE later re-harden"): qkd_attn_result_face_s
// with a BOOT-PROGRAMMABLE F_DLY.  Identical to rtl/qwen_sys/split_20261014/qkd_attn_result_face_s.sv (kept byte-identical
// for the closed qkd_kvs_attn / qkd_kvs_attn_fl views) except:
//   cfg_f_dly[7:0] = F_DLY (1 + (D(ks_pvfst) - PV_LEAD) + D(ks_pvfin) [+ face landing]), a static configuration net from the
//   KV die cfg (qkd_kv_die_cfg_a, pre-boot image target 10, sealed, POR-held; no handshake / credit / ready).  The die
//   derives it from its relay plan / netlist (kv_static_params) and the generator FAILS when the boot image value differs.
//   The parameter F_DLY is now the upper bound: cfg_f_dly < 1 or > F_DLY sets result_fault at the command start.
//   RESULT_AGE = PV_START + max(P0, P1, R) + 16 + F_DLY: the constant 16 + F_DLY is a registered constant (k_res).
// Edge for edge this is qkd_attn_result_face_s #(.F_DLY(v)) when cfg_f_dly = v (lockstep bench
// rtl/test/kv_bootage_1019/tb_kvba_attn.sv).
// MUT: 1-5 as qkd_attn_result_face_s; 6 = k_res off by one (F_DLY + 1); 7 = range check off.
// KV-PLAN-FIN 2026-10-17: qkd_attn_result_face_s -- qkd_attn_result_face with a 512-b BEAT-STREAM input from the
// stream final join qkd_pv_fin_s (die element pvfin, results/arch/qwen_kv_pvfin_1017/plan.json), instead of the
// 16,384-b word of ot_qwen_tp8_pv256_finalize_static_cal.  Everything the programme sees is unchanged: beat b of the
// result is presented on service age RESULT_AGE + 1 + b, result_done on RESULT_AGE + 33, the same epoch / layer /
// service_fault, the same RESULT_RELAY face relay.
//   * RESULT_AGE = PV_START + max(P0, P1, R) + 16 + F_DLY: F_DLY = the fixed edges the stream adds (qkd_pv_fin_s pin
//     stage 1 + the die relay edges pvfin -> this face; compiler-priced from the die plan, like RESULT_RELAY);
//     max(P0, P1, R) is the 16-kb face's / the reference final join's LAST_CAPTURE and the compiler law
//     (kv_static_programme.attention_calendar: service_cycles = PV_START + max(P, R) + 16 + 33; the service root's
//     END_AGE uses the same max).  QXF-FACE 10-18 (TOKEN-XDIE-QWEN F3): this face had max(P0, P1) -- exact only while
//     R <= max(P0, P1) (STRETCH=0).  The die's generator runs STRETCH=1 (R stretched so the service ends on the link's
//     fixed RESULT slot): the face then expected beat 0 at 913 (T = 256) / 1639 (T = 8192) while the programme reserves
//     TX_FIRST 1750 (= the face's RESULT_AGE 1745 + 1 + the root->programme offset 4), so every layer faulted.
//     qkd_pv_fin_s follows the same max (it holds its 32 sums until R);
//   * beat b must arrive exactly on age RESULT_AGE + b with f_beat == b and the command epoch: the per-beat window,
//     beat-index and epoch checks replace the one-edge capture check; a missing, extra or misordered beat sets
//     result_fault (sticky), never a stall;
//   * the 16,384-b capture / shift register (rbuf) is gone: the face registers one 512-b beat.
// MUT (diagnostic, bench only): 1 = emission one edge late, 2 = result_done one edge early, 3 = unit_fault not folded,
//   4 = R left out of RESULT_AGE (the pre-10-18 max(P0, P1) law), 5 = CAL_PIPE stage sampled every edge and summed on start_qk
//   (the PREVIOUS calendar: a mis-timed pipe).
// KV-ATTNKIT 10-18: CAL_PIPE=1 (die knob OT_KV_ATTN_LAND; kit qkd_kvs_attn-g1 failed root cal -> res_t, ~21 levels:
// 3-way max + two adds in the start_qk edge).  PV_START and max(P0, P1, R) are registered on the start_qk edge (cal is
// the root's held calendar, loaded on the same accept edge as start_qk) and res_t is their sum one edge later, i.e. it
// holds from service age 2 instead of 1.  At age 1 the only readers are in_win (age >= res_t) and boff, which give the
// same values for any res_t >= 2 old or new; a new RESULT_AGE < 2 (a 16-bit wrapped calendar) sets result_fault.
// hdr_l = {f_valid, 2'b00, f_beat} one edge late (the registered fv_d / fb_d): the die's ar_h header word for the
// sequencer through a flop (the generated tile otherwise passes fin pins straight to its arh pins; +1 edge on ks_arh).
module qkd_attn_result_face_sc #(
 parameter integer NF=10,
 parameter integer RESULT_RELAY=0,
 parameter integer F_DLY=127,
 parameter integer CAL_PIPE=0,
 parameter integer MUT=0
)(
 input wire ck,rst_n,
 input wire [7:0] cfg_f_dly,           // boot-loaded F_DLY (static after the seal)
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
 output wire result_fault,
 output wire [7:0] hdr_l
);
 // calendar fields: R [175:160], P1 [159:144], P0 [143:128], PV_START [127:112]
 wire [15:0] c_pv=cal[127:112],c_p0=cal[143:128],c_p1=cal[159:144],c_r=cal[175:160];
 wire [15:0] c_lastp=(c_p0>c_p1)?c_p0:c_p1;
 wire [15:0] c_last=(MUT==4||c_lastp>c_r)?c_lastp:c_r;   // max(P0, P1, R): the stream join waits for R (qkd_pv_fin_s)
 reg rf;                          // sticky result fault (CAL_PIPE: result_fault = rf | the landed beat check)
 reg l_win;reg [4:0] l_boff;reg [15:0] l_fe,l_ep;
 reg [15:0] res_t;                // RESULT_AGE of the running command (beat 0 arrival)
 reg [511:0] rdata;reg [4:0] rbeat;reg emitting,done_r;
 reg fv_d;reg [4:0] fb_d;reg [511:0] fd_d;
 reg [15:0] cp_pv,cp_last;reg cp_sq;               // CAL_PIPE stage (start_qk edge) and its load strobe
 reg [7:0] fd_q;reg [15:0] k_res;reg fd_bad;
 always @(posedge ck)begin
  fd_q<=cfg_f_dly;
  k_res<=16'd16+16'(fd_q)+((MUT==6)?16'd1:16'd0);   // 16 + F_DLY
  fd_bad<=(MUT==7)?1'b0:(fd_q<8'd1||fd_q>8'(F_DLY));
 end
 wire [15:0] res_c=cp_pv+cp_last+k_res;
 wire cp_ld=(MUT==5)?start_qk:cp_sq;
 assign hdr_l={fv_d,2'b00,fb_d};
 wire fire=(MUT==1)?fv_d:f_valid;
 wire [4:0] fbeat=(MUT==1)?fb_d:f_beat;

 // Source-defined binary hold mux. Keep actual native topology at synthesis;
 // unlike a complementary-select mux, fire has exactly one terminal per bit.
 wire [511:0] hold_data=(MUT==1)?fd_d:f_data;
 wire [511:0] hold_next;
 for(genvar hb=0;hb<512;hb=hb+1)begin:g_hold
  wire delta,selected;
`ifdef SYNTHESIS
  (* keep=1, dont_touch=1 *) XOR2x1_ASAP7_75t_R u_delta(.A(rdata[hb]),.B(hold_data[hb]),.Y(delta));
  (* keep=1, dont_touch=1 *) AND2x2_ASAP7_75t_R u_select(.A(fire),.B(delta),.Y(selected));
  (* keep=1, dont_touch=1 *) XOR2x1_ASAP7_75t_R u_next(.A(rdata[hb]),.B(selected),.Y(hold_next[hb]));
`else
  assign delta=rdata[hb]^hold_data[hb];
  assign selected=fire&delta;
  assign hold_next[hb]=rdata[hb]^selected;
`endif
 end
 wire [15:0] boff=age-res_t;
 wire in_win=running&&!start_qk&&(age>=res_t)&&(boff<16'd32);
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin emitting<=0;rbeat<=0;done_r<=0;rf<=0;l_win<=0;res_t<=16'hffff;fv_d<=0;cp_sq<=0;end
  else begin
   done_r<=0;fv_d<=f_valid;cp_sq<=start_qk&&CAL_PIPE!=0;
   if(start_qk&&fd_bad)rf<=1;                       // an invalid boot age: the command's result is refused
   if(CAL_PIPE==0)begin if(start_qk)res_t<=c_pv+c_last+k_res;end
   else if(cp_ld)begin res_t<=res_c;if(res_c<16'd2)rf<=1;end
   if(CAL_PIPE==0)begin
    if(f_valid!=in_win)rf<=1;
    if(f_valid&&(f_beat!=boff[4:0]||f_epoch!=ep))rf<=1;
   end else begin
    l_win<=in_win;if(f_chk)rf<=1;
   end
   if(fire)begin rbeat<=fbeat;emitting<=1;end
   else if(emitting)begin
    if(rbeat==((MUT==2)?5'd30:5'd31))begin emitting<=0;done_r<=1;end
    else rf<=1;                        // a gap inside the 32-beat run
   end
  end
 end
 always @(posedge ck)begin
  fb_d<=f_beat;fd_d<=f_data;l_boff<=boff[4:0];l_fe<=f_epoch;l_ep<=ep;
  if(start_qk||MUT==5)begin cp_pv<=c_pv;cp_last<=c_last;end
  rdata<=hold_next;
 end
 // CAL_PIPE: the beat window / index / epoch check on the landed beat header (fv_d, fb_d, l_fe; g2: fin -> result_fault
 // 8 levels); result_fault = rf | f_chk is the original sticky flop edge for edge
 wire f_chk=CAL_PIPE!=0&&((fv_d!=l_win)||(fv_d&&(fb_d!=l_boff||l_fe!=l_ep)));
 assign result_fault=rf|f_chk;
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

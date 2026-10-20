`timescale 1ns/1ps
// KV-CTL3 10-20 (SAFE checklist item 3 / PRE-GATE NATIVE CENSUS: no driver > 32 loads in the mapped netlist):
// qkd_static_kv_layer_programme_s32 = qkd_static_kv_layer_programme_mus with the SAME ports, SAME macros, SAME outputs on
// every edge (lockstep vs qkd_static_kv_layer_programme_mu: rtl/test/mu_qwen_1018/run_kv_ctl_s32_c.sh), restructured so no
// net drives more than ~32 mapped loads.  mus census (mu6c mapped netlist, results/arch/kv_ctl3_1020/cls.txt): the row
// landing enables (c_load[k] & !fault & rn, 322 hold bits per context = 644 select loads), the fault flop (198), the start
// writes of the per-context metadata (68 bits / context), the per-context counters (c_cnt / c_age / c_tc, selects c_wait
// etc.), the output metadata muxes (fire_u / owner selects -> o_attn / kg / lp pins, 64..162 loads), the shadow / g0 /
// bound_digest / duration_sum boot writes (35..90) and the cfg data pin flops (33..55).
// Structure (0 added edges, same flop count + copies):
//   * every wide held register is written in SLICES of <= 16 bits (an ASAP7 hold-enable / 2:1 select = 2 loads a bit);
//     each slice's enable / selects are ANDed with its own KEPT literal rs_s[j] (a kept copy of the reset pin flop rnv,
//     identical D = rst_n, NOT a split family), so no two slices share a gate (opt_merge / ABC cannot fold them) and every
//     shared condition drives one gate per slice.  rs_s[j] == rn on every edge, so the function is unchanged (async-reset
//     slices: rs_s and rnv are the same registered rst_n).
//   * fault: FC KEPT identical registers (family fault_f, ot_rst_split, D = fault | fault_set: one net) -> the synthesis split
//     (physical/common_flow/ot_rst_copies.py, OT_RST_COPIES_WIDE=1 folds the hold into identical enables) spreads its loads.
//   * cfg data pin flop: 3 KEPT copies (strided family dqf, ot_rst_split = 64).
//   * per-context counters: explicit next-state (start / wait / run / stage-end priority of the mus process, unchanged);
//     the 4:1 output metadata muxes are one-hot AND-OR on per-slice gated selects; c_X[k] + 1 is formed per context.
module qkd_static_kv_layer_programme_s32 #(parameter integer MUT=0,parameter integer MU=1,parameter integer CTLSRAM=0,
 parameter integer RCOPIES=4,parameter integer RS=32,parameter integer FC=8)(
 input wire ck,rst_n,
 input wire cfg_we,input wire[8:0]cfg_addr,input wire[63:0]cfg_data,
 input wire start,authority_valid,programme_authorized,
 input wire[15:0]programme_epoch,input wire[63:0]programme_digest,
 input wire[15:0]authority_epoch,input wire[17:0]authority_token,authority_position,
 input wire[1:0]authority_generation,
 output reg ctrl_go,kgo,vgo,attention_issue,attention_run,writer_start,link_start,
 output reg stage_start,stage_done,expected_upstream_quiet,output reg[5:0]completed_stage,
 output wire[5:0]stage,output wire[5:0]layer,
 output wire[15:0]epoch,output wire[17:0]token,position,output wire[13:0]ctx_t,
 output wire[1:0]generation,
 output reg configured,active,done,output wire fault,output reg[7:0]fault_code,
 output wire[31:0]age,token_cycles
);
 localparam integer RC=RCOPIES;
 (* keep = "true", ot_rst_split *) reg[RC-1:0]rnv;
 always @(posedge ck)rnv<={RC{rst_n}};
 wire rn=rnv[0];
 // slice literals: kept copies of the reset pin flop (not a split family: each slice owns one)
 (* keep = "true" *) reg[RS-1:0]rs_s;
 always @(posedge ck)rs_s<={RS{rst_n}};
 reg we_q,start_q,av_q,authorized_q;reg[8:0]addr_q;
 (* keep = "true", ot_rst_split = 64 *) reg[191:0]dqf;
 wire[63:0]data_q=dqf[63:0];
 reg[15:0]epoch_q;reg[17:0]token_q,pos_q;reg[1:0]gen_q;
 wire[63:0]bound_digest;reg[15:0]bound_epoch;
 reg dig_ok_q,ep_ok_q,pos_ok_q;
 always @(posedge ck)begin
  addr_q<=cfg_addr;dqf<={3{cfg_data}};
  epoch_q<=authority_epoch;token_q<=authority_token;pos_q<=authority_position;gen_q<=authority_generation;
  dig_ok_q<=programme_digest==bound_digest;ep_ok_q<=programme_epoch==bound_epoch;pos_ok_q<=authority_position<=18'd8191;
 end
 always @(posedge ck or negedge rn)
 if(!rn)begin we_q<=0;start_q<=0;av_q<=0;authorized_q<=0;end
 else begin we_q<=cfg_we;start_q<=start;av_q<=authority_valid;authorized_q<=programme_authorized;end
 // ---- fault + kept copies (family fault_f): FC identical registers, D = fault | fault_set (one net), async clear ----
 // fault_set mirrors every fault site of the mus process (taken only while !fault; fault is sticky until reset).
 (* keep = "true", ot_rst_split *) reg[FC-1:0]fault_f;
 wire fault_q=fault_f[0];
 assign fault=fault_q;
 wire fault_set;
 // ---- contexts (flat per-context vectors; context k = [W*k +: W]) ----
 reg[3:0]c_act,c_wait,c_load,c_quiet;reg[5:0]c_stage[0:3];
 wire[4*32-1:0]c_cnt_f,c_age_f,c_tc_f;
 wire[4*16-1:0]c_epoch_f;wire[4*18-1:0]c_token_f,c_pos_f;wire[4*14-1:0]c_ctx_f;wire[4*2-1:0]c_gen_f;
 // per-context row registers (loaded from the macros on the c_load edge): land_k = {ngone,ngz,ng,p_end,rowa fields}
 wire[4*322-1:0]land_f;
 wire[4*32-1:0]p_ctrl_f,p_k_f,p_v_f,p_issue_f,p_run_f,p_writer_f,p_link_f,p_quiet_f,p_end_f,ng_f;wire[3:0]ngz,ngone;
 wire[4*32-1:0]g0_f;wire[3:0]g0z,g0one;
 // registered next events
 reg[3:0]f_ctrl,f_k,f_v,f_issue,f_run,f_writer,f_link,f_quiet,f_end,f_wx;
 // ---- boot ----
 reg[8:0]next_cfg;reg[5:0]cfg_stage;reg[3:0]cfg_word;reg[7:0]cfg_gap;reg[1:0]gap_u;reg[5:0]gap_j;
 wire[36:0]duration_sum;
 wire[8*32-1:0]shadow_f;
 wire accept_cfg=we_q&&!configured&&!(|c_act)&&!fault&&addr_q==next_cfg;
 reg bad_row;
 always @*begin
  bad_row=data_q[63:32]!=0;
  for(integer k=0;k<8;k=k+1)if(shadow_f[32*k+:32]<3||shadow_f[32*k+:32]>=data_q[31:0])bad_row=1;
  for(integer k=0;k<7;k=k+1)if(shadow_f[32*7+:32]<=shadow_f[32*k+:32])bad_row=1;
  if({1'b0,shadow_f[32*4+:32]} < {1'b0,shadow_f[32*3+:32]}+33'd4)bad_row=1;
  if(duration_sum+{5'b0,data_q[31:0]}>37'h0ffffffff)bad_row=1;
 end
 // write pipeline (one edge after the accept, as the original's wq): stage words -> P = r - 2; gap words j >= 1 -> rowb
 reg wq,wg;reg[5:0]w_row;reg[7:0]w_field;reg w_end;reg[1:0]w_u;reg[31:0]w_data;reg w_zero,w_one;
 wire row_acc=accept_cfg&&addr_q<324;
 wire gap_acc=accept_cfg&&addr_q>=326&&addr_q<470;
 always @(posedge ck or negedge rn)if(!rn)begin wq<=0;wg<=0;end else begin wq<=row_acc;wg<=gap_acc&&gap_j!=0;end
 // KV-CTL3 census: kept copies of wq / w_u for the rowb write mask (a 32-bit mask field + its flag bits were one net, 34 loads)
 (* keep = "true" *) reg wq_m;(* keep = "true" *) reg[1:0]w_u_m;
 always @(posedge ck or negedge rn)if(!rn)wq_m<=0;else wq_m<=row_acc;
 always @(posedge ck)w_u_m<=gap_u;
 always @(posedge ck)begin
  w_row<=row_acc?cfg_stage:(gap_j-6'd1);w_field<=8'd1<<cfg_word[2:0];w_end<=cfg_word==8;w_u<=gap_u;
  w_data<=row_acc?(data_q[31:0]-32'd2):data_q[31:0];w_zero<=data_q[31:0]==0;w_one<=data_q[31:0]==1;
 end
 wire[255:0]a_mask={{32{w_field[7]}},{32{w_field[6]}},{32{w_field[5]}},{32{w_field[4]}},
                    {32{w_field[3]}},{32{w_field[2]}},{32{w_field[1]}},{32{w_field[0]}}};
 wire[3:0]u1=4'd1<<w_u;
 wire[3:0]u1m=4'd1<<w_u_m;
 wire[255:0]b_mask={88'd0,u1m&{4{!wq_m}},u1m&{4{!wq_m}},(wq?128'd0:{{32{u1[3]}},{32{u1[2]}},{32{u1[1]}},{32{u1[0]}}}),{32{wq_m}}};
 wire[255:0]b_data={88'd0,{4{w_one}},{4{w_zero}},{4{w_data}},w_data};
 // ---- stage begin / row read ----
 wire[1:0]us=epoch_q[1:0];
 wire start_ok=configured&&!c_act[us]&&!we_q&&av_q&&authorized_q&&pos_ok_q&&ep_ok_q&&dig_ok_q;
 wire start_go=start_q&&start_ok&&!fault;
 reg[3:0]last;
 reg[3:0]e_begin,e_any;
 reg[5:0]rd_idx;
 always @*begin
  for(integer k=0;k<4;k=k+1)last[k]=c_stage[k]==6'd36;
  e_begin=f_wx|(f_end&~last&ngz);
  if(start_go&&g0z[us])e_begin[us]=1'b1;
  e_any=f_ctrl|f_k|f_v|f_issue|f_run|f_writer|f_link|f_quiet|f_end|e_begin;
  rd_idx=0;
  for(integer k=0;k<4;k=k+1)if(e_begin[k])
   rd_idx=rd_idx|((start_go&&us==k)?6'd0:(f_wx[k]?c_stage[k]-6'd1:c_stage[k]));
 end
 wire[255:0]rowa,rowb;
 wire r_ce=|e_begin,wa_ce=wq&&!w_end,wb_ce=(wq&&w_end)||wg;
 wire[255:0]wa_d={8{w_data}};
 generate if(CTLSRAM==0)begin:g_s0
 ot_sram_1r1w_128x256_m1_r2c2 u_rowa(.clk(ck),.r_ce_in(r_ce),.r_addr_in({1'b0,rd_idx}),.rd_out(rowa),
  .w_ce_in(wa_ce),.w_addr_in({1'b0,w_row}),.wd_in(wa_d),.w_mask_in(a_mask),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 ot_sram_1r1w_128x256_m1_r2c2 u_rowb(.clk(ck),.r_ce_in(r_ce),.r_addr_in({1'b0,rd_idx}),.rd_out(rowb),
  .w_ce_in(wb_ce),.w_addr_in({1'b0,w_row}),.wd_in(b_data),.w_mask_in(b_mask),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end else if(CTLSRAM==1)begin:g_s1
 ctl_sram_1r1w_64x64_p192 u_rowa_b0(.clk(ck),.r_ce_in(r_ce),.r_addr_in(rd_idx),.rd_out(rowa[0+:64]),
  .w_ce_in(wa_ce),.w_addr_in(w_row),.wd_in(wa_d[0+:64]),.w_mask_in(a_mask[0+:64]));
 ctl_sram_1r1w_64x64_p192 u_rowa_b1(.clk(ck),.r_ce_in(r_ce),.r_addr_in(rd_idx),.rd_out(rowa[64+:64]),
  .w_ce_in(wa_ce),.w_addr_in(w_row),.wd_in(wa_d[64+:64]),.w_mask_in(a_mask[64+:64]));
 ctl_sram_1r1w_64x64_p192 u_rowa_b2(.clk(ck),.r_ce_in(r_ce),.r_addr_in(rd_idx),.rd_out(rowa[128+:64]),
  .w_ce_in(wa_ce),.w_addr_in(w_row),.wd_in(wa_d[128+:64]),.w_mask_in(a_mask[128+:64]));
 ctl_sram_1r1w_64x64_p192 u_rowa_b3(.clk(ck),.r_ce_in(r_ce),.r_addr_in(rd_idx),.rd_out(rowa[192+:64]),
  .w_ce_in(wa_ce),.w_addr_in(w_row),.wd_in(wa_d[192+:64]),.w_mask_in(a_mask[192+:64]));
 ctl_sram_1r1w_64x64_p192 u_rowb_b0(.clk(ck),.r_ce_in(r_ce),.r_addr_in(rd_idx),.rd_out(rowb[0+:64]),
  .w_ce_in(wb_ce),.w_addr_in(w_row),.wd_in(b_data[0+:64]),.w_mask_in(b_mask[0+:64]));
 ctl_sram_1r1w_64x64_p192 u_rowb_b1(.clk(ck),.r_ce_in(r_ce),.r_addr_in(rd_idx),.rd_out(rowb[64+:64]),
  .w_ce_in(wb_ce),.w_addr_in(w_row),.wd_in(b_data[64+:64]),.w_mask_in(b_mask[64+:64]));
 ctl_sram_1r1w_64x64_p192 u_rowb_b2(.clk(ck),.r_ce_in(r_ce),.r_addr_in(rd_idx),.rd_out(rowb[128+:64]),
  .w_ce_in(wb_ce),.w_addr_in(w_row),.wd_in(b_data[128+:64]),.w_mask_in(b_mask[128+:64]));
 assign rowb[255:192]=64'd0;
 end else begin:g_s2
 ctl_sram_1r1w_64x128_p192 u_rowa_b0(.clk(ck),.r_ce_in(r_ce),.r_addr_in(rd_idx),.rd_out(rowa[0+:128]),
  .w_ce_in(wa_ce),.w_addr_in(w_row),.wd_in(wa_d[0+:128]),.w_mask_in(a_mask[0+:128]));
 ctl_sram_1r1w_64x128_p192 u_rowa_b1(.clk(ck),.r_ce_in(r_ce),.r_addr_in(rd_idx),.rd_out(rowa[128+:128]),
  .w_ce_in(wa_ce),.w_addr_in(w_row),.wd_in(wa_d[128+:128]),.w_mask_in(a_mask[128+:128]));
 ctl_sram_1r1w_64x128_p192 u_rowb_b0(.clk(ck),.r_ce_in(r_ce),.r_addr_in(rd_idx),.rd_out(rowb[0+:128]),
  .w_ce_in(wb_ce),.w_addr_in(w_row),.wd_in(b_data[0+:128]),.w_mask_in(b_mask[0+:128]));
 ctl_sram_1r1w_64x128_p192 u_rowb_b1(.clk(ck),.r_ce_in(r_ce),.r_addr_in(rd_idx),.rd_out(rowb[128+:128]),
  .w_ce_in(wb_ce),.w_addr_in(w_row),.wd_in(b_data[128+:128]),.w_mask_in(b_mask[128+:128]));
 end endgenerate
 // ---- events ----
 wire[3:0]e_ctrl=f_ctrl,e_k=f_k,e_v=f_v,e_issue=f_issue,e_run=f_run,e_writer=f_writer,e_link=f_link,e_quiet=f_quiet,e_end=f_end;
 wire collide=(e_any&(e_any-4'd1))!=0;
 // fault_set: the mus process's fault sites, in its branch order (we_q word checks, collision, start refusal)
 wire fs_we=we_q&&(!accept_cfg||
  (addr_q<324&&(data_q[63:32]!=0||(cfg_word==8&&bad_row)))||
  (addr_q==325&&data_q[63:16]!=0)||
  (addr_q>325&&addr_q<470&&data_q[63:32]!=0)||
  (addr_q==470&&(data_q!=64'h514b564c59523336||cfg_stage!=36||cfg_gap!=144||duration_sum==0))||
  (addr_q>470));
 assign fault_set=fs_we||collide||(start_q&&!start_ok);
 always @(posedge ck or negedge rn)if(!rn)fault_f<=0;else fault_f<={FC{fault_q||fault_set}};
 reg[1:0]owner;reg[5:0]stage_o;
 reg[1:0]fire_u;always @*begin fire_u=owner;for(integer k=3;k>=0;k=k-1)if(e_any[k])fire_u=2'(k);end
 assign stage=(MUT==2)?(stage_o^6'd1):stage_o;
 assign layer=stage-6'd1;
 // ---- control process (the mus process without the sliced data registers; fault itself = fault_f, set by fault_set) ----
 always @(posedge ck or negedge rn)begin
  if(!rn)begin
   ctrl_go<=0;kgo<=0;vgo<=0;attention_issue<=0;attention_run<=0;writer_start<=0;link_start<=0;
   stage_start<=0;stage_done<=0;expected_upstream_quiet<=0;completed_stage<=0;
   configured<=0;active<=0;done<=0;fault_code<=0;
   next_cfg<=0;cfg_stage<=0;cfg_word<=0;cfg_gap<=0;gap_u<=0;gap_j<=0;bound_epoch<=0;
   c_act<=0;c_wait<=0;c_load<=0;c_quiet<=0;owner<=0;stage_o<=0;
   f_ctrl<=0;f_k<=0;f_v<=0;f_issue<=0;f_run<=0;f_writer<=0;f_link<=0;f_quiet<=0;f_end<=0;f_wx<=0;
   for(integer k=0;k<4;k=k+1)c_stage[k]<=0;
  end else begin
   ctrl_go<=0;kgo<=0;vgo<=0;attention_issue<=0;attention_run<=0;writer_start<=0;link_start<=0;
   stage_start<=0;stage_done<=0;done<=0;
   if(fault)begin
    active<=0;c_act<=0;
    f_ctrl<=0;f_k<=0;f_v<=0;f_issue<=0;f_run<=0;f_writer<=0;f_link<=0;f_quiet<=0;f_end<=0;f_wx<=0;
   end else begin
    if(we_q)begin
     if(!accept_cfg)begin fault_code[0]<=1;end
     else if(addr_q<324)begin
      if(data_q[63:32]!=0||(cfg_word==8&&bad_row))begin fault_code[1]<=1;end
      if(cfg_word==8)begin cfg_stage<=cfg_stage+1'b1;cfg_word<=0;end else cfg_word<=cfg_word+1'b1;
      next_cfg<=next_cfg+1'b1;
     end else if(addr_q==324)begin next_cfg<=325;end
     else if(addr_q==325)begin
      if(data_q[63:16]!=0)begin fault_code[2]<=1;end
      bound_epoch<=data_q[15:0];next_cfg<=326;
     end else if(addr_q<470)begin
      if(data_q[63:32]!=0)begin fault_code[2]<=1;end
      if(gap_j==35)begin gap_j<=0;gap_u<=gap_u+1'b1;end else gap_j<=gap_j+1'b1;
      next_cfg<=next_cfg+1'b1;cfg_gap<=cfg_gap+1'b1;
     end else if(addr_q==470)begin
      if(data_q!=64'h514b564c59523336||cfg_stage!=36||cfg_gap!=144||duration_sum==0)begin fault_code[2]<=1;end
      else configured<=1;
     end else begin fault_code[0]<=1;end
    end
    if(collide)begin fault_code[4]<=1;end
    if(start_q)begin
     if(!start_ok)begin fault_code[3]<=1;end
     else begin
      c_act[us]<=1;c_stage[us]<=1;c_quiet[us]<=0;
      if(g0z[us])begin c_wait[us]<=0;c_load[us]<=1;end
      else begin c_wait[us]<=1;c_load[us]<=0;end
     end
    end
    for(integer k=0;k<4;k=k+1)begin
     f_ctrl[k]<=0;f_k[k]<=0;f_v[k]<=0;f_issue[k]<=0;f_run[k]<=0;f_writer[k]<=0;f_link[k]<=0;f_quiet[k]<=0;f_end[k]<=0;f_wx[k]<=0;
     if(start_go&&us==k)f_wx[k]<=!g0z[k]&&g0one[k];
     else if(c_act[k])begin
      if(c_wait[k])f_wx[k]<=c_cnt_f[32*k+:32]==2;
      else if(!c_load[k])begin
       if(e_end[k])f_wx[k]<=!last[k]&&!ngz[k]&&ngone[k];
       else begin
        f_ctrl[k]<=c_age_f[32*k+:32]==p_ctrl_f[32*k+:32];f_k[k]<=c_age_f[32*k+:32]==p_k_f[32*k+:32];
        f_v[k]<=c_age_f[32*k+:32]==p_v_f[32*k+:32];f_issue[k]<=c_age_f[32*k+:32]==p_issue_f[32*k+:32];
        f_run[k]<=c_age_f[32*k+:32]==p_run_f[32*k+:32];f_writer[k]<=c_age_f[32*k+:32]==p_writer_f[32*k+:32];
        f_link[k]<=c_age_f[32*k+:32]==p_link_f[32*k+:32];f_quiet[k]<=c_age_f[32*k+:32]==p_quiet_f[32*k+:32];
        f_end[k]<=c_age_f[32*k+:32]==p_end_f[32*k+:32];
       end
      end
     end
    end
    for(integer k=0;k<4;k=k+1)if(c_act[k]&&!(start_q&&start_ok&&us==k))begin
     if(c_load[k])c_load[k]<=0;
     if(c_wait[k])begin
      if(f_wx[k])begin c_wait[k]<=0;c_load[k]<=1;end
     end else begin
      if(e_quiet[k])c_quiet[k]<=1;
      if(e_end[k])begin
       if(last[k])begin c_act[k]<=0;end
       else begin
        c_stage[k]<=c_stage[k]+1'b1;c_quiet[k]<=0;
        if(ngz[k])c_load[k]<=1;
        else c_wait[k]<=1;
       end
      end
     end
    end
    ctrl_go<=|e_ctrl;kgo<=|e_k;vgo<=|e_v;attention_issue<=|e_issue;attention_run<=|e_run;writer_start<=|e_writer;
    link_start<=|e_link;stage_done<=|e_end;stage_start<=|e_begin;
    if(|e_any)begin
     owner<=fire_u;
     if(e_end[fire_u])begin completed_stage<=c_stage[fire_u];if(last[fire_u])done<=1;end
     stage_o<=(e_end[fire_u]&&!last[fire_u])?c_stage[fire_u]+1'b1:((start_q&&start_ok&&fire_u==us)?6'd1:c_stage[fire_u]);
     expected_upstream_quiet<=e_quiet[fire_u]||(c_quiet[fire_u]&&!e_begin[fire_u]);
    end else begin
     if(e_quiet[owner])expected_upstream_quiet<=1;
    end
    active<=|(c_act&~(e_end&last))||(start_q&&start_ok);
   end
  end
 end
 // ---- sliced data registers ----
 // Every held slice <= 16 bits: next = ot_s32_sel(select, new, held) / ot_s32_and leaves (rtl/lib/ot_s32_cells.sv, kept
 // hierarchy: ABC cannot fold a shared condition into the bits).  Every leaf select is a distinct net: the shared
 // condition ANDed with the slice's literal rs_s[(base + slice) % RS]; fault / rn are read through their copy families
 // (fault_f, rnv) one bit per slice (the synthesis split re-balances them).
 wire[4*68-1:0]meta_f;wire[4*32-1:0]ag1_f,tc1_f;
 genvar gk,gs;
 generate for(gk=0;gk<4;gk=gk+1)begin:g_ctx
  // (G1) row landing: land_k <= {rowb[164+k], rowb[160+k], rowb[32+32k +: 32], rowb[31:0], rowa}
  wire[321:0]lsrc={rowb[164+gk],rowb[160+gk],rowb[32+32*gk+:32],rowb[31:0],rowa};
  reg[321:0]land;wire[321:0]lnx;
  for(gs=0;gs<21;gs=gs+1)begin:g_l
   localparam integer LO=16*gs,W=(gs==20)?2:16,J=(gk*21+gs)%RS;
   wire e=c_load[gk]&&!fault_f[J%FC]&&rnv[J%RC]&&rs_s[J];
   ot_s32_sel #(.W(W)) u_s(.s(e),.a(lsrc[LO+:W]),.b(land[LO+:W]),.y(lnx[LO+:W]));
  end
  always @(posedge ck)land<=lnx;
  assign p_ctrl_f[32*gk+:32]=land[0+:32];assign p_k_f[32*gk+:32]=land[32+:32];assign p_v_f[32*gk+:32]=land[64+:32];
  assign p_issue_f[32*gk+:32]=land[96+:32];assign p_run_f[32*gk+:32]=land[128+:32];assign p_writer_f[32*gk+:32]=land[160+:32];
  assign p_link_f[32*gk+:32]=land[192+:32];assign p_quiet_f[32*gk+:32]=land[224+:32];assign p_end_f[32*gk+:32]=land[256+:32];
  assign ng_f[32*gk+:32]=land[288+:32];assign ngz[gk]=land[320];assign ngone[gk]=land[321];
  // (G2) start metadata: {gen, ctx, pos, token, epoch}
  wire sk=start_q&&start_ok&&us==gk;
  wire[67:0]msrc={gen_q,14'(pos_q+1),pos_q,token_q,epoch_q};
  reg[67:0]meta;wire[67:0]mnx;
  for(gs=0;gs<5;gs=gs+1)begin:g_m
   localparam integer LO=16*gs,W=(gs==4)?4:16,J=(gk*5+gs+84)%RS;
   wire e=sk&&!fault_f[J%FC]&&rs_s[J];
   ot_s32_sel #(.W(W)) u_s(.s(e),.a(msrc[LO+:W]),.b(meta[LO+:W]),.y(mnx[LO+:W]));
  end
  always @(posedge ck or negedge rn)if(!rn)meta<=0;else meta<=mnx;
  // (G7) counters (the mus process's priority): sk = start of this context; a = active and not starting
  wire a=c_act[gk]&&!sk;
  wire wt=a&&c_wait[gk],nw=a&&!c_wait[gk];
  wire el=e_end[gk]&&!last[gk];
  reg[31:0]cnt,ag,tc;wire[31:0]cnx,anx,tnx;
  wire[31:0]tc1=tc+1'b1,ag1=ag+1'b1,cn1=cnt-1'b1;
  wire tc_c=sk||a;
  wire ag_c=sk||(wt&&f_wx[gk])||nw;
  wire ag_z=sk||(wt&&f_wx[gk])||(nw&&el);
  wire cn_c=(sk&&!g0z[gk])||wt||(nw&&el&&!ngz[gk]);
  for(gs=0;gs<2;gs=gs+1)begin:g_c
   localparam integer LO=16*gs,J1=(gk*6+gs+104)%RS,J2=(gk*6+gs+106)%RS,J3=(gk*6+gs+108)%RS;
   wire[15:0]t0,a0,c0,c1;
   ot_s32_and #(.W(16)) u_tz(.s(!(sk&&rs_s[J1])),.a(tc1[LO+:16]),.y(t0));
   ot_s32_sel #(.W(16)) u_te(.s(tc_c&&!fault_f[J1%FC]&&rs_s[J1]),.a(t0),.b(tc[LO+:16]),.y(tnx[LO+:16]));
   ot_s32_and #(.W(16)) u_az(.s(!(ag_z&&rs_s[J2])),.a(ag1[LO+:16]),.y(a0));
   ot_s32_sel #(.W(16)) u_ae(.s(ag_c&&!fault_f[J2%FC]&&rs_s[J2]),.a(a0),.b(ag[LO+:16]),.y(anx[LO+:16]));
   ot_s32_sel #(.W(16)) u_cw(.s(wt&&rs_s[J3]),.a(cn1[LO+:16]),.b(ng_f[32*gk+LO+:16]),.y(c0));
   ot_s32_sel #(.W(16)) u_cs(.s(sk&&rs_s[J3]),.a(g0_f[32*gk+LO+:16]),.b(c0),.y(c1));
   ot_s32_sel #(.W(16)) u_ce(.s(cn_c&&!fault_f[J3%FC]&&rs_s[J3]),.a(c1),.b(cnt[LO+:16]),.y(cnx[LO+:16]));
  end
  always @(posedge ck or negedge rn)if(!rn)begin tc<=0;ag<=0;cnt<=0;end else begin tc<=tnx;ag<=anx;cnt<=cnx;end
  assign meta_f[68*gk+:68]=meta;assign ag1_f[32*gk+:32]=ag1;assign tc1_f[32*gk+:32]=tc1;
  assign c_cnt_f[32*gk+:32]=cnt;assign c_age_f[32*gk+:32]=ag;assign c_tc_f[32*gk+:32]=tc;
  assign c_epoch_f[16*gk+:16]=meta[0+:16];assign c_token_f[18*gk+:18]=meta[16+:18];assign c_pos_f[18*gk+:18]=meta[34+:18];
  assign c_ctx_f[14*gk+:14]=meta[52+:14];assign c_gen_f[2*gk+:2]=meta[66+:2];
 end endgenerate
 // (G4) shadow words, (G5) stage-1 gaps, (G6) bound digest, (G8) duration sum: boot writes
 wire bw=we_q&&accept_cfg;
 generate for(gk=0;gk<8;gk=gk+1)begin:g_sh
  wire c=bw&&addr_q<324&&cfg_word<8&&cfg_word[2:0]==gk;
  reg[31:0]sh;wire[31:0]nx;
  for(gs=0;gs<2;gs=gs+1)begin:g_s
   localparam integer J=(gk*2+gs+132)%RS;
   ot_s32_sel #(.W(16)) u_s(.s(c&&!fault_f[J%FC]&&rnv[J%RC]&&rs_s[J]),.a(data_q[16*gs+:16]),.b(sh[16*gs+:16]),.y(nx[16*gs+:16]));
  end
  always @(posedge ck)sh<=nx;
  assign shadow_f[32*gk+:32]=sh;
 end endgenerate
 generate for(gk=0;gk<4;gk=gk+1)begin:g_g0
  wire c=bw&&addr_q>=326&&addr_q<470&&gap_j==0&&gap_u==gk;
  wire[33:0]src={data_q[31:0]==1,data_q[31:0]==0,data_q[31:0]};
  reg[33:0]g;wire[33:0]nx;
  for(gs=0;gs<3;gs=gs+1)begin:g_s
   localparam integer LO=16*gs,W=(gs==2)?2:16,J=(gk*3+gs+148)%RS;
   ot_s32_sel #(.W(W)) u_s(.s(c&&!fault_f[J%FC]&&rnv[J%RC]&&rs_s[J]),.a(src[LO+:W]),.b(g[LO+:W]),.y(nx[LO+:W]));
  end
  always @(posedge ck)g<=nx;
  assign g0_f[32*gk+:32]=g[31:0];assign g0z[gk]=g[32];assign g0one[gk]=g[33];
 end endgenerate
 reg[63:0]bd;reg[36:0]ds;wire[63:0]bnx;wire[36:0]dnx;
 wire bd_c=bw&&addr_q==324;
 wire ds_c=bw&&addr_q<324&&!(cfg_word<8);
 wire[36:0]ds_n=ds+{5'b0,data_q[31:0]};
 generate for(gs=0;gs<4;gs=gs+1)begin:g_bd
  localparam integer J=(gs+160)%RS;
  ot_s32_sel #(.W(16)) u_s(.s(bd_c&&!fault_f[J%FC]&&rs_s[J]),.a(data_q[16*gs+:16]),.b(bd[16*gs+:16]),.y(bnx[16*gs+:16]));
 end
 for(gs=0;gs<3;gs=gs+1)begin:g_ds
  localparam integer LO=16*gs,W=(gs==2)?5:16,J=(gs+164)%RS;
  ot_s32_sel #(.W(W)) u_s(.s(ds_c&&!fault_f[J%FC]&&rs_s[J]),.a(ds_n[LO+:W]),.b(ds[LO+:W]),.y(dnx[LO+:W]));
 end endgenerate
 always @(posedge ck or negedge rn)if(!rn)begin bd<=0;ds<=0;end else begin bd<=bnx;ds<=dnx;end
 assign bound_digest=bd;assign duration_sum=ds;
 // (G3) output metadata: one-hot fire / owner selects, gated per slice
 wire any=|e_any;
 wire hit=start_q&&start_ok&&fire_u==us;
 wire[3:0]fs={fire_u==2'd3,fire_u==2'd2,fire_u==2'd1,fire_u==2'd0};
 wire[3:0]os={owner==2'd3,owner==2'd2,owner==2'd1,owner==2'd0};
 wire ebf=|(fs&e_begin);
 wire aw=|(os&c_act&~c_wait),ao=|(os&c_act);
 wire[67:0]mq={gen_q,14'(pos_q+1),pos_q,token_q,epoch_q};
 reg[67:0]om;reg[31:0]oag,otc;wire[67:0]omx;wire[31:0]oax,otx;
 generate for(gs=0;gs<5;gs=gs+1)begin:g_om
  localparam integer LO=16*gs,W=(gs==4)?4:16,J=(gs+168)%RS;
  wire r=rs_s[J];
  wire[W-1:0]m0,m1,m2,m3,v;
  ot_s32_and #(.W(W)) u_a0(.s(fs[0]&&r),.a(meta_f[68*0+LO+:W]),.y(m0));
  ot_s32_and #(.W(W)) u_a1(.s(fs[1]&&r),.a(meta_f[68*1+LO+:W]),.y(m1));
  ot_s32_and #(.W(W)) u_a2(.s(fs[2]&&r),.a(meta_f[68*2+LO+:W]),.y(m2));
  ot_s32_and #(.W(W)) u_a3(.s(fs[3]&&r),.a(meta_f[68*3+LO+:W]),.y(m3));
  ot_s32_sel #(.W(W)) u_h(.s(hit&&r),.a(mq[LO+:W]),.b(m0|m1|m2|m3),.y(v));
  ot_s32_sel #(.W(W)) u_e(.s(any&&!fault_f[J%FC]&&r),.a(v),.b(om[LO+:W]),.y(omx[LO+:W]));
 end
 for(gs=0;gs<2;gs=gs+1)begin:g_oa
  localparam integer LO=16*gs,J=(gs+173)%RS,K=(gs+175)%RS;
  wire r=rs_s[J],q=rs_s[K];
  wire[15:0]f0,f1,f2,f3,o0,o1,o2,o3,fz,va,t0,t1,t2,t3,u0,u1,u2,u3,tz,vt;
  ot_s32_and #(.W(16)) u_f0(.s(fs[0]&&r),.a(ag1_f[32*0+LO+:16]),.y(f0));
  ot_s32_and #(.W(16)) u_f1(.s(fs[1]&&r),.a(ag1_f[32*1+LO+:16]),.y(f1));
  ot_s32_and #(.W(16)) u_f2(.s(fs[2]&&r),.a(ag1_f[32*2+LO+:16]),.y(f2));
  ot_s32_and #(.W(16)) u_f3(.s(fs[3]&&r),.a(ag1_f[32*3+LO+:16]),.y(f3));
  ot_s32_and #(.W(16)) u_o0(.s(os[0]&&r),.a(ag1_f[32*0+LO+:16]),.y(o0));
  ot_s32_and #(.W(16)) u_o1(.s(os[1]&&r),.a(ag1_f[32*1+LO+:16]),.y(o1));
  ot_s32_and #(.W(16)) u_o2(.s(os[2]&&r),.a(ag1_f[32*2+LO+:16]),.y(o2));
  ot_s32_and #(.W(16)) u_o3(.s(os[3]&&r),.a(ag1_f[32*3+LO+:16]),.y(o3));
  ot_s32_and #(.W(16)) u_fz(.s(!(ebf&&r)),.a(f0|f1|f2|f3),.y(fz));
  ot_s32_sel #(.W(16)) u_va(.s(any&&r),.a(fz),.b(o0|o1|o2|o3),.y(va));
  ot_s32_sel #(.W(16)) u_ea(.s((any||aw)&&!fault_f[J%FC]&&r),.a(va),.b(oag[LO+:16]),.y(oax[LO+:16]));
  ot_s32_and #(.W(16)) u_t0(.s(fs[0]&&q),.a(tc1_f[32*0+LO+:16]),.y(t0));
  ot_s32_and #(.W(16)) u_t1(.s(fs[1]&&q),.a(tc1_f[32*1+LO+:16]),.y(t1));
  ot_s32_and #(.W(16)) u_t2(.s(fs[2]&&q),.a(tc1_f[32*2+LO+:16]),.y(t2));
  ot_s32_and #(.W(16)) u_t3(.s(fs[3]&&q),.a(tc1_f[32*3+LO+:16]),.y(t3));
  ot_s32_and #(.W(16)) u_u0(.s(os[0]&&q),.a(tc1_f[32*0+LO+:16]),.y(u0));
  ot_s32_and #(.W(16)) u_u1(.s(os[1]&&q),.a(tc1_f[32*1+LO+:16]),.y(u1));
  ot_s32_and #(.W(16)) u_u2(.s(os[2]&&q),.a(tc1_f[32*2+LO+:16]),.y(u2));
  ot_s32_and #(.W(16)) u_u3(.s(os[3]&&q),.a(tc1_f[32*3+LO+:16]),.y(u3));
  ot_s32_and #(.W(16)) u_tz(.s(!(hit&&q)),.a(t0|t1|t2|t3),.y(tz));
  ot_s32_sel #(.W(16)) u_vt(.s(any&&q),.a(tz),.b(u0|u1|u2|u3),.y(vt));
  ot_s32_sel #(.W(16)) u_et(.s((any||ao)&&!fault_f[K%FC]&&q),.a(vt),.b(otc[LO+:16]),.y(otx[LO+:16]));
 end endgenerate
 always @(posedge ck or negedge rn)if(!rn)begin om<=0;oag<=0;otc<=0;end else begin om<=omx;oag<=oax;otc<=otx;end
 assign epoch=om[0+:16];assign token=om[16+:18];assign position=om[34+:18];assign ctx_t=om[52+:14];assign generation=om[66+:2];
 assign age=oag;assign token_cycles=otc;
`ifndef SYNTHESIS
 initial if(MU!=1)$fatal(1,"qkd_static_kv_layer_programme_s32: MU must be 1");
 initial if(FC<2||RS<24||RC<2)$fatal(1,"qkd_static_kv_layer_programme_s32: FC >= 2, RS >= 24, RCOPIES >= 2");
`endif
endmodule

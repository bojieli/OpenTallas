`timescale 1ns/1ps
// KV-GRP-CTL/MU5 10-19: STRUCTURAL successor of qkd_static_kv_layer_programme_mu MU 1 (same ports, same boot image, same
// outputs on every edge; that file is untouched).  SAFE-DESIGN checklist (owner 10-19) items 4 and 5 of the mu4_safe gate:
//   Storage: the 9 x 36 x 32 b stage table + the 144 x 32 b GAP table (+ shadow) were runtime-indexed flop tables (~15.2 kb).
//            Here they live in two ot_sram_1r1w_128x256_m1_r2c2 macros, one row per stage (row = stage - 1):
//              u_rowa  bits 32w+:32 = P_w = r_w - 2   for w = 0..7 (ctrl k v issue run writer link quiet)
//              u_rowb  bits   0+:32 = P_end = r_end - 2
//                      bits 32+32u+:32 = GAP[u][row+1] (the gap before stage row+2 of user u; row 35: unused)
//                      bit 160+u = (GAP[u][row+1] == 0), bit 164+u = (GAP[u][row+1] == 1)
//            and the 4 stage-1 gaps GAP[u][0] are boot-written registers (g0, g0z, g0one).  Boot writes stay 32-bit words:
//            the macros' bit write mask writes one field per word (registered one edge after the accept, as the
//            original's wq pipeline; nothing reads a row before the seal).
//   Row fetch: the read is ISSUED on the edge that sets c_load (a stage begins), address = the beginning context's new
//            stage; the macro's registered output is latched into that context's row registers on the c_load edge, the
//            same edge the original copied t_X[c_stage-1] -> r_X.  0 added token-schedule cycles.  The next-gap value,
//            its ==0 / ==1 flags arrive with the row (per-user registers), so no 4-user GAP table read remains.
//   Depth:   the row holds r_X - 2, so the original combinational e_X = (c_age == r_X - 1) [subtract + compare + 4-user
//            priority + metadata mux in one stage, mu4 ~675 ps / 17 lv] becomes a REGISTERED flag f_X computed one edge
//            early as the plain equality c_age == P_X; the wait-expiry e_begin (c_cnt == 1) is registered the same way
//            (c_cnt == 2 one edge early, or the loaded gap's ==1 flag).  Exact because every r_X >= 3 after the boot row
//            check (bad_row), so no event can fire on the first cycle after a row load (P_X >= 1 > 0 = c_age there).
//            Digest / epoch / position start checks are compared on the pin values one edge early (bound_* is stable
//            from >= 146 edges before configured until reset).
//   Reset:   RC KEPT identical copies of the reset pin flop (family wire rnv, ot_rst_split) for the synthesis
//            reset-relay split (physical/common_flow/ot_rst_copies.py).
// MUT (bench only): 2 = stage output xor 1 (as the original); MUT 1 of the original (writer offset) is not carried.
// MU must be 1 (the multi-user form; the generator passes MUT 0 / MU 1).
module qkd_static_kv_layer_programme_ctlp #(parameter integer ENABLE=0,parameter integer MUT=0,parameter integer MU=1)(
 input wire ck,rst_n,
 input wire cfg_we,input wire[8:0]cfg_addr,input wire[63:0]cfg_data,
 input wire start,authority_valid,programme_authorized,
 input wire[15:0]programme_epoch,input wire[63:0]programme_digest,
 input wire[15:0]authority_epoch,input wire[17:0]authority_token,authority_position,
 input wire[1:0]authority_generation,
 output reg ctrl_go,kgo,vgo,attention_issue,attention_run,writer_start,link_start,
 output reg stage_start,stage_done,expected_upstream_quiet,output reg[5:0]completed_stage,
 output wire[5:0]stage,output wire[5:0]layer,
 output reg[15:0]epoch,output reg[17:0]token,position,output reg[13:0]ctx_t,
 output reg[1:0]generation,
 output reg configured,active,done,fault,output reg[7:0]fault_code,
 output reg[31:0]age,token_cycles
);
 localparam integer RC=4;
 (* keep = "true", ot_rst_split *) reg[RC-1:0]rnv;
 always @(posedge ck)rnv<={RC{rst_n}};
 wire rn=rnv[0];
 reg we_q,start_q,av_q,authorized_q;reg[8:0]addr_q;reg[63:0]data_q;
 reg[15:0]epoch_q;reg[17:0]token_q,pos_q;reg[1:0]gen_q;
 reg[63:0]bound_digest;reg[15:0]bound_epoch;
 reg dig_ok_q,ep_ok_q,pos_ok_q;
 always @(posedge ck)begin
  addr_q<=cfg_addr;data_q<=cfg_data;
  epoch_q<=authority_epoch;token_q<=authority_token;pos_q<=authority_position;gen_q<=authority_generation;
  dig_ok_q<=programme_digest==bound_digest;ep_ok_q<=programme_epoch==bound_epoch;pos_ok_q<=authority_position<=18'd8191;
 end
 always @(posedge ck or negedge rn)
 if(!rn)begin we_q<=0;start_q<=0;av_q<=0;authorized_q<=0;end
 else begin we_q<=cfg_we;start_q<=start;av_q<=authority_valid;authorized_q<=programme_authorized;end
 // ---- contexts ----
 reg[3:0]c_act,c_wait,c_load,c_quiet;reg[31:0]c_cnt[0:3],c_age[0:3],c_tc[0:3];reg[5:0]c_stage[0:3];
 reg[15:0]c_epoch[0:3];reg[17:0]c_token[0:3],c_pos[0:3];reg[13:0]c_ctx[0:3];reg[1:0]c_gen[0:3];
 // per-context row registers (loaded from the macros on the c_load edge)
 reg[31:0]p_ctrl[0:3],p_k[0:3],p_v[0:3],p_issue[0:3],p_run[0:3],p_writer[0:3],p_link[0:3],p_quiet[0:3],p_end[0:3];
 reg[31:0]ng[0:3];reg[3:0]ngz,ngone;
 reg[31:0]g0[0:3];reg[3:0]g0z,g0one;
 // registered next events
 reg[3:0]f_ctrl,f_k,f_v,f_issue,f_run,f_writer,f_link,f_quiet,f_end,f_wx;
 // ---- boot ----
 reg[8:0]next_cfg;reg[5:0]cfg_stage;reg[3:0]cfg_word;reg[7:0]cfg_gap;reg[1:0]gap_u;reg[5:0]gap_j;
 reg[36:0]duration_sum;
 reg[31:0]shadow[0:7];
 wire accept_cfg=we_q&&!configured&&!(|c_act)&&!fault&&addr_q==next_cfg;
 reg bad_row;
 always @*begin
  bad_row=data_q[63:32]!=0;
  for(integer k=0;k<8;k=k+1)if(shadow[k]<3||shadow[k]>=data_q[31:0])bad_row=1;
  for(integer k=0;k<7;k=k+1)if(shadow[7]<=shadow[k])bad_row=1;
  if({1'b0,shadow[4]} < {1'b0,shadow[3]}+33'd4)bad_row=1;
  if(duration_sum+{5'b0,data_q[31:0]}>37'h0ffffffff)bad_row=1;
 end
 // write pipeline (one edge after the accept, as the original's wq): stage words -> P = r - 2; gap words j >= 1 -> rowb
 reg wq,wg;reg[5:0]w_row;reg[7:0]w_field;reg w_end;reg[1:0]w_u;reg[31:0]w_data;reg w_zero,w_one;
 wire row_acc=accept_cfg&&addr_q<324;
 wire gap_acc=accept_cfg&&addr_q>=326&&addr_q<470;
 always @(posedge ck or negedge rn)if(!rn)begin wq<=0;wg<=0;end else begin wq<=row_acc;wg<=gap_acc&&gap_j!=0;end
 always @(posedge ck)begin
  w_row<=row_acc?cfg_stage:(gap_j-6'd1);w_field<=8'd1<<cfg_word[2:0];w_end<=cfg_word==8;w_u<=gap_u;
  w_data<=row_acc?(data_q[31:0]-32'd2):data_q[31:0];w_zero<=data_q[31:0]==0;w_one<=data_q[31:0]==1;
 end
 wire[255:0]a_mask={{32{w_field[7]}},{32{w_field[6]}},{32{w_field[5]}},{32{w_field[4]}},
                    {32{w_field[3]}},{32{w_field[2]}},{32{w_field[1]}},{32{w_field[0]}}};
 wire[3:0]u1=4'd1<<w_u;
 wire[255:0]b_mask=wq?{224'd0,32'hffffffff}:
                     {88'd0,u1,u1,{32{u1[3]}},{32{u1[2]}},{32{u1[1]}},{32{u1[0]}},32'd0};
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
  // a waiting context begins when its gap expires; a stage end begins the next stage on the same edge when its gap
  // is 0; a start begins stage 1 at once when the user's stage-1 gap is 0
  e_begin=f_wx|(f_end&~last&ngz);
  if(start_go&&g0z[us])e_begin[us]=1'b1;
  e_any=f_ctrl|f_k|f_v|f_issue|f_run|f_writer|f_link|f_quiet|f_end|e_begin;
  // row of the stage that begins (at most one context per edge; two are a collision fault)
  rd_idx=0;
  for(integer k=0;k<4;k=k+1)if(e_begin[k])
   rd_idx=rd_idx|((start_go&&us==k)?6'd0:(f_wx[k]?c_stage[k]-6'd1:c_stage[k]));
 end
 wire[255:0]rowa,rowb;
 ot_sram_1r1w_128x256_m1_r2c2 u_rowa(.clk(ck),.r_ce_in(|e_begin),.r_addr_in({1'b0,rd_idx}),.rd_out(rowa),
  .w_ce_in(wq&&!w_end),.w_addr_in({1'b0,w_row}),.wd_in({8{w_data}}),.w_mask_in(a_mask),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 ot_sram_1r1w_128x256_m1_r2c2 u_rowb(.clk(ck),.r_ce_in(|e_begin),.r_addr_in({1'b0,rd_idx}),.rd_out(rowb),
  .w_ce_in((wq&&w_end)||wg),.w_addr_in({1'b0,w_row}),.wd_in(b_data),.w_mask_in(b_mask),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 // ---- events ----
 wire[3:0]e_ctrl=f_ctrl,e_k=f_k,e_v=f_v,e_issue=f_issue,e_run=f_run,e_writer=f_writer,e_link=f_link,e_quiet=f_quiet,e_end=f_end;
 wire collide=(e_any&(e_any-4'd1))!=0;                  // two or more contexts fire on this edge
 reg[1:0]owner;reg[5:0]stage_o;
 reg[1:0]fire_u;always @*begin fire_u=owner;for(integer k=3;k>=0;k=k-1)if(e_any[k])fire_u=2'(k);end
 assign stage=(MUT==2)?(stage_o^6'd1):stage_o;
 assign layer=stage-6'd1;
 always @(posedge ck or negedge rn)begin
  if(!rn)begin
   ctrl_go<=0;kgo<=0;vgo<=0;attention_issue<=0;attention_run<=0;writer_start<=0;link_start<=0;
   stage_start<=0;stage_done<=0;expected_upstream_quiet<=0;completed_stage<=0;
   epoch<=0;token<=0;position<=0;ctx_t<=0;generation<=0;
   configured<=0;active<=0;done<=0;fault<=0;fault_code<=0;age<=0;token_cycles<=0;
   next_cfg<=0;cfg_stage<=0;cfg_word<=0;cfg_gap<=0;gap_u<=0;gap_j<=0;bound_digest<=0;bound_epoch<=0;duration_sum<=0;
   c_act<=0;c_wait<=0;c_load<=0;c_quiet<=0;owner<=0;stage_o<=0;
   f_ctrl<=0;f_k<=0;f_v<=0;f_issue<=0;f_run<=0;f_writer<=0;f_link<=0;f_quiet<=0;f_end<=0;f_wx<=0;
   for(integer k=0;k<4;k=k+1)begin c_cnt[k]<=0;c_age[k]<=0;c_tc[k]<=0;c_stage[k]<=0;c_epoch[k]<=0;c_token[k]<=0;c_pos[k]<=0;c_ctx[k]<=0;c_gen[k]<=0;end
  end else begin
   ctrl_go<=0;kgo<=0;vgo<=0;attention_issue<=0;attention_run<=0;writer_start<=0;link_start<=0;
   stage_start<=0;stage_done<=0;done<=0;
   if(fault)begin
    active<=0;c_act<=0;
    f_ctrl<=0;f_k<=0;f_v<=0;f_issue<=0;f_run<=0;f_writer<=0;f_link<=0;f_quiet<=0;f_end<=0;f_wx<=0;
   end else begin
    // boot
    if(we_q)begin
     if(!accept_cfg)begin fault<=1;fault_code[0]<=1;end
     else if(addr_q<324)begin
      if(data_q[63:32]!=0||(cfg_word==8&&bad_row))begin fault<=1;fault_code[1]<=1;end
      if(cfg_word<8)shadow[cfg_word[2:0]]<=data_q[31:0];
      else duration_sum<=duration_sum+{5'b0,data_q[31:0]};
      if(cfg_word==8)begin cfg_stage<=cfg_stage+1'b1;cfg_word<=0;end else cfg_word<=cfg_word+1'b1;
      next_cfg<=next_cfg+1'b1;
     end else if(addr_q==324)begin bound_digest<=data_q;next_cfg<=325;end
     else if(addr_q==325)begin
      if(data_q[63:16]!=0)begin fault<=1;fault_code[2]<=1;end
      bound_epoch<=data_q[15:0];next_cfg<=326;
     end else if(addr_q<470)begin
      if(data_q[63:32]!=0)begin fault<=1;fault_code[2]<=1;end
      if(gap_j==0)begin g0[gap_u]<=data_q[31:0];g0z[gap_u]<=data_q[31:0]==0;g0one[gap_u]<=data_q[31:0]==1;end
      if(gap_j==35)begin gap_j<=0;gap_u<=gap_u+1'b1;end else gap_j<=gap_j+1'b1;
      next_cfg<=next_cfg+1'b1;cfg_gap<=cfg_gap+1'b1;
     end else if(addr_q==470)begin
      if(data_q!=64'h514b564c59523336||cfg_stage!=36||cfg_gap!=144||duration_sum==0)begin fault<=1;fault_code[2]<=1;end
      else configured<=1;
     end else begin fault<=1;fault_code[0]<=1;end
    end
    if(collide)begin fault<=1;fault_code[4]<=1;end
    // start: user = authority epoch[1:0]
    if(start_q)begin
     if(!start_ok)begin fault<=1;fault_code[3]<=1;end
     else begin
      c_act[us]<=1;c_epoch[us]<=epoch_q;c_token[us]<=token_q;c_pos[us]<=pos_q;c_ctx[us]<=14'(pos_q+1);c_gen[us]<=gen_q;
      c_stage[us]<=1;c_tc[us]<=0;c_age[us]<=0;c_quiet[us]<=0;
      if(g0z[us])begin c_wait[us]<=0;c_load[us]<=1;end
      else begin c_wait[us]<=1;c_load[us]<=0;c_cnt[us]<=g0[us];end
     end
    end
    for(integer k=0;k<4;k=k+1)begin
     // next-edge event flags (the original's combinational e_X of the next cycle)
     f_ctrl[k]<=0;f_k[k]<=0;f_v[k]<=0;f_issue[k]<=0;f_run[k]<=0;f_writer[k]<=0;f_link[k]<=0;f_quiet[k]<=0;f_end[k]<=0;f_wx[k]<=0;
     if(start_go&&us==k)f_wx[k]<=!g0z[k]&&g0one[k];
     else if(c_act[k])begin
      if(c_wait[k])f_wx[k]<=c_cnt[k]==2;
      else if(!c_load[k])begin
       if(e_end[k])f_wx[k]<=!last[k]&&!ngz[k]&&ngone[k];
       else begin
        f_ctrl[k]<=c_age[k]==p_ctrl[k];f_k[k]<=c_age[k]==p_k[k];f_v[k]<=c_age[k]==p_v[k];
        f_issue[k]<=c_age[k]==p_issue[k];f_run[k]<=c_age[k]==p_run[k];f_writer[k]<=c_age[k]==p_writer[k];
        f_link[k]<=c_age[k]==p_link[k];f_quiet[k]<=c_age[k]==p_quiet[k];f_end[k]<=c_age[k]==p_end[k];
       end
      end
      // (c_load: the row lands on this edge; P >= 1 so nothing fires on the next cycle, c_age = 1)
     end
    end
    for(integer k=0;k<4;k=k+1)if(c_act[k]&&!(start_q&&start_ok&&us==k))begin
     c_tc[k]<=c_tc[k]+1'b1;
     if(c_load[k])c_load[k]<=0;
     if(c_wait[k])begin
      c_cnt[k]<=c_cnt[k]-1'b1;
      if(f_wx[k])begin c_wait[k]<=0;c_load[k]<=1;c_age[k]<=0;end
     end else begin
      c_age[k]<=c_age[k]+1'b1;
      if(e_quiet[k])c_quiet[k]<=1;
      if(e_end[k])begin
       if(last[k])begin c_act[k]<=0;end
       else begin
        c_stage[k]<=c_stage[k]+1'b1;c_age[k]<=0;c_quiet[k]<=0;
        if(ngz[k])c_load[k]<=1;
        else begin c_wait[k]<=1;c_cnt[k]<=ng[k];end
       end
      end
     end
    end
    // row landing (the read was issued on the edge that set c_load)
    for(integer k=0;k<4;k=k+1)if(c_load[k])begin
     p_ctrl[k]<=rowa[31:0];p_k[k]<=rowa[63:32];p_v[k]<=rowa[95:64];p_issue[k]<=rowa[127:96];
     p_run[k]<=rowa[159:128];p_writer[k]<=rowa[191:160];p_link[k]<=rowa[223:192];p_quiet[k]<=rowa[255:224];
     p_end[k]<=rowb[31:0];ng[k]<=rowb[32+32*k+:32];ngz[k]<=rowb[160+k];ngone[k]<=rowb[164+k];
    end
    // outputs: OR of the (at most one) firing context; metadata follow it
    ctrl_go<=|e_ctrl;kgo<=|e_k;vgo<=|e_v;attention_issue<=|e_issue;attention_run<=|e_run;writer_start<=|e_writer;
    link_start<=|e_link;stage_done<=|e_end;stage_start<=|e_begin;
    if(|e_any)begin
     owner<=fire_u;
     epoch<=(start_q&&start_ok&&fire_u==us)?epoch_q:c_epoch[fire_u];
     token<=(start_q&&start_ok&&fire_u==us)?token_q:c_token[fire_u];
     position<=(start_q&&start_ok&&fire_u==us)?pos_q:c_pos[fire_u];
     ctx_t<=(start_q&&start_ok&&fire_u==us)?14'(pos_q+1):c_ctx[fire_u];
     generation<=(start_q&&start_ok&&fire_u==us)?gen_q:c_gen[fire_u];
     if(e_end[fire_u])begin completed_stage<=c_stage[fire_u];if(last[fire_u])done<=1;end
     stage_o<=(e_end[fire_u]&&!last[fire_u])?c_stage[fire_u]+1'b1:((start_q&&start_ok&&fire_u==us)?6'd1:c_stage[fire_u]);
     expected_upstream_quiet<=e_quiet[fire_u]||(c_quiet[fire_u]&&!e_begin[fire_u]);
     age<=e_begin[fire_u]?32'd0:c_age[fire_u]+1'b1;
     token_cycles<=(start_q&&start_ok&&fire_u==us)?32'd0:c_tc[fire_u]+1'b1;
    end else begin
     if(e_quiet[owner])expected_upstream_quiet<=1;
     if(c_act[owner]&&!c_wait[owner])age<=c_age[owner]+1'b1;
     if(c_act[owner])token_cycles<=c_tc[owner]+1'b1;
    end
    active<=|(c_act&~(e_end&last))||(start_q&&start_ok);
   end
  end
 end
`ifndef SYNTHESIS
 initial if(MU!=1)$fatal(1,"qkd_static_kv_layer_programme_mus: MU must be 1");
`endif
endmodule

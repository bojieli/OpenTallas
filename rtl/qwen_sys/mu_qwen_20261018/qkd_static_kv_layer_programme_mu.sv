`timescale 1ns/1ps
// MU-ADOPT-HROOT 10-19 (Qwen ROM 4 users, the KV analogue of compute-die R1): multi-context successor of
// qkd_static_kv_layer_programme (same ports; the original file is untouched).
//   MU 0: instantiates the unchanged original (behaviour-identical by construction).
//   MU 1: four token contexts, one per user (user = authority_epoch[1:0], the epoch {seq14, user2} convention), sharing
//         the one boot-loaded stage table (every user runs the single-user layer programme: same 9 roots per stage).
//         Static calendar: a compiled per-user, per-stage GAP table says how many idle cycles user u waits before its
//         stage s (s = 1..36; for stage 1, after its start is accepted).  User 0 (the latency user) is compiled with
//         all gaps 0, so its every start / stage / root / metadata edge is the original's (bench: lockstep).
//         Collision rule (static schedule, never a stall): two contexts with an event (any root pulse, stage_start,
//         stage_done) on the same edge is a sticky fault (fault_code[4]); the compiler must never emit such a calendar.
//         A start for a user whose context is active is fault_code[3] (as a start while active in the original).
//   Boot image (MU): addresses 0..323 rows (unchanged), 324 digest64, 325 epoch16, 326..469 GAP[u][s-1] (u-major,
//         144 words, low 32 bits, upper 32 must be 0), 470 seal 514b564c59523336.  Metadata outputs (epoch, token,
//         position, ctx_t, generation, stage, layer, completed_stage, age, token_cycles, expected_upstream_quiet) follow
//         the context that fired the latest event, so every consumer that latches them at its event pulse sees that
//         user's stage (the user rides in epoch[1:0] downstream, MU-ADOPT-KV).  Single shared table read port: only one
//         context can load a stage row per edge (a second is a stage_start collision, already a fault).
//   TOKLIST 1 (MU-KV-TOKLIST 10-19, opt-in; MU 1 only; TOKLIST 0 = the GAP mode above, unchanged): every filler user
//         (1..3) plays a frame-periodic LIST of per-token 36-gap tables instead of one table (the op-granular frame
//         gives each filler token its own KV stage pattern; tools/qwen_static_schedule/mu_calendar.kv_token_lists).
//         User 0 (the latency user) is hard-wired to gap 0 (no entries).  Store: 2 x ot_sram_1rw_256x64_m4_r2c2 (512
//         words, 3 20-bit entries a word, bits [63:60] 0: a token table = 12 words).  Each context holds its NEXT gap in a
//         prefetch register (ng, valid ngv); consuming it (a start, or a stage end before stage 36) requests the next
//         entry; one shared read port serves the requests (2 edges each, lowest user first), the pointer walks the user's
//         words [wbase, wend) and wraps at wend (frame-periodic).  Consuming an entry that has not arrived is a sticky
//         fault (fault_code[5]); the compiler's stages are thousands of edges, the refill takes <= 6.
//         Boot (layer bus): 326 header {ntok3, ntok2, ntok1, ntok0 = 0} [31:0] (upper 32 = 0, 12 (n1 + n2 + n3) <= 512),
//         327 the list words (a counted stream: NW = 12 (n1 + n2 + n3) writes at address 327), 470 the seal.
//   TLMUT (bench mutants, 0 = off): 1 the pointer does not wrap at the user's list end; 2 the lane select is off by one.
module qkd_static_kv_layer_programme_mu #(parameter integer MUT=0,parameter integer MU=1,parameter integer TOKLIST=0,parameter integer TLMUT=0)(
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
generate if(MU==0)begin:g_plain
 wire w_ctrl_go,w_kgo,w_vgo,w_ai,w_ar,w_ws,w_ls,w_ss,w_sd,w_q,w_cf,w_ac,w_dn,w_ft;wire[5:0]w_cs;
 wire[15:0]w_ep;wire[17:0]w_tk,w_ps;wire[13:0]w_ct;wire[1:0]w_gn;wire[7:0]w_fc;wire[31:0]w_age,w_tc;
 qkd_static_kv_layer_programme #(.MUT(MUT))u_plain(.ck(ck),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .start(start),.authority_valid(authority_valid),.programme_authorized(programme_authorized),.programme_epoch(programme_epoch),
  .programme_digest(programme_digest),.authority_epoch(authority_epoch),.authority_token(authority_token),
  .authority_position(authority_position),.authority_generation(authority_generation),
  .ctrl_go(w_ctrl_go),.kgo(w_kgo),.vgo(w_vgo),.attention_issue(w_ai),.attention_run(w_ar),.writer_start(w_ws),.link_start(w_ls),
  .stage_start(w_ss),.stage_done(w_sd),.expected_upstream_quiet(w_q),.completed_stage(w_cs),.stage(stage),.layer(layer),
  .epoch(w_ep),.token(w_tk),.position(w_ps),.ctx_t(w_ct),.generation(w_gn),.configured(w_cf),.active(w_ac),.done(w_dn),
  .fault(w_ft),.fault_code(w_fc),.age(w_age),.token_cycles(w_tc));
 always @*begin
  ctrl_go=w_ctrl_go;kgo=w_kgo;vgo=w_vgo;attention_issue=w_ai;attention_run=w_ar;writer_start=w_ws;link_start=w_ls;
  stage_start=w_ss;stage_done=w_sd;expected_upstream_quiet=w_q;completed_stage=w_cs;epoch=w_ep;token=w_tk;position=w_ps;
  ctx_t=w_ct;generation=w_gn;configured=w_cf;active=w_ac;done=w_dn;fault=w_ft;fault_code=w_fc;age=w_age;token_cycles=w_tc;
 end
end else begin:g_mu
 (* keep *)reg rn;always @(posedge ck)rn<=rst_n;
 reg we_q,start_q,av_q,authorized_q;reg[8:0]addr_q;reg[63:0]data_q,pdigest_q;
 reg[15:0]pepoch_q,epoch_q;reg[17:0]token_q,pos_q;reg[1:0]gen_q;
 always @(posedge ck)begin
  addr_q<=cfg_addr;data_q<=cfg_data;pdigest_q<=programme_digest;pepoch_q<=programme_epoch;
  epoch_q<=authority_epoch;token_q<=authority_token;pos_q<=authority_position;gen_q<=authority_generation;
 end
 always @(posedge ck or negedge rn)
 if(!rn)begin we_q<=0;start_q<=0;av_q<=0;authorized_q<=0;end
 else begin we_q<=cfg_we;start_q<=start;av_q<=authority_valid;authorized_q<=programme_authorized;end
 // ---- contexts ----
 reg[3:0]c_act,c_wait,c_load;reg[31:0]c_cnt[0:3],c_age[0:3],c_tc[0:3];reg[5:0]c_stage[0:3];
 reg[31:0]r_ctrl[0:3],r_k[0:3],r_v[0:3],r_issue[0:3],r_run[0:3],r_writer[0:3],r_link[0:3],r_quiet[0:3],r_end[0:3];
 reg[15:0]c_epoch[0:3];reg[17:0]c_token[0:3],c_pos[0:3];reg[13:0]c_ctx[0:3];reg[1:0]c_gen[0:3];reg[3:0]c_quiet;
 // ---- boot (rows as the original; + the GAP table) ----
 reg[8:0]next_cfg;reg[5:0]cfg_stage;reg[3:0]cfg_word;reg[7:0]cfg_gap;
 reg[63:0]bound_digest;reg[15:0]bound_epoch;reg[36:0]duration_sum;
 reg[31:0]shadow[0:7];
 reg[31:0]t_ctrl[0:35],t_k[0:35],t_v[0:35],t_issue[0:35],t_run[0:35];
 reg[31:0]t_writer[0:35],t_link[0:35],t_quiet[0:35],t_end[0:35];
 reg[31:0]t_gap[0:143];
 reg wq;reg[35:0]wq_stage;reg[8:0]wq_word;reg[31:0]wq_data;
 wire accept_cfg=we_q&&!configured&&!(|c_act)&&!fault&&addr_q==next_cfg;
 reg bad_row;
 always @*begin
  bad_row=data_q[63:32]!=0;
  for(integer k=0;k<8;k=k+1)if(shadow[k]<3||shadow[k]>=data_q[31:0])bad_row=1;
  for(integer k=0;k<7;k=k+1)if(shadow[7]<=shadow[k])bad_row=1;
  if({1'b0,shadow[4]} < {1'b0,shadow[3]}+33'd4)bad_row=1;
  if(duration_sum+{5'b0,data_q[31:0]}>37'h0ffffffff)bad_row=1;
 end
 always @(posedge ck or negedge rn)if(!rn)wq<=0;else wq<=accept_cfg&&addr_q<324;
 always @(posedge ck)begin wq_stage<=36'd1<<cfg_stage;wq_word<=9'd1<<cfg_word;wq_data<=data_q[31:0];end
 genvar g;
 for(g=0;g<36;g=g+1)begin:rows
  always @(posedge ck)if(wq&&wq_stage[g])begin
   if(wq_word[0])t_ctrl[g]<=wq_data;if(wq_word[1])t_k[g]<=wq_data;
   if(wq_word[2])t_v[g]<=wq_data;if(wq_word[3])t_issue[g]<=wq_data;
   if(wq_word[4])t_run[g]<=wq_data;if(wq_word[5])t_writer[g]<=wq_data;
   if(wq_word[6])t_link[g]<=wq_data;if(wq_word[7])t_quiet[g]<=wq_data;
   if(wq_word[8])t_end[g]<=wq_data;
  end
 end
 always @(posedge ck)if(TOKLIST==0&&accept_cfg&&addr_q>=326&&addr_q<470)t_gap[addr_q-9'd326]<=data_q[31:0];
 // ---- TOKLIST state + the list SRAM (2 x 256 x 64, 1RW: boot writes, then prefetch reads) ----
 reg tl_hdr;reg[9:0]tl_nw,tl_cnt;reg[7:0]tl_n[1:3];reg[8:0]tl_wb[1:3];reg[9:0]tl_we[1:3];
 reg[8:0]tl_pw[1:3];reg[1:0]tl_pl[1:3];reg[19:0]ng[0:3];reg[3:0]ngv,ngr;
 reg f_v;reg[1:0]f_u,f_l;reg f_b;
 wire[13:0]tl_nw_d=14'd12*({6'd0,data_q[15:8]}+{6'd0,data_q[23:16]}+{6'd0,data_q[31:24]});
 wire tl_wr=TOKLIST!=0&&accept_cfg&&addr_q==327;
 reg rd_go;reg[1:0]rd_u;
 always @*begin rd_go=0;rd_u=0;if(TOKLIST!=0&&!f_v&&!fault)for(integer k=3;k>=1;k=k-1)if(ngr[k])begin rd_go=1;rd_u=2'(k);end end
 wire[8:0]m_addr=tl_wr?tl_cnt[8:0]:tl_pw[rd_u==0?1:rd_u];
 wire[63:0]m_rd0,m_rd1;
 if(TOKLIST!=0)begin:g_tl
  ot_sram_1rw_256x64_m4_r2c2 u_tl0(.clk(ck),.ce_in((tl_wr||rd_go)&&!m_addr[8]),.we_in(tl_wr),.addr_in(m_addr[7:0]),.wd_in(data_q),
   .w_mask_in({64{1'b1}}),.rd_out(m_rd0),.rr_en(2'b0),.rr_addr(12'd0),.cr_en(2'b0),.cr_sel(12'd0));
  ot_sram_1rw_256x64_m4_r2c2 u_tl1(.clk(ck),.ce_in((tl_wr||rd_go)&&m_addr[8]),.we_in(tl_wr),.addr_in(m_addr[7:0]),.wd_in(data_q),
   .w_mask_in({64{1'b1}}),.rd_out(m_rd1),.rr_en(2'b0),.rr_addr(12'd0),.cr_en(2'b0),.cr_sel(12'd0));
 end else begin:g_notl
  assign m_rd0=0;assign m_rd1=0;
 end
 wire[63:0]m_rd=f_b?m_rd1:m_rd0;
 wire[1:0]f_ls=(TLMUT==2)?((f_l==2)?2'd0:f_l+2'd1):f_l;
 wire[19:0]m_ent=(f_ls==0)?m_rd[19:0]:(f_ls==1)?m_rd[39:20]:m_rd[59:40];
 reg[1:0]owner;reg[5:0]stage_o;
 assign stage=(MUT==2)?(stage_o^6'd1):stage_o;
 assign layer=stage-6'd1;
 wire[1:0]us=epoch_q[1:0];
 wire start_ok=configured&&!c_act[us]&&!we_q&&av_q&&authorized_q&&pos_q<=8191&&pepoch_q==bound_epoch&&pdigest_q==bound_digest;
 // the gap before a context's next stage begin: GAP mode the table, TOKLIST the prefetched entry (user 0: 0)
 reg[31:0]gv_next[0:3];reg[31:0]gv_start;
 always @*begin
  for(integer k=0;k<4;k=k+1)gv_next[k]=(TOKLIST!=0)?((k==0)?32'd0:{12'd0,ng[k]}):t_gap[8'(36*k)+8'(c_stage[k])];
  gv_start=(TOKLIST!=0)?((us==0)?32'd0:{12'd0,ng[us]}):t_gap[8'(36*us)];
 end
 // per-context next events (combinational from registered state)
 reg[3:0]e_ctrl,e_k,e_v,e_issue,e_run,e_writer,e_link,e_quiet,e_end,e_begin,e_any;
 integer u;
 always @*begin
  for(u=0;u<4;u=u+1)begin
   e_ctrl[u]=c_act[u]&&!c_wait[u]&&!c_load[u]&&c_age[u]==r_ctrl[u]-1;
   e_k[u]=c_act[u]&&!c_wait[u]&&!c_load[u]&&c_age[u]==r_k[u]-1;
   e_v[u]=c_act[u]&&!c_wait[u]&&!c_load[u]&&c_age[u]==r_v[u]-1;
   e_issue[u]=c_act[u]&&!c_wait[u]&&!c_load[u]&&c_age[u]==r_issue[u]-1;
   e_run[u]=c_act[u]&&!c_wait[u]&&!c_load[u]&&c_age[u]==r_run[u]-1;
   e_writer[u]=c_act[u]&&!c_wait[u]&&!c_load[u]&&c_age[u]==r_writer[u]-((MUT==1)?32'd2:32'd1);
   e_link[u]=c_act[u]&&!c_wait[u]&&!c_load[u]&&c_age[u]==r_link[u]-1;
   e_quiet[u]=c_act[u]&&!c_wait[u]&&!c_load[u]&&c_age[u]==r_quiet[u]-1;
   e_end[u]=c_act[u]&&!c_wait[u]&&!c_load[u]&&c_age[u]==r_end[u]-1;
   // a waiting context begins its stage when its gap counter expires
   e_begin[u]=c_act[u]&&c_wait[u]&&c_cnt[u]==1;
  end
  // a stage end begins the next stage on the same edge when its gap is 0 (the original's stage boundary)
  for(u=0;u<4;u=u+1)if(e_end[u]&&c_stage[u]!=36&&gv_next[u]==0)e_begin[u]=1;
  // a start begins stage 1 at once when its gap is 0
  if(start_q&&start_ok&&!fault&&gv_start==0)e_begin[us]=1;
  e_any=e_ctrl|e_k|e_v|e_issue|e_run|e_writer|e_link|e_quiet|e_end|e_begin;
 end
 // TOKLIST: entries consumed this edge (a start; a stage end before stage 36), and a consumption before its entry arrived
 reg[3:0]tl_use;
 always @*begin
  tl_use=0;
  if(TOKLIST!=0)begin
   for(integer k=1;k<4;k=k+1)if(e_end[k]&&c_stage[k]!=36&&c_act[k]&&!(start_q&&start_ok&&us==k))tl_use[k]=1;
   if(start_q&&start_ok&&us!=0)tl_use[us]=1;
  end
 end
 wire tl_miss=|(tl_use&~ngv);
 wire collide=(e_any&(e_any-4'd1))!=0;                  // two or more contexts fire on this edge
 reg[1:0]fire_u;always @*begin fire_u=owner;for(integer k=3;k>=0;k=k-1)if(e_any[k])fire_u=2'(k);end
 // single table read port: the context that begins a stage (or the one after its end)
 reg[5:0]load_idx;reg[1:0]load_u;reg load_any;
 always @*begin load_any=0;load_u=0;load_idx=0;for(integer k=0;k<4;k=k+1)if(c_load[k])begin load_any=1;load_u=2'(k);load_idx=c_stage[k]-6'd1;end end
 always @(posedge ck or negedge rn)begin
  if(!rn)begin
   ctrl_go<=0;kgo<=0;vgo<=0;attention_issue<=0;attention_run<=0;writer_start<=0;link_start<=0;
   stage_start<=0;stage_done<=0;expected_upstream_quiet<=0;completed_stage<=0;
   epoch<=0;token<=0;position<=0;ctx_t<=0;generation<=0;
   configured<=0;active<=0;done<=0;fault<=0;fault_code<=0;age<=0;token_cycles<=0;
   next_cfg<=0;cfg_stage<=0;cfg_word<=0;cfg_gap<=0;bound_digest<=0;bound_epoch<=0;duration_sum<=0;
   c_act<=0;c_wait<=0;c_load<=0;c_quiet<=0;owner<=0;stage_o<=0;
   tl_hdr<=0;tl_nw<=0;tl_cnt<=0;ngv<=0;ngr<=0;f_v<=0;f_u<=0;f_l<=0;f_b<=0;
   for(integer k=1;k<4;k=k+1)begin tl_n[k]<=0;tl_wb[k]<=0;tl_we[k]<=0;tl_pw[k]<=0;tl_pl[k]<=0;end
   for(integer k=0;k<4;k=k+1)ng[k]<=0;
   for(integer k=0;k<4;k=k+1)begin c_cnt[k]<=0;c_age[k]<=0;c_tc[k]<=0;c_stage[k]<=0;c_epoch[k]<=0;c_token[k]<=0;c_pos[k]<=0;c_ctx[k]<=0;c_gen[k]<=0;end
  end else begin
   ctrl_go<=0;kgo<=0;vgo<=0;attention_issue<=0;attention_run<=0;writer_start<=0;link_start<=0;
   stage_start<=0;stage_done<=0;done<=0;
   if(fault)begin active<=0;c_act<=0;end
   else begin
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
     end else if(TOKLIST!=0&&addr_q==326)begin
      if(data_q[63:32]!=0||data_q[7:0]!=0||tl_nw_d>14'd512)begin fault<=1;fault_code[2]<=1;end
      tl_hdr<=1;tl_nw<=10'(tl_nw_d);tl_cnt<=0;next_cfg<=(tl_nw_d==0)?9'd470:9'd327;
      tl_wb[1]<=0;tl_wb[2]<=9'(12*data_q[15:8]);tl_wb[3]<=9'(12*(data_q[15:8]+data_q[23:16]));
      tl_we[1]<=10'(12*data_q[15:8]);tl_we[2]<=10'(12*(data_q[15:8]+data_q[23:16]));tl_we[3]<=10'(tl_nw_d);
      tl_n[1]<=data_q[15:8];tl_n[2]<=data_q[23:16];tl_n[3]<=data_q[31:24];
     end else if(TOKLIST!=0&&addr_q==327)begin
      if(data_q[63:60]!=0)begin fault<=1;fault_code[2]<=1;end
      tl_cnt<=tl_cnt+1'b1;if(tl_cnt+10'd1==tl_nw)next_cfg<=470;
     end else if(TOKLIST==0&&addr_q<470)begin
      if(data_q[63:32]!=0)begin fault<=1;fault_code[2]<=1;end
      next_cfg<=next_cfg+1'b1;cfg_gap<=cfg_gap+1'b1;
     end else if(addr_q==470)begin
      if(data_q!=64'h514b564c59523336||cfg_stage!=36||duration_sum==0||
         (TOKLIST==0&&cfg_gap!=144)||(TOKLIST!=0&&(!tl_hdr||tl_cnt!=tl_nw)))begin fault<=1;fault_code[2]<=1;end
      else begin
       configured<=1;
       // TOKLIST: every filler with a list fetches its first entry (token 0, stage 1)
       for(integer k=1;k<4;k=k+1)begin tl_pw[k]<=tl_wb[k];tl_pl[k]<=0;ngr[k]<=(TOKLIST!=0)&&tl_n[k]!=0;ngv[k]<=0;end
      end
     end else begin fault<=1;fault_code[0]<=1;end
    end
    if(collide)begin fault<=1;fault_code[4]<=1;end
    // ---- TOKLIST prefetch: consume -> request; one read in flight; the entry lands 2 edges after the request ----
    if(TOKLIST!=0)begin
     if(tl_miss)begin fault<=1;fault_code[5]<=1;end
     if(f_v)begin ng[f_u]<=m_ent;ngv[f_u]<=1;f_v<=0;end
     if(rd_go)begin
      f_v<=1;f_u<=rd_u;f_l<=tl_pl[rd_u];f_b<=tl_pw[rd_u][8];ngr[rd_u]<=0;
      if(tl_pl[rd_u]==2)begin
       tl_pl[rd_u]<=0;
       tl_pw[rd_u]<=(TLMUT!=1&&{1'b0,tl_pw[rd_u]}+10'd1==tl_we[rd_u])?tl_wb[rd_u]:tl_pw[rd_u]+1'b1;
      end else tl_pl[rd_u]<=tl_pl[rd_u]+1'b1;
     end
     for(integer k=1;k<4;k=k+1)if(tl_use[k])begin ngv[k]<=0;ngr[k]<=1;end
    end
    // start: user = authority epoch[1:0]
    if(start_q)begin
     if(!start_ok)begin fault<=1;fault_code[3]<=1;end
     else begin
      c_act[us]<=1;c_epoch[us]<=epoch_q;c_token[us]<=token_q;c_pos[us]<=pos_q;c_ctx[us]<=14'(pos_q+1);c_gen[us]<=gen_q;
      c_stage[us]<=1;c_tc[us]<=0;c_age[us]<=0;c_quiet[us]<=0;
      if(gv_start==0)begin c_wait[us]<=0;c_load[us]<=1;end
      else begin c_wait[us]<=1;c_load[us]<=0;c_cnt[us]<=gv_start;end
     end
    end
    for(integer k=0;k<4;k=k+1)if(c_act[k]&&!(start_q&&start_ok&&us==k))begin
     c_tc[k]<=c_tc[k]+1'b1;
     if(c_load[k])c_load[k]<=0;
     if(c_wait[k])begin
      c_cnt[k]<=c_cnt[k]-1'b1;
      if(c_cnt[k]==1)begin c_wait[k]<=0;c_load[k]<=1;c_age[k]<=0;end
     end else begin
      c_age[k]<=c_age[k]+1'b1;
      if(e_quiet[k])c_quiet[k]<=1;
      if(e_end[k])begin
       if(c_stage[k]==36)begin c_act[k]<=0;end
       else begin
        c_stage[k]<=c_stage[k]+1'b1;c_age[k]<=0;c_quiet[k]<=0;
        if(gv_next[k]==0)c_load[k]<=1;
        else begin c_wait[k]<=1;c_cnt[k]<=gv_next[k];end
       end
      end
     end
    end
    // row fetch (one context per edge)
    if(load_any)begin
     r_ctrl[load_u]<=t_ctrl[load_idx];r_k[load_u]<=t_k[load_idx];r_v[load_u]<=t_v[load_idx];r_issue[load_u]<=t_issue[load_idx];
     r_run[load_u]<=t_run[load_idx];r_writer[load_u]<=t_writer[load_idx];r_link[load_u]<=t_link[load_idx];
     r_quiet[load_u]<=t_quiet[load_idx];r_end[load_u]<=t_end[load_idx];
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
     if(e_end[fire_u])begin completed_stage<=c_stage[fire_u];if(c_stage[fire_u]==36)done<=1;end
     stage_o<=(e_end[fire_u]&&c_stage[fire_u]!=36)?c_stage[fire_u]+1'b1:((start_q&&start_ok&&fire_u==us)?6'd1:c_stage[fire_u]);
     expected_upstream_quiet<=e_quiet[fire_u]||(c_quiet[fire_u]&&!e_begin[fire_u]);
     age<=e_begin[fire_u]?32'd0:c_age[fire_u]+1'b1;
     token_cycles<=(start_q&&start_ok&&fire_u==us)?32'd0:c_tc[fire_u]+1'b1;
    end else begin
     if(e_quiet[owner])expected_upstream_quiet<=1;
     if(c_act[owner]&&!c_wait[owner])age<=c_age[owner]+1'b1;
     if(c_act[owner])token_cycles<=c_tc[owner]+1'b1;
    end
    active<=|(c_act&~(e_end&{c_stage[3]==36,c_stage[2]==36,c_stage[1]==36,c_stage[0]==36}))||(start_q&&start_ok);
   end
  end
 end
end endgenerate
endmodule

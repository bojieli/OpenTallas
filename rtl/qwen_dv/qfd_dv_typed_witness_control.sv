`timescale 1ns/1ps
// Isolated SOURCE vehicle, not instantiated by production wrappers.
// Template is one1742-bit block. Future growth beyond2kb requires native SRAM.
// Install contract: PW0 restarts loading; PW400..438 must arrive once, in order;
// all-copy authentication asserted while loading is an EARLY-AUTH fault; seal only
// after the final record with matching digest/epoch/fusedcap. Any later loss of
// profile/auth invalidates the template (idle) or faults (active context).
// The 13-bit context cycle faults at 8191 only while witnesses are outstanding;
// a completed context holds its cycle until retirement (long stage periods).
module qfd_dv_typed_witness_control #(
 parameter integer ENABLE=0,SAFE_COMPARE=0,SAFE_SELECT=0,SAFE_PHYS=0,GROUPS=13,TEMPLATE_BITS=134,
 parameter[63:0] PROFILE_DIGEST=64'h198f7708b478a667,
 parameter[15:0] PROFILE_EPOCH=16'd7
)(
 input wire ck,rst_n,pw_v,input wire[9:0]pw_addr,input wire[63:0]pw_data,
 input wire all_copies_authenticated,fusedcap,input wire[63:0]installed_digest,input wire[15:0]installed_epoch,
 input wire start_v,input wire[1:0]start_user,input wire[5:0]start_stage,input wire[15:0]start_epoch,
 input wire retire_v,input wire[1:0]retire_user,input wire ME_XPF_retired,
 input wire[15:0]observation,input wire[5:0]event_stage,input wire[15:0]event_epoch,
 output wire template_ready,output wire[3:0]context_active,all_witnesses_complete,
 output reg group_complete,output reg[1:0]complete_user,output reg[3:0]complete_group,
 output reg fault
);
 initial if(SAFE_SELECT&&!SAFE_COMPARE) $error("SAFE_SELECT requires SAFE_COMPARE");
 initial if(SAFE_PHYS&&!SAFE_SELECT) $error("SAFE_PHYS requires SAFE_SELECT");
 initial if(GROUPS!=13||TEMPLATE_BITS!=134||GROUPS*TEMPLATE_BITS>2048)
  $error("exact WTN1 source profile and <=2048-bit template required; growth needs real SRAM");
 reg[133:0]templates[0:12]; // unreset data, guarded by loaded/atomicseal
 reg[127:0]partial;reg[12:0]loaded;reg[5:0]next_pw;reg[3:0]record_index;reg[1:0]part;
 reg loading,loaded_complete,sealed;
 wire profile_ok=all_copies_authenticated&&fusedcap&&installed_digest==PROFILE_DIGEST&&installed_epoch==PROFILE_EPOCH;
 localparam integer NC=SAFE_COMPARE?6:1;
 reg[3:0]active;(* keep=1 *) reg[12:0]cycle[0:3][0:NC-1];reg[5:0]stage[0:3];reg[15:0]epoch[0:3];reg[3:0]next_group[0:3];
 reg[133:0]cache[0:7];
 reg[24:0]cache_meta[0:7];reg[12:0]cache_due[0:7][0:11];
 wire[11:0]cache_mask[0:7];wire[6:0]cache_pc[0:7];wire[3:0]cache_group[0:7];reg[11:0]seen[0:7];reg[7:0]cache_valid;
 reg pending;reg[1:0]pending_user;reg pending_slot;reg[3:0]pending_group;reg[5:0]pending_stage;reg[15:0]pending_epoch;reg[1:0]rr;
 reg pick;reg[1:0]pick_user;reg pick_slot;integer k,u,s,b,sl,c;reg[1:0]scan;
 reg matched;reg[11:0]new_seen;reg[12:0]due;reg[133:0]record_word;
 wire[1:0]obs_user=observation[14:13];wire[3:0]obs_slice=observation[12:9];wire[8:0]obs_pc=observation[8:0];
 // Physical source candidate: useful per-sector selects, no added edge.
 (* keep=1 *) wire[12:0] template_select[0:14];
 (* keep=1 *) wire publish_enable[0:7][0:13];
 wire[12:0] selected_base[0:11];wire[7:0] selected_delta[0:11];
 wire[24:0] selected_meta;wire[12:0] selected_first_due;
 genvar ss,tt,bb,ee;
 generate if(SAFE_SELECT)begin:gs
  for(ss=0;ss<15;ss=ss+1)begin:sel
   wire[12:0] decoded;
   for(tt=0;tt<13;tt=tt+1)begin:decode
    assign decoded[tt]=ENABLE&&pick&&next_group[pick_user]==tt;
   end
   (* keep=1, keep_hierarchy=1 *) qfd_wtn_kept_select #(.W(13),.ID(ss),.RST(SAFE_PHYS==0)) ff(.ck(ck),.rst_n(rst_n),.d(decoded),.q(template_select[ss]));
  end
  for(ss=0;ss<12;ss=ss+1)begin:due_sel
   reg[20:0] selected;integer ti;
   always@*begin
    selected=0;
    for(ti=0;ti<13;ti=ti+1)selected=selected|({21{template_select[ss][ti]}}&{templates[ti][34+8*ss+:8],templates[ti][12:0]});
   end
   assign selected_base[ss]=selected[12:0];assign selected_delta[ss]=selected[20:13];
  end
  for(ss=0;ss<3;ss=ss+1)begin:other_sel
   reg[12:0] selected;integer ti;
   always@*begin
    selected=0;
    for(ti=0;ti<13;ti=ti+1)begin
     if(ss==0)selected=selected|({13{template_select[12][ti]}}&templates[ti][25:13]);
     else if(ss==1)selected=selected|({13{template_select[13][ti]}}&{1'b0,templates[ti][133:130],templates[ti][33:26]});
     else selected=selected|({13{template_select[14][ti]}}&templates[ti][12:0]);
    end
   end
   if(ss==0)assign selected_meta[12:0]=selected;
   else if(ss==1)assign selected_meta[24:13]=selected[11:0];
   else assign selected_first_due=selected;
  end
  for(bb=0;bb<8;bb=bb+1)begin:bank
   for(ee=0;ee<14;ee=ee+1)begin:sector
    (* keep=1, keep_hierarchy=1 *) qfd_wtn_kept_select #(.W(1),.ID(15+bb*14+ee),.RST(SAFE_PHYS==0)) ff(.ck(ck),.rst_n(rst_n),.d(ENABLE&&pick&&pick_user==bb/2&&pick_slot==bb%2),.q(publish_enable[bb][ee]));
    if(ee<12)begin:due_write
     always@(posedge ck)if(ENABLE&&publish_enable[bb][ee])cache_due[bb][ee]<=selected_base[ee]+{5'd0,selected_delta[ee]};
    end else if(ee==12)begin:meta_lo
     always@(posedge ck)if(ENABLE&&publish_enable[bb][ee])cache_meta[bb][12:0]<=selected_meta[12:0];
    end else begin:meta_hi
     always@(posedge ck)if(ENABLE&&publish_enable[bb][ee])cache_meta[bb][24:13]<=selected_meta[24:13];
    end
   end
  end
 end endgenerate
 genvar m;generate for(m=0;m<8;m=m+1)begin:gm
  assign cache_mask[m]=SAFE_COMPARE?cache_meta[m][20:9]:cache[m][33:22];
  assign cache_pc[m]=SAFE_COMPARE?cache_meta[m][6:0]:cache[m][19:13];
  assign cache_group[m]=SAFE_COMPARE?cache_meta[m][24:21]:cache[m][133:130];
 end endgenerate
 wire[3:0] awc;wire tr_c;reg s_fault; // s_fault: SAFE_PHYS internal fault state (output register follows)
 genvar g;generate for(g=0;g<4;g=g+1)begin:gc
  assign awc[g]=ENABLE!=0&&active[g]&&next_group[g]==13&&!cache_valid[2*g]&&!cache_valid[2*g+1]&&!(pending&&pending_user==g);
 end endgenerate
 assign tr_c=ENABLE!=0&&sealed&&!(SAFE_PHYS?s_fault:fault);
 reg tr_q;reg[3:0] ca_q,awc_q; // SAFE_PHYS registered output face
 assign all_witnesses_complete=SAFE_PHYS?awc_q:awc;
 assign template_ready=SAFE_PHYS?tr_q:tr_c;
 assign context_active=SAFE_PHYS?ca_q:(ENABLE!=0?active:4'd0);
 wire[1:0] rr_k[0:3]; // SAFE_PHYS: kept rr copy per arbitration step (else rr)
 always@*begin
  pick=0;pick_user=0;pick_slot=0;
  for(k=0;k<4;k=k+1)begin
   scan=(SAFE_PHYS?rr_k[k]:rr)+2'(k);
   if(!pick&&active[scan]&&next_group[scan]<13)begin
    if(!cache_valid[2*scan]&&!(pending&&pending_user==scan&&pending_slot==0))begin pick=1;pick_user=scan;pick_slot=0;end
    else if(!cache_valid[2*scan+1]&&!(pending&&pending_user==scan&&pending_slot==1))begin pick=1;pick_user=scan;pick_slot=1;end
   end
  end
 end
 generate if(SAFE_PHYS==0)begin:gl
 always@(posedge ck or negedge rst_n)begin
  if(!rst_n)begin
   loaded<=0;next_pw<=0;record_index<=0;part<=0;loading<=0;loaded_complete<=0;sealed<=0;fault<=0;
   active<=0;cache_valid<=0;pending<=0;pending_user<=0;pending_slot<=0;pending_group<=0;pending_stage<=0;pending_epoch<=0;rr<=0;
   group_complete<=0;complete_user<=0;complete_group<=0;
   for(u=0;u<4;u=u+1)begin for(c=0;c<NC;c=c+1)cycle[u][c]<=0;stage[u]<=0;epoch[u]<=0;next_group[u]<=0;end
   for(b=0;b<8;b=b+1)seen[b]<=0;
  end else if(ENABLE!=0)begin
   group_complete<=0;
   if(active!=0&&!profile_ok)fault<=1;
   if(loading&&all_copies_authenticated)fault<=1; // early authentication
   if(active==0&&!pending&&sealed&&!all_copies_authenticated)begin
    // authentication/profile withdrawn while idle: template must be reinstalled
    sealed<=0;loaded_complete<=0;loaded<=0;
   end
   if(pw_v)begin
    if(active!=0||pending)fault<=1;
    else if(pw_addr==0)begin loaded<=0;next_pw<=0;record_index<=0;part<=0;loading<=1;loaded_complete<=0;sealed<=0;end
    else if(pw_addr>=400&&pw_addr<=438)begin
     if(!loading||pw_addr!=400+next_pw||loaded_complete)fault<=1;
     else begin
      next_pw<=next_pw+1'b1;
      if(part==0)begin partial[63:0]<=pw_data;part<=1;end
      else if(part==1)begin partial[127:64]<=pw_data;part<=2;end
      else begin
       record_word={pw_data[5:0],partial};
       if((record_index==0&&pw_data[63:6]!=(64'h57544e3101640340>>6))||
          (record_index!=0&&pw_data[63:6]!=0)||record_word[133:130]!=record_index||
          record_word[33:22]==0||record_word[21:20]!=0||loaded[record_index])fault<=1;
       else begin templates[record_index]<=record_word;loaded[record_index]<=1;end
       if(record_index==12)begin
        if(loaded!=13'h0fff||pw_addr!=438)fault<=1;
        else begin loaded_complete<=1;loading<=0;end
       end
       record_index<=record_index+1'b1;part<=0;
      end
     end
    end
   end
   if(loaded_complete&&!sealed&&all_copies_authenticated&&!fault)begin
    if(!profile_ok)fault<=1;else sealed<=1;
   end
   if(sealed&&all_copies_authenticated&&!profile_ok)fault<=1; // authenticated other profile
   if(start_v)begin
    if(!sealed||fault||!profile_ok||active[start_user]||start_stage<1||start_stage>36)fault<=1;
    else begin active[start_user]<=1;for(c=0;c<NC;c=c+1)cycle[start_user][c]<=0;stage[start_user]<=start_stage;epoch[start_user]<=start_epoch;next_group[start_user]<=0;end
   end
   for(u=0;u<4;u=u+1)if(active[u])begin
    if(cycle[u][0]!=8191)begin for(c=0;c<NC;c=c+1)cycle[u][c]<=cycle[u][c]+1'b1;end
    else if(!all_witnesses_complete[u])fault<=1;
   end
   // One FF template lookup port; request -> cache publication+1 -> use+2.
   pending<=pick;
   if(pick)begin
    pending_user<=pick_user;pending_slot<=pick_slot;pending_group<=next_group[pick_user];pending_stage<=stage[pick_user];pending_epoch<=epoch[pick_user];
    next_group[pick_user]<=next_group[pick_user]+1'b1;rr<=pick_user+1'b1;
   end
   if(pending)begin
    b=2*pending_user+pending_slot;
    if(!active[pending_user]||stage[pending_user]!=pending_stage||epoch[pending_user]!=pending_epoch||cache_valid[b]||cycle[pending_user][0]>=(SAFE_SELECT?selected_first_due:templates[pending_group][12:0]))fault<=1;
    if(SAFE_COMPARE&&!SAFE_SELECT)begin
     cache_meta[b]<={templates[pending_group][133:130],templates[pending_group][33:13]};
     for(c=0;c<12;c=c+1)cache_due[b][c]<=templates[pending_group][12:0]+{5'd0,templates[pending_group][34+8*c+:8]};
    end else if(!SAFE_COMPARE)cache[b]<=templates[pending_group];
    seen[b]<=0;cache_valid[b]<=1;
   end
   matched=0;
   for(b=0;b<8;b=b+1)if(cache_valid[b]&&active[b/2])begin
    new_seen=seen[b];
    for(sl=0;sl<12;sl=sl+1)if(cache_mask[b][sl])begin
     due=SAFE_COMPARE?cache_due[b][sl]:(cache[b][12:0]+{5'd0,cache[b][34+8*sl+:8]});
     if(cycle[b/2][SAFE_COMPARE?((b%2)*3+sl/4):0]==due)begin
      if(!observation[15]||obs_user!=2'(b/2)||obs_slice!=4'(sl)||obs_pc!={2'(b/2),cache_pc[b]}||event_stage!=stage[b/2]||event_epoch!=epoch[b/2]||seen[b][sl])fault<=1;
      else begin new_seen[sl]=1;matched=1;end
     end
     if(cycle[b/2][SAFE_COMPARE?((b%2)*3+sl/4):0]>due&&!seen[b][sl])fault<=1;
    end
    seen[b]<=new_seen;
    if(new_seen==cache_mask[b])begin
     cache_valid[b]<=0;group_complete<=1;complete_user<=2'(b/2);complete_group<=cache_group[b];
    end
   end
   if(observation[15]&&!matched)fault<=1;
   if(retire_v)begin
    if(!active[retire_user]||!all_witnesses_complete[retire_user]||!ME_XPF_retired)fault<=1;
    else active[retire_user]<=0;
   end
  end
 end
 end else begin:gp
  // ---------------- SAFE_PHYS structural candidate (default off) ----------------
  // Same decision logic as the legacy block, re-timed by exactly +2 edges at the
  // faces: every input is pin-registered (+1) and every output is registered (+1).
  // Reset lands in two registered stages, then three kept leaf copies (<=32 sync
  // loads each); data state is unreset and qualified by reset control state.
  // Template/partial storage writes one edge after the decision through kept
  // registered write-enable sectors (<=32 loads each); no added SU/token cycle.
  reg rs1,rs2;
  always@(posedge ck or negedge rst_n)if(!rst_n)begin rs1<=0;rs2<=0;end else begin rs1<=1'b1;rs2<=rs1;end
  (* keep=1 *) wire rl_ins,rl_run,rl_out;
  (* keep=1, keep_hierarchy=1 *) qfd_wtn_kept_select #(.W(1),.ID(300),.RST(0)) rli(.ck(ck),.rst_n(1'b1),.d(rs2),.q(rl_ins));
  (* keep=1, keep_hierarchy=1 *) qfd_wtn_kept_select #(.W(1),.ID(301),.RST(0)) rlr(.ck(ck),.rst_n(1'b1),.d(rs2),.q(rl_run));
  (* keep=1, keep_hierarchy=1 *) qfd_wtn_kept_select #(.W(1),.ID(302),.RST(0)) rlo(.ck(ck),.rst_n(1'b1),.d(rs2),.q(rl_out));
  // Pin registers (data face, unreset; parent holds valids low through reset).
  reg f_pw_v;reg[9:0]f_pw_addr;reg[63:0]f_pw_data;reg f_auth,f_fcap;reg[63:0]f_dig;reg[15:0]f_iep;
  reg f_start_v;reg[1:0]f_start_user;reg[5:0]f_start_stage;reg[15:0]f_start_epoch;
  reg f_retire_v;reg[1:0]f_retire_user;reg f_mexpf;reg[15:0]f_obs;reg[5:0]f_ev_stage;reg[15:0]f_ev_epoch;
  always@(posedge ck)begin
   f_pw_v<=pw_v;f_pw_addr<=pw_addr;f_pw_data<=pw_data;f_auth<=all_copies_authenticated;f_fcap<=fusedcap;f_dig<=installed_digest;f_iep<=installed_epoch;
   f_start_v<=start_v;f_start_user<=start_user;f_start_stage<=start_stage;f_start_epoch<=start_epoch;
   f_retire_v<=retire_v;f_retire_user<=retire_user;f_mexpf<=ME_XPF_retired;f_obs<=observation;f_ev_stage<=event_stage;f_ev_epoch<=event_epoch;
  end
  // Kept per-(user,copy) start decodes at the pin face: one counter copy each.
  (* keep=1 *) wire start_hit[0:3][0:NC-1];
  genvar pu,pc;
  for(pu=0;pu<4;pu=pu+1)begin:sh
   for(pc=0;pc<NC;pc=pc+1)begin:cp
    (* keep=1, keep_hierarchy=1 *) qfd_wtn_kept_select #(.W(1),.ID(310+pu*8+pc),.RST(0)) ff(.ck(ck),.rst_n(1'b1),.d(start_v&&start_user==pu),.q(start_hit[pu][pc]));
   end
  end
  wire p_prof=f_auth&&f_fcap&&f_dig==PROFILE_DIGEST&&f_iep==PROFILE_EPOCH;
  wire[1:0]p_ou=f_obs[14:13];wire[3:0]p_os=f_obs[12:9];wire[8:0]p_opc=f_obs[8:0];
  // Per-bank witness compare (old state only).
  wire[7:0] bk_act,bk_match,bk_fault,bk_done;wire[11:0] bk_seen[0:7];
  genvar pb;
  for(pb=0;pb<8;pb=pb+1)begin:bk
   reg[11:0] ns;reg m,f;integer l;reg[12:0] cy;
   always@*begin
    ns=seen[pb];m=0;f=0;cy=0; // cy: temporary (no latch)
    for(l=0;l<12;l=l+1)if(cache_mask[pb][l])begin
     cy=cycle[pb/2][(pb%2)*3+l/4];
     if(cy==cache_due[pb][l])begin
      if(!f_obs[15]||p_ou!=2'(pb/2)||p_os!=4'(l)||p_opc!={2'(pb/2),cache_pc[pb]}||f_ev_stage!=stage[pb/2]||f_ev_epoch!=epoch[pb/2]||seen[pb][l])f=1;
      else begin ns[l]=1;m=1;end
     end
     if(cy>cache_due[pb][l]&&!seen[pb][l])f=1;
    end
   end
   assign bk_act[pb]=cache_valid[pb]&&active[pb/2];
   assign bk_match[pb]=bk_act[pb]&&m;assign bk_fault[pb]=bk_act[pb]&&f;
   assign bk_done[pb]=bk_act[pb]&&ns==cache_mask[pb];assign bk_seen[pb]=ns;
  end
  // Control next state, statement order = legacy NBA order (last write wins).
  reg n_fault,n_loading,n_lc,n_sealed,n_pending,n_gc;reg[12:0]n_loaded;reg[5:0]n_next_pw;reg[3:0]n_ri;reg[1:0]n_part;
  reg[3:0]n_active;reg[7:0]n_cv;reg[1:0]n_rr,n_cu;reg[3:0]n_cg;reg start_ok;reg w_lo,w_hi,w_rec;
  reg s_loading,s_lc,s_gc;reg[1:0]s_cu;reg[3:0]s_cg;
  reg[133:0] rw;integer pbi,pui;reg[2:0] pbn;
  always@*begin
   n_fault=s_fault;n_loading=s_loading;n_lc=s_lc;n_sealed=sealed;n_loaded=loaded;n_next_pw=next_pw;n_ri=record_index;n_part=part;
   n_active=active;n_cv=cache_valid;n_rr=rr;n_gc=0;n_cu=s_cu;n_cg=s_cg;start_ok=0;w_lo=0;w_hi=0;w_rec=0;
   rw={f_pw_data[5:0],partial};pbn=3'(2*pending_user+pending_slot);
   if(active!=0&&!p_prof)n_fault=1;
   if(s_loading&&f_auth)n_fault=1;
   if(active==0&&!pending&&sealed&&!f_auth)begin n_sealed=0;n_lc=0;n_loaded=0;end
   if(f_pw_v)begin
    if(active!=0||pending)n_fault=1;
    else if(f_pw_addr==0)begin n_loaded=0;n_next_pw=0;n_ri=0;n_part=0;n_loading=1;n_lc=0;n_sealed=0;end
    else if(f_pw_addr>=400&&f_pw_addr<=438)begin
     if(!s_loading||f_pw_addr!=10'(400+next_pw)||s_lc)n_fault=1;
     else begin
      n_next_pw=next_pw+1'b1;
      if(part==0)begin w_lo=1;n_part=1;end
      else if(part==1)begin w_hi=1;n_part=2;end
      else begin
       if((record_index==0&&f_pw_data[63:6]!=(64'h57544e3101640340>>6))||
          (record_index!=0&&f_pw_data[63:6]!=0)||rw[133:130]!=record_index||
          rw[33:22]==0||rw[21:20]!=0||loaded[record_index])n_fault=1;
       else begin w_rec=1;n_loaded[record_index]=1;end
       if(record_index==12)begin
        if(loaded!=13'h0fff||f_pw_addr!=438)n_fault=1;
        else begin n_lc=1;n_loading=0;end
       end
       n_ri=record_index+1'b1;n_part=0;
      end
     end
    end
   end
   if(s_lc&&!sealed&&f_auth&&!s_fault)begin
    if(!p_prof)n_fault=1;else n_sealed=1;
   end
   if(sealed&&f_auth&&!p_prof)n_fault=1;
   if(f_start_v)begin
    if(!sealed||s_fault||!p_prof||active[f_start_user]||f_start_stage<1||f_start_stage>36)n_fault=1;
    else begin start_ok=1;n_active[f_start_user]=1;end
   end
   for(pui=0;pui<4;pui=pui+1)if(active[pui]&&cycle[pui][0]==8191&&!awc[pui])n_fault=1;
   n_pending=pick;
   if(pick)n_rr=pick_user+1'b1;
   if(pending)begin
    if(!active[pending_user]||stage[pending_user]!=pending_stage||epoch[pending_user]!=pending_epoch||cache_valid[pbn]||cycle[pending_user][0]>=selected_first_due)n_fault=1;
    n_cv[pbn]=1;
   end
   for(pbi=0;pbi<8;pbi=pbi+1)begin
    if(bk_fault[pbi])n_fault=1;
    if(bk_done[pbi])begin n_cv[pbi]=0;n_gc=1;n_cu=2'(pbi/2);n_cg=cache_group[pbi];end
   end
   if(f_obs[15]&&bk_match==0)n_fault=1;
   if(f_retire_v)begin
    if(!active[f_retire_user]||!awc[f_retire_user]||!f_mexpf)n_fault=1;
    else n_active[f_retire_user]=0;
   end
  end
  // Kept rr copies (one per arbitration step, sync reset with the run group)
  // and a kept active copy that only enables the counter copies.
  (* keep=1 *) wire[3:0] act_cnt;
  genvar pk;
  for(pk=0;pk<4;pk=pk+1)begin:rk
   (* keep=1, keep_hierarchy=1 *) qfd_wtn_kept_select #(.W(2),.ID(400+pk),.RST(0)) ff(.ck(ck),.rst_n(1'b1),.d(!rl_run?2'd0:(ENABLE!=0?n_rr:rr)),.q(rr_k[pk]));
   (* keep=1, keep_hierarchy=1 *) qfd_wtn_kept_select #(.W(1),.ID(404+pk),.RST(0)) ac(.ck(ck),.rst_n(1'b1),.d(!rl_run?1'b0:(ENABLE!=0?n_active[pk]:active[pk])),.q(act_cnt[pk]));
  end
  // Install control (leaf reset rl_ins: 28 loads).
  always@(posedge ck)if(!rl_ins)begin loaded<=0;next_pw<=0;record_index<=0;part<=0;s_loading<=0;s_lc<=0;sealed<=0;end
   else if(ENABLE!=0)begin loaded<=n_loaded;next_pw<=n_next_pw;record_index<=n_ri;part<=n_part;s_loading<=n_loading;s_lc<=n_lc;sealed<=n_sealed;end
  // Run control (leaf reset rl_run: 25 loads).
  always@(posedge ck)if(!rl_run)begin s_fault<=0;active<=0;cache_valid<=0;pending<=0;rr<=0;s_gc<=0;s_cu<=0;s_cg<=0;end
   else if(ENABLE!=0)begin s_fault<=n_fault;active<=n_active;cache_valid<=n_cv;pending<=n_pending;rr<=n_rr;s_gc<=n_gc;s_cu<=n_cu;s_cg<=n_cg;end
  // Output face registers (leaf reset rl_out: 17 loads).
  always@(posedge ck)if(!rl_out)begin fault<=0;group_complete<=0;complete_user<=0;complete_group<=0;tr_q<=0;ca_q<=0;awc_q<=0;end
   else begin fault<=s_fault;group_complete<=s_gc;complete_user<=s_cu;complete_group<=s_cg;tr_q<=tr_c;ca_q<=ENABLE!=0?active:4'd0;awc_q<=awc;end
  // Unreset data qualified by the control state above.
  always@(posedge ck)if(ENABLE!=0)begin
   pending_user<=pick_user;pending_slot<=pick_slot;pending_group<=next_group[pick_user];pending_stage<=stage[pick_user];pending_epoch<=epoch[pick_user];
   if(start_ok)begin stage[f_start_user]<=f_start_stage;epoch[f_start_user]<=f_start_epoch;end
  end
  for(pu=0;pu<4;pu=pu+1)begin:ud
   always@(posedge ck)if(ENABLE!=0)begin
    if(start_ok&&f_start_user==pu)next_group[pu]<=0;else if(pick&&pick_user==pu)next_group[pu]<=next_group[pu]+1'b1;
   end
   for(pc=0;pc<NC;pc=pc+1)begin:cc
    always@(posedge ck)if(ENABLE!=0)begin
     if(start_ok&&start_hit[pu][pc])cycle[pu][pc]<=0;
     else if(act_cnt[pu]&&cycle[pu][pc]!=8191)cycle[pu][pc]<=cycle[pu][pc]+1'b1;
    end
   end
  end
  for(pb=0;pb<8;pb=pb+1)begin:sw
   always@(posedge ck)if(ENABLE!=0)begin
    if(bk_act[pb])seen[pb]<=bk_seen[pb];else if(pending&&pbn==pb)seen[pb]<=0;
   end
  end
  // Template store: decision -> kept registered write-enable sectors -> write (+1).
  reg[63:0] dq2;
  always@(posedge ck)dq2<=f_pw_data;
  // Each kept enable sector drives <=16 storage bits (two mapped mux pins/bit).
  (* keep=1 *) wire[3:0] e_lo,e_hi;
  genvar ps,pr;
  for(ps=0;ps<4;ps=ps+1)begin:pe
   (* keep=1, keep_hierarchy=1 *) qfd_wtn_kept_select #(.W(1),.ID(350+ps),.RST(0)) lo(.ck(ck),.rst_n(1'b1),.d(ENABLE!=0&&rl_ins&&w_lo),.q(e_lo[ps]));
   (* keep=1, keep_hierarchy=1 *) qfd_wtn_kept_select #(.W(1),.ID(354+ps),.RST(0)) hi(.ck(ck),.rst_n(1'b1),.d(ENABLE!=0&&rl_ins&&w_hi),.q(e_hi[ps]));
   always@(posedge ck)begin
    if(e_lo[ps])partial[16*ps+:16]<=dq2[16*ps+:16];
    if(e_hi[ps])partial[64+16*ps+:16]<=dq2[16*ps+:16];
   end
  end
  wire[133:0] tword={dq2[5:0],partial};
  for(pr=0;pr<13;pr=pr+1)begin:tr
   for(ps=0;ps<9;ps=ps+1)begin:sc
    localparam integer LO=15*ps,W=(ps==8)?14:15;
    (* keep=1 *) wire e;
    (* keep=1, keep_hierarchy=1 *) qfd_wtn_kept_select #(.W(1),.ID(500+pr*9+ps),.RST(0)) ff(.ck(ck),.rst_n(1'b1),.d(ENABLE!=0&&rl_ins&&w_rec&&record_index==pr),.q(e));
    always@(posedge ck)if(e)templates[pr][LO+:W]<=tword[LO+:W];
   end
  end
 end endgenerate
endmodule

// Unique parameter identities preserve same-age useful copies through synthesis.
// This is actual resettable storage, never a black box or functional stub.
// RST=0 (SAFE_PHYS): plain kept register; its D is idle (0) whenever the
// controller is held in landed reset, so it clears within one edge of reset.
(* keep_hierarchy=1 *) module qfd_wtn_kept_select #(parameter integer W=1,ID=0,RST=1)(
 input wire ck,rst_n,input wire[W-1:0]d,output reg[W-1:0]q);
 generate if(RST)begin:ar
  always@(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=d;
 end else begin:nr
  always@(posedge ck)q<=d;
 end endgenerate
endmodule

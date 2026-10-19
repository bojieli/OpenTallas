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
 parameter integer ENABLE=0,SAFE_COMPARE=0,GROUPS=13,TEMPLATE_BITS=134,
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
 genvar m;generate for(m=0;m<8;m=m+1)begin:gm
  assign cache_mask[m]=SAFE_COMPARE?cache_meta[m][20:9]:cache[m][33:22];
  assign cache_pc[m]=SAFE_COMPARE?cache_meta[m][6:0]:cache[m][19:13];
  assign cache_group[m]=SAFE_COMPARE?cache_meta[m][24:21]:cache[m][133:130];
 end endgenerate
 genvar g;generate for(g=0;g<4;g=g+1)begin:gc
  assign all_witnesses_complete[g]=ENABLE!=0&&active[g]&&next_group[g]==13&&!cache_valid[2*g]&&!cache_valid[2*g+1]&&!(pending&&pending_user==g);
 end endgenerate
 assign template_ready=ENABLE!=0&&sealed&&!fault;
 assign context_active=ENABLE!=0?active:4'd0;
 always@*begin
  pick=0;pick_user=0;pick_slot=0;
  for(k=0;k<4;k=k+1)begin
   scan=rr+2'(k);
   if(!pick&&active[scan]&&next_group[scan]<13)begin
    if(!cache_valid[2*scan]&&!(pending&&pending_user==scan&&pending_slot==0))begin pick=1;pick_user=scan;pick_slot=0;end
    else if(!cache_valid[2*scan+1]&&!(pending&&pending_user==scan&&pending_slot==1))begin pick=1;pick_user=scan;pick_slot=1;end
   end
  end
 end
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
    if(!active[pending_user]||stage[pending_user]!=pending_stage||epoch[pending_user]!=pending_epoch||cache_valid[b]||cycle[pending_user][0]>=templates[pending_group][12:0])fault<=1;
    if(SAFE_COMPARE)begin
     cache_meta[b]<={templates[pending_group][133:130],templates[pending_group][33:13]};
     for(c=0;c<12;c=c+1)cache_due[b][c]<=templates[pending_group][12:0]+{5'd0,templates[pending_group][34+8*c+:8]};
    end else cache[b]<=templates[pending_group];
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
endmodule

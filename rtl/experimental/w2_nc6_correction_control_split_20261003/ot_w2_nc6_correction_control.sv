`timescale 1ps/1ps
// Pure combinational scheduler. ALL state is the existing eight coded contexts.
// Parent OPT_EXACT=0 gates enable. No codec, FF, clock, reset or memory added.
module ot_w2_nc6_correction_control(
 input wire enable,
 input wire [767:0] context_current,
 input wire [7:0] context_clean,
 input wire [15767:0] current_raw,current_fixed,
 input wire [9635:0] current_payload,
 input wire [218:0] current_clean,current_ce,current_bad,
 output reg [767:0] context_next,
 output reg [7:0] context_we,
 output reg [7:0] scrub_v,
 output reg [79:0] scrub_index,
 output reg [575:0] scrub_original,scrub_candidate,
 input wire [7:0] retire_ready,
 output reg busy,error
);
 reg [767:0] base_next;
 reg [7:0] base_we;
 reg [95:0] ack_restored;
 integer r,ack_address,ack_owner;
 reg [95:0] ctx[0:7];
 reg [7:0] trusted;
 reg [218:0] reserved;
 reg context_ce;
 reg [95:0] restored;
 reg [71:0] rawword,candidate;
 reg [6:0] syn;
 reg odd;
 integer e,f,g,t,a,b,ph,status,owner,pass,chosen;

 function automatic [6:0] syndrome(input [71:0] word);
  integer bitno,k;
  begin
   syndrome=0;
   for(k=0;k<7;k=k+1)
    for(bitno=1;bitno<=71;bitno=bitno+1)
     if((bitno & (1<<k))!=0) syndrome[k]=syndrome[k]^word[bitno-1];
  end
 endfunction
 function automatic legal(input integer engine,address);
  begin
   legal=(address>=0 && address<219);
   if(engine<6) legal=legal && address>=16*engine && address<16*(engine+1);
   else legal=legal && address>=96 && !(address>=145+3*engine && address<148+3*engine);
  end
 endfunction
 function automatic [95:0] decoded_context(input integer engine,input [9635:0] payload);
  begin
   decoded_context={payload[44*(147+3*engine)+:8],
                    payload[44*(146+3*engine)+:44],
                    payload[44*(145+3*engine)+:44]};
  end
 endfunction

 always @* begin
  base_next=context_current;base_we=0;
  scrub_v=0;scrub_index=0;scrub_original=0;scrub_candidate=0;
  error=0;busy=(|current_ce)||(|current_bad);reserved=0;context_ce=0;
  trusted=0;restored=0;rawword=0;candidate=0;syn=0;odd=0;
  e=0;f=0;g=0;t=0;a=0;b=0;ph=0;status=0;owner=0;pass=0;chosen=0;
  for(g=0;g<219;g=g+1)begin
   if(current_bad[g] || (current_clean[g]&&current_ce[g]) ||
      !(current_clean[g]||current_ce[g]||current_bad[g])) error=1;
  end
  for(e=0;e<8;e=e+1)begin
   ctx[e]=context_current[96*e+:96];
   trusted[e]=context_clean[e];
   for(t=0;t<3;t=t+1)
    trusted[e]=trusted[e]&&current_clean[145+3*e+t]&&!current_ce[145+3*e+t]&&!current_bad[145+3*e+t];
   if(!trusted[e])busy=1;
   if(trusted[e]&&ctx[e][95])begin
    busy=1;a=integer'(ctx[e][81:72]);ph=integer'(ctx[e][92:90]);status=integer'(ctx[e][94:93]);
    if(!legal(e,a)||ph>3||status>1)error=1;
    else begin
     if(reserved[a])error=1;
     reserved[a]=1;
    end
   end
  end
  if(!trusted[6]&&!trusted[7])error=1;
  // A dirty context is never used as an address/phase/valid control source.
  // Exactly one context codeword may be repaired; its other two must be clean.
  for(g=145;g<169;g=g+1)if(current_ce[g])begin
   context_ce=1;owner=(g-145)/3;
   for(t=0;t<3;t=t+1)if(145+3*owner+t!=g)
    if(!current_clean[145+3*owner+t]||current_ce[145+3*owner+t]||current_bad[145+3*owner+t])error=1;
  end
  if(enable&&!error)begin
   // Progress only CURRENT-clean contexts, even while another context is dirty.
   for(e=0;e<8;e=e+1)if(trusted[e]&&ctx[e][95])begin
    a=integer'(ctx[e][81:72]);ph=integer'(ctx[e][92:90]);status=integer'(ctx[e][94:93]);
    if(!current_ce[a]||current_clean[a]||current_bad[a])error=1;
    else if(status==1)begin // CAP: address reservation, FOUR quiet edges.
     if(ph<3)begin
      base_next[96*e+:96]=ctx[e];base_next[96*e+90+:3]=3'(ph+1);base_we[e]=1;
     end else begin
      rawword=current_raw[72*a+:72];syn=syndrome(rawword);odd=^rawword;
      if(!odd || syn>71)error=1;
      else begin
       base_next[96*e+:96]=0;
       base_next[96*e+:72]=rawword;base_next[96*e+72+:10]=10'(a);
       base_next[96*e+82+:7]=syn;base_next[96*e+89]=odd;
       base_next[96*e+95]=1;base_we[e]=1; // FIX0 phase0
      end
     end
    end else begin // FIX: check original/current identity before EVERY advance.
     // Validate restored control BEFORE offering, independent of retire_ready.
     // The parent may qualify readiness with error; no ready/error feedback loop.
     if(a>=145&&a<169)begin
      owner=(a-145)/3;restored=decoded_context(owner,current_payload);
      if(owner==e)error=1;
      if(restored[95] && (!legal(owner,integer'(restored[81:72]))||restored[92:90]>3||restored[94:93]>1))error=1;
     end
     rawword=ctx[e][71:0];syn=syndrome(rawword);odd=^rawword;
     candidate=rawword;
     if(syn==0)candidate[71]=~candidate[71];
     else if(syn<=71)candidate[syn-1]=~candidate[syn-1];
     if(!odd||syn>71||ctx[e][88:82]!=syn||ctx[e][89]!=odd||
        current_raw[72*a+:72]!=rawword||current_fixed[72*a+:72]!=candidate)error=1;
     else if(ph<3)begin
      base_next[96*e+:96]=ctx[e];base_next[96*e+90+:3]=3'(ph+1);base_we[e]=1;
     end else begin
      scrub_v[e]=1;scrub_index[10*e+:10]=10'(a);
      scrub_original[72*e+:72]=rawword;scrub_candidate[72*e+:72]=candidate;

     end
    end
   end
   // Reserve from OLD idle contexts; no same-edge freed-context reuse.
   // If any context has CE, only context repair can be newly allocated.
   // Lowest global address first; clean utility6 before7; bank engines are scoped.
   for(e=0;e<8;e=e+1)if(trusted[e]&&!ctx[e][95])begin
    chosen=-1;
    for(pass=0;pass<2;pass=pass+1)
     for(g=0;g<219;g=g+1)if(chosen<0 && current_ce[g] && !reserved[g] && legal(e,g))begin
      if((pass==0 && g>=145 && g<169) || (pass==1 && !context_ce && !(g>=145&&g<169)))chosen=g;
     end
    if(chosen>=0)begin
     reserved[chosen]=1;base_next[96*e+:96]=0;
     base_next[96*e+72+:10]=10'(chosen);base_next[96*e+93+:2]=1;
     base_next[96*e+95]=1;base_we[e]=1;
    end
   end
  end
  // Atomic fail-closed batch: no partial phase/scrub/peer-restart on any error.
  busy=busy||error;
  if(error || !enable)begin
   base_next=context_current;base_we=0;scrub_v=0;scrub_index=0;scrub_original=0;scrub_candidate=0;
  end
 end
 // Retirement cone only. No error/busy/offer assignments or feedback into validation.
 always @* begin
  context_next=base_next;context_we=base_we;
  ack_restored=0;r=0;ack_address=0;ack_owner=0;
  if(enable&&!error)begin
   for(r=0;r<8;r=r+1)if(scrub_v[r]&&retire_ready[r])begin
    context_next[96*r+:96]=0;context_we[r]=1;
    ack_address=integer'(scrub_index[10*r+:10]);
    if(ack_address>=145&&ack_address<169)begin
     ack_owner=(ack_address-145)/3;
     // Restored legality was already validated before the ready-independent offer.
     ack_restored=decoded_context(ack_owner,current_payload);
     ack_restored[92:90]=0;
     context_next[96*ack_owner+:96]=ack_restored;context_we[ack_owner]=1;
    end
   end
  end
 end
endmodule

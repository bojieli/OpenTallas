`timescale 1ps/1ps
// Default-off functional component. Cold reset requires external all-copy fence.
// Runtime rearm refuses live debt. No backend/caller/physical-protection claim.
module ot_hdc_qwen_pc_exact_completion #(
 parameter integer OPT_EXACT=0, NC=6, MAX_OUT=16, AW=34,
 parameter integer CTAGW=32, GENW=4, SIDW=3, PTAGW=35
)(
 input wire clk,rst_n,admission_stop,rearm_v,provider_fenced,reset_fenced,
 output wire rearm_rdy,idle,
 input wire [NC-1:0] c_req_v,c_req_we,
 output reg [NC-1:0] c_req_rdy,
 input wire [NC*AW-1:0] c_req_addr,
 input wire [NC*CTAGW-1:0] c_req_tag,
 input wire [NC*GENW-1:0] c_req_gen,
 input wire [NC*256-1:0] c_req_data,
 output reg [NC-1:0] c_rsp_v,c_wr_done_v,
 input wire [NC-1:0] c_rsp_rdy,c_wr_done_rdy,
 output reg [NC*CTAGW-1:0] c_rsp_tag,c_wr_done_tag,
 output reg [NC*GENW-1:0] c_rsp_gen,c_wr_done_gen,
 output reg [NC*256-1:0] c_rsp_data,
 output reg p_req_v,p_req_we,
 input wire p_req_rdy,
 output reg [AW-1:0] p_req_addr,
 output reg [PTAGW-1:0] p_req_tag,
 output reg [GENW-1:0] p_req_gen,
 output reg [255:0] p_req_data,
 input wire p_rsp_v,p_wr_done_v,
 output reg p_rsp_rdy,p_wr_done_ready,
 input wire [PTAGW-1:0] p_rsp_tag,p_wr_done_tag,
 input wire [GENW-1:0] p_rsp_gen,p_wr_done_gen,
 input wire [255:0] p_rsp_data,
 output reg fault
);
 localparam [1:0] FREE=0,ISSUED=1,RD_HELD=2,WR_HELD=3;
 reg [1:0] state[0:NC-1][0:MAX_OUT-1];
 reg [CTAGW-1:0] tag[0:NC-1][0:MAX_OUT-1];
 reg [GENW-1:0] gen[0:NC-1][0:MAX_OUT-1];
 reg direction[0:NC-1][0:MAX_OUT-1];
 reg [4:0] outstanding[0:NC-1];reg [SIDW-1:0] rr;
 reg hv,hw;reg [SIDW-1:0] hc;reg [3:0] hs;
 reg [AW-1:0] ha;reg [CTAGW-1:0] ht;reg [GENW-1:0] hg;reg [255:0] hd;
 reg rqv,rqbad;reg [SIDW-1:0] rqc;reg [CTAGW-1:0] rqt;
 reg [GENW-1:0] rqg;reg [255:0] rqd;
 reg rdv;reg [SIDW-1:0] rdc;reg [3:0] rds;
 reg [CTAGW-1:0] rdt;reg [GENW-1:0] rdg;reg [255:0] rdd;
 reg wqv,wqbad;reg [SIDW-1:0] wqc;reg [CTAGW-1:0] wqt;reg [GENW-1:0] wqg;
 reg [NC-1:0] sv;reg [3:0] ss[0:NC-1];
 reg bad,found,duplicate,all_empty;integer candidate,choice,slot;
 integer rhits,whits,rslot,wslot;integer i,j,step,delta;
 wire [SIDW-1:0] incoming_rc=p_rsp_tag[PTAGW-1:CTAGW];
 wire [SIDW-1:0] incoming_wc=p_wr_done_tag[PTAGW-1:CTAGW];
 wire req_take=p_req_v&&p_req_rdy;
 wire rd_take=rdv&&c_rsp_v[rdc]&&c_rsp_rdy[rdc];
 assign idle=all_empty&&!hv&&!rqv&&!rdv&&!wqv&&!(|sv);
 assign rearm_rdy=OPT_EXACT&&admission_stop&&provider_fenced&&reset_fenced&&idle;
 initial begin
  if(NC!=6||MAX_OUT!=16||CTAGW!=32||GENW!=4||SIDW!=3||PTAGW!=35||AW!=34)
   $fatal(1,"exact component requires full NC6/MAX16/tag32/gen4/AW34 geometry");
 end
 always @* begin
  all_empty=1;for(integer c=0;c<NC;c=c+1)for(integer s=0;s<MAX_OUT;s=s+1)
   if(state[c][s]!=FREE)all_empty=0;
  rhits=0;whits=0;rslot=0;wslot=0;
  if(rqv&&rqc<NC)for(integer s=0;s<MAX_OUT;s=s+1)
   if(state[rqc][s]==ISSUED&&!direction[rqc][s]&&tag[rqc][s]==rqt&&gen[rqc][s]==rqg)begin rhits=rhits+1;rslot=s;end
  if(wqv&&wqc<NC)for(integer s=0;s<MAX_OUT;s=s+1)
   if(state[wqc][s]==ISSUED&&direction[wqc][s]&&tag[wqc][s]==wqt&&gen[wqc][s]==wqg)begin whits=whits+1;wslot=s;end
  bad=(rqv&&(rqbad||rhits!=1))||(wqv&&(wqbad||whits!=1));
  found=0;choice=0;slot=0;duplicate=0;candidate=0;
  // One request lookup across client banks. No credit freed on this edge is used.
  if(!hv&&!admission_stop)for(integer k=0;k<NC;k=k+1)begin
   candidate=integer'(rr)+k;if(candidate>=NC)candidate=candidate-NC;
   if(!found&&c_req_v[candidate])begin
    for(integer s=0;s<MAX_OUT;s=s+1)
     if(state[candidate][s]!=FREE&&tag[candidate][s]==c_req_tag[candidate*CTAGW+:CTAGW]&&
       gen[candidate][s]==c_req_gen[candidate*GENW+:GENW]&&direction[candidate][s]==c_req_we[candidate])duplicate=1;
    if(duplicate)bad=1;
    if(outstanding[candidate]<MAX_OUT)begin
     found=1;choice=candidate;slot=0;
     for(integer s=MAX_OUT-1;s>=0;s=s-1)if(state[candidate][s]==FREE)slot=s;
    end
   end
  end
  // Caller must hold until actual backend acceptance, including the frozen cycle.
  if(hv&&(!c_req_v[hc]||c_req_we[hc]!=hw||c_req_addr[hc*AW+:AW]!=ha||
      c_req_tag[hc*CTAGW+:CTAGW]!=ht||c_req_gen[hc*GENW+:GENW]!=hg||c_req_data[hc*256+:256]!=hd))bad=1;
  if(rearm_v&&!rearm_rdy)bad=1;
  c_req_rdy=0;c_rsp_v=0;c_wr_done_v=0;c_rsp_tag=0;c_rsp_gen=0;c_rsp_data=0;c_wr_done_tag=0;c_wr_done_gen=0;
  p_req_v=0;p_req_we=hw;p_req_addr=ha;p_req_tag={hc,ht};p_req_gen=hg;p_req_data=hd;
  p_rsp_rdy=0;p_wr_done_ready=0;
  if(OPT_EXACT&&!fault&&!bad&&rst_n)begin
   // Freeze new backend admission on stop; accepted returns may still drain.
   p_req_v=hv&&!admission_stop;
   if(p_req_v)c_req_rdy[hc]=p_req_rdy;
   p_rsp_rdy=!rqv;p_wr_done_ready=1;
   if(rdv)begin c_rsp_v[rdc]=1;c_rsp_tag[rdc*CTAGW+:CTAGW]=rdt;c_rsp_gen[rdc*GENW+:GENW]=rdg;c_rsp_data[rdc*256+:256]=rdd;end
   for(integer c=0;c<NC;c=c+1)if(sv[c])begin
    c_wr_done_v[c]=1;c_wr_done_tag[c*CTAGW+:CTAGW]=tag[c][ss[c]];c_wr_done_gen[c*GENW+:GENW]=gen[c][ss[c]];
   end
  end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   fault<=0;rr<=0;hv<=0;hw<=0;hc<=0;hs<=0;ha<=0;ht<=0;hg<=0;hd<=0;
   rqv<=0;rqbad<=0;rqc<=0;rqt<=0;rqg<=0;rqd<=0;
   rdv<=0;rdc<=0;rds<=0;rdt<=0;rdg<=0;rdd<=0;
   wqv<=0;wqbad<=0;wqc<=0;wqt<=0;wqg<=0;sv<=0;
   for(i=0;i<NC;i=i+1)begin outstanding[i]<=0;ss[i]<=0;
    for(j=0;j<MAX_OUT;j=j+1)begin state[i][j]<=FREE;tag[i][j]<=0;gen[i][j]<=0;direction[i][j]<=0;end
   end
  end else if(OPT_EXACT)begin
   if(rearm_v&&rearm_rdy)begin fault<=0;rr<=0;end
   else if(bad)fault<=1;
   else if(!fault)begin
    // An unaccepted holder is source-owned; stop cancels reservation without ACK.
    if(admission_stop)hv<=0;
    if(!hv&&found&&!admission_stop)begin
     hv<=1;hc<=SIDW'(choice);hs<=4'(slot);hw<=c_req_we[choice];ha<=c_req_addr[choice*AW+:AW];
     ht<=c_req_tag[choice*CTAGW+:CTAGW];hg<=c_req_gen[choice*GENW+:GENW];hd<=c_req_data[choice*256+:256];
    end
    if(req_take)begin
     hv<=0;state[hc][hs]<=ISSUED;tag[hc][hs]<=ht;gen[hc][hs]<=hg;direction[hc][hs]<=hw;
     rr<=(hc==NC-1)?0:hc+1'b1;
    end
    if(rd_take)begin rdv<=0;state[rdc][rds]<=FREE;end
    if(rqv&&!rdv)begin
     rqv<=0;rdv<=1;rdc<=rqc;rds<=4'(rslot);rdt<=rqt;rdg<=rqg;rdd<=rqd;state[rqc][rslot]<=RD_HELD;
    end
    if(p_rsp_v&&p_rsp_rdy)begin
     rqv<=1;rqc<=incoming_rc;rqt<=p_rsp_tag[CTAGW-1:0];rqg<=p_rsp_gen;rqd<=p_rsp_data;
     rqbad<=req_take&&!hw&&incoming_rc==hc&&p_rsp_tag[CTAGW-1:0]==ht&&p_rsp_gen==hg;
    end
    if(wqv)begin state[wqc][wslot]<=WR_HELD;wqv<=0;end
    if(p_wr_done_v&&p_wr_done_ready)begin
     wqv<=1;wqc<=incoming_wc;wqt<=p_wr_done_tag[CTAGW-1:0];wqg<=p_wr_done_gen;
     wqbad<=req_take&&hw&&incoming_wc==hc&&p_wr_done_tag[CTAGW-1:0]==ht&&p_wr_done_gen==hg;
    end
    for(i=0;i<NC;i=i+1)begin
     if(sv[i]&&c_wr_done_rdy[i])begin state[i][ss[i]]<=FREE;sv[i]<=0;end
     if(!sv[i])begin
      for(j=MAX_OUT-1;j>=0;j=j-1)if(state[i][j]==WR_HELD)begin sv[i]<=1;ss[i]<=4'(j);end
     end
     delta=0;if(req_take&&hc==i)delta=delta+1;
     if(rd_take&&rdc==i)delta=delta-1;
     if(sv[i]&&c_wr_done_rdy[i])delta=delta-1;
     outstanding[i]<=5'(integer'(outstanding[i])+delta);
    end
   end
  end
 end
endmodule

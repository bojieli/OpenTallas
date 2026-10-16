`timescale 1ns/1ps
`default_nettype none
// Opt-in G25 candidate. R must be an immutable protected snapshot with the
// producer retired/fenced and the span/version held until consumer retirement.
// Two serialized passes; first verifies dense local-slot numbering per owner.
module ot_hgi_inverse_selected #(parameter integer ENABLE=0, MUT=0)(
 input wire clk,rst_n,go,retire,input wire[11:0]k,input wire[7:0]group,
 input wire span_valid,input wire[31:0]source_version,source_version_now,
 output wire r_req_v,input wire r_req_rdy,output wire[10:0]r_req_index,
 input wire r_rsp_v, input wire[10:0]r_rsp_index,input wire[31:0]r_rsp_data,input wire r_rsp_fault,output wire r_rsp_rdy,
 output reg build_done,output reg fault,output wire ready,
 input wire[3:0]look_v,output wire[3:0]look_rdy,input wire[27:0]look_owner,
 input wire[47:0]look_slot,input wire[63:0]look_tag,
 output reg[3:0]ret_v,ret_filtered,ret_fault,output reg[43:0]ret_index,output reg[63:0]ret_tag);
 localparam IDLE=0,INIT=1,IWAIT=2,REQ=3,RWAIT=4,OREAD=5,OWAIT=6,CWRITE=7,CWAIT=8,
  PREAD=9,PWAIT=10,PWRITE=11,PWRWAIT=12,MAPWRITE=13,MAPWAIT=14,FINISH=15,ACTIVE=16;
 reg[4:0]st,stbar;reg[11:0]kq,kbar,idx,idxbar,prefix,prefixbar;
 reg[7:0]gq,gbar;reg[6:0]owner,ownerbar,it,itbar;reg[11:0]slot,slotbar;
 reg[31:0]version,versionbar;reg pass2,pass2bar;reg[31:0]owner_word,owner_wordbar;reg[11:0]map_addr,map_addrbar;
 reg owv,mwv,orv;reg[11:0]owa,ora,mwa;reg[31:0]owd,mwd;
 wire[3:0]oov,mov,oue,mue,oce,mce,owdone,mwdone;
 wire[31:0]ord[0:3],mrd[0:3]; wire[3:0]ocf,mcf;wire[3:0]ordv;wire[11:0]orda[0:3];
 reg[3:0]mrv;reg[11:0]mra[0:3];
 wire control_bad=(stbar!=~st)||(kbar!=~kq)||(gbar!=~gq)||(idxbar!=~idx)||
  (prefixbar!=~prefix)||(ownerbar!=~owner)||(slotbar!=~slot)||(itbar!=~it)||(versionbar!=~version)||(pass2bar!=~pass2)||(|ocf)||(|mcf)||
  ((st==CWRITE||st==PWRITE||st==MAPWRITE)&&owner_wordbar!=~owner_word)||
  (st==MAPWRITE&&map_addrbar!=~map_addr);
 assign ready=ENABLE&&st==ACTIVE&&!fault&&!control_bad&&span_valid&&source_version_now==version;
 assign look_rdy={4{ready}};
 assign r_req_v=ENABLE&&st==REQ&&!fault&&!control_bad&&span_valid&&source_version_now==version;
 assign r_req_index=idx[10:0]; assign r_rsp_rdy=st==RWAIT;
 function automatic[18:0]decode(input[31:0]v,input[7:0]g);
  reg[11:0]j;reg[6:0]r;reg[12:0]q;begin
   case(g)
    1:begin j=v[11:0];r=0;end
    2:begin j=v[12:1];r={6'd0,v[0]};end
    4:begin j=v[13:2];r={5'd0,v[1:0]};end
    8:begin j=v[14:3];r={4'd0,v[2:0]};end
    default:begin q=v[17:5]/13'd3;j=q[11:0];r={(v[17:5]%13'd3),v[4:0]};end
   endcase
   decode={r,j};end
 endfunction
 function automatic[17:0]limit(input[11:0]n,input[7:0]g);
  begin case(g)
   1:limit={6'd0,n};2:limit={5'd0,n,1'b0};4:limit={4'd0,n,2'd0};8:limit={3'd0,n,3'd0};
   default:limit=({6'd0,n}<<6)+({6'd0,n}<<5);
  endcase end
 endfunction
 reg[18:0]decoded;integer l,t;
 // Metadata for protected owner read (6 cycles). All lookup boundaries register.
 reg[11:0]ls[0:3][0:5];reg[15:0]lt[0:3][0:5];reg[5:0]lv[0:3],lb[0:3];reg[6:0]ownerid[0:3][0:5],owneridbar[0:3][0:5];reg[10:0]addrid[0:3][0:6],addridbar[0:3][0:6];
 reg[6:0]fv[0:3],ff[0:3],fe[0:3];reg[15:0]ft[0:3][0:6];
 reg[11:0]lsbar[0:3][0:5];reg[15:0]ltbar[0:3][0:5],ftbar[0:3][0:6];
 reg[5:0]lvbar[0:3],lbbar[0:3];reg[6:0]fvbar[0:3],ffbar[0:3],febar[0:3];
 reg meta_bad;
 genvar lane;generate for(lane=0;lane<4;lane=lane+1)begin:lanes
  assign ordv[lane]=(lane==0&&st!=ACTIVE)?orv:(look_v[lane]&&ready);
  assign orda[lane]=(lane==0&&st!=ACTIVE)?ora:{5'd0,look_owner[7*lane+:7]};
  ot_hgi_inverse_mem #(.BANKS(1))owners(.clk(clk),.rst_n(rst_n),.rv(ordv[lane]),.ra(orda[lane]),
   .ov(oov[lane]),.rd(ord[lane]),.ue(oue[lane]),.ce(oce[lane]),.wv(owv),.wa(owa),.wd(owd),.wdone(owdone[lane]),.ctrl_fault(ocf[lane]));
  ot_hgi_inverse_mem #(.BANKS(3))map(.clk(clk),.rst_n(rst_n),.rv(mrv[lane]),.ra(mra[lane]),
   .ov(mov[lane]),.rd(mrd[lane]),.ue(mue[lane]),.ce(mce[lane]),.wv(mwv),.wa(mwa),.wd(mwd),.wdone(mwdone[lane]),.ctrl_fault(mcf[lane]));
 end endgenerate
 task next_state(input[4:0]s);begin st<=s;stbar<=~s;end endtask
 task setidx(input[11:0]v);begin idx<=v;idxbar<=~v;end endtask
 task setit(input[6:0]v);begin it<=v;itbar<=~v;end endtask
 always @(posedge clk or negedge rst_n) if(!rst_n)begin
  st<=IDLE;stbar<=~5'(IDLE);fault<=0;build_done<=0;owv<=0;mwv<=0;orv<=0;mrv<=0;ret_v<=0;
  pass2<=0;pass2bar<=1;owner_word<=0;owner_wordbar<=32'hffffffff;map_addr<=0;map_addrbar<=12'hfff;
  kq<=0;kbar<=12'hfff;gq<=0;gbar<=8'hff;idx<=0;idxbar<=12'hfff;prefix<=0;prefixbar<=12'hfff;
  owner<=0;ownerbar<=7'h7f;slot<=0;slotbar<=12'hfff;it<=0;itbar<=7'h7f;version<=0;versionbar<=32'hffffffff;
  for(l=0;l<4;l=l+1)begin lv[l]<=0;lb[l]<=0;fv[l]<=0;ff[l]<=0;fe[l]<=0;lvbar[l]<=6'h3f;lbbar[l]<=6'h3f;fvbar[l]<=7'h7f;ffbar[l]<=7'h7f;febar[l]<=7'h7f;end
 end else begin
  owv<=0;mwv<=0;orv<=0;mrv<=0;ret_v<=0;build_done<=0;
  if(st!=IDLE&&(control_bad||!span_valid||source_version_now!=version)) begin fault<=1;next_state(IDLE);end
  else case(st)
   IDLE:if(go&&ENABLE&&!fault)begin
    fault<=0;
    if(k==0||k>2048||!(group==1||group==2||group==4||group==8||group==96)||!span_valid||source_version!=source_version_now)fault<=1;
    else begin kq<=k;kbar<=~k;gq<=group;gbar<=~group;version<=source_version;versionbar<=~source_version;
      setidx(0);setit(0);prefix<=0;prefixbar<=12'hfff;pass2<=0;pass2bar<=1;next_state(INIT);end
   end
   INIT:begin owv<=1;owa<={5'd0,it};owd<={1'b1,it,24'd0};next_state(IWAIT);end
   IWAIT:if(owdone[0])begin if(it+1==gq)begin setidx(0);next_state(REQ);end
     else begin setit(it+1);next_state(INIT);end end
   REQ:if(r_req_rdy)next_state(RWAIT);
   RWAIT:if(r_rsp_v)begin
    decoded=decode(r_rsp_data,gq);
    if(r_rsp_fault||r_rsp_index!=idx[10:0]||r_rsp_data>=limit(kq,gq))begin fault<=1;next_state(IDLE);end
    else begin owner<=decoded[18:12];ownerbar<=~decoded[18:12];slot<=decoded[11:0];slotbar<=~decoded[11:0];next_state(OREAD);end
   end
   OREAD:begin orv<=1;ora<={5'd0,owner};next_state(OWAIT);end
   OWAIT:if(oov[0])begin
    if(oue[0]||!ord[0][31]||ord[0][30:24]!=owner||(!pass2&&slot!=ord[0][11:0])||
       (pass2&&(slot>=ord[0][11:0]||{1'b0,ord[0][23:12]}+slot>=kq)))begin fault<=1;next_state(IDLE);end
    else begin owner_word<=ord[0];owner_wordbar<=~ord[0];map_addr<=ord[0][23:12]+slot;map_addrbar<=~(ord[0][23:12]+slot);next_state(pass2?MAPWRITE:CWRITE);end
   end
   CWRITE:begin owv<=1;owa<={5'd0,owner};owd<=owner_word+1;next_state(CWAIT);end
   CWAIT:if(owdone[0])begin
    if(idx+1==kq)begin setit(0);next_state(PREAD);end else begin setidx(idx+1);next_state(REQ);end
   end
   PREAD:begin orv<=1;ora<={5'd0,it};next_state(PWAIT);end
   PWAIT:if(oov[0])begin
    if(oue[0]||!ord[0][31]||ord[0][30:24]!=it||ord[0][23:12]!=0||{1'b0,prefix}+ord[0][11:0]>kq)begin fault<=1;next_state(IDLE);end
    else begin owner_word<=ord[0];owner_wordbar<=~ord[0];next_state(PWRITE);end
   end
   PWRITE:begin owv<=1;owa<={5'd0,it};owd<={1'b1,it,prefix,owner_word[11:0]};
    prefix<=prefix+owner_word[11:0];prefixbar<=~(prefix+owner_word[11:0]);next_state(PWRWAIT);end
   PWRWAIT:if(owdone[0])begin
    if(it+1==gq)begin if(prefix!=kq)begin fault<=1;next_state(IDLE);end
     else begin pass2<=1;pass2bar<=0;setidx(0);next_state(REQ);end end
    else begin setit(it+1);next_state(PREAD);end
   end
   MAPWRITE:begin mwv<=1;mwa<=map_addr;mwd<={1'b1,9'd0,map_addr[10:0],(MUT==1?11'(kq-1-idx):idx[10:0])};next_state(MAPWAIT);end
   MAPWAIT:if(mwdone[0])begin if(idx+1==kq)next_state(FINISH);else begin setidx(idx+1);next_state(REQ);end end
   FINISH:begin build_done<=1;next_state(ACTIVE);end
   ACTIVE:if(retire)begin
    if(look_v!=0||lv[0]!=0||lv[1]!=0||lv[2]!=0||lv[3]!=0||fv[0]!=0||fv[1]!=0||fv[2]!=0||fv[3]!=0)fault<=1;
    next_state(IDLE);
   end
   default:begin fault<=1;next_state(IDLE);end
  endcase
  for(l=0;l<4;l=l+1)begin
   lv[l]<={lv[l][4:0],look_v[l]&&ready};
   lb[l]<={lb[l][4:0],look_owner[7*l+:7]>=gq};
   lvbar[l]<=~{lv[l][4:0],look_v[l]&&ready};lbbar[l]<=~{lb[l][4:0],look_owner[7*l+:7]>=gq};
   ownerid[l][0]<=look_owner[7*l+:7];owneridbar[l][0]<=~look_owner[7*l+:7];
   lsbar[l][0]<=~look_slot[12*l+:12];ltbar[l][0]<=~look_tag[16*l+:16];
   ls[l][0]<=look_slot[12*l+:12];lt[l][0]<=look_tag[16*l+:16];
   for(t=1;t<6;t=t+1)begin ls[l][t]<=ls[l][t-1];lt[l][t]<=lt[l][t-1];lsbar[l][t]<=lsbar[l][t-1];ltbar[l][t]<=ltbar[l][t-1];ownerid[l][t]<=ownerid[l][t-1];owneridbar[l][t]<=owneridbar[l][t-1];end
   fv[l]<={fv[l][5:0],lv[l][5]};ff[l]<={ff[l][5:0],1'b0};fe[l]<={fe[l][5:0],1'b0};
   fvbar[l]<=~{fv[l][5:0],lv[l][5]};ffbar[l]<=~{ff[l][5:0],1'b0};febar[l]<=~{fe[l][5:0],1'b0};
   ftbar[l][0]<=ltbar[l][5];ft[l][0]<=lt[l][5];for(t=1;t<7;t=t+1)begin ft[l][t]<=ft[l][t-1];ftbar[l][t]<=ftbar[l][t-1];addrid[l][t]<=addrid[l][t-1];addridbar[l][t]<=addridbar[l][t-1];end
   if(lv[l][5])begin
    if(owneridbar[l][5]!=~ownerid[l][5]||lsbar[l][5]!=~ls[l][5]||ltbar[l][5]!=~lt[l][5]||lvbar[l]!=~lv[l]||lbbar[l]!=~lb[l]||lb[l][5]||!oov[l]||oue[l]||!ord[l][31]||ord[l][30:24]!=ownerid[l][5]||{1'b0,ord[l][23:12]}+ord[l][11:0]>kq)begin fe[l][0]<=1;febar[l][0]<=0;end
    else if(ls[l][5]>=ord[l][11:0])begin ff[l][0]<=1;ffbar[l][0]<=0;end
    else begin mrv[l]<=1;mra[l]<=ord[l][23:12]+ls[l][5];addrid[l][0]<=11'(ord[l][23:12]+ls[l][5]);addridbar[l][0]<=~11'(ord[l][23:12]+ls[l][5]);end
   end
   if(lvbar[l]!=~lv[l]||lbbar[l]!=~lb[l]||fvbar[l]!=~fv[l]||ffbar[l]!=~ff[l]||febar[l]!=~fe[l])fault<=1;
   if(fv[l][6])begin
    meta_bad=ftbar[l][6]!=~ft[l][6]||fvbar[l]!=~fv[l]||ffbar[l]!=~ff[l]||febar[l]!=~fe[l];
    ret_v[l]<=1;ret_tag[16*l+:16]<=ft[l][6];ret_filtered[l]<=(MUT==2)?1'b0:ff[l][6];
    ret_fault[l]<=meta_bad||fe[l][6]||(!ff[l][6]&&(!mov[l]||mue[l]||!mrd[l][31]||mrd[l][30:22]!=0||mrd[l][21:11]!=addrid[l][6]||addridbar[l][6]!=~addrid[l][6]||mrd[l][10:0]>=kq));
    ret_index[11*l+:11]<=mrd[l][10:0];
    if(meta_bad||fe[l][6]||(!ff[l][6]&&(!mov[l]||mue[l]||!mrd[l][31]||mrd[l][30:22]!=0||mrd[l][21:11]!=addrid[l][6]||addridbar[l][6]!=~addrid[l][6]||mrd[l][10:0]>=kq)))fault<=1;
   end
  end
 end
endmodule
`default_nettype wire

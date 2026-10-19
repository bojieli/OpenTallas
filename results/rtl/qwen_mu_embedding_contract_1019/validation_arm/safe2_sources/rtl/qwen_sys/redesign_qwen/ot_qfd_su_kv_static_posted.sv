`timescale 1ns/1ps
// Compiler-slotted successor reuses the exact existing FP8 assembly/encoding.
// No readiness, credit or data arrival can choose the emission cycle.
// word_slot/index is an actual compiled command; an unavailable word faults.
// Original posted formatter remains unchanged. Candidate, default off. Native FP8 epoch (HEADS1 TP8 candidate; HEADS2 historical), not a generic SU transport.
// The native program has V(HEADSx128), Klo(HEADSx64), Khi(HEADSx64). Posted writes
// cannot stall: all HEADS*256 bytes have dedicated assembly seats until epoch drain.
// Addresses and all byte masks are checked locally before omitting them from
// the existing KVN class wire. The receiver's layer/position descriptor must
// describe the SAME admitted epoch; this module does not fabricate that link.
module ot_qfd_su_kv_static_posted #(
 parameter integer ENABLE=0, HEADS=1, KV_FP8=1, MUT_LANE=0, MUT_TAG=0, MUT_MASK=0, SAFE=0
)(
 input wire clk,rst_n,
 input wire epoch_begin,input wire [17:0] epoch_pos,
 input wire issue_v,input wire [1:0] issue_kind, // 0 V, 1 Klo, 2 Khi
 input wire [17:0] issue_nout,issue_nin,
 input wire [63:0] kv_we,input wire [1535:0] kv_waddr,input wire [2047:0] kv_wdata,
 output wire epoch_idle,output wire drained,
 output reg word_v,output reg [10:0] word_tag,output reg [511:0] word_data,
 input wire word_slot,input wire [1:0] word_index,
 output reg fault,output reg [7:0] fault_code
);
 // Every arriving face bit is captured before decode/arbitration.
 reg slot_q;reg [1:0] slot_index_q;
 reg eb_q,iv_q;reg [17:0] ep_q,ino_q,ini_q;reg [1:0] ik_q;
 reg [63:0] we_q;reg [1535:0] wa_q;reg [2047:0] wd_q;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin slot_q<=0;slot_index_q<=0;eb_q<=0;iv_q<=0;ep_q<=0;ino_q<=0;ini_q<=0;ik_q<=0;we_q<=0;wa_q<=0;wd_q<=0;end
  else begin slot_q<=word_slot;slot_index_q<=word_index;eb_q<=epoch_begin;ep_q<=epoch_pos;iv_q<=issue_v;ik_q<=issue_kind;ino_q<=issue_nout;ini_q<=issue_nin;we_q<=kv_we;wa_q<=kv_waddr;wd_q<=kv_wdata;end
 end
 function automatic [8:0] encode(input [31:0] b);
  reg [7:0] e;reg [22:0] m;begin
   e=b[30:23];m=b[22:0];
   if(e==0&&m==0)encode={1'b0,b[31],7'd0};
   else if(e>=121&&e<=135&&m[19:0]==0 && !(e==135&&m[22:20]==7))
    encode={1'b0,b[31],e[3:0]-4'd8,m[22:20]};
   else if(e==120&&m[20:0]==0)encode={1'b0,b[31],4'd0,1'b1,m[22:21]};
   else if(e==119&&m[21:0]==0)encode={1'b0,b[31],5'd0,1'b1,m[22]};
   else if(e==118&&m==0)encode={1'b0,b[31],7'd1};
   else encode={1'b1,8'd0};
  end
 endfunction
 localparam integer VBASE=HEADS*65536, NBYTES=HEADS*256, NWORDS=HEADS*4;
 initial if(HEADS!=1||KV_FP8!=1)$fatal(1,"Static native formatter requires exact TP8 one-head FP8 profile");
 reg active;reg [12:0] pos;
 reg [2:0] issued;
 reg [NBYTES-1:0] seen,seen_n;
 reg [NWORDS-1:0] sent,sent_n;
 reg [NBYTES*8-1:0] bytes_r,bytes_n;
 reg [7:0] err;
 reg choose;integer selected,li,idx,dim,head,kind,halfidx;
 reg [23:0] e;reg [19:0] a;reg [16:0] w;reg [12:0] pp;
 reg [8:0] code;reg [2:0] allowed;
 wire take=word_v; // one-cycle pulse; delivery time belongs to the compiler
 assign epoch_idle=ENABLE!=0&&!active&&!word_v&&!fault&&!eb_q;
 assign drained=!active&&!word_v;
 generate if(SAFE==0)begin:g_legacy
 always_comb begin
  seen_n=seen;sent_n=sent;bytes_n=bytes_r;err=0;
  allowed=issued;
  if(iv_q&&ik_q<3)allowed[ik_q]=1;
  e=0;a=0;w=0;pp=0;code=0;dim=0;head=0;kind=0;idx=0;halfidx=0;
  for(li=0;li<64;li=li+1)if(we_q[li])begin
   e=wa_q[24*li+:24];a=e[23:4];code=encode(wd_q[32*li+:32]);
   if(a<VBASE)begin
    kind=0;head=a[16];dim=a[6:0];pp={a[15:7],e[3:0]};
    if(!allowed[dim<64?1:2])err[2]=1;
   end else begin
    w=a-VBASE;kind=1;head=w[16];pp=w[15:3];dim={w[2:0],e[3:0]};
    if(!allowed[0])err[2]=1;
   end
   idx=kind*HEADS*128+head*128+dim;
   if(MUT_LANE!=0)idx=idx^1;
   if(!active||a>=2*VBASE||head>=HEADS||pp!=pos)err[0]=1;
   if(code[8]||KV_FP8==0)err[1]=1;
   if(head<HEADS)begin
    if(seen_n[idx])err[3]=1;
    seen_n[idx]=1;bytes_n[8*idx+:8]=code[7:0];
   end
  end
  choose=slot_q;selected=slot_index_q;
  if(slot_q&&(!active||sent[selected]||!(&seen[64*selected+:64])))err[6]=1;
  if(choose)sent_n[selected]=1;

 end
 end else begin:g_safe
  // Native59 has eight active lanes. Encode and validate each lane locally,
  // then register its byte-seat address before the constant-index seat decode.
  (* keep = "true" *) reg[7:0]dv[0:15];
  (* keep = "true" *) reg[63:0]di[0:15],dc[0:15];reg[7:0]de;
  integer j,seg;reg[23:0]da;reg[19:0]aa;reg[16:0]ww;reg[12:0]dp;
  reg[7:0]ix;reg[8:0]co;reg[2:0]permit;
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin for(seg=0;seg<16;seg=seg+1)begin dv[seg]<=0;di[seg]<=0;dc[seg]<=0;end de<=0;end
   else begin
    for(seg=0;seg<16;seg=seg+1)dv[seg]<=we_q[7:0];de<=0;
    permit=issued;if(iv_q&&ik_q<3)permit[ik_q]=1;
    if(|we_q[63:8])de[0]<=1;
    for(j=0;j<8;j=j+1)begin
     da=wa_q[24*j+:24];aa=da[23:4];ww=aa-VBASE;co=encode(wd_q[32*j+:32]);
     if(aa<VBASE)begin ix={1'b0,aa[6:0]};dp={aa[15:7],da[3:0]};end
     else begin ix={1'b1,ww[2:0],da[3:0]};dp=ww[15:3];end
     for(seg=0;seg<16;seg=seg+1)begin di[seg][8*j+:8]<=ix^8'(MUT_LANE!=0);dc[seg][8*j+:8]<=co[7:0];end
     if(we_q[j])begin
      if(!active||aa>=2*VBASE||(aa<VBASE?aa[16]:ww[16])||dp!=pos)de[0]<=1;
      if(co[8]||KV_FP8==0)de[1]<=1;
      if(!(aa<VBASE?permit[aa[6]?2:1]:permit[0]))de[2]<=1;
     end
    end
   end
  end
  integer seat,lane;reg[7:0]hits;reg[7:0]value;
  always_comb begin
   seen_n=seen;sent_n=sent;bytes_n=bytes_r;err=de;
   allowed=issued;e=0;a=0;w=0;pp=0;code=0;dim=0;head=0;kind=0;idx=0;halfidx=0;li=0;
   hits=0;value=0;
   for(seat=0;seat<NBYTES;seat=seat+1)begin
    hits=0;value=bytes_r[8*seat+:8];
    for(lane=0;lane<8;lane=lane+1)begin
     hits[lane]=dv[seat/16][lane]&&(di[seat/16][8*lane+:8]==8'(seat));
     if(hits[lane])value=dc[seat/16][8*lane+:8];
    end
    if(|hits)begin
     if(seen[seat]||(|(hits&(hits-8'd1))))err[3]=1;
     seen_n[seat]=1;bytes_n[8*seat+:8]=value;
    end
   end
   choose=slot_q;selected=slot_index_q;
   if(slot_q&&(!active||sent[selected]||!(&seen[64*selected+:64])))err[6]=1;
   if(choose)sent_n[selected]=1;
  end
 end endgenerate
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;pos<=0;issued<=0;sent<=0;word_v<=0;word_tag<=0;word_data<=0;fault<=0;fault_code<=0;end
  else if(ENABLE!=0)begin
   if(eb_q)begin
    if(active||word_v||fault||ep_q>=8192)begin fault<=1;fault_code[4]<=1;end
    else begin active<=1;pos<=ep_q[12:0];issued<=0;sent<=0;end
   end else begin
    sent<=sent_n;
    if(iv_q)begin
     if(!active||ik_q>=3||ino_q!=HEADS||ini_q!=(ik_q==0?128:64)||issued[ik_q])begin fault<=1;fault_code[5]<=1;end
     else issued[ik_q]<=1;
    end
    if(|err)begin fault<=1;fault_code<=fault_code|err;end
    if(!fault&&!(|err)&&choose&&(!word_v||take))begin
     word_v<=1;word_tag<={3'b010,5'd0,({1'(selected/(HEADS*2)),1'((selected/2)%HEADS),1'(selected%2)}^3'(MUT_TAG!=0?1:0))};
     case(selected)
      0:word_data<=bytes_r[0+:512];1:word_data<=bytes_r[512+:512];
      2:word_data<=bytes_r[1024+:512];3:word_data<=bytes_r[1536+:512];
      default:word_data<=0;
     endcase
     if(MUT_MASK!=0)word_data[7:0]<=0;
    end else if(take||fault||(|err))word_v<=0;
    if(active&&(&sent)&&!word_v&&issued==3'b111)active<=0;
   end
  end
 end
 // Epoch-begin broadcast replicated per byte segment (QW-N59 10-19): the 256-seat seen / bytes_r assembly bank took its
 // clear / hold select from one eb_q flop (synthesis merged it with the service's iss[0]: 4,826 loads > 3,000).  EBC kept
 // copies of the same register, one per NBYTES/EBC-byte segment; function unchanged (the same cycle and condition).
 localparam integer EBC=16, NB=NBYTES/EBC;
 (* keep = "true" *) reg [EBC-1:0] eb_r;
 always @(posedge clk or negedge rst_n)if(!rst_n)eb_r<=0;else eb_r<={EBC{epoch_begin}};
 wire eb_clear_ok=!(active||word_v||fault||ep_q>=8192);
 genvar gs;
 generate for(gs=0;gs<EBC;gs=gs+1)begin:g_ebseg
  always @(posedge clk or negedge rst_n)
   if(!rst_n)begin seen[NB*gs+:NB]<=0;bytes_r[8*NB*gs+:8*NB]<=0;end
   else if(ENABLE!=0)begin
    if(eb_r[gs])begin if(eb_clear_ok)seen[NB*gs+:NB]<=0;end
    else begin seen[NB*gs+:NB]<=seen_n[NB*gs+:NB];bytes_r[8*NB*gs+:8*NB]<=bytes_n[8*NB*gs+:8*NB];end
   end
 end endgenerate
endmodule

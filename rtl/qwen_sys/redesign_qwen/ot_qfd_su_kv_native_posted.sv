`timescale 1ns/1ps
// Candidate, default off. Native FP8 epoch (HEADS1 TP8 candidate; HEADS2 historical), not a generic SU transport.
// The native program has V(HEADSx128), Klo(HEADSx64), Khi(HEADSx64). Posted writes
// cannot stall: all HEADS*256 bytes have dedicated assembly seats until epoch drain.
// Addresses and all byte masks are checked locally before omitting them from
// the existing KVN class wire. The receiver's layer/position descriptor must
// describe the SAME admitted epoch; this module does not fabricate that link.
module ot_qfd_su_kv_native_posted #(
 parameter integer ENABLE=0, HEADS=1, KV_FP8=1, MUT_LANE=0, MUT_TAG=0, MUT_MASK=0
)(
 input wire clk,rst_n,
 input wire epoch_begin,input wire [17:0] epoch_pos,
 input wire issue_v,input wire [1:0] issue_kind, // 0 V, 1 Klo, 2 Khi
 input wire [17:0] issue_nout,issue_nin,
 input wire [63:0] kv_we,input wire [1535:0] kv_waddr,input wire [2047:0] kv_wdata,
 output wire epoch_ready,output wire drained,
 output reg word_v,output reg [10:0] word_tag,output reg [511:0] word_data,
 input wire word_ready,
 output reg fault,output reg [7:0] fault_code
);
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
 localparam integer VBASE=HEADS*65536;
 initial if(HEADS<1||HEADS>2)$error("Only exact one/two-head profiles supported");
 reg active;reg [12:0] pos;
 reg [2:0] issued;
 reg [511:0] seen,seen_n;
 reg [7:0] sent,sent_n;
 reg [4095:0] bytes_r,bytes_n;
 reg [7:0] err;
 reg choose;integer selected,li,idx,dim,head,kind,halfidx;
 reg [23:0] e;reg [19:0] a;reg [16:0] w;reg [12:0] pp;
 reg [8:0] code;reg [2:0] allowed;
 wire take=word_v&&word_ready;
 assign epoch_ready=ENABLE!=0&&!active&&!word_v&&!fault;
 assign drained=!active&&!word_v;
 always @* begin
  seen_n=seen;sent_n=sent;bytes_n=bytes_r;err=0;
  allowed=issued;
  if(issue_v&&issue_kind<3)allowed[issue_kind]=1;
  e=0;a=0;w=0;pp=0;code=0;dim=0;head=0;kind=0;idx=0;halfidx=0;
  for(li=0;li<64;li=li+1)if(kv_we[li])begin
   e=kv_waddr[24*li+:24];a=e[23:4];code=encode(kv_wdata[32*li+:32]);
   if(a<VBASE)begin
    kind=0;head=a[16];dim=a[6:0];pp={a[15:7],e[3:0]};
    if(!allowed[dim<64?1:2])err[2]=1;
   end else begin
    w=a-VBASE;kind=1;head=w[16];pp=w[15:3];dim={w[2:0],e[3:0]};
    if(!allowed[0])err[2]=1;
   end
   idx=kind*256+head*128+dim;
   if(MUT_LANE!=0)idx=idx^1;
   if(!active||a>=2*VBASE||head>=HEADS||pp!=pos)err[0]=1;
   if(code[8]||KV_FP8==0)err[1]=1;
   if(seen_n[idx])err[3]=1;
   seen_n[idx]=1;bytes_n[8*idx+:8]=code[7:0];
  end
  choose=0;selected=0;
  for(halfidx=0;halfidx<8;halfidx=halfidx+1)
   if((halfidx/2)%2<HEADS&&!choose&&!sent[halfidx]&&(&seen[64*halfidx+:64]))begin choose=1;selected=halfidx;end
  if(choose&&(!word_v||take))sent_n[selected]=1;
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;pos<=0;issued<=0;seen<=0;sent<=0;bytes_r<=0;word_v<=0;word_tag<=0;word_data<=0;fault<=0;fault_code<=0;end
  else if(ENABLE!=0)begin
   if(epoch_begin)begin
    if(!epoch_ready||epoch_pos>=8192)begin fault<=1;fault_code[4]<=1;end
    else begin active<=1;pos<=epoch_pos[12:0];issued<=0;seen<=0;sent<=(HEADS==1?8'hCC:8'h00);end
   end else begin
    seen<=seen_n;sent<=sent_n;bytes_r<=bytes_n;
    if(issue_v)begin
     if(!active||issue_kind>=3||issue_nout!=HEADS||issue_nin!=(issue_kind==0?128:64)||issued[issue_kind])begin fault<=1;fault_code[5]<=1;end
     else issued[issue_kind]<=1;
    end
    if(|err)begin fault<=1;fault_code<=fault_code|err;end
    if(!fault&&!(|err)&&choose&&(!word_v||take))begin
     word_v<=1;word_tag<={3'b010,5'd0,3'(selected^(MUT_TAG!=0?1:0))};
     word_data<=bytes_r[512*selected+:512];
     if(MUT_MASK!=0)word_data[7:0]<=0;
    end else if(take||fault||(|err))word_v<=0;
    if(active&&(&sent)&&!word_v&&issued==3'b111)active<=0;
   end
  end
 end
endmodule

// Registered credit sender, same 40-word pool for Q and KVN. These inputs are
// LOCAL ready/valid faces; output is posted through relays. Credits return
// only from the receiver's actual retirement, never from wire launch.
module ot_qfd_su_kv_native_credit #(parameter integer ENABLE=0,CREDITS=40)(
 input wire clk,rst_n,kv_v,input wire [10:0] kv_tag,input wire [511:0] kv_data,
 output wire kv_ready,input wire q_v,input wire [5:0] q_beat,input wire [511:0] q_data,
 output wire q_ready,input wire credit_return,
 output reg x_v,output reg [10:0] x_tag,output reg [511:0] x_data,output reg fault
);
 reg [5:0] credits;reg prefer_q;
 wire admit=ENABLE!=0&&credits!=0&&!fault;
 assign q_ready=admit&&(!kv_v||prefer_q);
 assign kv_ready=admit&&(!q_v||!prefer_q);
 wire qt=q_v&&q_ready,kt=kv_v&&kv_ready;
 initial if(CREDITS!=40)$error("Native receiver requires one 40-word pool");
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin credits<=CREDITS;prefer_q<=0;x_v<=0;x_tag<=0;x_data<=0;fault<=0;end
  else begin
   x_v<=qt||kt;
   if(qt)begin x_tag<={3'b001,2'b00,q_beat};x_data<=q_data;prefer_q<=0;end
   if(kt)begin x_tag<=kv_tag;x_data<=kv_data;prefer_q<=1;end
   if(credit_return&&credits==CREDITS&&!qt&&!kt)fault<=1;
   case({credit_return,qt||kt})
    2'b10:if(credits<CREDITS)credits<=credits+1'b1;
    2'b01:credits<=credits-1'b1;
    default:credits<=credits;
   endcase
  end
 end
endmodule

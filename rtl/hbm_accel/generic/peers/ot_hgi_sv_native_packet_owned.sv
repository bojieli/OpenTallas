`timescale 1ps/1fs
`default_nettype none
// Source-bound SV rfile packet writes (at most four outstanding) and the
// sequential external preload/readback client. All accesses use global S15.
// Whole-word masks only: the SV emits four identical mask bits per word.
module ot_hgi_sv_native_packet_owned(
 input wire clk,rst_n,input wire [127:0] leaf_clk,
 input wire [337:0] su_q,bench_q,
 output reg [273:0] su_r,bench_r,
 input wire [3:0] rgrant,wgrant,rack,wack,
 output wire [3:0] rreq,wreq,drained,
 output wire [543:0] native_rq,input wire [31:0] native_credit,
 input wire [8223:0] native_rr,
 output wire [8991:0] native_wq,input wire [31:0] native_wcredit,native_done,
 output wire [130:0] fault
);
 wire [337:0] q=bench_q[337]?bench_q:su_q;
 wire [14:0] sector=q[323:309];
 wire [4:0] lane=sector[4:0];
 reg [512:0] lrq;reg[8960:0]lwq;
 wire[8256:0]lrr;wire[31:0]wc,wd;wire[3:0]rd,wwd;
 wire[64:0]rf,wf;reg pf;
 reg[16:0]ticket[0:31][0:3];reg[1:0]th[0:31],tt[0:31];reg[2:0]tn[0:31],dn[0:31];
 reg[255:0]read_data[0:31];reg[31:0]read_valid;
 reg[3:0]pending,read_pending,write_pending;integer pick;
 always @*begin
  lrq=0;lwq=0;lrq[512]=read_pending!=0||(q[337]&&!q[336]);lwq[8960]=write_pending!=0||(q[337]&&q[336]);
  if(q[337])begin
   if(q[336])begin
    lwq[lane*280+:280]={1'b1,sector,q[303:48],q[47],q[43],q[39],q[35],q[31],q[27],q[23],q[19]};
   end else lrq[lane*16+:16]={1'b1,sector};
  end
  pick=-1;
  for(integer l=31;l>=0;l--)if(tn[l]!=0&&((ticket[l][th[l]][16]&&dn[l]!=0)||(!ticket[l][th[l]][16]&&read_valid[l])))pick=l;
 end
 ot_hgi_dma_native_read_owned #(.HARD_CLOCKS(1),.LEGACY_SLOTS(4),.REQUIRE_GRANT(0)) reads(
  .clk(clk),.rst_n(rst_n),.leaf_clk(leaf_clk[63:0]),.legacy_q(lrq),.legacy_r(lrr),
  .rgrant(rgrant),.rack(rack),.rreq(rreq),.drained(rd),.released(),
  .native_rq(native_rq),.native_credit(native_credit),.native_rr(native_rr),.fault(rf));
 ot_hgi_sv_native_write_owned #(.HARD_CLOCKS(1),.SLOTS(4)) writes(
  .clk(clk),.rst_n(rst_n),.leaf_clk(leaf_clk[127:64]),.legacy_q(lwq),.legacy_credit(wc),.legacy_done(wd),.legacy_grant(),
  .wgrant(wgrant),.wack(wack),.wreq(wreq),.drained(wwd),.released(),
  .native_wq(native_wq),.native_credit(native_wcredit),.native_done(native_done),.fault(wf));
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   su_r<=0;bench_r<=0;read_valid<=0;pending<=0;read_pending<=0;write_pending<=0;pf<=0;
   for(integer l=0;l<32;l++)begin th[l]<=0;tt[l]<=0;tn[l]<=0;dn[l]<=0;end
  end else begin
   su_r[273]<=0;bench_r[273]<=0;
   pending<=pending+4'(q[337])-4'(pick>=0);
   read_pending<=read_pending+4'(q[337]&&!q[336])-4'(pick>=0&&!ticket[pick][th[pick]][16]);
   write_pending<=write_pending+4'(q[337]&&q[336])-4'(pick>=0&&ticket[pick][th[pick]][16]);
   if(bench_q[337]&&su_q[337]||q[337]&&(pending>=4||q[335:324]!=0||q[308:304]!=0))pf<=1;
   for(integer w=0;w<8;w++)if(q[337]&&q[336]&&q[16+w*4+:4]!={4{q[16+w*4]}})pf<=1;
   for(integer l=0;l<32;l++)begin
    tn[l]<=tn[l]+3'(q[337]&&int'(lane)==l)-3'(pick==l);
    dn[l]<=dn[l]+3'(wd[l])-3'(pick==l&&ticket[l][th[l]][16]);
    if(q[337]&&int'(lane)==l)begin ticket[l][tt[l]]<={q[336],q[15:0]};tt[l]<=tt[l]+1'b1;end
    if(lrr[l*257+256])begin
     if(read_valid[l]&&pick!=l)pf<=1;
     read_data[l]<=lrr[l*257+:256];read_valid[l]<=1;
    end
    if(pick==l)begin
     // su tag5357 and sequential bench tag0BE0 are kept through the queue.
     if(ticket[l][th[l]][15:0]==16'h0be0)bench_r<={1'b1,ticket[l][th[l]][15:0],ticket[l][th[l]][16],read_data[l]};
     else su_r<={1'b1,ticket[l][th[l]][15:0],ticket[l][th[l]][16],read_data[l]};
     th[l]<=th[l]+1'b1;
     if(!ticket[l][th[l]][16])read_valid[l]<=0;
    end
   end
  end
 end
 assign drained=rd&wwd&{4{pending==0&&!q[337]&&!su_r[273]&&!bench_r[273]}};
 assign fault={pf,wf,rf};
endmodule
`default_nettype wire

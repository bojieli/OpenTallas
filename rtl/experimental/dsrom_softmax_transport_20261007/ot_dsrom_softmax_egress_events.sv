// Additive protected committed-payload event bridge. A source packed SRAM
// commit certifies BOTH BF16 vectors. Destination receipts certify writes,
// never sends. Counter debt is finite and retains events through phase stalls.
module ot_dsrom_softmax_egress_events(
 input wire clk,rst_n,
 input wire begin_valid,begin_short,input wire [31:0] begin_epoch,input wire [15:0] begin_tag,
 output wire begin_ready,
 input wire capture_commit,input wire [6:0] capture_addr,
 input wire [31:0] capture_epoch,input wire [15:0] capture_tag,
 input wire receipt_valid,input wire [55:0] receipt_identity,
 input wire [2:0] phase_kind,input wire [6:0] phase_row,input wire phase_ready,
 output wire event_valid,output wire [2:0] event_kind,output wire [31:0] event_epoch,
 output wire [15:0] event_tag,output wire [6:0] event_row,output wire event_upper_half,
 output wire complete,input wire release_valid,output wire fault
);
 (* keep=1,dont_touch=1 *) reg active,active_n,failed,failed_n;
 (* keep=1,dont_touch=1 *) reg [48:0] context_q,context_n;
 (* keep=1,dont_touch=1 *) reg [5:0] ce,ce_n,re,re_n,xe,xe_n,ye,ye_n,xb,xb_n,yb,yb_n;
 (* keep=1,dont_touch=1 *) reg [4:0] cb,cb_n,rb,rb_n;
 wire [31:0] epoch=context_q[48:17];wire [15:0] tag=context_q[16:1];
 wire [5:0] elimit=context_q[0]?6'd8:6'd40;
 wire integrity=(active_n==~active)&&(failed_n==~failed)&&(context_n==~context_q)&&
  (ce_n==~ce)&&(re_n==~re)&&(xe_n==~xe)&&(ye_n==~ye)&&
  (xb_n==~xb)&&(yb_n==~yb)&&(cb_n==~cb)&&(rb_n==~rb)&&
  ce<=elimit&&re<=ce&&xe<=ce&&ye<=re&&cb<=16&&rb<=cb&&xb<={cb,1'b0}&&yb<={rb,1'b0};
 wire cap_b=capture_addr>=112;
 wire [6:0] cap_expected=cap_b?(7'd112+{2'd0,cb}):(7'd72+{1'b0,ce});
 wire cap_identity_bad=(capture_epoch!=epoch)||(capture_tag!=tag);
 wire bad_capture=capture_commit&&(!active||cap_identity_bad||capture_addr!=cap_expected||
  (cap_b?(cb>=16||re!=elimit):(ce>=elimit)));
 wire rec_b=receipt_identity[55];wire [6:0] rec_row=receipt_identity[6:0];
`ifdef SOFTMAX_EVENTS_IGNORE_EPOCH
 wire rec_identity_bad=receipt_identity[22:7]!=tag;
`else
 wire rec_identity_bad=(receipt_identity[54:23]!=epoch)||(receipt_identity[22:7]!=tag);
`endif
 wire [6:0] rec_expected=rec_b?(7'd112+{2'd0,rb}):(7'd72+{1'b0,re});
 wire bad_receipt=receipt_valid&&(!active||rec_identity_bad||rec_row!=rec_expected||
  (rec_b?(rb>=cb||re!=elimit):(re>=ce)));
 reg selected;reg [6:0] selected_row;reg selected_half;
 always @*begin
  selected=0;selected_row=0;selected_half=0;
  case(phase_kind)
   2:begin selected=xe<ce;selected_row=7'd72+{1'b0,xe};end
   3:begin selected=ye<re;selected_row=7'd72+{1'b0,ye};end
   6:begin selected=xb<{cb,1'b0};selected_row=7'd112+{2'd0,xb[5:1]};selected_half=xb[0];end
   7:begin selected=yb<{rb,1'b0};selected_row=7'd112+{2'd0,yb[5:1]};selected_half=yb[0];end
   default:begin end
  endcase
 end
 wire finished=active&&ce==elimit&&re==elimit&&cb==16&&rb==16&&xe==elimit&&ye==elimit&&xb==32&&yb==32;
 wire phase_order_bad=(phase_kind==3&&xe!=elimit)||(phase_kind==6&&ye!=elimit)||(phase_kind==7&&xb!=32);
 wire bad_phase=active&&selected&&phase_ready&&((phase_row!=selected_row)||phase_order_bad);
 wire bad_release=release_valid&&!finished;
 wire bad_begin=begin_valid&&!begin_ready;
 assign fault=failed||!integrity;
 assign begin_ready=rst_n&&!active&&!fault;
 assign complete=rst_n&&finished&&!fault;
 assign event_valid=rst_n&&active&&selected&&phase_ready&&!fault&&!bad_capture&&!bad_receipt&&!bad_phase&&!bad_release;
 assign event_kind=phase_kind;assign event_epoch=epoch;assign event_tag=tag;
 assign event_row=selected_row;assign event_upper_half=selected_half;
 always @(posedge clk)begin
  if(!rst_n)begin
   active<=0;active_n<=1;failed<=0;failed_n<=1;context_q<=0;context_n<=~49'd0;
   ce<=0;ce_n<=~6'd0;re<=0;re_n<=~6'd0;xe<=0;xe_n<=~6'd0;ye<=0;ye_n<=~6'd0;
   xb<=0;xb_n<=~6'd0;yb<=0;yb_n<=~6'd0;cb<=0;cb_n<=~5'd0;rb<=0;rb_n<=~5'd0;
  end else if(fault||bad_begin||bad_capture||bad_receipt||bad_phase||bad_release)begin failed<=1;failed_n<=0;end
  else begin
   if(begin_valid&&begin_ready)begin
    active<=1;active_n<=0;context_q<={begin_epoch,begin_tag,begin_short};context_n<=~{begin_epoch,begin_tag,begin_short};
    ce<=0;ce_n<=~6'd0;re<=0;re_n<=~6'd0;xe<=0;xe_n<=~6'd0;ye<=0;ye_n<=~6'd0;
    xb<=0;xb_n<=~6'd0;yb<=0;yb_n<=~6'd0;cb<=0;cb_n<=~5'd0;rb<=0;rb_n<=~5'd0;
   end
   if(capture_commit)begin
    if(cap_b)begin cb<=cb+1'b1;cb_n<=~(cb+5'd1);end
    else begin ce<=ce+1'b1;ce_n<=~(ce+6'd1);end
   end
   if(receipt_valid)begin
    if(rec_b)begin rb<=rb+1'b1;rb_n<=~(rb+5'd1);end
    else begin re<=re+1'b1;re_n<=~(re+6'd1);end
   end
   if(event_valid)begin
    case(phase_kind)
     2:begin xe<=xe+1'b1;xe_n<=~(xe+6'd1);end
     3:begin ye<=ye+1'b1;ye_n<=~(ye+6'd1);end
     6:begin xb<=xb+1'b1;xb_n<=~(xb+6'd1);end
     7:begin
`ifdef SOFTMAX_EVENTS_DROP_UPPER
      yb<=yb+6'd2;yb_n<=~(yb+6'd2);
`else
      yb<=yb+1'b1;yb_n<=~(yb+6'd1);
`endif
     end
     default:begin end
    endcase
   end
   if(release_valid&&complete)begin active<=0;active_n<=1;end
  end
 end
endmodule

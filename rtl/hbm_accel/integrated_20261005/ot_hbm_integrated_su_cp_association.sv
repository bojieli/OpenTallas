`timescale 1ns/1ps
// Qualified admission is distinct from the lifetime of an accepted executor.
// Shared grant owns all request/response debt. Live veto never cancels it.
module ot_hbm_integrated_su_cp_association #(parameter integer ENABLE=0,FAST_OWNER_FRONTIER=0,CONTROL_TAIL_CUT=0,OWNER_VETO_POLARITY=0,PIN_MARGIN=0)(
 input wire clk,por_n,raw_grant,qualified_owned,input wire [11:0] qualified_owned_terms,
 output wire exec_owned,new_request_permit,fault
);
 initial if(OWNER_VETO_POLARITY&&!FAST_OWNER_FRONTIER)$fatal(1,"negative association requires complete fast-owner factors");
 initial if(PIN_MARGIN&&!OWNER_VETO_POLARITY)$fatal(1,"PIN_MARGIN association is defined on the owner-veto receiver only");
 generate if(!ENABLE)begin:off
  assign exec_owned=raw_grant;
  assign new_request_permit=1'b1;
  assign fault=1'b0;
 end else begin:on
  reg associated_q,associated_n;
  wire rails_bad=associated_q==associated_n;
  wire associated=associated_q&&!associated_n;
  assign fault=raw_grant&&rails_bad;
  if(OWNER_VETO_POLARITY)begin:negative_receiver
   // Accepted debt retains its original bypass for both owner and local
   // predicates. Only new admissions require current complete ownership.
   wire [2:0] owner_bad=~qualified_owned_terms[8:6];
   wire local_ok=raw_grant&&!rails_bad&&(&qualified_owned_terms[5:0]);
   wire drain_ok=raw_grant&&!rails_bad&&((&qualified_owned_terms[5:0])||associated);
   wire admit_g,executor_g;
   ot_hbm_cp_veto_nor4 admit(.bad({owner_bad,!local_ok}),.permit(admit_g));
   ot_hbm_cp_veto_nor4 executor(.bad({owner_bad&{3{!associated}},!drain_ok}),.permit(executor_g));
   if(PIN_MARGIN)begin:final_validity
    // PIN_MARGIN CP: terms[5] is constant 1 and terms[9] carries the phase
    // validity, applied here as the final term (Shannon) exactly as before.
    wire phase_valid=qualified_owned_terms[9];
    // Invalid phase: admission 0; accepted debt keeps raw grant and own rails.
    assign new_request_permit=admit_g&&phase_valid;
    assign exec_owned=phase_valid?executor_g:(associated&&raw_grant&&!rails_bad);
   end else begin:direct
    assign new_request_permit=admit_g;assign exec_owned=executor_g;
   end
  end else if(FAST_OWNER_FRONTIER)begin:fast_receiver
   // Accepted association bypass applies only to executor debt/drain. New
   // admission retains every current owner, phase/status and error factor.
   ot_hbm_cp_frontier_and12 #(.FAST(1),.RETAINED_TAIL(CONTROL_TAIL_CUT)) admit(.bits({1'b1,raw_grant,!rails_bad,qualified_owned_terms[8:0]}),.result(new_request_permit));
   if(CONTROL_TAIL_CUT==2)begin:late_executor
    wire admitted,owner_bad,local_ok;
    ot_hbm_cp_frontier_and12 #(.FAST(1),.RETAINED_TAIL(1)) early_gate(.bits({6'b111111,qualified_owned_terms[5:0]}),.result(local_ok));
    ot_hbm_cp_frontier_nand3 owner_gate(.bits(qualified_owned_terms[8:6]),.result(owner_bad));
    assign admitted=associated||(!owner_bad&&local_ok);
    ot_hbm_cp_frontier_and12 #(.FAST(1),.RETAINED_TAIL(1)) executor_gate(.bits({9'b111111111,raw_grant,!rails_bad,admitted}),.result(exec_owned));
   end else begin:prior_executor
   ot_hbm_cp_frontier_and12 #(.FAST(1),.RETAINED_TAIL(CONTROL_TAIL_CUT)) executor(.bits({1'b1,raw_grant,!rails_bad,(qualified_owned_terms[8:0]|{9{associated}})}),.result(exec_owned));
   end
  end else begin:prior_receiver
   assign exec_owned=raw_grant&&!rails_bad&&(associated||qualified_owned);
   assign new_request_permit=raw_grant&&!rails_bad&&qualified_owned;
  end
  always @(posedge clk or negedge por_n)begin
   if(!por_n)begin associated_q<=0;associated_n<=1;end
   else if(!raw_grant)begin associated_q<=0;associated_n<=1;end
   else if(qualified_owned&&!rails_bad)begin associated_q<=1;associated_n<=0;end
  end
 end endgenerate
endmodule

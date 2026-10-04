// Observe actual canonical handshakes without changing upstream ready/valid.
// The owner supplies the manifest mapping and full retained rank/job/generation.
// W6 visibility means scheduler dependency ready; it is NOT W6 retire/drain.
module ot_hbm_txcount_tap #(parameter bit ENABLE=0)(
 input wire rf_ack_accept,rf_ack_fault,
 input wire w6_visible_valid,w6_visible_ready,w6_fault,
 output wire w4_accept,w6_accept,source_fault
);
 assign w4_accept=ENABLE&&rf_ack_accept&&!rf_ack_fault;
 assign w6_accept=ENABLE&&w6_visible_valid&&w6_visible_ready&&!w6_fault;
 assign source_fault=ENABLE&&(rf_ack_fault||w6_fault);
endmodule

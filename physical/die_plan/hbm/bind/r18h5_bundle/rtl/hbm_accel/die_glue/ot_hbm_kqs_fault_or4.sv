`default_nettype none
// Exact combinational fault reduction from ot_hgi_coll_kq_share2 composition.
module ot_hbm_kqs_fault_or4(input wire [3:0] leaf_faults, output wire fault);
 assign fault = |leaf_faults;
endmodule
`default_nettype wire

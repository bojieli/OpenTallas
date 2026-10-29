// S81-LP-2 probe: coll lanes (w and e wrappers, identical ports/body ot_s81ph_coll_lane_safe4) as hard children = exact-port blackboxes
(* blackbox *)
module dsfd_coll_lane_w_safe8_ntf #(parameter integer CORE_CRED = 8) (
    input wire [0:0] ck, input wire [0:0] rs, input wire [0:0] chb, input wire [514:0] rx, output wire [511:0] tx,
    input wire [0:0] lo_v, output wire [0:0] lo_r, input wire [552:0] lo_d,
    output wire [0:0] li_v, input wire [0:0] li_r, output wire [552:0] li_d, output wire [2:0] flt);
endmodule
(* blackbox *)
module dsfd_coll_lane_e_safe8_ntf #(parameter integer CORE_CRED = 8) (
    input wire [0:0] ck, input wire [0:0] rs, input wire [0:0] chb, input wire [514:0] rx, output wire [511:0] tx,
    input wire [0:0] lo_v, output wire [0:0] lo_r, input wire [552:0] lo_d,
    output wire [0:0] li_v, input wire [0:0] li_r, output wire [552:0] li_d, output wire [2:0] flt);
endmodule

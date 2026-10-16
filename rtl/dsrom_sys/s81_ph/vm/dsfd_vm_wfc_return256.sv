`timescale 1ns/1ps
`default_nettype none
// Structural 256-bit-per-lane return slice. Exact stages match frozen full return.
module dsfd_vm_wfc_return256 #(parameter integer RESPONSE_PAD=0) (
 input wire ck,rn,input wire[1:0] return_valid,input wire[3:0] return_lane,
 input wire[3:0] e_v,input wire[1023:0] e_d,
 output wire s_v,output wire[513:0] s_d,output reg r_bad
);
 reg[1:0] tq;
 always @(posedge ck or negedge rn) if(!rn)tq<=0;else tq<={tq[0],1'b1};
 wire tn=tq[1];
 reg[3:0] ev_pin;reg[1023:0] ed_pin;reg[1:0] valid_pin;reg[3:0] lane_pin;
 always @(posedge ck)begin ev_pin<=tn?e_v:4'd0;ed_pin<=e_d;valid_pin<=tn?return_valid:2'd0;lane_pin<=return_lane;end
    reg [513:0] r_q; reg r_qv; 
    // decoded constant-index lane select (one-hot AND-OR), replaces the runtime part-select e_d[512*l +: 256]
    // Exact fixed-width quarter selection; no dynamic part select.
    function automatic [255:0] lane256(input [1023:0] d, input [1:0] l);
        lane256 = ({256{l == 2'd0}} & d[0    +: 256]) | ({256{l == 2'd1}} & d[256  +: 256]) |
                  ({256{l == 2'd2}} & d[512  +: 256]) | ({256{l == 2'd3}} & d[768  +: 256]);
    endfunction
    wire e0 = valid_pin[0], e1=valid_pin[1];
    wire [1:0] l0=lane_pin[1:0],l1=lane_pin[3:2];
    always @(posedge ck) begin
        if (!tn) begin r_q <= 514'd0; r_qv <= 1'b0; r_bad <= 1'b0; end
        else begin
`ifdef OT_VM_WFC_MUT_PAIR
            r_q <= {e0, e0 ? lane256(ed_pin, l0) : 256'd0, e1, e1 ? lane256(ed_pin, l1) : 256'd0};
`else
            r_q <= {e1, e1 ? lane256(ed_pin, l1) : 256'd0, e0, e0 ? lane256(ed_pin, l0) : 256'd0};
`endif
`ifdef OT_VM_WFC_CTL_MUT_LANE
            if (e1) r_q[512:257] <= lane256(ed_pin, l0);   // MUTANT: second response from the first lane
`endif
            r_qv <= e0 | e1;
            if (ev_pin != ((e0 ? (4'd1 << l0) : 4'd0) | (e1 ? (4'd1 << l1) : 4'd0))) r_bad <= 1'b1;
        end
    end
    `ifdef S81_RETURN256_MUT_TAIL
    localparam integer TAIL_PAD = RESPONSE_PAD + 1;
`else
    localparam integer TAIL_PAD = RESPONSE_PAD + 2;
`endif
    generate if (TAIL_PAD == 0) begin : no_pad
        assign s_d = r_q; assign s_v = r_qv;
    end else begin : fixed_pad
        reg [513:0] pad [0:TAIL_PAD-1]; reg [TAIL_PAD-1:0] padv; integer k;
        always @(posedge ck) begin
            if (!tn) begin for (k=0;k<TAIL_PAD;k=k+1) pad[k]<=514'd0; padv <= '0; end
            else begin pad[0]<=r_q; for(k=1;k<TAIL_PAD;k=k+1) pad[k]<=pad[k-1];
                       padv <= {padv, r_qv}; end
        end
        assign s_d = pad[TAIL_PAD-1]; assign s_v = padv[TAIL_PAD-1];
    end endgenerate
endmodule

// Standalone opt-in candidate: no production parent adoption yet.
// Each slice and diagnostic leaf needs its own phi-minus-R clock delivery.
module dsfd_vm_wfc_return_split256 #(parameter integer RESPONSE_PAD=2)(
 input wire [2:0] ck,rn,input wire[1:0] return_valid,input wire[3:0] return_lane,
 input wire[3:0] e_v,input wire[2047:0] e_d,
 output wire s_v,output wire[1025:0] s_d,output wire r_bad
);
 wire[1:0] sv,rb;wire[513:0] sd0,sd1;wire[1023:0] ed0,ed1;
 genvar lane;
 generate for(lane=0;lane<4;lane=lane+1)begin:deinterleave
  assign ed0[lane*256+:256]=e_d[lane*512+:256];
  `ifdef S81_RETURN256_MUT_HIGH
  assign ed1[lane*256+:256]=e_d[lane*512+:256];
`else
  assign ed1[lane*256+:256]=e_d[lane*512+256+:256];
`endif
 end endgenerate
 dsfd_vm_wfc_return256 #(.RESPONSE_PAD(RESPONSE_PAD)) lo(
 .ck(ck[0]),.rn(rn[0]),.return_valid(return_valid),.return_lane(return_lane),
 .e_v(e_v),.e_d(ed0),.s_v(sv[0]),.s_d(sd0),.r_bad(rb[0]));
 dsfd_vm_wfc_return256 #(.RESPONSE_PAD(RESPONSE_PAD)) hi(
 .ck(ck[1]),.rn(rn[1]),.return_valid(return_valid),.return_lane(return_lane),
 .e_v(e_v),.e_d(ed1),.s_v(sv[1]),.s_d(sd1),.r_bad(rb[1]));
 assign s_v=sv[0];
 assign s_d={sd0[513],sd1[512:257],sd0[512:257],sd0[256],sd1[255:0],sd0[255:0]};
 // All duplicate sticky fault outputs enter actual existing native diagnostic RTL.
 // This adds two diagnostic edges only; no normal data/control stage is changed.
 dsfd_vm_native_valid_diag diag(.ck(ck[2]),.rst_n(rn[2]),.i_v(32'd0),
 .expected_v(18'd0),.release_slot(90'd0),
`ifdef S81_RETURN256_MUT_FAULT_HI
 .i_fault({15'd0,rb[0]}),
`elsif S81_RETURN256_MUT_FAULT_LO
 .i_fault({15'd0,rb[1]}),
`else
 .i_fault({14'd0,rb}),
`endif
 .fault(r_bad));
endmodule
`default_nettype wire

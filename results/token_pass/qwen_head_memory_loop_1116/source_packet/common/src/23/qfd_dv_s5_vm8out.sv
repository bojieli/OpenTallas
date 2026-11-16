`timescale 1ns/1ps
// QW-SLICE2R 10-20: consumer-side capture register of the VM8 leaf group (region r_io).  lp.py lands each leaf answer
// into r_io (ring write beside the leaf on the leaf root, read beside this register on ck_r_io); this register is the
// group's boundary launch flop on the neighbour clock.  In the full slice2 parent it is the SU consumer's own input
// register (the +1 edge belongs to the vehicle only).  No reset: datapath (owner 10-20 09:05).
module qfd_dv_s5_vm8out #(parameter integer W = 1) (input wire ck, input wire [W-1:0] d, output reg [W-1:0] q);
    always @(posedge ck) q <= d;
endmodule

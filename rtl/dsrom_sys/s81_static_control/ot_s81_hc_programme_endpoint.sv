`timescale 1ns/1ps
`default_nettype none
// Additive fixed-clock endpoint for the real stage controller's c2 command.
// Connect hc_* to the serial-domain HC cpin public command/calendar ports and
// serial_done to that cpin's real completion. No engine result is generated.
// Related-clock phase/reset and metadata image are part of the compiled tuple.
// Done return uses the existing actual alternating-register mailbox. For a
// completion pin observed on serial edge S, stream done rises on floor(4*S/3)+3
// under the declared common epoch; this phase-specific age must be compiled.
module ot_s81_hc_programme_endpoint #(parameter string IMAGE="",parameter integer RAW_ROM_CLOCK=0)(
 input wire stream_ck,stream_rst_n,serial_ck,serial_rst_n,rom_ck,
 input wire[84:0]c2,
 output wire[84:0]hc_command,
 output wire[31:0]hc_done_age,hc_ss_age,hc_scalar_age,hc_y_tag,
 output wire[639:0]hc_post_ages,
 input wire[8:0]serial_done,
 output wire[8:0]stream_done,
 output wire fault
);
 ot_s81_hc_programme_source #(.IMAGE(IMAGE),.RAW_ROM_CLOCK(RAW_ROM_CLOCK))u_source(
  .stream_ck(stream_ck),.stream_rst_n(stream_rst_n),.serial_ck(serial_ck),.serial_rst_n(serial_rst_n),
  .rom_ck(rom_ck),.command_v(c2[84]),.command_d(c2[83:0]),.hc_v(hc_command[84]),.hc_d(hc_command[83:0]),
  .hc_done_age(hc_done_age),.hc_ss_age(hc_ss_age),.hc_scalar_age(hc_scalar_age),.hc_y_tag(hc_y_tag),
  .hc_post_ages(hc_post_ages),.fault(fault));
 ot_s81_fixed_mailbox #(.W(8))u_return(
  .s_clk(serial_ck),.s_rst_n(serial_rst_n),.s_v(serial_done[8]),.s_d(serial_done[7:0]),
  .d_clk(stream_ck),.d_rst_n(stream_rst_n),.d_v(stream_done[8]),.d_d(stream_done[7:0]));
endmodule
`default_nettype wire

`timescale 1ns/1ps
// Existing SECDED64/72 primitive; padding is validated, never ignored.
module ot_dsrom_vm_codec #(parameter integer BITS=64,
 parameter integer WORDS=(BITS+63)/64,CODE_BITS=WORDS*72)(
 input wire [BITS-1:0] raw_in,
 output wire [CODE_BITS-1:0] encoded,
 input wire [CODE_BITS-1:0] coded_in,
 output wire [BITS-1:0] decoded,
 output wire corrected,uncorrectable
);
 import ot_gpu_w6_secded_pkg::*;
 wire [WORDS*64-1:0] padded={{(WORDS*64-BITS){1'b0}},raw_in};
 wire [WORDS*64-1:0] unpacked_data;
 wire [WORDS-1:0] ce,ue;
 for(genvar g=0;g<WORDS;g=g+1)begin:g_word
  wire [65:0] d=decode64(coded_in[g*72+:72]);
  assign encoded[g*72+:72]=encode64(padded[g*64+:64]);
  assign unpacked_data[g*64+:64]=d[63:0];assign ce[g]=d[64];assign ue[g]=d[65];
 end
 assign decoded=unpacked_data[BITS-1:0];assign corrected=|ce;
 if(WORDS*64>BITS)assign uncorrectable=(|ue)||(|unpacked_data[WORDS*64-1:BITS]);
 else assign uncorrectable=|ue;
endmodule

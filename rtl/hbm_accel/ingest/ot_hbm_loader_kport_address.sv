`timescale 1ns/1ps
// Existing ADDR37/STACK2 facade: high2bits stack, low35 local byte.
// Physical K-port s30 is localbyte/32, and PC is the exact controller XOR
// permutation documented and inverted by ot_hbm_kport_map. No region allocation
// occurs here. Capacity must be configured by the owning region inventory.
module ot_hbm_loader_kport_address #(parameter integer ENABLE=0)(
 input wire[36:0] byte_address,input wire[35:0] stack_bytes,
 output wire[1:0] stack,output wire[4:0] pc,
 output wire[29:0] sector_address,output wire valid
);
 wire[29:0] s=byte_address[34:5];
 wire[35:0] end_byte={1'b0,byte_address[34:0]}+36'd32;
 assign stack=ENABLE?byte_address[36:35]:0;
 assign sector_address=ENABLE?s:0;
 assign pc=ENABLE?(s[6:2]^s[11:7]^s[16:12]):0;
 assign valid=ENABLE && byte_address[4:0]==0 && stack_bytes!=0 &&
               stack_bytes<=36'h800000000 && end_byte<=stack_bytes;
endmodule

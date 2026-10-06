`timescale 1ns/1ps
package ot_dsrom_vm_pkg;
 typedef struct packed {
  logic [31:0] ordinal;
  logic [46:0] owner;
  logic [1:0] re;
  logic [29:0] ra;
  logic [4:0] we;
  logic [74:0] wa;
  logic [2559:0] wd;
  logic [79:0] wm;
 } request_t;
 typedef struct packed {
  logic final_receipt;
  logic [31:0] ordinal;
  logic [46:0] owner;
  logic [1:0] re;
  logic [1023:0] data;
  logic [4:0] visible;
  logic [74:0] wa;
  logic [79:0] wm;
  logic corrected;
 } reply_t;
 localparam integer REQ_BITS=$bits(request_t),REP_BITS=$bits(reply_t);
 localparam integer REQ_CODE=((REQ_BITS+63)/64)*72,REP_CODE=((REP_BITS+63)/64)*72;
endpackage

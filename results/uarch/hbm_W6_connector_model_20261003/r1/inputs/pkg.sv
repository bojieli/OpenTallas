`timescale 1ps/1fs
package ot_hbm_r14_pkg;
  // Actual local sector and channel identity; never flatten away channel bits.
  typedef struct packed {
    logic die; logic [1:0] stack; logic [33:0] sector;
    logic [63:0] producer; logic [31:0] transport;
    logic [15:0] caller; logic [5:0] client;
    logic [4:0] irs_slot; logic [31:0] irs_serial;
  } identity_t; //192
  typedef struct packed {identity_t id; logic [5:0] len;
    logic we; logic [255:0] data;} request_t; //455
  typedef struct packed {logic we; logic [33:0] sector;logic [15:0] tag;
    logic [4:0] beat;logic [255:0] data;logic [63:0] arrived;
    logic [31:0] transport;logic [63:0] producer;} queued_t; //472
  typedef struct packed {logic [63:0] due;logic [15:0] tag;logic [4:0] beat;
    logic [255:0] data;logic [33:0] sector;
    logic [31:0] transport;logic [63:0] producer;} returned_t; //471
  typedef struct packed {identity_t id;logic [255:0] data;logic [11:0] physical_tag;
    logic [4:0] beat;} owned_t; //465
  typedef struct packed {logic [2:0] op;logic [4:0] pc,bank;logic [18:0] row;
    logic [33:0] sector;logic [11:0] tag;logic [4:0] beat;logic [255:0] data;} command_t; //339<=344
  localparam logic [2:0] PRE=0,ACT=1,RD=2,WR=3,REF=4,PREALL=5;
  localparam logic [34:0] CAPACITY_SECTORS=35'd703125000;
  function automatic logic [4:0] pc_of(input logic [33:0] s);
    pc_of=((s>>2)^(s>>7)^(s>>12))&31;
  endfunction
  function automatic logic [4:0] bank_of(input logic [33:0] s);
    logic [18:0] row;begin row=s>>15;
      bank_of=((((s>>12)^(row>>2))&7)<<2)|((s^row)&3);end
  endfunction
  function automatic logic [63:0] later(input logic [63:0] a,b);
    later=(a>b)?a:b;
  endfunction
  function automatic logic [31:0] beat_mask(input logic [5:0] n);
    beat_mask=(n==32)?32'hffffffff:((32'b1<<n)-1);
  endfunction
endpackage

`timescale 1ns/1ps
package ot_hgi_attn_pv_stream_pkg;
 typedef struct packed {
  bit scratch_read_v;
  bit [4:0] scratch_read_slot;
  bit load_v;
  bit [3:0] load_tag;
  bit add_read;
  bit [3:0] read_tag;
  bit add_issue;
  bit pub_read;
  bit [3:0] pub_tag;
  bit pub_issue;
  bit capture;
  bit [4:0] capture_slot;
  bit clear_bank_v,clear_bank;
  bit final_pub;
  bit [6:0] batch;
  bit [1:0] destination;
 } stream_cmd_t;
endpackage

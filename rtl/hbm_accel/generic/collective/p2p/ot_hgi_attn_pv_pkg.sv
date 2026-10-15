`timescale 1ns/1ps
package ot_hgi_attn_pv_pkg;
    typedef struct packed {
        bit lp_we;bit[2:0] lp_tag;bit[255:0] lp_data;
        bit read_add,read_tx,read_rr;bit[2:0] read_add_tag,read_tx_tag,read_rr_tag;
        bit[1:0] read_add_src;bit read_rhs_acc,read_tx_acc;
        bit add_v;bit[2:0] add_tag;bit[1:0] add_src;bit rhs_acc;
        bit[1:0] inject,fwd;bit[2:0] tx_tag;bit[1:0] dst;bit result,acc;
        bit[1:0] rx;bit[3:0] kind,src;bit[5:0] tag;
        bit rr;bit[2:0] rr_tag;
    } ring_cmd_t;
    typedef struct packed {
        bit clear;
        bit [3:0] scratch_read;
        bit scratch_read_v;
        bit load_v,add_read,add_issue,pub_read,pub_issue;
        bit capture;
        bit [3:0] capture_slot;
    } local_cmd_t;
endpackage

`timescale 1ns/1ps
`default_nettype none
// One PMAX8 bank's actual static SRAM shell. The 278-bit aperture retains
// its existing one-edge write staging. Reads use a three-edge memory path:
// macro -> raw capture (both weight slots) -> selected output capture.
// A downstream MAC input register consumes that output on the next edge.
// There are no credits or ready-driven scheduling decisions.
module ot_hgi_hc_bank_memory_shared_static #(
    parameter integer MUT_SLOT=0
)(
    input wire clk,rst_n,
    input wire [2:0] expected_bank_id,
    input wire [277:0] weight_ap,
    input wire x_write_v,
    input wire [9:0] x_write_word,
    input wire [511:0] x_write_data,
    input wire w_read_v,x_read_v,read_slot,
    input wire [6:0] w_read_row,
    input wire [9:0] x_read_word,
    output reg write_done,read_valid,fault,
    output reg [1023:0] weight_data,
    output reg [511:0] residual_data
);
    reg [277:0] ap_q;
    // Parent straps this identity for the instance lifetime, before reset release.
    // Three explicit pin capture FFs; no load/ready/configuration handshake.
    reg [2:0] expected_id_q;
    reg ap_valid;
    reg slot_q,slot_qq;
    reg read_v_q,read_v_qq;
    wire [2047:0] weight_raw;
    wire [511:0] residual_raw;
    reg [2047:0] weight_capture;
    reg [511:0] residual_capture;
    always @(posedge clk)begin
        expected_id_q<=expected_bank_id;
        ap_q<=weight_ap;
        slot_q<=read_slot;slot_qq<=slot_q;
        weight_capture<=weight_raw;residual_capture<=residual_raw;
        weight_data<=(slot_qq ^ (MUT_SLOT!=0))?weight_capture[1024+:1024]:weight_capture[0+:1024];
        residual_data<=residual_capture;
    end
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin ap_valid<=0;write_done<=0;read_v_q<=0;read_v_qq<=0;read_valid<=0;fault<=0;end
        else begin
            ap_valid<=weight_ap[277];write_done<=ap_valid;
            read_v_q<=w_read_v|x_read_v;read_v_qq<=read_v_q;read_valid<=read_v_qq;
            if(ap_valid&&ap_q[273+:3]!=expected_id_q)fault<=1;
            if(ap_valid&&w_read_v&&ap_q[276]==read_slot&&ap_q[266+:7]==w_read_row)fault<=1;
            if(x_write_v&&x_write_word>=640)fault<=1;
            if(x_write_v&&x_read_v&&x_write_word==x_read_word)fault<=1;
        end
    end
    for(genvar s=0;s<2;s=s+1)begin:slot
        for(genvar q=0;q<4;q=q+1)begin:quarter
            wire [255:0] mask;
            for(genvar w=0;w<8;w=w+1)begin:word
                assign mask[w*32+:32]={32{ap_q[w]}};
            end
            ot_sram_1r1w_128x256_m1_r2c2 u_weight(
                .clk(clk),.r_ce_in(w_read_v&&read_slot==1'(s)),
                .r_addr_in(w_read_row),.rd_out(weight_raw[(s*4+q)*256+:256]),
                .w_ce_in(ap_valid&&ap_q[276]==1'(s)&&ap_q[273+:3]==expected_id_q&&ap_q[264+:2]==2'(q)),
                .w_addr_in(ap_q[266+:7]),.wd_in(ap_q[8+:256]),.w_mask_in(mask),
                .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
        end
        ot_sram_1r1w_1024x256_m2_r2c2 u_residual(
            .clk(clk),.r_ce_in(x_read_v),.r_addr_in(x_read_word),.rd_out(residual_raw[s*256+:256]),
            .w_ce_in(x_write_v),.w_addr_in(x_write_word),.wd_in(x_write_data[s*256+:256]),.w_mask_in({256{1'b1}}),
            .rr_en(2'd0),.rr_addr(18'd0),.cr_en(2'd0),.cr_sel(16'd0));
    end
endmodule
`default_nettype wire

`timescale 1ns/1ps
// Four physical 512-bit VM banks, one 1R1W port per bank. Logical word
// address low bits select the bank; the remaining bits select one of 16
// depth groups and one of 512 rows. Four consecutive logical words are read
// every cycle and returned in physical bank order, with base mod 4 as a tag.
// Full DEPTH_GROUPS=16 is 2 MiB. Smaller values are simulation slices only.
module ot_v41_vm_bank4_macro #(
    parameter integer DEPTH_GROUPS = 16,
    parameter integer AW = 15
) (
    input  wire clk,
    input  wire rst_n,
    input  wire rd_v,
    input  wire [AW-1:0] rd_base_word,
    output reg  rd_out_v,
    output reg  [1:0] rd_out_rot,
    output reg  [2047:0] rd_out_bank_words,
    output wire rd_fault,
    input  wire [3:0] wr_v,
    input  wire [4*AW-1:0] wr_word_addr,
    input  wire [2047:0] wr_word_data,
    output wire wr_fault,
    output wire rw_collision_fault
);
    localparam integer CAP_WORDS = 4 * DEPTH_GROUPS * 512;
    wire [3:0] bad_read, bad_write, colliding;
    wire [511:0] bank_read [0:3];
    reg [3:0] read_v_q;
    reg [1:0] rot_q;

    genvar b,g,c;
    generate for (b=0; b<4; b=b+1) begin : g_bank
        localparam [1:0] BANK = b[1:0];
        wire [1:0] delta = BANK - rd_base_word[1:0];
        wire [AW:0] read_word = {1'b0,rd_base_word} + {{(AW-1){1'b0}},delta};
        wire [AW-1:0] write_word = wr_word_addr[b*AW +: AW];
        wire [3:0] read_group = read_word[AW-1:11];
        wire [3:0] write_group = write_word[AW-1:11];
        wire [8:0] read_row = read_word[10:2];
        wire [8:0] write_row = write_word[10:2];
        wire [511:0] group_data [0:DEPTH_GROUPS-1];
        reg [3:0] read_group_q;

        assign bad_read[b] = rd_v && (read_word >= CAP_WORDS);
        assign bad_write[b] = wr_v[b] &&
            ((write_word >= CAP_WORDS) || (write_word[1:0] != BANK));
        assign colliding[b] = rd_v && wr_v[b] && !bad_read[b] &&
            !bad_write[b] && (read_word[AW-1:0] == write_word);
        always @(posedge clk) begin
            if (!rst_n) read_group_q <= 0;
            else if (rd_v && !bad_read[b]) read_group_q <= read_group;
        end
        assign bank_read[b] = group_data[read_group_q];

        for (g=0; g<DEPTH_GROUPS; g=g+1) begin : g_group
            for (c=0; c<4; c=c+1) begin : g_col
                ot_sram_1r1w_512x128_m4_r2c2 u_sram (
                    .clk(clk),
                    .r_ce_in(rd_v && !bad_read[b] && read_group == g),
                    .r_addr_in(read_row),
                    .rd_out(group_data[g][c*128 +: 128]),
                    .w_ce_in(wr_v[b] && !bad_write[b] && write_group == g),
                    .w_addr_in(write_row),
                    .wd_in(wr_word_data[b*512+c*128 +: 128]),
                    .w_mask_in({128{1'b1}}),
                    .rr_en(2'b0), .rr_addr(14'b0),
                    .cr_en(2'b0), .cr_sel(14'b0)
                );
            end
        end
    end endgenerate

    assign rd_fault = |bad_read;
    assign wr_fault = |bad_write;
    assign rw_collision_fault = |colliding;

    // One macro read edge, then one bank-local register edge. The 16:1
    // depth-group selector is between those edges, not on the converter path.
    always @(posedge clk) begin
        if (!rst_n) begin
            read_v_q <= 0;
            rot_q <= 0;
            rd_out_v <= 0;
            rd_out_rot <= 0;
            rd_out_bank_words <= 0;
        end else begin
            read_v_q <= {4{rd_v && !rd_fault}};
            rot_q <= rd_base_word[1:0];
            rd_out_v <= &read_v_q;
            rd_out_rot <= rot_q;
            for (integer i=0;i<4;i=i+1)
                rd_out_bank_words[i*512 +: 512] <= bank_read[i];
        end
    end
endmodule

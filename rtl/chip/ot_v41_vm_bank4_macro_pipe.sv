`timescale 1ns/1ps
// Registered 4-bank VM service. Each full bank is 16 groups of four 512x128
// 1R1W SRAM macros (2 MiB total). Four logical consecutive words are issued
// together; output is physical-bank order with a rotation tag. This variant
// pipelines command/decode, local macro access and two levels of bank-local
// output reduction. It adds fill latency but retains one beat/cycle issue.
// W2: the bank-local partial ORs are one packed register per bank (Icarus 11
// left a continuous assign over the former unpacked reg array stale when this
// module is instantiated under a parent); logic is unchanged.
module ot_v41_vm_bank4_macro_pipe #(
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
    output reg  rd_fault,
    input  wire [3:0] wr_v,
    input  wire [4*AW-1:0] wr_word_addr,
    input  wire [2047:0] wr_word_data,
    output reg  wr_fault,
    output reg  rw_collision_fault
);
    localparam integer CAP_WORDS = 4 * DEPTH_GROUPS * 512;
    reg [3:0] rd_cmd_v_q,wr_cmd_v_q;
    reg [1:0] rot_cmd_q,rot_mem_q,rot_mask_q,rot_part_q;
    reg [3:0] valid_mem_q,valid_mask_q,valid_part_q;
    wire [3:0] rd_bad,wr_bad,rw_collide;
    wire [511:0] bank_word [0:3];

    genvar b,g,c,s,p;
    generate for (b=0;b<4;b=b+1) begin : g_bank
        localparam [1:0] BANK = b[1:0];
        wire [1:0] delta = BANK - rd_base_word[1:0];
        wire [AW:0] rd_word = {1'b0,rd_base_word} + {{(AW-1){1'b0}},delta};
        wire [AW-1:0] wr_word = wr_word_addr[b*AW +: AW];
        reg [3:0] rd_group_cmd_q,wr_group_cmd_q;
        reg [8:0] rd_row_cmd_q,wr_row_cmd_q;
        reg [511:0] wr_data_cmd_q;
        wire [511:0] masked_word [0:15];
        reg [2047:0] partial_f;

        assign rd_bad[b] = rd_v && (rd_word >= CAP_WORDS);
        assign wr_bad[b] = wr_v[b] &&
            ((wr_word >= CAP_WORDS) || (wr_word[1:0] != BANK));
        assign rw_collide[b] = rd_v && wr_v[b] && !rd_bad[b] &&
            !wr_bad[b] && (rd_word[AW-1:0] == wr_word);

        always @(posedge clk) begin
            if (!rst_n) begin
                rd_group_cmd_q <= 0;
                wr_group_cmd_q <= 0;
                rd_row_cmd_q <= 0;
                wr_row_cmd_q <= 0;
                wr_data_cmd_q <= 0;
            end else begin
                rd_group_cmd_q <= rd_word[AW-1:11];
                rd_row_cmd_q <= rd_word[10:2];
                wr_group_cmd_q <= wr_word[AW-1:11];
                wr_row_cmd_q <= wr_word[10:2];
                wr_data_cmd_q <= wr_word_data[b*512 +: 512];
            end
        end

        for (g=0;g<16;g=g+1) begin : g_group
            if (g<DEPTH_GROUPS) begin : g_live
                reg [511:0] wr_data_local_q;
                reg [8:0] wr_row_local_q;
                reg wr_enable_local_q;
                wire [511:0] macro_word;
                reg [511:0] mask_q;
                // Unique 16-bit-local selector flops prevent a single
                // cross-cluster 512-bit enable after logic sharing.
                for (s=0;s<32;s=s+1) begin : g_segment
                    wire salt_now = rd_row_cmd_q[s%9] ^ rd_group_cmd_q[s/9];
                    reg salt_q,sel_code_q;
                    always @(posedge clk) begin
                        salt_q <= salt_now;
                        sel_code_q <= (rd_group_cmd_q == g) ^ salt_now;
                        mask_q[s*16 +:16] <=
                            {16{sel_code_q ^ salt_q}} & macro_word[s*16 +:16];
                    end
                end
                always @(posedge clk) begin
                    if (!rst_n) begin
                        wr_data_local_q <= 0;
                        wr_row_local_q <= 0;
                        wr_enable_local_q <= 0;
                    end else begin
                        wr_enable_local_q <= wr_cmd_v_q[b] &&
                            (wr_group_cmd_q == g);
                        if (wr_cmd_v_q[b] && wr_group_cmd_q == g) begin
                            wr_data_local_q <= wr_data_cmd_q;
                            wr_row_local_q <= wr_row_cmd_q;
                        end
                    end
                end
                for (c=0;c<4;c=c+1) begin : g_col
                    ot_sram_1r1w_512x128_m4_r2c2 u_sram (
                        .clk(clk),
                        .r_ce_in(rd_cmd_v_q[b] && rd_group_cmd_q == g),
                        .r_addr_in(rd_row_cmd_q),
                        .rd_out(macro_word[c*128 +:128]),
                        .w_ce_in(wr_enable_local_q),
                        .w_addr_in(wr_row_local_q),
                        .wd_in(wr_data_local_q[c*128 +:128]),
                        .w_mask_in({128{1'b1}}),
                        .rr_en(2'b0),.rr_addr(14'b0),
                        .cr_en(2'b0),.cr_sel(14'b0)
                    );
                end
                assign masked_word[g] = mask_q;
            end else begin : g_empty
                assign masked_word[g] = 512'b0;
            end
        end
        for (p=0;p<4;p=p+1) begin : g_partial
            always @(posedge clk)
                partial_f[p*512 +: 512] <= masked_word[4*p] | masked_word[4*p+1] |
                                masked_word[4*p+2] | masked_word[4*p+3];
        end
        assign bank_word[b] = partial_f[0 +: 512] | partial_f[512 +: 512] |
                              partial_f[1024 +: 512] | partial_f[1536 +: 512];
    end endgenerate

    always @(posedge clk) begin
        if (!rst_n) begin
            rd_cmd_v_q <= 0;
            wr_cmd_v_q <= 0;
            rot_cmd_q <= 0;
            rot_mem_q <= 0;
            rot_mask_q <= 0;
            rot_part_q <= 0;
            valid_mem_q <= 0;
            valid_mask_q <= 0;
            valid_part_q <= 0;
            rd_out_v <= 0;
            rd_out_rot <= 0;
            rd_out_bank_words <= 0;
            rd_fault <= 0;
            wr_fault <= 0;
            rw_collision_fault <= 0;
        end else begin
            rd_cmd_v_q <= {4{rd_v && !(|rd_bad)}};
            wr_cmd_v_q <= wr_v & ~wr_bad;
            rd_fault <= |rd_bad;
            wr_fault <= |wr_bad;
            rw_collision_fault <= |rw_collide;
            rot_cmd_q <= rd_base_word[1:0];
            valid_mem_q <= rd_cmd_v_q;
            rot_mem_q <= rot_cmd_q;
            valid_mask_q <= valid_mem_q;
            rot_mask_q <= rot_mem_q;
            valid_part_q <= valid_mask_q;
            rot_part_q <= rot_mask_q;
            rd_out_v <= &valid_part_q;
            rd_out_rot <= rot_part_q;
            for (integer i=0;i<4;i=i+1)
                rd_out_bank_words[i*512 +:512] <= bank_word[i];
        end
    end
endmodule

`timescale 1ns/1ps
// Additive opt-in raw macro backend. Original module is unchanged/default.
// Caller reserves finite response seats before accepted commands; this module
// has pulse outputs and is NOT a consumer-credit or protected-publication unit.
// No reset is admitted with owned read/write/visibility debt. A reset does not
// roll back already visible SRAM writes or certify old-epoch retirement.
module ot_v41_vm_bank4_macro_pipe_masked_visible_r2 #(
    parameter integer MASKED_VISIBLE = 0,
    parameter integer DEPTH_GROUPS = 16,
    parameter integer AW = 15,
    parameter integer TAG_W = 227
)(
    input wire clk, rst_n,
    input wire rd_v,
    input wire [AW-1:0] rd_base_word,
    input wire [TAG_W-1:0] rd_owner,
    output wire rd_accept_v, rd_out_v,
    output wire [1:0] rd_out_rot,
    output wire [2047:0] rd_out_bank_words,
    output wire [TAG_W-1:0] rd_out_owner,
    output wire rd_fault,
    input wire [3:0] wr_v,
    input wire [4*AW-1:0] wr_word_addr,
    input wire [2047:0] wr_word_data,
    input wire [63:0] wr_lane_mask,
    input wire [4*TAG_W-1:0] wr_owner,
    output wire [3:0] wr_accept_v, wr_ack_v,
    output wire [4*TAG_W-1:0] wr_ack_owner,
    output wire [59:0] wr_ack_word_addr,
    output wire [63:0] wr_ack_lane_mask,
    output wire wr_fault, rw_collision_fault
);
    generate if (MASKED_VISIBLE == 0) begin : g_original
        ot_v41_vm_bank4_macro_pipe #(.DEPTH_GROUPS(DEPTH_GROUPS),.AW(AW)) u_original (
            .clk(clk),.rst_n(rst_n),.rd_v(rd_v),.rd_base_word(rd_base_word),
            .rd_out_v(rd_out_v),.rd_out_rot(rd_out_rot),.rd_out_bank_words(rd_out_bank_words),
            .rd_fault(rd_fault),.wr_v(wr_v),.wr_word_addr(wr_word_addr),.wr_word_data(wr_word_data),
            .wr_fault(wr_fault),.rw_collision_fault(rw_collision_fault));
        // New owner/event interface is disabled with the opt-in off.
        assign wr_accept_v=0; assign rd_accept_v=0; assign rd_out_owner=0;
        assign wr_ack_v=0; assign wr_ack_owner=0;
        assign wr_ack_word_addr=0; assign wr_ack_lane_mask=0;
    end else begin : g_masked
        ot_v41_vm_bank4_macro_pipe_masked_visible_r2_impl #(
            .DEPTH_GROUPS(DEPTH_GROUPS),.AW(AW),.TAG_W(TAG_W)) u_native (.*);
    end endgenerate
endmodule

`timescale 1ns/1ps
// Registered 4-bank VM service. Each full bank is 16 groups of four 512x128
// 1R1W SRAM macros (2 MiB total). Four logical consecutive words are issued
// together; output is physical-bank order with a rotation tag. This variant
// pipelines command/decode, local macro access and two levels of bank-local
// output reduction. It adds fill latency but retains one beat/cycle issue.
module ot_v41_vm_bank4_macro_pipe_masked_visible_r2_impl #(
    parameter integer DEPTH_GROUPS = 16,
    parameter integer AW = 15,
    parameter integer TAG_W = 227
) (
    input  wire clk,
    input  wire rst_n,
    input  wire [63:0] wr_lane_mask,
    input  wire [4*TAG_W-1:0] wr_owner,
    input  wire [TAG_W-1:0] rd_owner,
    output wire [3:0] wr_accept_v,
    output wire rd_accept_v,
    output reg [3:0] wr_ack_v,
    output reg [4*TAG_W-1:0] wr_ack_owner,
    output reg [59:0] wr_ack_word_addr,
    output reg [63:0] wr_ack_lane_mask,
    output wire [TAG_W-1:0] rd_out_owner,
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

    // The existing macro writes at command edge+2. These tags are registered
    // again at edge+3, after that write was visible after the preceding NBA.
    // This is a raw visibility event; protected publication is external.
    reg [3:0] ack_valid_q [0:2];
    reg [4*TAG_W-1:0] ack_owner_q [0:2];
    reg [59:0] ack_addr_q [0:2];
    reg [63:0] ack_mask_q [0:2];
    reg [TAG_W-1:0] read_owner_q [0:4];
    assign wr_accept_v = {4{rst_n}} & wr_v & ~wr_bad;
    assign rd_accept_v = rst_n && rd_v && !(|rd_bad);
    assign rd_out_owner = read_owner_q[4];
    initial begin
        if (DEPTH_GROUPS != 16 || AW != 15 || TAG_W < 217)
            $error("Full2MiB native VM and full owner context required");
    end
    always @(posedge clk) begin
        if (!rst_n) begin
            wr_ack_v <= 0; wr_ack_owner <= 0;
            wr_ack_word_addr <= 0; wr_ack_lane_mask <= 0;
            for (integer j=0;j<3;j=j+1) begin
                ack_valid_q[j] <= 0; ack_owner_q[j] <= 0;
                ack_addr_q[j] <= 0; ack_mask_q[j] <= 0;
            end
            for (integer j=0;j<5;j=j+1) read_owner_q[j] <= 0;
        end else begin
            ack_valid_q[0] <= wr_accept_v;
            ack_owner_q[0] <= wr_owner;
            ack_addr_q[0] <= wr_word_addr;
            ack_mask_q[0] <= wr_lane_mask;
            for (integer j=1;j<3;j=j+1) begin
                ack_valid_q[j] <= ack_valid_q[j-1];
                ack_owner_q[j] <= ack_owner_q[j-1];
                ack_addr_q[j] <= ack_addr_q[j-1];
                ack_mask_q[j] <= ack_mask_q[j-1];
            end
            wr_ack_v <= ack_valid_q[2];
            wr_ack_owner <= ack_owner_q[2];
            wr_ack_word_addr <= ack_addr_q[2];
            wr_ack_lane_mask <= ack_mask_q[2];
            read_owner_q[0] <= rd_owner;
            for (integer j=1;j<5;j=j+1) read_owner_q[j] <= read_owner_q[j-1];
        end
    end
    genvar b,g,c,s,p;
    generate for (b=0;b<4;b=b+1) begin : g_bank
        localparam [1:0] BANK = b[1:0];
        wire [1:0] delta = BANK - rd_base_word[1:0];
        wire [AW:0] rd_word = {1'b0,rd_base_word} + {{(AW-1){1'b0}},delta};
        wire [AW-1:0] wr_word = wr_word_addr[b*AW +: AW];
        reg [3:0] rd_group_cmd_q,wr_group_cmd_q;
        reg [8:0] rd_row_cmd_q,wr_row_cmd_q;
        reg [511:0] wr_data_cmd_q;
        reg [15:0] wr_mask_cmd_q;
        wire [511:0] masked_word [0:15];
        reg [511:0] partial_q [0:3];

        assign rd_bad[b] = rd_v && (rd_word >= CAP_WORDS);
        assign wr_bad[b] = wr_v[b] &&
            ((wr_word >= CAP_WORDS) || (wr_word[1:0] != BANK) ||
             (wr_lane_mask[b*16 +:16] == 16'b0));
        assign rw_collide[b] = rd_v && wr_v[b] && !rd_bad[b] &&
            !wr_bad[b] && (rd_word[AW-1:0] == wr_word);

        always @(posedge clk) begin
            if (!rst_n) begin
                rd_group_cmd_q <= 0;
                wr_group_cmd_q <= 0;
                rd_row_cmd_q <= 0;
                wr_row_cmd_q <= 0;
                wr_data_cmd_q <= 0;
                wr_mask_cmd_q <= 0;
            end else begin
                rd_group_cmd_q <= rd_word[AW-1:11];
                rd_row_cmd_q <= rd_word[10:2];
                wr_group_cmd_q <= wr_word[AW-1:11];
                wr_row_cmd_q <= wr_word[10:2];
                wr_data_cmd_q <= wr_word_data[b*512 +: 512];
                wr_mask_cmd_q <= wr_lane_mask[b*16 +:16];
            end
        end

        for (g=0;g<16;g=g+1) begin : g_group
            if (g<DEPTH_GROUPS) begin : g_live
                reg [511:0] wr_data_local_q;
                reg [15:0] wr_mask_local_q;
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
                        wr_mask_local_q <= 0;
                        wr_row_local_q <= 0;
                        wr_enable_local_q <= 0;
                    end else begin
                        wr_enable_local_q <= wr_cmd_v_q[b] &&
                            (wr_group_cmd_q == g);
                        if (wr_cmd_v_q[b] && wr_group_cmd_q == g) begin
                            wr_data_local_q <= wr_data_cmd_q;
                            wr_mask_local_q <= wr_mask_cmd_q;
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
                        .w_mask_in({{32{wr_mask_local_q[4*c+3]}},
                                    {32{wr_mask_local_q[4*c+2]}},
                                    {32{wr_mask_local_q[4*c+1]}},
                                    {32{wr_mask_local_q[4*c]}}}),
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
                partial_q[p] <= masked_word[4*p] | masked_word[4*p+1] |
                                masked_word[4*p+2] | masked_word[4*p+3];
        end
        assign bank_word[b] = partial_q[0] | partial_q[1] |
                              partial_q[2] | partial_q[3];
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
            rd_cmd_v_q <= {4{rd_accept_v}};
            wr_cmd_v_q <= wr_accept_v;
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

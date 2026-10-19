`timescale 1ns/1ps
`default_nettype none
// Opt-in native XC descriptor/control tile. Model committed before this source.
// clk is the explicit descriptor root. Crossings use normal single-edge STA.
module ot_hbm_xcal_desc_native #(parameter integer MUT=0, PAW=11, DD=256, DAW=8)(
 input wire clk,rst_n,
 input wire cfg_we, input wire [PAW-1:0] cfg_addr,input wire [255:0] cfg_data,
 input wire desc_we,input wire [DAW-1:0] desc_addr,input wire [255:0] desc_data,
 input wire run_v,input wire [DAW-1:0] run_base,input wire [DAW:0] run_count,
 input wire prog_done,prog_fault,
 output reg cfg_we_o,output reg [PAW-1:0] cfg_addr_o,output reg [255:0] cfg_data_o,
 output reg start_v_o,output reg [PAW-1:0] start_base_o,output reg [PAW:0] start_limit_o,
 output reg [15:0] start_loops_o,output reg [4:0] start_ctx_o,
 output reg active,done,fault
);
 (* keep = 1 *) reg [1:0] reset_landing;
 always @(posedge clk or negedge rst_n)
   if(!rst_n) reset_landing<=0; else reset_landing<={reset_landing[0],1'b1};
 wire rst_q=reset_landing[1] && (MUT!=3);
 reg prog_done_q,prog_fault_q,outstanding;
 always @(posedge clk or negedge rst_q)
   if(!rst_q)begin prog_done_q<=0;prog_fault_q<=0;end
   else begin prog_done_q<=prog_done;prog_fault_q<=prog_fault;end
    // Local descriptor SRAM input capture.
    // ---------------- pin flops
    reg desc_we_q, run_q;
    reg [DAW-1:0] desc_addr_q, run_base_q;
    reg [255:0] desc_data_q;
    reg [DAW:0] run_count_q;
    always @(posedge clk) begin desc_addr_q <= desc_addr; desc_data_q <= desc_data; run_base_q <= run_base; run_count_q <= run_count; end
    always @(posedge clk or negedge rst_q)
        if (!rst_q) begin desc_we_q <= 1'b0; run_q <= 1'b0; end
        else begin desc_we_q <= desc_we; run_q <= run_v; end
    // ---------------- go table (copy of the svg issuer's descriptor table)
    reg running, rd_q, ent_v;
    reg [DAW-1:0] rp, rp_q;
    reg [DAW:0] n_rd, n_go;
    reg [23:0] rc;
    reg [23:0] e_at; reg [PAW-1:0] e_base; reg [PAW:0] e_limit; reg [15:0] e_loops; reg [4:0] e_ctx;   // {mode3, mrel, fl}
    wire [255:0] rd;
    wire rd_go = running && n_rd != 0 && !ent_v && !rd_q;
    generate if (DD == 128) begin : g_t1
        ot_sram_1r1w_128x256_m1_r2c2 u_tab (.clk(clk), .r_ce_in(rd_go), .r_addr_in(rp[6:0]), .rd_out(rd),
            .w_ce_in(desc_we_q && !running), .w_addr_in(desc_addr_q[6:0]), .wd_in(desc_data_q), .w_mask_in({256{1'b1}}),
            .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
    end else begin : g_t2
        wire [255:0] rd_lo, rd_hi;
        ot_sram_1r1w_128x256_m1_r2c2 u_tab_lo (.clk(clk), .r_ce_in(rd_go && !rp[7]), .r_addr_in(rp[6:0]), .rd_out(rd_lo),
            .w_ce_in(desc_we_q && !running && !desc_addr_q[7]), .w_addr_in(desc_addr_q[6:0]), .wd_in(desc_data_q),
            .w_mask_in({256{1'b1}}), .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
        ot_sram_1r1w_128x256_m1_r2c2 u_tab_hi (.clk(clk), .r_ce_in(rd_go && rp[7]), .r_addr_in(rp[6:0]), .rd_out(rd_hi),
            .w_ce_in(desc_we_q && !running && desc_addr_q[7]), .w_addr_in(desc_addr_q[6:0]), .wd_in(desc_data_q),
            .w_mask_in({256{1'b1}}), .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
        assign rd = rp_q[7] ? rd_hi : rd_lo;
    end endgenerate
    // Sender capture plus receiver native capture costs exactly two extra edges.
    // Refuse unpayable lead; never fall back to a late GO.
    wire go = ent_v && e_at>=2 && rc == e_at-2;
    always @(posedge clk) begin
      cfg_addr_o<=cfg_addr; cfg_data_o<=cfg_data;
      start_base_o<=e_base;start_limit_o<=e_limit;start_loops_o<=e_loops;start_ctx_o<=e_ctx;
    end
    always @(posedge clk or negedge rst_q)
      if(!rst_q)begin cfg_we_o<=0;start_v_o<=0;end
      else begin cfg_we_o<=cfg_we;start_v_o<=go;end
    always @(posedge clk or negedge rst_q) begin
        if (!rst_q) begin
            running <= 1'b0; rd_q <= 1'b0; ent_v <= 1'b0; rp <= 0; rp_q <= 0; n_rd <= 0; n_go <= 0;
            rc <= 24'd0; e_at <= 24'd0; e_base <= 0; e_limit <= 0; e_loops <= 16'd0; e_ctx <= 5'd0;
            active <= 1'b0; done <= 1'b0; fault <= 1'b0; outstanding <= 1'b0;
        end else begin
            done <= 1'b0;
            active <= running || outstanding;
            if (run_q) begin
                if (running || run_count_q == 0 || {1'b0, run_base_q} + run_count_q > DD) fault <= 1'b1;
                else begin
                    running <= 1'b1; outstanding <= 1'b1; rp <= run_base_q; n_rd <= run_count_q; n_go <= run_count_q;
                    rc <= (MUT == 1) ? 24'd0 : 24'd1;
                end
            end else if (running) rc <= rc + 24'd1;
            rd_q <= rd_go; rp_q <= rp;
            if (rd_go) begin rp <= rp + 1'b1; n_rd <= n_rd - 1'b1; end
            if (rd_q) begin
                ent_v <= 1'b1;
                e_at <= rd[142:119]; e_base <= PAW'({rd[189], rd[91:82]}); e_limit <= (PAW+1)'({rd[190], rd[102:92]}); e_loops <= rd[118:103];
                e_ctx <= {rd[197:195], rd[198], rd[199]};
                if (rd[255:240] != 16'h5d15 || rd[232 +: DAW] != rp_q || (DAW == 7 && rd[239]) || rd[231:200] != 0) fault <= 1'b1;
            end
            if (go) begin
                ent_v <= 1'b0; n_go <= n_go - 1'b1;
                if (n_go == 1) running <= 1'b0;
            end
            if (ent_v && (e_at < 2 || rc > e_at-2)) fault <= 1'b1;            // missed compiler slot: never a late start
            if (prog_fault_q) fault <= 1'b1;
            if (prog_done_q && !running) begin done <= 1'b1; outstanding <= 1'b0; end          // the run's last programme has issued its last word
        end
    end
endmodule
`default_nettype wire

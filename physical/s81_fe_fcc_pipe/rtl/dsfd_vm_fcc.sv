(* keep_hierarchy = "yes" *)
module dsfd_vm_be_kreg #(parameter integer W = 1, parameter integer ID = 0) (input wire clk, input wire [W-1:0] d, output reg [W-1:0] q);
    always @(posedge clk) q <= d;
endmodule

module dsfd_vm_fob #(parameter integer STALE = 0, parameter integer WEV = 1, parameter integer MV = 0,
                     parameter integer DF = 1, parameter integer DX = 0) (
    input  wire clk, input wire rn,
    input  wire i_v, input wire i_we, input wire [13:0] i_row, input wire [15:0] i_m, input wire [511:0] i_d,
    output wire [4*(15 + WEV + 4*MV + 128*DF)-1:0] s_o, output wire [((DX > 0) ? DX : 1)-1:0] x_o, output wire [31:0] k_o
);
    localparam integer SW = 15 + WEV + 4*MV + 128*DF;
    reg b_v, b_we; reg [13:0] b_row; reg [15:0] b_m; reg [511:0] b_d;
    always @(posedge clk) begin
        if (!rn) b_v <= 1'b0; else b_v <= i_v;
        b_we <= i_we; b_row <= i_row; b_m <= i_m; b_d <= i_d;
    end
    wire c_v, c_we; wire [13:0] c_row; wire [15:0] c_m; wire [511:0] c_d;
    generate if (STALE != 0) begin : g_st
        reg s_v6, s_we6; reg [13:0] s_row6; reg [15:0] s_m6; reg [511:0] s_d6;
        always @(posedge clk) begin
            if (!rn) s_v6 <= 1'b0; else s_v6 <= b_v;
            s_we6 <= b_we; s_row6 <= b_row; s_m6 <= b_m; s_d6 <= b_d;
        end
        assign c_v = s_v6; assign c_we = s_we6; assign c_row = s_row6; assign c_m = s_m6; assign c_d = s_d6;
    end else begin : g_ns
        assign c_v = b_v; assign c_we = b_we; assign c_row = b_row; assign c_m = b_m; assign c_d = b_d;
    end endgenerate
    genvar gs;
    generate for (gs = 0; gs < 4; gs = gs + 1) begin : g_s
        wire [SW-1:0] w;
        assign w[SW-1] = rn ? c_v : 1'b0;
        if (WEV != 0) begin : g_we assign w[SW-2] = c_we; end
        assign w[4*MV + 128*DF +: 14] = c_row;
        if (MV != 0) begin : g_m assign w[128*DF +: 4] = c_m[4*gs +: 4]; end
        if (DF != 0) begin : g_d assign w[127:0] = c_d[128*gs +: 128]; end
        dsfd_vm_be_kreg #(.W(SW), .ID(600 + gs)) u_s0 (.clk(clk), .d(w), .q(s_o[SW*gs +: SW]));
    end
    if (DX > 0) begin : g_x
        dsfd_vm_be_kreg #(.W(DX), .ID(604)) u_x0 (.clk(clk), .d(c_d[DX-1:0]), .q(x_o));
    end else begin : g_nx
        assign x_o = 1'b0;
    end endgenerate
    (* keep = 1 *) reg k_v; (* keep = 1 *) reg k_we; (* keep = 1 *) reg [13:0] k_row; (* keep = 1 *) reg [15:0] k_m;
    always @(posedge clk) begin
        if (!rn) k_v <= 1'b0; else k_v <= b_v;
        k_we <= b_we; k_row <= b_row; k_m <= b_m;
    end
    assign k_o = {k_v, k_we, k_row, k_m};
endmodule

(* keep_hierarchy = "yes" *)
module dsfd_vm_fcc (
    input  wire [0:0]    ck, input wire rni,
    input  wire [0:0]    cks, input wire [0:0] rss,
    input  wire [0:0]    rst,            
    input  wire [0:0]    vwe, input wire [13:0] vwa, input wire [511:0] vwd,
    input  wire [0:0]    vre, input wire [13:0] vra,
    output wire [1151:0] s_o,            
    output wire [63:0]   k_o,
    output wire          so_o,
    output reg  [1:0]    rn_o
);
    localparam integer CCA = 1;
    wire clk = ck[0];
    reg rn; wire rns;
    (* keep = 1 *) reg [1:0] rn_k;
    always @(posedge clk) begin rn <= rni; rn_k <= {2{rn}}; end
    always @* rn_o = rn_k;
    ot_dsrom_mtp_rstsync u_rss (.clk(cks[0]), .rst_n_async(rss[0]), .rst_n(rns));
    reg s_we, s_re, s_tg; reg [13:0] s_wa, s_ra; reg [511:0] s_wd;
    always @(posedge cks[0]) begin
        if (!rns) begin s_we <= 1'b0; s_re <= 1'b0; end else begin s_we <= vwe[0]; s_re <= vre[0]; end
        s_wa <= vwa; s_ra <= vra; s_wd <= vwd;
    end
    wire [526:0] s_wo = {1'b1, s_wa, s_wd}, s_ro = {1'b0, s_ra, 512'd0};    
    wire s_f = s_we | s_re;                        
    wire s_s = s_we & s_re;                        
    wire [526:0] s_fd = s_we ? s_wo : s_ro;
    wire [1:0] sw_v = {(s_f && s_tg) || (s_s && !s_tg), (s_f && !s_tg) || (s_s && s_tg)};
    wire [526:0] sw_d0 = (s_f && !s_tg) ? s_fd : s_ro;
    wire [526:0] sw_d1 = (s_f && s_tg) ? s_fd : s_ro;
    always @(posedge cks[0]) if (!rns) s_tg <= 1'b0; else if (s_f && !s_s) s_tg <= ~s_tg;
    wire [1:0] cw_rdy, cr_v, cw_live; wire [526:0] cr_d0, cr_d1; reg [1:0] cr_take; reg s_ovf;
    generate if (CCA != 0) begin : g_cca
        wire x_arn = rst[0] & rss[0];
        wire xw0, xr0; wire [1:0] xr_v;
        ot_reset_sync u_xw (.clk(cks[0]), .async_rst_n(x_arn), .sync_rst_n(xw0));
        ot_reset_sync u_xr (.clk(clk), .async_rst_n(x_arn), .sync_rst_n(xr0));
        (* keep = 1 *) reg [1:0] xw_t; (* keep = 1 *) reg [1:0] xr_t;
        always @(posedge cks[0] or negedge xw0) if (!xw0) xw_t <= 2'b00; else xw_t <= 2'b11;
        always @(posedge clk or negedge xr0) if (!xr0) xr_t <= 2'b00; else xr_t <= 2'b11;
        ot_async_fifo #(.WIDTH(527), .DEPTH(16), .EXT_RST(1)
            , .FIFO_PIPE(1)
            ) u_cc0 (.wr_clk(cks[0]), .wr_rst_n(xw_t[0]), .wr_valid(sw_v[0]),
            .wr_ready(cw_rdy[0]), .wr_data(sw_d0), .wr_overflow(), .rd_clk(clk), .rd_rst_n(xr_t[0]), .rd_valid(xr_v[0]),
            .rd_ready(cr_take[0]), .rd_data(cr_d0), .rd_underflow()
            );
        ot_async_fifo #(.WIDTH(527), .DEPTH(16), .EXT_RST(1)
            , .FIFO_PIPE(1)
            ) u_cc1 (.wr_clk(cks[0]), .wr_rst_n(xw_t[1]), .wr_valid(sw_v[1]),
            .wr_ready(cw_rdy[1]), .wr_data(sw_d1), .wr_overflow(), .rd_clk(clk), .rd_rst_n(xr_t[1]), .rd_valid(xr_v[1]),
            .rd_ready(cr_take[1]), .rd_data(cr_d1), .rd_underflow()
            );
        assign cr_v = rn ? xr_v : 2'b00;         
        assign cw_live = 2'b11;
    end else begin : g_ncca
        ot_ratio_cdc_fifo #(.W(527), .DEPTH(8)) u_cc0 (.wclk(cks[0]), .wrst_n(rns), .w_v(sw_v[0]), .w_rdy(cw_rdy[0]), .w_d(sw_d0),
            .rclk(clk), .rrst_n(rn), .r_v(cr_v[0]), .r_rdy(cr_take[0]), .r_d(cr_d0), .w_live(cw_live[0]), .r_live(
            ));
        ot_ratio_cdc_fifo #(.W(527), .DEPTH(8)) u_cc1 (.wclk(cks[0]), .wrst_n(rns), .w_v(sw_v[1]), .w_rdy(cw_rdy[1]), .w_d(sw_d1),
            .rclk(clk), .rrst_n(rn), .r_v(cr_v[1]), .r_rdy(cr_take[1]), .r_d(cr_d1), .w_live(cw_live[1]), .r_live(
            ));
    end endgenerate
    always @(posedge cks[0]) if (!rns) s_ovf <= 1'b0;
        else if ((sw_v[0] && !cw_rdy[0]) || (sw_v[1] && !cw_rdy[1])) s_ovf <= 1'b1;    
    reg c_nx;                            
    reg ca_v, cb_v; reg [526:0] ca_d, cb_d;
    always @* begin
        cr_take = 2'b00;
        if (cr_v[c_nx]) begin
            cr_take[c_nx] = 1'b1;
            if (cr_v[~c_nx]) cr_take[~c_nx] = 1'b1;
        end
    end
    always @(posedge clk) begin
        if (!rn) c_nx <= 1'b0; else if (cr_take == 2'b01 || cr_take == 2'b10) c_nx <= ~c_nx;
    end
    always @* begin
        ca_v = cr_v[c_nx]; ca_d = c_nx ? cr_d1 : cr_d0;
        cb_v = cr_v[c_nx] && cr_v[~c_nx]; cb_d = c_nx ? cr_d0 : cr_d1;
    end
    reg [1:0] so_s;
    always @(posedge clk) begin so_s <= {so_s[0], s_ovf}; end
    assign so_o = so_s[1];
    wire [575:0] fs0, fs1;
    dsfd_vm_fob u_b3 (
        .clk(clk), .rn(rn), .i_v(ca_v), .i_we(ca_d[526]), .i_row(ca_d[525:512]), .i_m(16'hffff), .i_d(ca_d[511:0]),
        .s_o(fs0), .x_o(), .k_o(k_o[31:0]));
    dsfd_vm_fob u_b4 (.clk(clk), .rn(rn), .i_v(cb_v), .i_we(cb_d[526]), .i_row(cb_d[525:512]), .i_m(16'hffff),
        .i_d(cb_d[511:0]), .s_o(fs1), .x_o(), .k_o(k_o[63:32]));
    genvar gs;
    generate for (gs = 0; gs < 4; gs = gs + 1) begin : g_s
        assign s_o[(2*gs)*144 +: 144] = fs0[144*gs +: 144]; assign s_o[(2*gs + 1)*144 +: 144] = fs1[144*gs +: 144];
    end endgenerate
endmodule

module ot_async_fifo #(
    parameter integer WIDTH = 32,
    parameter integer DEPTH = 4,
    parameter integer EXT_RST = 0
    , parameter integer FIFO_PIPE = 0, parameter integer PIPE_CHUNK = 128
) (
    input  wire             wr_clk,
    input  wire             wr_rst_n,
    input  wire             wr_valid,
    output wire             wr_ready,
    input  wire [WIDTH-1:0] wr_data,
    output reg              wr_overflow,
    input  wire             rd_clk,
    input  wire             rd_rst_n,
    output wire             rd_valid,
    input  wire             rd_ready,
    output wire [WIDTH-1:0] rd_data,
    output reg              rd_underflow
);
    initial begin
        if (DEPTH < 4 || (DEPTH & (DEPTH-1)) != 0)
            $error("ot_async_fifo DEPTH must be a power of two >= 4");
    end
    localparam integer ADDR_W = $clog2(DEPTH);
    localparam integer PTR_W = ADDR_W + 1;
    wire fifo_async_rst_n = wr_rst_n && rd_rst_n;
    wire wr_domain_rst_n;
    wire rd_domain_rst_n;
    generate if (EXT_RST != 0) begin : g_xr
        assign wr_domain_rst_n = wr_rst_n;
        assign rd_domain_rst_n = rd_rst_n;
    end else begin : g_ir
        ot_reset_sync wr_reset_conditioner (
            .clk(wr_clk), .async_rst_n(fifo_async_rst_n),
            .sync_rst_n(wr_domain_rst_n));
        ot_reset_sync rd_reset_conditioner (
            .clk(rd_clk), .async_rst_n(fifo_async_rst_n),
            .sync_rst_n(rd_domain_rst_n));
    end endgenerate
    reg [WIDTH-1:0] mem [0:DEPTH-1];
    wire [PTR_W-1:0] wr_gray_visible;
    reg [PTR_W-1:0] wr_bin, wr_gray;
    reg [PTR_W-1:0] rd_bin, rd_gray;
    (* async_reg = "true" *) reg [PTR_W-1:0] rd_gray_w1, rd_gray_w2;
    (* async_reg = "true" *) reg [PTR_W-1:0] wr_gray_r1, wr_gray_r2;
    reg wr_online, rd_online;
    (* async_reg = "true" *) reg rd_online_w1, rd_online_w2;
    (* async_reg = "true" *) reg wr_online_r1, wr_online_r2;
    reg wr_full, rd_empty;
    wire wr_fire = wr_valid && wr_ready;
    wire rd_fire = rd_valid && rd_ready;
    wire [PTR_W-1:0] wr_increment = {{(PTR_W-1){1'b0}},wr_fire};
    wire [PTR_W-1:0] wr_bin_next = wr_bin + wr_increment;
    wire [PTR_W-1:0] wr_gray_next = (wr_bin_next >> 1) ^ wr_bin_next;
    wire [PTR_W-1:0] rd_increment = {{(PTR_W-1){1'b0}},rd_fire};
    wire [PTR_W-1:0] rd_bin_next = rd_bin + rd_increment;
    wire [PTR_W-1:0] rd_gray_next = (rd_bin_next >> 1) ^ rd_bin_next;
    wire wr_full_next;
    wire rd_empty_next;
    assign wr_full_next = (wr_gray_next ==
                           {~rd_gray_w2[PTR_W-1:PTR_W-2],
                            rd_gray_w2[PTR_W-3:0]});
    assign rd_empty_next = (rd_gray_next == wr_gray_r2);
    assign wr_ready = wr_domain_rst_n && rd_online_w2 && !wr_full;
    assign rd_valid = rd_domain_rst_n && wr_online_r2 && !rd_empty;
    generate if (FIFO_PIPE != 0) begin : g_pipe
        localparam integer NCH = (WIDTH + PIPE_CHUNK - 1) / PIPE_CHUNK;
        reg [WIDTH-1:0] data_q;
        reg [PTR_W-1:0] pub_q;
        wire [DEPTH-1:0] selected [0:NCH-1], read_sel [0:NCH-1];
        wire [DEPTH-1:0] w_sel = {{(DEPTH-1){1'b0}},1'b1} << wr_bin[ADDR_W-1:0];
        wire [DEPTH-1:0] r_sel_next = {{(DEPTH-1){1'b0}},1'b1} << rd_bin_next[ADDR_W-1:0];
        always @(posedge wr_clk) data_q <= wr_data;  
        always @(posedge wr_clk or negedge wr_domain_rst_n)
            if (!wr_domain_rst_n) pub_q <= {PTR_W{1'b0}};
            else pub_q <= wr_gray;  
        assign wr_gray_visible = pub_q;
        for (genvar pc=0;pc<NCH;pc=pc+1) begin : g_c
            localparam integer LO=pc*PIPE_CHUNK;
            localparam integer CW=(WIDTH-LO < PIPE_CHUNK) ? WIDTH-LO : PIPE_CHUNK;
            ot_async_fifo_select_copy #(.W(DEPTH),.ID(pc),.RESET_ONE(0)) u_wsel
              (.clk(wr_clk),.rst_n(wr_domain_rst_n),.d(w_sel & {DEPTH{wr_fire}}),.q(selected[pc]));
            ot_async_fifo_select_copy #(.W(DEPTH),.ID(100+pc),.RESET_ONE(1)) u_rsel
              (.clk(rd_clk),.rst_n(rd_domain_rst_n),.d(r_sel_next),.q(read_sel[pc]));
            always @(posedge wr_clk) begin : p_write integer pe;
                for(pe=0;pe<DEPTH;pe=pe+1)
                    if(selected[pc][pe]) mem[pe][LO+:CW] <= data_q[LO+:CW];
            end
            reg [CW-1:0] row_or;
            always @* begin : p_read integer pe;
                row_or={CW{1'b0}};
                for(pe=0;pe<DEPTH;pe=pe+1)
                    row_or=row_or | (mem[pe][LO+:CW] & {CW{read_sel[pc][pe]}});
            end
            assign rd_data[LO+:CW]=row_or;
        end
    end else begin : g_no_pipe
        assign wr_gray_visible=wr_gray;
        assign rd_data=mem[rd_bin[ADDR_W-1:0]];
        always @(posedge wr_clk) if(wr_domain_rst_n && wr_fire) mem[wr_bin[ADDR_W-1:0]] <= wr_data;
    end endgenerate
    always @(posedge wr_clk or negedge wr_domain_rst_n) begin
        if (!wr_domain_rst_n) begin
            rd_gray_w1 <= {PTR_W{1'b0}};
            rd_gray_w2 <= {PTR_W{1'b0}};
            rd_online_w1 <= 1'b0;
            rd_online_w2 <= 1'b0;
            wr_online <= 1'b0;
            wr_bin <= {PTR_W{1'b0}};
            wr_gray <= {PTR_W{1'b0}};
            wr_full <= 1'b0;
            wr_overflow <= 1'b0;
        end else begin
            wr_online <= 1'b1;
            rd_online_w1 <= rd_online;
            rd_online_w2 <= rd_online_w1;
            rd_gray_w1 <= rd_gray;
            rd_gray_w2 <= rd_gray_w1;
            wr_bin <= wr_bin_next;
            wr_gray <= wr_gray_next;
            wr_full <= wr_full_next;
        end
    end
    always @(posedge rd_clk or negedge rd_domain_rst_n) begin
        if (!rd_domain_rst_n) begin
            wr_gray_r1 <= {PTR_W{1'b0}};
            wr_gray_r2 <= {PTR_W{1'b0}};
            wr_online_r1 <= 1'b0;
            wr_online_r2 <= 1'b0;
            rd_online <= 1'b0;
            rd_bin <= {PTR_W{1'b0}};
            rd_gray <= {PTR_W{1'b0}};
            rd_empty <= 1'b1;
            rd_underflow <= 1'b0;
        end else begin
            rd_online <= 1'b1;
            wr_online_r1 <= wr_online;
            wr_online_r2 <= wr_online_r1;
            wr_gray_r1 <= wr_gray_visible;
            wr_gray_r2 <= wr_gray_r1;
            rd_bin <= rd_bin_next;
            rd_gray <= rd_gray_next;
            rd_empty <= rd_empty_next;
        end
    end
endmodule

(* keep_hierarchy = "yes" *)
module ot_async_fifo_select_copy #(parameter integer W=16,ID=0,RESET_ONE=0)
(input wire clk,rst_n,input wire [W-1:0] d,output reg [W-1:0] q);
    (* keep = 1 *) wire [W-1:0] dq=d;
    always @(posedge clk or negedge rst_n)
        if(!rst_n) q <= RESET_ONE ? {{(W-1){1'b0}},1'b1} : {W{1'b0}};
        else q<=dq;
endmodule

module ot_reset_sync #(
    parameter integer ASYNC_STAGES = 2
) (
    input  wire clk,
    input  wire async_rst_n,
    output wire sync_rst_n
);
    (* async_reg = "true" *) reg [ASYNC_STAGES-1:0] reset_pipe;
    always @(posedge clk or negedge async_rst_n) begin
        if (!async_rst_n)
            reset_pipe <= {ASYNC_STAGES{1'b0}};
        else
            reset_pipe <= {reset_pipe[ASYNC_STAGES-2:0],1'b1};
    end
    assign sync_rst_n = reset_pipe[ASYNC_STAGES-1];
endmodule

module ot_dsrom_mtp_rstsync (input wire clk, input wire rst_n_async, output wire rst_n);
    reg [1:0] s;
    always @(posedge clk or negedge rst_n_async) if (!rst_n_async) s <= 2'b00; else s <= {s[0], 1'b1};
    assign rst_n = s[1];
endmodule

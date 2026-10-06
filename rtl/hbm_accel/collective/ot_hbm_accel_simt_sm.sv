`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hbm_accel_simt_sm: HBM-accelerator successor of rtl/gpu_sys/ot_gpu_simt_sm.sv
// (which stays byte-identical) for HA3, the cut-through collective and the
// fused receive-path epilogue (dataflow levels 2 and 5).
//
// HA3 = 0 (default): identical behaviour to ot_gpu_simt_sm; the added ports
// are driven 0 / ignored and the two added opcodes are illegal (fault).
//
// HA3 = 1 adds two instructions (opcodes outside OTG-1's set):
//   COLLX d, a, b, imm   (0x49) contribute-and-receive collective:
//       imm[7:0] count, imm[15:8] off, imm[23:16] nown, imm[24] mode,
//       imm[25] fuse.  This SM's lanes a[0 .. nown-1] are the collective's
//       lanes off .. off+nown-1 (no store, barrier or reload: the die's
//       collective port takes them straight from the register, and sends each
//       16-lane word as soon as every lane of it has been contributed).
//       Every SM of the die issues the COLLX of a collective (nown may be 0),
//       and every SM receives the whole result into d.  fuse = 1: the port's
//       receive-path epilogue returns d = fl(b + result) lane-wise (b = the
//       residual register, read at the residual's own lanes off..off+nown-1)
//       and latches the golden-order sum of squares of d (R-ARITH chunk 8,
//       pairwise tree over the chunks) for COLLSS.
//   COLLSS d             (0x4A) d = the last fused COLLX's sum of squares,
//       broadcast to every lane (1-cycle ALU op).
//   A response with coll_rsp_err set (epilogue FP fault: nonfinite operand or
//   overflow, the same fail-closed rule as the SM's own FP pipes) faults the SM.
// ---------------------------------------------------------------------------
module ot_hbm_accel_simt_sm #(
    parameter integer ENABLE     = 0,
    parameter integer HA3        = 0,           // 1: COLLX / COLLSS (cut-through collective, fused epilogue)
    parameter integer NL         = 128,
    parameter integer NV         = 256,
    parameter integer IMW        = 13,          // log2 instruction memory words
    parameter integer SMEM_WORDS = 8192,        // 32 KiB
    parameter integer MAXO       = 32,          // LSU outstanding sector requests
    parameter integer TC_SUB     = 4,
    parameter integer TC_LS      = 4,
    parameter integer TC_XDEPTH  = 16,
    parameter integer TC_RMAX    = 1024,
    parameter integer TC_LEV     = 3,
    parameter integer BC_DEPTH   = 64,          // bulk-copy staging lines
    parameter integer BC_MAXOUT  = 32,
    parameter integer FPW        = 32,          // physical FP32 lanes: an NL-lane op issues over NL/FPW cycles
    parameter integer FLAT       = 5,           // FP pipe depth (5: qualified pipes; 7: W11 SS re-pipelined copies)
    parameter integer HAS_DIV    = 0,           // 1: div.rn / sqrt.rn unit (rtl/abi3 correctly-rounded divider and square root per lane)
    parameter integer HAS_BD     = 0,           // 1: block-scaled (MX FP8/FP4) tensor core rtl/gpu/ot_gpu_sm_bd.sv
    parameter integer GU_JOIN    = 0,           // default-off caller-enrolled BF16 retirement export
    parameter integer BD_XDEPTH  = 64
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire [7:0]            sm_id,
    input  wire [7:0]            die_id,
    // instruction memory loader (module load)
    input  wire                  im_we,
    input  wire [IMW-1:0]        im_addr,
    input  wire [63:0]           im_data,
    // kernel launch / completion
    input  wire                  launch_v,
    input  wire [31:0]           launch_pc,
    input  wire [15:0]           launch_token,
    input  wire [15:0]           launch_pos,
    output reg                   sm_done,
    output wire                  sm_fault,
    output reg                   res_v,
    output reg  [31:0]           res_data,
    output wire                  busy,
    // grid barrier
    output wire                  bar_arrive,
    input  wire                  bar_release,
    // LSU memory port (MREQ)
    output wire                  lreq_v,
    input  wire                  lreq_rdy,
    output wire                  lreq_we,
    output wire [31:0]           lreq_addr,
    output wire [255:0]          lreq_wdata,
    output wire [31:0]           lreq_wstrb,
    output wire [15:0]           lreq_tag,
    input  wire                  lrsp_v,
    output wire                  lrsp_rdy,
    input  wire [15:0]           lrsp_tag,
    input  wire                  lrsp_we,
    input  wire [255:0]          lrsp_data,
    // bulk-copy (weight stream) memory port (MREQ, reads only)
    output wire                  treq_v,
    input  wire                  treq_rdy,
    output wire [31:0]           treq_addr,
    output wire [15:0]           treq_tag,
    input  wire                  trsp_v,
    output wire                  trsp_rdy,
    input  wire [15:0]           trsp_tag,
    input  wire [255:0]          trsp_data,
    // collective endpoint
    output wire                  coll_req_v,
    input  wire                  coll_req_rdy,
    output wire                  coll_mode,
    output wire [7:0]            coll_count,
    output wire [NL*32-1:0]      coll_data,
    input  wire                  coll_rsp_v,
    output wire                  coll_rsp_rdy,
    input  wire [NL*32-1:0]      coll_rsp_data,
    // HA3 collective extension (HA3 = 1; 0 otherwise)
    output wire                  coll_x,          // this request is a COLLX contribution
    output wire [7:0]            coll_off,
    output wire [7:0]            coll_nown,
    output wire                  coll_fuse,
    output wire [NL*32-1:0]      coll_resid,
    input  wire [31:0]           coll_rsp_ss,
    input  wire                  coll_rsp_err,
    // One immutable GU span per kernel launch. The caller installs the actual
    // CVTBF16 PC/source and released row descriptor under its existing grant.
    // FRAME is the protected parent's {position20,token17,generation4,job32};
    // retain its upper identity bits even though this SM's launch API is 16/16.
    input  wire                  gu_join_launch,
    input  wire                  gu_join_owner_valid,
    input  wire [31:0]           gu_join_pc,
    input  wire [7:0]            gu_join_src,
    input  wire [8:0]            gu_join_expert,
    input  wire                  gu_join_matrix, // 0=w1/G, 1=w3/U
    input  wire [11:0]           gu_join_row_base,
    input  wire [7:0]            gu_join_lane_first,
    input  wire [8:0]            gu_join_count,
    input  wire [72:0]           gu_join_frame,
    input  wire [31:0]           gu_join_op,
    output wire                  gu_join_v,
    input  wire                  gu_join_accept,
    output wire [NL*16-1:0]      gu_join_bf16,
    output wire [8:0]            gu_join_out_expert,
    output wire                  gu_join_out_matrix,
    output wire [11:0]           gu_join_out_row_base,
    output wire [7:0]            gu_join_out_lane_first,
    output wire [8:0]            gu_join_out_count,
    output wire [72:0]           gu_join_out_frame,
    output wire [31:0]           gu_join_out_op,
    output wire [7:0]            gu_join_out_sm,
    output wire [7:0]            gu_join_out_die,
    output wire                  gu_join_terminal,
    // Warm CP reset is quarantined, never mapped to this module's root rst_n.
    input wire                   gu_join_warm_reset_req,
    output wire                  gu_join_warm_reset_ack,
    output wire                  gu_join_retained,
    output wire                  gu_join_ce,
    output wire                  gu_join_due,
    // statistics
    output reg  [31:0]           st_instr,
    output reg  [31:0]           st_cycles,
    output reg  [31:0]           st_stall_mem,
    output reg  [31:0]           st_tc_rows
);
    /*verilator no_inline_module*/
generate if (ENABLE == 0) begin : g_off
    always @(posedge clk) begin
        sm_done <= 1'b0; res_v <= 1'b0; res_data <= 32'd0;
        st_instr <= 32'd0; st_cycles <= 32'd0; st_stall_mem <= 32'd0; st_tc_rows <= 32'd0;
    end
    assign sm_fault = 1'b0; assign busy = 1'b0; assign bar_arrive = 1'b0;
    assign lreq_v = 1'b0; assign lreq_we = 1'b0; assign lreq_addr = 32'd0; assign lreq_wdata = 256'd0;
    assign lreq_wstrb = 32'd0; assign lreq_tag = 16'd0; assign lrsp_rdy = 1'b0;
    assign treq_v = 1'b0; assign treq_addr = 32'd0; assign treq_tag = 16'd0; assign trsp_rdy = 1'b0;
    assign coll_req_v = 1'b0; assign coll_mode = 1'b0; assign coll_count = 8'd0; assign coll_data = {NL*32{1'b0}};
    assign coll_rsp_rdy = 1'b0;
    assign coll_x = 1'b0; assign coll_off = 8'd0; assign coll_nown = 8'd0; assign coll_fuse = 1'b0;
    assign coll_resid = {NL*32{1'b0}};
    assign gu_join_v = 1'b0; assign gu_join_bf16 = {NL*16{1'b0}};
    assign gu_join_out_expert = 0; assign gu_join_out_matrix = 0;
    assign gu_join_out_row_base = 0; assign gu_join_out_lane_first = 0;
    assign gu_join_out_count = 0; assign gu_join_out_frame = 0;
    assign gu_join_out_op = 0; assign gu_join_out_sm = 0; assign gu_join_out_die = 0;
    assign gu_join_terminal = 1'b0;
    assign gu_join_warm_reset_ack=0;assign gu_join_retained=0;assign gu_join_ce=0;assign gu_join_due=0;
end else begin : g_on
    localparam integer VW  = NL * 32;
    localparam integer RB  = $clog2(NV);
    localparam integer LB  = $clog2(NL);
    localparam integer SWB = $clog2(SMEM_WORDS);
    localparam integer TCL = TC_SUB * TC_LS;
    localparam integer OB  = $clog2(MAXO);
    // opcodes (tools/gpu_sys/isa.py)
    localparam [7:0] O_NOP=8'h00, O_FADD=8'h01, O_FMUL=8'h02, O_XOR=8'h03, O_AND=8'h04, O_OR=8'h05, O_SHR=8'h06,
        O_SHL=8'h07, O_IADD=8'h08, O_ISUB=8'h09, O_UGT=8'h0A, O_ULT=8'h0B, O_FCMPGT=8'h0C, O_F2I=8'h0D,
        O_CVTBF16=8'h0E, O_CVTE4M3=8'h0F, O_FDIV=8'h10, O_FSQRT=8'h11, O_IMUL=8'h12,
        O_MOVI=8'h20, O_LANEID=8'h21, O_MOVU=8'h22, O_SHFL=8'h23,
        O_UMOVI=8'h28, O_UADDI=8'h29, O_UMULI=8'h2A, O_UFROMV=8'h2B, O_UADD=8'h2C,
        O_BRA=8'h30, O_BNZ=8'h31, O_EXIT=8'h32, O_BAR=8'h33, O_MEMBAR=8'h34, O_RESULT=8'h35,
        O_LDG=8'h38, O_STG=8'h39, O_LDS=8'h3A, O_STS=8'h3B, O_LDSX=8'h3C, O_STSX=8'h3D,
        O_TCX=8'h40, O_TCMMA=8'h41, O_TCWAIT=8'h42, O_COLL=8'h48,
        O_FMAX=8'h13, O_FMIN=8'h14, O_IMULHI=8'h15, O_CVTE2M1=8'h16, O_CVTE4M3B=8'h17,
        O_TCXB=8'h43, O_TCBMMA=8'h44, O_TCXE=8'h45,
        O_COLLX=8'h49, O_COLLSS=8'h4A;

    // ------------------------------------------------------------------ element encode/decode (LSU)
    function automatic [7:0] f_e4m3_enc(input [31:0] a);   // on-grid E4M3 value -> byte
        integer e; reg [23:0] sig;
        begin
            e = a[30:23] - 127;
            sig = {1'b1, a[22:0]};
            if (a[30:0] == 0) f_e4m3_enc = 8'd0;
            else if (e >= -6) f_e4m3_enc = {a[31], 4'(e + 7), a[22:20]};
            else f_e4m3_enc = {a[31], 4'd0, 3'(sig >> (14 - e))};
        end
    endfunction
    function automatic [31:0] f_e4m3_dec(input [7:0] c);
        integer p;
        begin
            if (c[6:3] == 0) begin
                if (c[2:0] == 0) f_e4m3_dec = 32'd0;
                else begin
                    p = c[2] ? 2 : (c[1] ? 1 : 0);
                    f_e4m3_dec = {c[7], 8'(127 - 9 + p), 23'(({20'd0, c[2:0]} << (23 - p)) & 23'h7FFFFF)};
                end
            end else f_e4m3_dec = {c[7], 8'(c[6:3] + 120), c[2:0], 20'd0};
        end
    endfunction

    // ------------------------------------------------------------------ architectural state
    reg [63:0]    imem [0:(1 << IMW)-1];
    always @(posedge clk) if (im_we) imem[im_addr] <= im_data;
    reg [VW-1:0]  vr [0:NV-1];
    reg [31:0]    ur [0:15];
    reg [31:0]    smem [0:SMEM_WORDS-1];
    reg [NV-1:0]  pend;
    reg           running, faulted, bar_q;
    reg [IMW-1:0] pc;
    assign sm_fault = faulted || ((GU_JOIN != 0) && gu_meta_due);
    assign bar_arrive = bar_q;

    wire [63:0] ir = imem[pc];
    wire [7:0]  op = ir[63:56];
    wire [7:0]  fd = ir[55:48], fa = ir[47:40], fb = ir[39:32];
    wire [31:0] imm = ir[31:0];
    wire [RB-1:0] rd = fd[RB-1:0], ra = fa[RB-1:0], rbx = fb[RB-1:0];
    wire [VW-1:0] va = vr[ra], vb = vr[rbx], vd = vr[rd];

    // operand classes
    wire c_bin   = (op >= O_FADD && op <= O_ULT) || op == O_FCMPGT || op == O_FDIV || op == O_IMUL ||
                   op == O_FMAX || op == O_FMIN || op == O_IMULHI;
    wire c_un    = op == O_F2I || op == O_CVTBF16 || op == O_CVTE4M3 || op == O_FSQRT || op == O_CVTE2M1 || op == O_CVTE4M3B;
    wire is_cx   = (HA3 != 0) && op == O_COLLX;
    wire is_css  = (HA3 != 0) && op == O_COLLSS;
    wire c_alu   = (c_bin && op != O_FADD && op != O_FMUL && op != O_FDIV) || (c_un && op != O_FSQRT) || op == O_MOVI || op == O_LANEID ||
                   op == O_MOVU || op == O_SHFL || op == O_LDS || op == O_LDSX || is_css;
    wire use_a   = c_bin || c_un || op == O_SHFL || op == O_LDSX || op == O_STSX || op == O_TCX || op == O_COLL ||
                   op == O_TCXB || op == O_TCXE ||
                   op == O_UFROMV || is_cx;
    wire use_b   = c_bin || op == O_SHFL || op == O_TCXB || (is_cx && imm[25]);
    wire use_ds  = op == O_STG || op == O_STS || op == O_STSX;            // d is a source
    wire wr_d    = c_bin || c_un || op == O_MOVI || op == O_LANEID || op == O_MOVU || op == O_SHFL ||
                   op == O_LDG || op == O_LDS || op == O_LDSX || op == O_COLL || is_cx || is_css;
    wire hazard  = (use_a && pend[ra]) || (use_b && pend[rbx]) || ((use_ds || wr_d) && pend[rd]);

    // ------------------------------------------------------------------ blocking-unit state
    localparam [3:0] B_IDLE=0, B_LSU=1, B_COLL_REQ=2, B_COLL_RSP=3, B_BAR=4, B_TCWAIT=5, B_DRAIN=6, B_TCSTART=7, B_DIV=8;
    reg [3:0]     bst;
    // LSU op
    reg           l_we;
    reg [1:0]     l_esz;          // 0: 4 B, 1: 2 B, 2: 1 B
    reg [31:0]    l_base, l_stride;
    reg [LB:0]    l_count, l_next;
    reg [RB-1:0]  l_dst;
    reg [VW-1:0]  l_buf;          // load gather buffer / store source
    reg [OB:0]    l_out;
    reg [LB:0]    l_first [0:NL-1];      // per request (request index = tag; at most one request per lane)
    reg [LB:0]    l_last  [0:NL-1];
    reg [LB:0]    l_tagp;
    reg           l_issue_done;
    // collective
    reg           c_mode;
    reg [7:0]     c_count;
    reg [VW-1:0]  c_data;
    reg [RB-1:0]  c_dst;
    reg           c_x, c_fuse;
    reg [7:0]     c_off, c_nown;
    reg [VW-1:0]  c_resid;
    reg [31:0]    c_ss;
    // tensor core
    reg [31:0]    tc_sbase;
    reg [10:0]    tc_rows, tc_got;
    reg           tc_active;

    function automatic [31:0] lane_addr(input [31:0] base, input [31:0] stride, input integer l);
        lane_addr = base + stride * l;
    endfunction
    wire [31:0] esz_b = (l_esz == 2'd0) ? 32'd4 : (l_esz == 2'd1) ? 32'd2 : 32'd1;

    // the next coalesced run of lanes [l_next, run_end] sharing one sector (at most 32 lanes: 1-byte elements)
    reg [LB:0]  run_end;
    reg [26:0]  run_sec;
    reg [255:0] st_wdata;
    reg [31:0]  st_wstrb;
    reg         run_open;
    integer li, bi, jj;
    reg [LB+1:0] lj;
    reg [31:0] la;
    always @* begin
        la = lane_addr(l_base, l_stride, l_next);
        run_sec = la[31:5];
        run_end = l_next;
        run_open = 1'b1;
        for (jj = 1; jj < 32; jj = jj + 1) begin
            lj = l_next + jj;
            la = lane_addr(l_base, l_stride, lj);
            if (run_open && lj < l_count && la[31:5] == run_sec) run_end = lj[LB:0];
            else run_open = 1'b0;
        end
        st_wdata = 256'd0;
        st_wstrb = 32'd0;
        for (jj = 0; jj < 32; jj = jj + 1) begin
            lj = l_next + jj;
            if (lj <= run_end && lj < NL) begin
                la = lane_addr(l_base, l_stride, lj);
                bi = la[4:0];
                case (l_esz)
                    2'd0: begin st_wdata[bi*8 +: 32] = l_buf[lj*32 +: 32]; st_wstrb[bi +: 4] = 4'hF; end
                    2'd1: begin st_wdata[bi*8 +: 16] = l_buf[lj*32+16 +: 16]; st_wstrb[bi +: 2] = 2'h3; end
                    default: begin st_wdata[bi*8 +: 8] = f_e4m3_enc(l_buf[lj*32 +: 32]); st_wstrb[bi] = 1'b1; end
                endcase
            end
        end
    end
    wire l_can_issue = (bst == B_LSU) && !l_issue_done && (l_out < MAXO);
    assign lreq_v = l_can_issue;
    assign lreq_we = l_we;
    assign lreq_addr = {run_sec, 5'd0};
    assign lreq_wdata = st_wdata;
    assign lreq_wstrb = l_we ? st_wstrb : 32'd0;
    assign lreq_tag = {{(15-LB){1'b0}}, l_tagp};
    assign lrsp_rdy = (bst == B_LSU);
    wire l_take = lreq_v && lreq_rdy;

    // ------------------------------------------------------------------ tensor core + bulk copy
    wire bc_dv_ready, bc_idle, bc_sv;
    wire [255:0] bc_sd;
    wire bc_sready;
    wire [26:0] bc_req_addr;
    wire [$clog2(BC_DEPTH)-1:0] bc_req_tag;
    wire [$clog2(BC_MAXOUT+1)-1:0] bc_out;
    wire tc_busy, tc_rv, tc_fault, tc_arrive, tc_released;
    wire [$clog2(TC_RMAX)-1:0] tc_rrow;
    wire [31:0] tc_rdata;
    reg  tc_start, bc_dv;
    reg  [26:0] bc_dbase;
    reg  [23:0] bc_dlines;
    reg  [15:0] tc_c;
    reg  [7:0]  tc_g;
    reg  tc_xw;
    reg  [$clog2(TC_XDEPTH)-1:0] tc_xa;
    reg  [TCL*16-1:0] tc_xd;
    ot_gpu_bulk_copy #(.LINE_BITS(256), .DEPTH(BC_DEPTH), .MAX_OUT(BC_MAXOUT), .AW(27), .DQ(2)) u_bc (
        .clk(clk), .rst_n(rst_n), .d_valid(bc_dv), .d_ready(bc_dv_ready), .d_base(bc_dbase), .d_lines(bc_dlines),
        .req_v(treq_v), .req_ready(treq_rdy), .req_addr(bc_req_addr), .req_tag(bc_req_tag),
        .rsp_v(trsp_v && trsp_rdy), .rsp_tag(trsp_tag[$clog2(BC_DEPTH)-1:0]), .rsp_data(trsp_data),
        .s_valid(bc_sv), .s_ready(bc_sready), .s_data(bc_sd), .outstanding(bc_out), .idle(bc_idle));
    // the sector stream goes to the BF16 tensor core, or (block-scaled op) through the line assembler to the
    // block-dot tensor core
    reg  bd_mode;
    wire tcq_wready, bdl_sready;
    assign bc_sready = bd_mode ? bdl_sready : tcq_wready;
    assign treq_addr = {bc_req_addr, 5'd0};
    assign treq_tag = {{(16-$clog2(BC_DEPTH)){1'b0}}, bc_req_tag};
    // the staging slot of every read is reserved at issue, so a response is always accepted
    assign trsp_rdy = running || !bc_idle;
    ot_gpu_sm #(.SUB(TC_SUB), .LS(TC_LS), .NC(1), .IL(8), .XDEPTH(TC_XDEPTH), .RMAX(TC_RMAX), .LEV(TC_LEV), .INT8(0)) u_tc (
        .clk(clk), .rst_n(rst_n), .start(tc_start), .op_rows(tc_rows), .op_c(tc_c), .op_g(tc_g), .op_gs(1'b0),
        .op_scale(1'b0), .busy(tcq_busy), .w_valid(bc_sv && !bd_mode), .w_ready(tcq_wready), .w_data(bc_sd),
        .xw_en(tc_xw), .xw_addr(tc_xa), .xw_data(tc_xd), .sw_en(1'b0), .sw_addr({$clog2(TC_RMAX){1'b0}}),
        .sw_data(16'd0), .rv(tcq_rv), .rrow(tcq_rrow), .rdata(tcq_rdata), .fault(tcq_fault),
        .arrive(tc_arrive), .release_in(tc_arrive), .released(tc_released));
    wire tcq_busy, tcq_rv, tcq_fault;
    wire [$clog2(TC_RMAX)-1:0] tcq_rrow;
    wire [31:0] tcq_rdata;
    wire bd_busy, bd_rv, bd_fault;
    wire [$clog2(TC_RMAX)-1:0] bd_rrow;
    wire [31:0] bd_rdata;
    reg  bd_start, bd_fp4, bd_xw;
    reg  [$clog2(BD_XDEPTH)-1:0] bd_xa;
    reg  [8*266-1:0] bd_xmirror [0:BD_XDEPTH-1];
    reg  [8*266-1:0] bd_xd;            // registered X-tile write data: sampled by u_bdtc on the edge after issue
    reg  [8*266-1:0] bd_xn;            // clocked-block temporary (never read outside it)
    if (HAS_BD != 0) begin : g_bd
        wire bdl_wv, bdl_wr, bd_arr, bd_rel;
        wire [8*266-1:0] bdl_wd;
        ot_gpu_bd_line #(.ENABLE(1), .LB(8)) u_line (.clk(clk), .rst_n(rst_n), .s_valid(bc_sv && bd_mode),
            .s_ready(bdl_sready), .s_data(bc_sd), .w_valid(bdl_wv), .w_ready(bdl_wr), .w_data(bdl_wd));
        ot_gpu_sm_bd #(.SUB(4), .LBS(2), .NC(1), .IL(8), .XDEPTH(BD_XDEPTH), .RMAX(TC_RMAX), .LEV(TC_LEV)) u_bdtc (
            .clk(clk), .rst_n(rst_n), .start(bd_start), .op_rows(tc_rows), .op_c(tc_c), .op_g(tc_g), .op_gs(1'b0),
            .op_fp4(bd_fp4), .busy(bd_busy), .w_valid(bdl_wv), .w_ready(bdl_wr), .w_data(bdl_wd),
            .xw_en(bd_xw), .xw_addr(bd_xa), .xw_data(bd_xd), .rv(bd_rv), .rrow(bd_rrow), .rdata(bd_rdata),
            .fault(bd_fault), .arrive(bd_arr), .release_in(bd_arr), .released(bd_rel));
    end else begin : g_nobd
        assign bdl_sready = 1'b0; assign bd_busy = 1'b0; assign bd_rv = 1'b0; assign bd_fault = 1'b0;
        assign bd_rrow = {$clog2(TC_RMAX){1'b0}}; assign bd_rdata = 32'd0;
    end
    assign tc_busy = tcq_busy | bd_busy;
    assign tc_rv = tcq_rv | bd_rv;
    assign tc_rrow = bd_rv ? bd_rrow : tcq_rrow;
    assign tc_rdata = bd_rv ? bd_rdata : tcq_rdata;
    assign tc_fault = tcq_fault | bd_fault;
    wire tc_done = tc_active && !tc_busy && !tc_start && !bd_start && (tc_got == tc_rows) && bc_idle;

    // ------------------------------------------------------------------ FP pipes
    // FPW physical lanes of the qualified add and multiply pipes; an NL-lane FADD/FMUL is fed one FPW-lane
    // quarter per cycle (as a SIMD datapath narrower than the warp executes it over several cycles) and each
    // quarter writes its slice of the destination when it leaves the pipe; the last quarter clears the scoreboard.
    localparam integer NQ = NL / FPW;
    localparam integer QB = (NQ > 1) ? $clog2(NQ) : 1;
    wire [FPW*32-1:0] add_y, mul_y;
    wire [FPW-1:0] add_f, mul_f;
    reg  add_v, mul_v;
    reg  [FPW*32-1:0] fp_a, fp_b;
    reg  [VW-1:0] fq_a, fq_b;          // the op's full operands
    reg  [QB:0]   fq_left;             // quarters still to feed
    reg  [QB-1:0] fq_q;
    reg           fq_mul;
    reg  [RB-1:0] fq_d;
    genvar gl;
    for (gl = 0; gl < FPW; gl = gl + 1) begin : g_fp
        ot_gpu_simt_fplane #(.FLAT(FLAT)) u_fp (.clk(clk), .rst_n(rst_n), .add_v(add_v), .mul_v(mul_v),
            .a(fp_a[gl*32 +: 32]), .b(fp_b[gl*32 +: 32]), .add_y(add_y[gl*32 +: 32]), .add_f(add_f[gl]),
            .mul_y(mul_y[gl*32 +: 32]), .mul_f(mul_f[gl]));
    end
    // writeback tags: {dest, quarter, last}; the tag sits at index k after k+1 edges, its valid bit at k-1
    reg [FLAT:0] addq_v, mulq_v;
    reg [RB+QB:0] addq_d [0:FLAT];
    reg [RB+QB:0] mulq_d [0:FLAT];

    // ------------------------------------------------------------------ div.rn / sqrt.rn unit (blocking)
    reg            dv_go, dv_sqrt;
    reg [VW-1:0]   dv_a, dv_b, dv_y;
    reg [NL-1:0]   dv_done;
    reg            dv_err;
    reg [RB-1:0]   dv_dst;
    wire [NL-1:0]  dvo_v, sqo_v, dvo_e, sqo_e;
    wire [VW-1:0]  dvo_y, sqo_y;
    if (HAS_DIV != 0) begin : g_div
        for (gl = 0; gl < NL; gl = gl + 1) begin : g_l
            ot_gpu_simt_divlane u_dl (.clk(clk), .rst_n(rst_n), .go(dv_go), .sqrt(dv_sqrt), .a(dv_a[gl*32 +: 32]),
                .b(dv_b[gl*32 +: 32]), .take(bst == B_DIV), .dv_v(dvo_v[gl]), .dv_y(dvo_y[gl*32 +: 32]), .dv_e(dvo_e[gl]),
                .sq_v(sqo_v[gl]), .sq_y(sqo_y[gl*32 +: 32]), .sq_e(sqo_e[gl]));
        end
    end else begin : g_nodiv
        assign dvo_v = {NL{1'b0}}; assign sqo_v = {NL{1'b0}}; assign dvo_e = {NL{1'b0}}; assign sqo_e = {NL{1'b0}};
        assign dvo_y = {VW{1'b0}}; assign sqo_y = {VW{1'b0}};
    end

    // ------------------------------------------------------------------ ALU (1 cycle)
    // lane-local ops in one lane module per lane (ot_gpu_simt_lane); shuffles and shared-memory reads cross lanes
    wire [VW-1:0] lane_y;
    for (gl = 0; gl < NL; gl = gl + 1) begin : g_lane
        ot_gpu_simt_lane u_lane (.op(op), .x(va[gl*32 +: 32]), .y(vb[gl*32 +: 32]), .imm(imm), .lane(gl[7:0]),
                                 .uval(ur[fa[3:0]]), .z(lane_y[gl*32 +: 32]));
    end
    reg [VW-1:0] alu_y;
    integer ln;
    reg [31:0] lds_base;
    always @* begin
        lds_base = (ur[fa[3:0]] + imm) >> 2;
        for (ln = 0; ln < NL; ln = ln + 1) begin
            case (op)
                O_SHFL:  alu_y[ln*32 +: 32] = va[(vb[ln*32 +: LB])*32 +: 32];
                O_LDS:   alu_y[ln*32 +: 32] = (ln <= fb) ? smem[(lds_base + ln) & (SMEM_WORDS - 1)] : 32'd0;
                O_LDSX:  alu_y[ln*32 +: 32] = smem[((va[ln*32 +: 32] + imm) >> 2) & (SMEM_WORDS - 1)];
                O_COLLSS: alu_y[ln*32 +: 32] = c_ss;
                default: alu_y[ln*32 +: 32] = lane_y[ln*32 +: 32];
            endcase
        end
    end
    reg            alu_wv;
    reg [RB-1:0]   alu_wd;
    reg [VW-1:0]   alu_wy;

    // GU retirement owns no payload queue: hold the original alu_wy/alu_wv
    // and destination scoreboard until the enrolled BF16 span is accepted.
    // PC + source register are literal enrollment, not semantic inference from
    // a generic CVT opcode, destination, SM number or TC shared-memory address.
    localparam integer GU_MB=171+IMW+RB; // phase2 + coded completion + actual destination
    wire gu_en,gu_seen,gu_alu,gu_finished;
    wire [1:0] gu_phase;
    wire [RB-1:0] gu_dst_q;
    wire [IMW-1:0] gu_pc_q;
    wire [7:0] gu_src_q,gu_first_q,gu_sm_q,gu_die_q;
    wire [8:0] gu_expert_q,gu_count_q;
    wire gu_matrix_q;
    wire [11:0] gu_row_q;
    wire [72:0] gu_frame_q;
    wire [31:0] gu_op_q;
    wire [GU_MB-1:0] gu_state;
    reg [GU_MB-1:0] gu_next;
    reg gu_we;
    wire gu_meta_good,gu_meta_ce,gu_meta_due;
    assign gu_en=gu_phase!=0;assign gu_seen=gu_phase==3;assign gu_alu=gu_phase==2;
    assign {gu_phase,gu_finished,gu_pc_q,gu_dst_q,gu_src_q,gu_first_q,
            gu_sm_q,gu_die_q,gu_expert_q,gu_count_q,gu_matrix_q,gu_row_q,gu_frame_q,gu_op_q}=gu_state;
    if(GU_JOIN!=0)begin:g_gu_coded
        ot_hbm_accel_gu_metadata #(.WIDTH(GU_MB)) u_meta(
            .clk(clk),.rst_n(rst_n),.we(gu_we),.next_data(gu_next),.data(gu_state),
            .good(gu_meta_good),.ce(gu_meta_ce),.due(gu_meta_due));
    end else begin:g_gu_unused
        assign gu_state=0;assign gu_meta_good=1;assign gu_meta_ce=0;assign gu_meta_due=0;
    end
    wire gu_owned = gu_join_owner_valid && gu_join_frame == gu_frame_q &&
                    sm_id == gu_sm_q && die_id == gu_die_q;
    wire gu_pc_hit = (GU_JOIN != 0) && gu_en && pc == gu_pc_q;
    wire gu_bound = gu_meta_good && gu_pc_hit && op == O_CVTBF16 && fa == gu_src_q && !gu_seen;
    wire gu_desc_ok = gu_join_owner_valid && gu_join_pc < (64'd1 << IMW) &&
        gu_join_src < NV && gu_join_expert < 384 && gu_join_count != 0 &&
        ({1'b0,gu_join_lane_first}+{1'b0,gu_join_count}) <= NL &&
        ({1'b0,gu_join_row_base}+gu_join_count) <= 2304 &&
        gu_join_frame[51:36] == launch_token && gu_join_frame[68:53] == launch_pos;
    reg gu_payload_ok;
    integer gu_l;
    always @* begin
        gu_payload_ok = 1'b1;
        for (gu_l=0; gu_l<NL; gu_l=gu_l+1)
            if (gu_l >= gu_first_q && gu_l < (gu_first_q+gu_count_q))
                if (alu_wy[gu_l*32 +: 16] != 0 || alu_wy[gu_l*32+23 +: 8] == 8'hff)
                    gu_payload_ok = 1'b0;
    end
    assign gu_join_v = (GU_JOIN != 0) && gu_alu && !faulted && gu_meta_good && gu_owned && gu_payload_ok;
    for (gl=0; gl<NL; gl=gl+1) begin : g_gu_payload
        assign gu_join_bf16[gl*16 +: 16] = (GU_JOIN != 0) ? alu_wy[gl*32+16 +: 16] : 16'd0;
    end
    assign gu_join_out_expert = (GU_JOIN != 0) ? gu_expert_q : 9'd0;
    assign gu_join_out_matrix = (GU_JOIN != 0) && gu_matrix_q;
    assign gu_join_out_row_base = (GU_JOIN != 0) ? gu_row_q : 12'd0;
    assign gu_join_out_lane_first = (GU_JOIN != 0) ? gu_first_q : 8'd0;
    assign gu_join_out_count = (GU_JOIN != 0) ? gu_count_q : 9'd0;
    assign gu_join_out_frame = (GU_JOIN != 0) ? gu_frame_q : 73'd0;
    assign gu_join_out_op = (GU_JOIN != 0) ? gu_op_q : 32'd0;
    assign gu_join_out_sm = (GU_JOIN != 0) ? gu_sm_q : 8'd0;
    assign gu_join_out_die = (GU_JOIN != 0) ? gu_die_q : 8'd0;
    // Persistent coded terminal debt: CE after the sm_done pulse cannot erase
    // the successful span's completion visibility. Clear only on a new launch.
    assign gu_join_terminal = (GU_JOIN != 0) && gu_meta_good && gu_finished && !faulted && gu_owned;
    assign gu_join_ce = (GU_JOIN != 0) && gu_meta_ce;
    assign gu_join_due = (GU_JOIN != 0) && gu_meta_due;
    assign gu_join_retained = (GU_JOIN != 0) &&
        (running || gu_alu || (gu_en && !gu_finished) || !gu_meta_good || faulted);
    assign gu_join_warm_reset_ack = (GU_JOIN != 0) && gu_join_warm_reset_req &&
        !gu_join_retained && drained && bc_idle && l_out==0 && !lrsp_v && !lreq_v;
    wire gu_fire = gu_join_v && gu_join_accept;
    wire launch_take = launch_v && !running &&
        ((GU_JOIN==0) || (gu_meta_good && !faulted && !gu_join_warm_reset_req));
    // Only actual acceptance changes seen/pending. CE service occurs solely
    // inside u_meta and cannot inherit an unaccepted downstream permission.
    always @*begin
        gu_next=gu_state;gu_we=0;
        if(GU_JOIN!=0 && gu_meta_good)begin
            if(launch_take)begin
                gu_next=gu_join_launch ? {2'd1,1'b0,gu_join_pc[IMW-1:0],{RB{1'b0}},gu_join_src,
                    gu_join_lane_first,sm_id,die_id,gu_join_expert,gu_join_count,
                    gu_join_matrix,gu_join_row_base,gu_join_frame,gu_join_op} : {GU_MB{1'b0}};
                gu_we=1;
            end
            if(can_issue && c_alu && gu_bound)begin
                gu_next[GU_MB-1 -: 2]=2'd2;gu_next[GU_MB-4-IMW -: RB]=rd;gu_we=1;
            end
            if(gu_fire)begin gu_next[GU_MB-1 -: 2]=2'd3;gu_we=1;end
            if(bst==B_DRAIN && drained && gu_en && gu_seen && !faulted)begin
                gu_next[GU_MB-3]=1'b1;gu_we=1;
            end
        end
    end

    // ------------------------------------------------------------------ issue
    wire bad_op = !(op == O_NOP || c_bin || c_un || op == O_MOVI || op == O_LANEID || op == O_MOVU || op == O_SHFL ||
                    (op >= O_UMOVI && op <= O_UADD) || (op >= O_BRA && op <= O_RESULT) ||
                    (op >= O_LDG && op <= O_STSX) || (op >= O_TCX && op <= O_TCWAIT) || op == O_COLL ||
                    ((op == O_TCXB || op == O_TCXE || op == O_TCBMMA) && HAS_BD != 0) || is_cx || is_css) ||
                  ((op == O_FDIV || op == O_FSQRT) && HAS_DIV == 0);   // no divide/sqrt unit in this build
    wire tc_needs_idle = (op == O_TCX || op == O_TCMMA || op == O_TCXB || op == O_TCXE || op == O_TCBMMA);
    wire fp_op = (op == O_FADD || op == O_FMUL);
    wire can_issue = running && !faulted && (bst == B_IDLE) && !hazard && !tc_start && !bd_start && !bc_dv && !(fp_op && fq_left > 1) &&
                     !(tc_needs_idle && tc_active) && !((GU_JOIN != 0) && gu_alu) && gu_meta_good;
    assign busy = running;
    assign coll_req_v = (bst == B_COLL_REQ);
    assign coll_mode = c_mode;
    assign coll_count = c_count;
    assign coll_data = c_data;
    assign coll_rsp_rdy = (bst == B_COLL_RSP);
    assign coll_x = (HA3 != 0) && c_x;
    assign coll_off = (HA3 != 0) ? c_off : 8'd0;
    assign coll_nown = (HA3 != 0) ? c_nown : 8'd0;
    assign coll_fuse = (HA3 != 0) && c_fuse;
    assign coll_resid = (HA3 != 0) ? c_resid : {VW{1'b0}};

    wire drained = (pend == {NV{1'b0}}) && (fq_left == 0) && !alu_wv && !tc_active && !tc_start && !bd_start && !bc_dv && ((GU_JOIN==0) || (gu_meta_good && !gu_alu && !faulted));
    integer i, q;
    // the clocked block's own loop temporaries: the combinational LSU block above has jj/lj/bi, and sharing a
    // module variable between two processes is an ordering race (it diverged under Verilator --threads)
    integer sj, sbi;
    reg [LB+1:0] slj;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            running <= 1'b0; faulted <= 1'b0; bar_q <= 1'b0; pc <= 0; pend <= {NV{1'b0}}; bst <= B_IDLE;
            sm_done <= 1'b0; res_v <= 1'b0; res_data <= 32'd0; add_v <= 1'b0; mul_v <= 1'b0;
            addq_v <= 0; mulq_v <= 0; alu_wv <= 1'b0; fq_left <= 0; fq_q <= 0; tc_start <= 1'b0; bc_dv <= 1'b0; tc_xw <= 1'b0;
            tc_active <= 1'b0; tc_got <= 0; l_out <= 0; l_next <= 0; l_issue_done <= 1'b0; l_tagp <= 0;
            dv_go <= 1'b0; dv_sqrt <= 1'b0; dv_done <= {NL{1'b0}}; dv_err <= 1'b0;
            bd_mode <= 1'b0; bd_start <= 1'b0; bd_xw <= 1'b0; bd_fp4 <= 1'b0;
            c_x <= 1'b0; c_fuse <= 1'b0; c_off <= 8'd0; c_nown <= 8'd0; c_ss <= 32'd0;
            st_instr <= 0; st_cycles <= 0; st_stall_mem <= 0; st_tc_rows <= 0;
            for (i = 0; i < 16; i = i + 1) ur[i] <= 32'd0;
        end else begin
            sm_done <= 1'b0;
            res_v <= 1'b0;
            add_v <= 1'b0;
            mul_v <= 1'b0;
            tc_xw <= 1'b0;
            bd_xw <= 1'b0;
            alu_wv <= 1'b0;
            if (running) st_cycles <= st_cycles + 1;
            if (bst == B_LSU) st_stall_mem <= st_stall_mem + 1;
            // ---- FP pipe writeback bookkeeping
            addq_v <= {addq_v[FLAT-1:0], add_v};
            mulq_v <= {mulq_v[FLAT-1:0], mul_v};
            for (q = FLAT; q > 0; q = q - 1) begin addq_d[q] <= addq_d[q-1]; mulq_d[q] <= mulq_d[q-1]; end
            if (addq_v[FLAT-1]) begin
                vr[addq_d[FLAT][RB+QB:QB+1]][addq_d[FLAT][QB:1]*FPW*32 +: FPW*32] <= add_y;
                if (addq_d[FLAT][0]) pend[addq_d[FLAT][RB+QB:QB+1]] <= 1'b0;
                if (|add_f) faulted <= 1'b1;
            end
            if (mulq_v[FLAT-1]) begin
                vr[mulq_d[FLAT][RB+QB:QB+1]][mulq_d[FLAT][QB:1]*FPW*32 +: FPW*32] <= mul_y;
                if (mulq_d[FLAT][0]) pend[mulq_d[FLAT][RB+QB:QB+1]] <= 1'b0;
                if (|mul_f) faulted <= 1'b1;
            end
            // ---- FP feeder: one quarter per cycle
            if (fq_left != 0) begin
                fp_a <= fq_a[fq_q*FPW*32 +: FPW*32]; fp_b <= fq_b[fq_q*FPW*32 +: FPW*32];
                if (fq_mul) begin mul_v <= 1'b1; mulq_d[0] <= {fq_d, fq_q, fq_left == 1}; end
                else begin add_v <= 1'b1; addq_d[0] <= {fq_d, fq_q, fq_left == 1}; end
                fq_q <= fq_q + 1'b1; fq_left <= fq_left - 1'b1;
            end
            if ((GU_JOIN != 0) && gu_meta_good && gu_en && running && !gu_owned) faulted <= 1'b1;
            if ((GU_JOIN != 0) && gu_meta_due) faulted <= 1'b1;
            if (alu_wv || ((GU_JOIN!=0) && gu_alu)) begin
                if ((GU_JOIN == 0) || (gu_meta_good && (!gu_alu || gu_fire))) begin
                    vr[(GU_JOIN!=0 && gu_alu)?gu_dst_q:alu_wd] <= alu_wy;
                    pend[(GU_JOIN!=0 && gu_alu)?gu_dst_q:alu_wd] <= 1'b0;
                end else begin
                    alu_wv <= 1'b1; // no retirement, overwrite, drop or EXIT while held
                    if (gu_meta_good && gu_alu && !gu_payload_ok) faulted <= 1'b1;
                end
            end
            // ---- tensor core result rows -> shared memory
            if (tc_start) begin tc_start <= 1'b0; end
            if (bd_start) begin bd_start <= 1'b0; end
            if (bc_dv && bc_dv_ready) bc_dv <= 1'b0;
            if (tc_rv) begin
                smem[(tc_sbase >> 2) + tc_rrow] <= tc_rdata;
                tc_got <= tc_got + 1'b1;
                st_tc_rows <= st_tc_rows + 1;
            end
            if (tc_fault) faulted <= 1'b1;
            if (tc_done) tc_active <= 1'b0;
            // ---- launch
            if (launch_take) begin
                running <= 1'b1; pc <= launch_pc[IMW-1:0]; faulted <= 1'b0;
                for (i = 0; i < 16; i = i + 1) ur[i] <= 32'd0;
                ur[0] <= {16'd0, launch_token}; ur[1] <= {16'd0, launch_pos};
                ur[2] <= {24'd0, sm_id}; ur[3] <= {24'd0, die_id};
                if ((GU_JOIN != 0) && gu_join_launch && !gu_desc_ok) faulted <= 1'b1;
            end
            // ---- blocking units
            case (bst)
                B_LSU: begin
                    if (l_take) begin
                        l_first[l_tagp[LB-1:0]] <= l_next;
                        l_last[l_tagp[LB-1:0]] <= run_end;
                        l_tagp <= l_tagp + 1'b1;
                        if (run_end + 1 >= l_count) l_issue_done <= 1'b1;
                        l_next <= run_end + 1'b1;
                    end
                    if (lrsp_v) begin
                        if (!l_we) begin
                            for (sj = 0; sj < 32; sj = sj + 1) begin
                                slj = l_first[lrsp_tag[LB-1:0]] + sj;
                                if (slj <= l_last[lrsp_tag[LB-1:0]] && slj < NL) begin
                                    sbi = lane_addr(l_base, l_stride, slj) & 31;
                                    case (l_esz)
                                        2'd0: l_buf[slj*32 +: 32] <= lrsp_data[sbi*8 +: 32];
                                        2'd1: l_buf[slj*32 +: 32] <= {lrsp_data[sbi*8 +: 16], 16'd0};
                                        default: l_buf[slj*32 +: 32] <= f_e4m3_dec(lrsp_data[sbi*8 +: 8]);
                                    endcase
                                end
                            end
                        end
                        if (lrsp_we != l_we) faulted <= 1'b1;            // response of the wrong kind
                    end
                    l_out <= l_out + (l_take ? 1 : 0) - (lrsp_v ? 1 : 0);
                    if (l_issue_done && l_out == 0 && !lrsp_v && !l_take) begin
                        bst <= B_IDLE;
                        if (!l_we) begin vr[l_dst] <= l_buf; pend[l_dst] <= 1'b0; end
                    end
                end
                B_COLL_REQ: if (coll_req_rdy) bst <= B_COLL_RSP;
                B_COLL_RSP: if (coll_rsp_v) begin
                    vr[c_dst] <= coll_rsp_data; pend[c_dst] <= 1'b0; bst <= B_IDLE;
                    if (HA3 != 0 && c_x) begin c_ss <= coll_rsp_ss; if (coll_rsp_err) faulted <= 1'b1; end
                end
                B_BAR: if (bar_release == bar_q) bst <= B_IDLE;
                B_TCWAIT: if (!tc_active) bst <= B_IDLE;
                B_DIV: begin
                    dv_go <= 1'b0;
                    for (li = 0; li < NL; li = li + 1)
                        if (!dv_done[li] && (dv_sqrt ? sqo_v[li] : dvo_v[li])) begin
                            dv_done[li] <= 1'b1;
                            dv_y[li*32 +: 32] <= dv_sqrt ? (sqo_y[li*32 +: 32] == 32'h80000000 ? 32'd0 : sqo_y[li*32 +: 32])
                                                         : dvo_y[li*32 +: 32];
                            if (dv_sqrt ? sqo_e[li] : dvo_e[li]) dv_err <= 1'b1;
                        end
                    if (dv_done == {NL{1'b1}}) begin
                        vr[dv_dst] <= dv_y; pend[dv_dst] <= 1'b0; bst <= B_IDLE;
                        if (dv_err) faulted <= 1'b1;
                    end
                end
                B_DRAIN: if (drained) begin
                    bst <= B_IDLE; running <= 1'b0; sm_done <= 1'b1;
                end
                default: ;
            endcase
            // ---- issue one instruction
            if (can_issue) begin
                st_instr <= st_instr + 1;
                pc <= pc + 1'b1;
                if (bad_op) faulted <= 1'b1;
                if ((GU_JOIN != 0) && gu_pc_hit && !gu_bound) faulted <= 1'b1;
                if (op == O_FADD || op == O_FMUL) begin
                    fq_a <= va; fq_b <= vb; fq_mul <= (op == O_FMUL); fq_d <= rd; fq_q <= 0; fq_left <= NQ;
                    pend[rd] <= 1'b1;
                end else if (c_alu) begin
                    alu_wv <= 1'b1; alu_wd <= rd; alu_wy <= alu_y; pend[rd] <= 1'b1;
                end
                case (op)
                    O_UMOVI:  ur[fd[3:0]] <= imm;
                    O_UADDI:  ur[fd[3:0]] <= ur[fa[3:0]] + imm;
                    O_UADD:   ur[fd[3:0]] <= ur[fa[3:0]] + ur[fb[3:0]];
                    O_UMULI:  ur[fd[3:0]] <= ur[fa[3:0]] * imm;
                    O_UFROMV: ur[fd[3:0]] <= va[imm[LB-1:0]*32 +: 32];
                    O_BRA:    pc <= imm[IMW-1:0];
                    O_BNZ:    if (ur[fa[3:0]] != 0) pc <= imm[IMW-1:0];
                    O_EXIT:   begin bst <= B_DRAIN; if ((GU_JOIN != 0) && gu_en && !gu_seen) faulted <= 1'b1; end
                    O_BAR:    begin bar_q <= ~bar_q; bst <= B_BAR; end
                    O_MEMBAR: ;                                  // every store completed (acknowledged) at retire
                    O_RESULT: begin res_v <= 1'b1; res_data <= ur[fa[3:0]]; end
                    O_STS:    for (li = 0; li < NL; li = li + 1)
                                  if (li <= fb) smem[((ur[fa[3:0]] + imm) >> 2) + li] <= vd[li*32 +: 32];
                    O_STSX:   for (li = 0; li < NL; li = li + 1)
                                  if (li <= fb) smem[((va[li*32 +: 32] + imm) >> 2) & (SMEM_WORDS - 1)] <= vd[li*32 +: 32];
                    O_LDG, O_STG: begin
                        bst <= B_LSU;
                        l_we <= (op == O_STG);
                        l_esz <= fa[5:4];
                        l_base <= ur[fa[3:0]] + imm;
                        l_stride <= fa[6] ? ur[15] : ((fa[5:4] == 2'd0) ? 32'd4 : (fa[5:4] == 2'd1) ? 32'd2 : 32'd1);
                        l_count <= {1'b0, fb[LB-1:0]} + 1'b1;
                        l_next <= 0; l_issue_done <= 1'b0; l_tagp <= 0;
                        l_dst <= rd;
                        l_buf <= (op == O_STG) ? vd : {VW{1'b0}};
                        if (op == O_LDG) pend[rd] <= 1'b1;
                    end
                    O_TCX: begin
                        tc_xw <= 1'b1; tc_xa <= imm[$clog2(TC_XDEPTH)-1:0];
                        for (li = 0; li < TCL; li = li + 1) tc_xd[li*16 +: 16] <= va[li*32+16 +: 16];
                    end
                    O_TCXB, O_TCXE: if (HAS_BD != 0) begin
                        bd_xw <= 1'b1; bd_xa <= imm[$clog2(BD_XDEPTH)-1:0];
                        bd_xn = bd_xmirror[imm[$clog2(BD_XDEPTH)-1:0]];
                        for (li = 0; li < 8; li = li + 1) begin
                            if (op == O_TCXB) for (sj = 0; sj < 32; sj = sj + 1)
                                bd_xn[li*266 + sj*8 +: 8] = (li < 4) ? va[(li*32 + sj)*32 +: 8] : vb[((li-4)*32 + sj)*32 +: 8];
                            else bd_xn[li*266 + 256 +: 10] = va[li*32 +: 10];
                        end
                        bd_xmirror[imm[$clog2(BD_XDEPTH)-1:0]] <= bd_xn;
                        bd_xd <= bd_xn;
                    end
                    O_TCBMMA: if (HAS_BD != 0) begin
                        tc_rows <= {1'b0, imm[9:0]}; tc_c <= {8'd0, imm[23:16]}; tc_g <= fb; bd_fp4 <= imm[12];
                        tc_sbase <= ur[fa[3:0]];
                        bc_dbase <= ur[fd[3:0]][31:5];
                        bc_dlines <= imm[11:0] * fb * imm[23:16] * 9;
                        bc_dv <= 1'b1; bd_start <= 1'b1; bd_mode <= 1'b1; tc_active <= 1'b1; tc_got <= 0;
                    end
                    O_TCMMA: begin
                        bd_mode <= 1'b0;
                        tc_rows <= imm[10:0]; tc_c <= imm[31:16]; tc_g <= fb;
                        tc_sbase <= ur[fa[3:0]];
                        bc_dbase <= ur[fd[3:0]][31:5];
                        bc_dlines <= imm[15:0] * fb * imm[31:16];
                        bc_dv <= 1'b1; tc_start <= 1'b1; tc_active <= 1'b1; tc_got <= 0;
                    end
                    O_TCWAIT: bst <= B_TCWAIT;
                    O_FDIV, O_FSQRT: if (HAS_DIV != 0) begin
                        bst <= B_DIV; dv_go <= 1'b1; dv_sqrt <= (op == O_FSQRT); dv_a <= va; dv_b <= vb;
                        dv_done <= {NL{1'b0}}; dv_err <= 1'b0; dv_dst <= rd; pend[rd] <= 1'b1;
                    end
                    O_COLL: begin
                        bst <= B_COLL_REQ; c_mode <= fb[0]; c_count <= imm[7:0]; c_data <= va; c_dst <= rd;
                        pend[rd] <= 1'b1; c_x <= 1'b0; c_fuse <= 1'b0; c_off <= 8'd0; c_nown <= 8'd0;
                    end
                    O_COLLX: if (HA3 != 0) begin
                        bst <= B_COLL_REQ; c_mode <= imm[24]; c_count <= imm[7:0]; c_data <= va; c_dst <= rd;
                        c_x <= 1'b1; c_fuse <= imm[25]; c_off <= imm[15:8]; c_nown <= imm[23:16]; c_resid <= vb;
                        pend[rd] <= 1'b1;
                    end
                    default: ;
                endcase
            end
        end
    end
end endgenerate
endmodule

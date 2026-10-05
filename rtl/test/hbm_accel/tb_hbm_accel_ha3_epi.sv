`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// HA3 fused-epilogue / cut-through gate bench: ND = 2 dies x NSM = 2
// ot_hbm_accel_simt_sm (HA3 = 1), one ot_hbm_accel_coll_port per die, the
// unchanged NVLS fabric ot_gpu_coll_fabric (in-switch reduce, R = 2).
// Per case (tools/hbm_accel_ha3_epilogue_gate.py writes case files): every SM's
// shared memory gets its partial rows P (64 words at 0x0000) and the residual X
// (128 words at 0x0400) by backdoor, then
//   kernel A (two-op): COLLX (cut-through, no fuse) -> FADD x + red -> the SM's
//            sum of squares (Lib.seg_sum8) ; stores x' and ss
//   kernel B (fused):  COLLX.fuse -> COLLSS ; stores x' and ss
// each launched on all four SMs after a reset; per SM it reports the fault,
// x', ss and the launch -> done cycles of both kernels.
// Plusargs: +DIR=<case dir> +N=<cases> +PA=<pc A> +PB=<pc B> +IMEM=<words>; prog_d<d>_s<s>.hex per SM
// ---------------------------------------------------------------------------
module tb_hbm_accel_ha3_epi;
    localparam integer ND = 2, NSM = 2, NL = 128, IMW = 12, PW = 32 * 16 + 2 + 32;
    reg clk_sm = 0, clk_link = 0;
    always #0.4165 clk_sm = ~clk_sm;
    always #0.45   clk_link = ~clk_link;
    reg rst_n = 0;
    reg launch = 0;
    reg [31:0] lpc = 0;
    reg im_we = 0;
    integer im_sel = 0;
    reg [IMW-1:0] im_addr = 0;
    reg [63:0] im_data = 0;
    wire [ND*NSM-1:0] done_w, fault_w;
    wire [ND-1:0] up_v, dn_v, pf;
    wire [ND*PW-1:0] up_rec, dn_rec;
    wire fab_f;
    ot_gpu_coll_fabric #(.ENABLE(1), .R(ND), .NL(NL), .SW_PIPE(8)) u_fab (.clk_link(clk_link), .rst_link_n(rst_n),
        .up_v(up_v), .up_rec(up_rec), .dn_v(dn_v), .dn_rec(dn_rec), .fault(fab_f));
    genvar d, s;
    for (d = 0; d < ND; d = d + 1) begin : g_die
        wire [NSM-1:0] cs_req_v, cs_req_rdy, cs_mode, cs_rsp_v, cs_rsp_rdy, cs_x, cs_fuse;
        wire [NSM*8-1:0] cs_count, cs_off, cs_nown;
        wire [NSM*NL*32-1:0] cs_data, cs_resid;
        wire [NL*32-1:0] cs_rsp_data;
        wire [31:0] cs_rsp_ss, st_coll;
        wire cs_rsp_err;
        for (s = 0; s < NSM; s = s + 1) begin : g_sm
            wire res_v, busy, bar_a;
            wire [31:0] res_d, s1, s2, s3, s4;
            wire lreq_v, lreq_we, treq_v, lrsp_rdy, trsp_rdy;
            wire [31:0] lreq_addr, lreq_wstrb, treq_addr;
            wire [255:0] lreq_wdata;
            wire [15:0] lreq_tag, treq_tag;
            ot_hbm_accel_simt_sm #(.ENABLE(1), .HA3(1), .NL(NL), .IMW(IMW)) u_sm (
                .clk(clk_sm), .rst_n(rst_n), .sm_id(s[7:0]), .die_id(d[7:0]),
                .im_we(im_we && im_sel == d*NSM + s), .im_addr(im_addr), .im_data(im_data),
                .launch_v(launch), .launch_pc(lpc), .launch_token(16'd0), .launch_pos(16'd0),
                .sm_done(done_w[d*NSM + s]), .sm_fault(fault_w[d*NSM + s]), .res_v(res_v), .res_data(res_d), .busy(busy),
                .bar_arrive(bar_a), .bar_release(bar_a),
                .lreq_v(lreq_v), .lreq_rdy(1'b0), .lreq_we(lreq_we), .lreq_addr(lreq_addr), .lreq_wdata(lreq_wdata),
                .lreq_wstrb(lreq_wstrb), .lreq_tag(lreq_tag), .lrsp_v(1'b0), .lrsp_rdy(lrsp_rdy), .lrsp_tag(16'd0),
                .lrsp_we(1'b0), .lrsp_data(256'd0),
                .treq_v(treq_v), .treq_rdy(1'b0), .treq_addr(treq_addr), .treq_tag(treq_tag), .trsp_v(1'b0),
                .trsp_rdy(trsp_rdy), .trsp_tag(16'd0), .trsp_data(256'd0),
                .coll_req_v(cs_req_v[s]), .coll_req_rdy(cs_req_rdy[s]), .coll_mode(cs_mode[s]),
                .coll_count(cs_count[s*8 +: 8]), .coll_data(cs_data[s*NL*32 +: NL*32]), .coll_rsp_v(cs_rsp_v[s]),
                .coll_rsp_rdy(cs_rsp_rdy[s]), .coll_rsp_data(cs_rsp_data),
                .coll_x(cs_x[s]), .coll_off(cs_off[s*8 +: 8]), .coll_nown(cs_nown[s*8 +: 8]), .coll_fuse(cs_fuse[s]),
                .coll_resid(cs_resid[s*NL*32 +: NL*32]), .coll_rsp_ss(cs_rsp_ss), .coll_rsp_err(cs_rsp_err),
                .st_instr(s1), .st_cycles(s2), .st_stall_mem(s3), .st_tc_rows(s4));
        end
        ot_hbm_accel_coll_port #(.ENABLE(1), .NSM(NSM), .NL(NL), .R(ND), .RANK(d)) u_port (
            .clk_sm(clk_sm), .rst_sm_n(rst_n), .s_req_v(cs_req_v), .s_req_rdy(cs_req_rdy), .s_mode(cs_mode),
            .s_count(cs_count), .s_data(cs_data), .s_x(cs_x), .s_off(cs_off), .s_nown(cs_nown), .s_fuse(cs_fuse),
            .s_resid(cs_resid), .s_rsp_v(cs_rsp_v), .s_rsp_rdy(cs_rsp_rdy), .s_rsp_data(cs_rsp_data),
            .s_rsp_ss(cs_rsp_ss), .s_rsp_err(cs_rsp_err), .fault(pf[d]), .st_coll(st_coll),
            .clk_link(clk_link), .rst_link_n(rst_n), .lk_tx_v(up_v[d]), .lk_tx_rec(up_rec[d*PW +: PW]),
            .lk_rx_v(dn_v[d]), .lk_rx_rec(dn_rec[d*PW +: PW]));
    end

    // ---------------- backdoor access to the SMs' shared memories
`define SMEM(D, S) g_die[D].g_sm[S].u_sm.g_on.smem
    task automatic smem_wr(input integer sm, input integer a, input [31:0] v);
        case (sm)
            0: `SMEM(0, 0)[a] = v;  1: `SMEM(0, 1)[a] = v;
            2: `SMEM(1, 0)[a] = v;  default: `SMEM(1, 1)[a] = v;
        endcase
    endtask
    function automatic [31:0] smem_rd(input integer sm, input integer a);
        case (sm)
            0: smem_rd = `SMEM(0, 0)[a];  1: smem_rd = `SMEM(0, 1)[a];
            2: smem_rd = `SMEM(1, 0)[a];  default: smem_rd = `SMEM(1, 1)[a];
        endcase
    endfunction

    string dir;
    integer n, pa, pb, nim, i, c, sm, k, fo, t0;
    integer cyc;
    reg [63:0] prog [0:(1<<IMW)-1];
    reg [31:0] cin [0:4*192-1];          // per SM: P 64, X 128
    integer tdone [0:3];
    always @(posedge clk_sm) cyc <= cyc + 1;
    always @(posedge clk_sm) for (int q = 0; q < 4; q++) if (done_w[q]) tdone[q] = cyc;

    task automatic run_kernel(input integer pc, input integer tag);
        rst_n = 0; repeat (4) @(posedge clk_sm); rst_n = 1; repeat (8) @(posedge clk_sm);
        for (int q = 0; q < 4; q++) tdone[q] = -1;
        @(negedge clk_sm); lpc = pc; launch = 1; t0 = cyc;
        @(negedge clk_sm); launch = 0;
        while ((tdone[0] < 0 && !fault_w[0]) || (tdone[1] < 0 && !fault_w[1]) || (tdone[2] < 0 && !fault_w[2]) ||
               (tdone[3] < 0 && !fault_w[3])) begin
            @(posedge clk_sm);
            if (cyc - t0 > 200000) begin $display("TIMEOUT"); $finish; end
        end
        repeat (400) @(posedge clk_sm);              // a faulted SM's peers: let the port settle
        repeat (2) @(posedge clk_sm);
        for (sm = 0; sm < 4; sm++) begin
            $fwrite(fo, "K %0d SM %0d FAULT %0d PORTF %0d CYC %0d SS %08x X", tag, sm, fault_w[sm], pf[sm / 2],
                    tdone[sm] - t0, smem_rd(sm, (tag == 0 ? 32'h1400 : 32'h1C00) >> 2));
            for (k = 0; k < NL; k++) $fwrite(fo, " %08x", smem_rd(sm, ((tag == 0 ? 32'h1000 : 32'h1800) >> 2) + k));
            $fwrite(fo, "\n");
        end
    endtask

    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        void'($value$plusargs("N=%d", n));
        void'($value$plusargs("PA=%d", pa));
        void'($value$plusargs("PB=%d", pb));
        void'($value$plusargs("IMEM=%d", nim));
        cyc = 0;
        for (sm = 0; sm < 4; sm++) begin
            $readmemh($sformatf("%s/prog_d%0d_s%0d.hex", dir, sm / 2, sm % 2), prog, 0, nim - 1);
            im_sel = sm;
            for (i = 0; i < nim; i++) begin
                @(negedge clk_sm); im_we = 1; im_addr = i; im_data = prog[i];
            end
            @(negedge clk_sm); im_we = 0;
        end
        fo = $fopen({dir, "/out.txt"}, "w");
        for (c = 0; c < n; c++) begin
            $readmemh($sformatf("%s/case%0d.hex", dir, c), cin);
            for (int pass = 0; pass < 2; pass++) begin
                for (sm = 0; sm < 4; sm++) begin
                    for (k = 0; k < 64; k++) smem_wr(sm, k, cin[sm*192 + k]);
                    for (k = 0; k < 128; k++) smem_wr(sm, (32'h400 >> 2) + k, cin[sm*192 + 64 + k]);
                    for (k = 0; k < 128; k++) begin
                        smem_wr(sm, (32'h1000 >> 2) + k, 32'hDEADBEEF); smem_wr(sm, (32'h1800 >> 2) + k, 32'hDEADBEEF);
                    end
                    smem_wr(sm, 32'h1400 >> 2, 32'hDEADBEEF); smem_wr(sm, 32'h1C00 >> 2, 32'hDEADBEEF);
                end
                $fwrite(fo, "CASE %0d\n", c);
                run_kernel(pass == 0 ? pa : pb, pass);
            end
        end
        $fclose(fo);
        $display("TB_HA3_EPI DONE %0d cases", n);
        $finish;
    end
endmodule

`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DISTRIBUTED VECTOR MEMORY (VM_DIST) of the DeepSeek-V4.1 die: NG lane-group
// banks (ot_v41_vm_dist_group, one module a group, replicated by generate) in
// place of the flat multi-port array.  Spec: results/floorplan/v41_vm_dist_spec.json
// (tools/w11_vm_dist_spec.py): at full shape NG = 128 groups of 8 stream-unit
// lanes, element e in group e mod 128, 2 banks of 256 rows x 8 elements a group,
// 6 read replicas (A, B, C, D, G, X), one masked row write a bank a cycle.
//
// Ports: a READ LIST (NRD one-element requests: address, class) answered one
// cycle later, exactly like the flat memory, and a WRITE LIST (NWR one-element
// writes) applied at the end of the cycle in list order (a later entry wins on
// the same element, the flat memory's statement order).  The caller orders the
// lists: reads 0 .. 4*NL-1 are the stream unit's operand reads (lane l, stream
// s at 4*l + s), 4*NL .. 5*NL-1 its gather-index reads, the rest tree reads;
// writes WE0 .. WE0+NL-1 are the stream unit's element writes (lane l).  The trees'
// register stages are the callers' (ot_hdc_core_v41x, ot_chip_v41x_tile): this
// module adds no latency.
//
// Monitors (st_*): per class the reads, the reads whose element is not in the
// requesting lane's group (lane l's group is l mod NG: they need a network the
// model does not price), the read-rule violations (a class asking for a second
// row of a bank in a cycle) and the write-port pressure (row writes beyond one a
// bank a cycle, the deepest write buffer).  fault: a group ran out of overflow
// ports or write slots (the data would be wrong).
//
// Simulation backdoor (not synthesised): bd_img is the flat image; bd_load
// copies it into the banks and bd_dump copies the banks back, each in one edge.
// ---------------------------------------------------------------------------
module ot_v41_vm_dist #(
    parameter integer NG   = 128,
    parameter integer VMA  = 19,
    parameter integer NL   = 1024,      // stream-unit lanes (the first 5*NL reads, NL writes)
    parameter integer NRD  = 5 * 1024 + 64,
    parameter integer NWR  = 1024 + 128,
    parameter integer NB   = 2,
    parameter integer NOVF = 48,
    parameter integer NWP  = 32,
    parameter integer WE0  = 0,          // index of the first stream-unit element write in the write list
    parameter integer LNG  = (NG > 1) ? $clog2(NG) : 0,
    parameter integer GW   = (LNG > 0) ? LNG : 1
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire [NRD-1:0]     rd_re,
    input  wire [NRD*VMA-1:0] rd_addr,
    input  wire [NRD*3-1:0]   rd_cls,
    output reg  [NRD*32-1:0]  rd_q,
    input  wire [NWR-1:0]     wr_we,
    input  wire [NWR*VMA-1:0] wr_addr,
    input  wire [NWR*32-1:0]  wr_data,
    input  wire               bd_load,
    input  wire               bd_dump,
    output reg                fault
);
    localparam integer NRC = 6, RW = 8;
    localparam integer LWA = VMA - LNG;
    localparam integer LNB = (NB > 1) ? $clog2(NB) : 0;
    localparam integer RA = LWA - 3 - LNB;
    localparam integer ROWS = 1 << RA;

    wire [NRD*32-1:0] g_q     [0:NG-1];
    wire [NRC*32-1:0] g_rconf [0:NG-1];
    wire [31:0]       g_rcyc  [0:NG-1];
    wire [31:0]       g_wx    [0:NG-1];
    wire [15:0]       g_wmax  [0:NG-1];
    wire [15:0]       g_omax  [0:NG-1];
    wire [NG-1:0]     g_fault;
    genvar g;
    generate for (g = 0; g < NG; g = g + 1) begin : g_grp
        ot_v41_vm_dist_group #(.NG(NG), .VMA(VMA), .NB(NB), .RW(RW), .NRC(NRC), .NOVF(NOVF), .NWP(NWP),
                               .NRD(NRD), .NWR(NWR)) u_grp (
            .clk(clk), .rst_n(rst_n), .gid(GW'(g)),
            .rd_re(rd_re), .rd_addr(rd_addr), .rd_cls(rd_cls), .rd_q(g_q[g]),
            .wr_we(wr_we), .wr_addr(wr_addr), .wr_data(wr_data),
            .mon_rconf(g_rconf[g]), .mon_rconf_cyc(g_rcyc[g]), .mon_wextra(g_wx[g]),
            .mon_wrows_max(g_wmax[g]), .mon_occ_max(g_omax[g]), .fault(g_fault[g]));
    end endgenerate

    // the requests' groups own disjoint elements: the answer is the OR of the groups' outputs
    integer k;
    always @(*) begin
        rd_q = 0;
        for (k = 0; k < NG; k = k + 1) rd_q = rd_q | g_q[k];
    end

    // ---- monitors -----------------------------------------------------------------------------------
    reg [31:0] st_reads   [0:NRC-1];
    reg [31:0] st_remote  [0:NRC-1];
    reg [31:0] st_writes_e, st_remote_e, st_writes_all;
    reg [31:0] st_rconf   [0:NRC-1];
    reg [31:0] st_rconf_cyc_sum, st_wextra;
    reg [15:0] st_wrows_max, st_occ_max;
    integer r, c, lane;
    reg [31:0] n_rd [0:NRC-1];
    reg [31:0] n_rm [0:NRC-1];
    reg [31:0] n_we, n_wr, n_wa;
    always @(*) begin
        for (c = 0; c < NRC; c = c + 1) begin n_rd[c] = 0; n_rm[c] = 0; end
        for (r = 0; r < NRD; r = r + 1) if (rd_re[r]) begin
            c = 32'(rd_cls[r*3 +: 3]);
            n_rd[c] = n_rd[c] + 1;
            lane = (r < 4 * NL) ? r / 4 : (r < 5 * NL) ? r - 4 * NL : -1;
            if (lane >= 0 && NG > 1 && (32'(rd_addr[r*VMA +: VMA]) % NG) != (lane % NG)) n_rm[c] = n_rm[c] + 1;
        end
        n_we = 0; n_wr = 0; n_wa = 0;
        for (r = 0; r < NWR; r = r + 1) if (wr_we[r]) begin
            n_wa = n_wa + 1;
            if (r >= WE0 && r < WE0 + NL) begin
                n_we = n_we + 1;
                if (NG > 1 && (32'(wr_addr[r*VMA +: VMA]) % NG) != ((r - WE0) % NG)) n_wr = n_wr + 1;
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (c = 0; c < NRC; c = c + 1) begin st_reads[c] <= 0; st_remote[c] <= 0; end
            st_writes_e <= 0; st_remote_e <= 0; st_writes_all <= 0; fault <= 1'b0;
        end else begin
            for (c = 0; c < NRC; c = c + 1) begin
                st_reads[c] <= st_reads[c] + n_rd[c]; st_remote[c] <= st_remote[c] + n_rm[c];
            end
            st_writes_e <= st_writes_e + n_we; st_remote_e <= st_remote_e + n_wr; st_writes_all <= st_writes_all + n_wa;
            fault <= |g_fault;
        end
    end
    always @(*) begin
        for (c = 0; c < NRC; c = c + 1) begin
            st_rconf[c] = 0;
            for (k = 0; k < NG; k = k + 1) st_rconf[c] = st_rconf[c] + g_rconf[k][c*32 +: 32];
        end
        st_rconf_cyc_sum = 0; st_wextra = 0; st_wrows_max = 0; st_occ_max = 0;
        for (k = 0; k < NG; k = k + 1) begin
            st_rconf_cyc_sum = st_rconf_cyc_sum + g_rcyc[k];
            st_wextra = st_wextra + g_wx[k];
            if (g_wmax[k] > st_wrows_max) st_wrows_max = g_wmax[k];
            if (g_omax[k] > st_occ_max) st_occ_max = g_omax[k];
        end
    end
    // one report line (benches $display it): the fields tools/w11_vm_dist_gate.py parses
    task report;
        $display("VMDIST ng=%0d reads=%0d,%0d,%0d,%0d,%0d,%0d remote=%0d,%0d,%0d,%0d,%0d,%0d writes_e=%0d remote_e=%0d writes=%0d rconf=%0d,%0d,%0d,%0d,%0d,%0d rconf_group_cycles=%0d wextra=%0d wrows_max=%0d occ_max=%0d fault=%0d",
                 NG, st_reads[0], st_reads[1], st_reads[2], st_reads[3], st_reads[4], st_reads[5],
                 st_remote[0], st_remote[1], st_remote[2], st_remote[3], st_remote[4], st_remote[5],
                 st_writes_e, st_remote_e, st_writes_all,
                 st_rconf[0], st_rconf[1], st_rconf[2], st_rconf[3], st_rconf[4], st_rconf[5],
                 st_rconf_cyc_sum, st_wextra, st_wrows_max, st_occ_max, fault);
    endtask

`ifndef SYNTHESIS
    // ---- simulation backdoor: flat image <-> banks ----------------------------------------------------
    reg [31:0] bd_img [0:(1<<VMA)-1];
    generate for (g = 0; g < NG; g = g + 1) begin : g_bd
        integer i, e;
        reg [RW*32-1:0] rowv;
        always @(posedge clk) begin
            if (bd_load)
                for (i = 0; i < (1 << LWA) / RW; i = i + 1) begin
                    for (e = 0; e < RW; e = e + 1) rowv[32*e +: 32] = bd_img[((i * RW + e) << LNG) + g];
                    // local word w = i*RW + e: bank i mod 2, row i / 2
                    if ((i % 2) == 0) g_grp[g].u_grp.g_bank[0].u_bank.mem[i / 2] = rowv;
                    else g_grp[g].u_grp.g_bank[1].u_bank.mem[i / 2] = rowv;
                end
            if (bd_dump)
                for (i = 0; i < (1 << LWA) / RW; i = i + 1) begin
                    if ((i % 2) == 0) rowv = g_grp[g].u_grp.g_bank[0].u_bank.mem[i / 2];
                    else rowv = g_grp[g].u_grp.g_bank[1].u_bank.mem[i / 2];
                    for (e = 0; e < RW; e = e + 1) bd_img[((i * RW + e) << LNG) + g] = rowv[32*e +: 32];
                end
        end
    end endgenerate
    initial if (NB != 2) $fatal(1, "ot_v41_vm_dist: the backdoor handles NB = 2 (the spec's banks)");
`endif
endmodule

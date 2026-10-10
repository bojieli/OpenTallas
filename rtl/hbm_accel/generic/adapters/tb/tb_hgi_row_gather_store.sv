`timescale 1ns/1ps
// Full-shape ROW_GATHER STORE: real record adapter, current mover and SECDED VM, one in-order KOUT64 HBM lane.
// The lane accepts up to one 32B sector per edge and replies at KLAT=40; this does not serialize each sector roundtrip.
// G96/c2 moves two 192KiB runs from a slot-interleaved VM region; a selected-row chunk moves64x512FP32 words.
// Vectors tools/hgi_adapters/row_gather_store_bench.py independently check every destination word and no stray address.
// Completion requires all write acknowledgements. Timeouts are omitted; the fleet's job lifecycle owns stuck-run policy.
module tb_hgi_row_gather_store;
    parameter integer KLAT = 40;
`ifdef MUT_WIDE_MASK
    localparam integer VMUT = 4;
`else
    localparam integer VMUT = 0;
`endif
`ifdef MUT_RNE
    localparam integer MR = 1;
`else
    localparam integer MR = 0;
`endif
    `include "mo_sizes.svh"
    reg clk = 0;
    always #1 clk = ~clk;
    reg [702:0] recm [0:NREC-1];
    reg [319:0] casem [0:NCASE-1];
    reg [63:0] vmim [0:VMI-1]; reg [63:0] vmem [0:VME-1];
    reg [71:0] hbim [0:HBI-1]; reg [71:0] hbem [0:HBE-1];
    reg [8*256-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/mo_rec.mem"}, recm); $readmemh({dir, "/mo_case.mem"}, casem);
        $readmemh({dir, "/mo_vmi.mem"}, vmim); $readmemh({dir, "/mo_vme.mem"}, vmem);
        $readmemh({dir, "/mo_hbi.mem"}, hbim); $readmemh({dir, "/mo_hbe.mem"}, hbem);
    end
    integer errors = 0, seed = 5;
    reg rst_n = 0; reg [702:0] cur; reg rec_v = 0;
    wire rec_rdy, done, fault, halted, mv_v, mv_rdy, mv_done, mv_fault, fence_v, fence_rdy, fence_done;
    wire [226:0] mv;
    ot_hgi_dma_record u_a (.clk(clk), .rst_n(rst_n), .hgi_en(1'b1), .rec_v(rec_v), .rec_rdy(rec_rdy),
        .rec_hdr(cur[127:0]), .rec_a(cur[383:128]), .rec_o(cur[639:384]), .rec_n_a(cur[660:640]), .rec_n_o(cur[681:661]),
        .rec_pos1(cur[702:682]), .rec_done(done), .rec_fault(fault), .halted(halted), .lg_mv_v(1'b0), .lg_mv_rdy(),
        .lg_mv(227'd0), .lg_fence_v(1'b0), .lg_fence_rdy(), .mv_v(mv_v), .mv_rdy(mv_rdy), .mv(mv), .mv_done(mv_done),
        .mv_fault(mv_fault), .fence_v(fence_v), .fence_rdy(fence_rdy), .fence_done(fence_done));
    wire k_req_v, k_req_we, k_rsp_rdy; reg k_req_rdy = 0, k_rsp_v = 0, k_rsp_we = 0; reg [255:0] k_rsp_data = 0;
    wire [36:0] k_addr; wire [255:0] k_wd; wire [31:0] k_ws; wire [15:0] k_tag;
    wire [337:0] vmq; wire [273:0] vmr0, vmr1; reg [337:0] tq = 0;
    ot_hgi_dma_mover #(.MUT_RNE(MR)) u_m (.clk(clk), .rst_n(rst_n), .mv_v(mv_v), .mv_rdy(mv_rdy), .mv(mv),
        .mv_done(mv_done), .mv_fault(mv_fault), .fence_v(fence_v), .fence_rdy(fence_rdy), .fence_done(fence_done),
        .k_req_v(k_req_v), .k_req_rdy(k_req_rdy), .k_req_we(k_req_we), .k_req_addr(k_addr), .k_req_wdata(k_wd),
        .k_req_wstrb(k_ws), .k_req_tag(k_tag), .k_rsp_v(k_rsp_v), .k_rsp_rdy(k_rsp_rdy), .k_rsp_we(k_rsp_we),
        .k_rsp_data(k_rsp_data), .k_fault(1'b0), .vmq(vmq), .vmr(vmr0), .wl(wl), .wl_done(wl_done));
    wire [279:0] wl; wire wl_done;   // the VM wide write port (hgi-takeover 2026-10-10)
    ot_hgi_vm_unit #(.NC(2), .WP(1), .MUT(VMUT)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, vmq}), .cr({vmr1, vmr0}), .status(), .wq(wl), .wq_done(wl_done));
    // ---- KOUT64 in-order lane model; fixed latency admits one sector per clock
    reg [31:0] hbm [longint];
    integer kh=0, kt=0, kn=0, cycle=0, q, kaccepted=0, kacked=0;
    reg [36:0] qa[0:63]; reg [255:0] qd_mem[0:63]; reg [31:0] qs[0:63]; reg qwe[0:63]; integer due[0:63];
    always @(posedge clk) begin
        cycle=cycle+1;k_rsp_v<=0;
        if (!rst_n) begin kh=0;kt=0;kn=0;kaccepted=0;kacked=0;k_req_rdy<=0;end
        else begin
            if (k_req_v && k_req_rdy) begin
                if(kn==64) $fatal(1,"lane queue overflow");
                qa[kt]=k_addr;qd_mem[kt]=k_wd;qs[kt]=k_ws;qwe[kt]=k_req_we;due[kt]=cycle+KLAT;
                kt=(kt+1)%64;kn=kn+1;kaccepted=kaccepted+1;
            end
            if (kn>0 && due[kh]<=cycle) begin
                for(q=0;q<8;q=q+1) begin
                    if(qwe[kh]) begin
                        for(integer by=0;by<4;by=by+1) if(qs[kh][4*q+by])
                            hbm[(qa[kh]>>2)+q][8*by+:8]=qd_mem[kh][32*q+8*by+:8];
                    end else k_rsp_data[32*q+:32]<=hbm.exists((qa[kh]>>2)+q)?hbm[(qa[kh]>>2)+q]:32'd0;
                end
                k_rsp_v<=1;k_rsp_we<=qwe[kh];kh=(kh+1)%64;kn=kn-1;kacked=kacked+1;
            end
            k_req_rdy<=kn<64;
        end
    end
    task automatic vm_req(input we, input [31:0] word, input [31:0] data, output [31:0] qd);
        integer tw;
        begin
            @(negedge clk); tq = {1'b1, we, word[29:3], 5'd0, {8{data}}, (32'hF << (4 * word[2:0])), 16'h0BE0};
            @(negedge clk); tq[337] = 1'b0;
            tw = 0; while (!vmr1[273] && 1) begin @(negedge clk); tw = tw + 1; end
            qd = vmr1[32 * word[2:0] +: 32];
        end
    endtask
    integer started, c, j, t, r0, nr, vi0, nvi, hi0, nhi, ve0, nve, he0, nhe, k, nf, words = 0;
    integer rec_started;
    reg [31:0] qd;
    always @(posedge clk) begin
        if (rst_n && rec_v && rec_rdy) rec_started=cycle;
        if (rst_n && done) begin k=k+1; $display("STORE_RECORD case=%0d record=%0d cycles=%0d",c,k,cycle-rec_started);end
        if (rst_n && fault) nf=nf+1;
    end
    initial begin
        repeat (3) @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            {r0, nr, vi0, nvi, hi0, nhi, ve0, nve, he0, nhe} = casem[c];
            rst_n = 0; hbm.delete(); repeat (3) @(posedge clk); rst_n = 1; repeat (2) @(posedge clk);
            for (j = 0; j < nvi; j = j + 1) vm_req(1'b1, vmim[vi0 + j][63:32], vmim[vi0 + j][31:0], qd);
            for (j = 0; j < nhi; j = j + 1) hbm[hbim[hi0 + j][71:32]] = hbim[hi0 + j][31:0];
            k = 0; nf = 0; started=cycle;
            for (j = 0; j < nr; j = j + 1) begin
                @(negedge clk); cur = recm[r0 + j]; rec_v = 1;
                t = 0; while (!rec_rdy && 1) begin @(negedge clk); t = t + 1; end
                @(posedge clk); #0.1 rec_v = 0;
            end
            t = 0; while (k < nr && nf == 0 && 1) begin @(posedge clk); t = t + 1; end
            $display("STORE_MEASURE case=%0d records=%0d cycles=%0d accepted=%0d acked=%0d KLAT=%0d",c,nr,cycle-started,kaccepted,kacked,KLAT);
            if (kaccepted!=kacked || kn!=0) $fatal(1,"completion before write visibility");
            if (k != nr || nf != 0) begin $display("ERR case %0d: retired %0d of %0d, faults %0d", c, k, nr, nf); errors = errors + 1; end
            for (j = 0; j < nve; j = j + 1) begin
                vm_req(1'b0, vmem[ve0 + j][63:32], 0, qd);
                if (qd !== vmem[ve0 + j][31:0]) begin
                    if (errors < 30) $display("ERR case %0d VM[%0d] = %h expected %h", c, vmem[ve0 + j][63:32], qd, vmem[ve0 + j][31:0]);
                    errors = errors + 1; end
            end
            if (hbm.num()!=nhe) begin $display("ERR stray HBM addresses case %0d got%0d expected%0d",c,hbm.num(),nhe);errors=errors+1;end
            for (j = 0; j < nhe; j = j + 1) begin
                qd = hbm.exists(hbem[he0 + j][71:32]) ? hbm[hbem[he0 + j][71:32]] : 32'd0;
                if (qd !== hbem[he0 + j][31:0]) begin
                    if (errors < 30) $display("ERR case %0d HBM word %h = %h expected %h", c, hbem[he0 + j][71:32], qd, hbem[he0 + j][31:0]);
                    errors = errors + 1; end
            end
            words = words + nve + nhe;
        end
        $display("summary: %0d cases (%0d records), %0d memory words checked", NCASE, NREC, words);
        if (errors == 0) $display("HGI_ROW_GATHER_STORE PASS"); else $display("HGI_ROW_GATHER_STORE FAIL errors=%0d", errors);
        $finish;
    end
endmodule

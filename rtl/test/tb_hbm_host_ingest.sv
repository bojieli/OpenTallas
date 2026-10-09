`timescale 1ps/1ps
// Bench of the HBM die's KV-ingest master hfd_host_ingest (stream ingest 2026-10-08): host stream -> ot_rom_host_ingest
// -> ot_hbm_ingest_xlat -> stack write requests.  Every write request is logged to wq.txt as "stack pc bank row col
// data"; tools/rtl_hbm_host_ingest_bench.py compares the set with the independent golden of the dskv_wb decode layout
// (tools/hbm_accel_dskv_wb.py sector_addr / owner_k).  Files: desc.mem, pay.mem, nb.mem.  +WQSTALL % of cycles the
// fabric is not ready.  Prints: HHING descs=.. beats=.. writes=.. dones=../.. fault=.. ck_cycles=.. timeout=..
module tb_hbm_host_ingest #(parameter integer ND = 16, parameter integer NP = 4096,
                            parameter integer HP = 1000, parameter integer IP = 1666, parameter integer CP = 833) ();
    reg clk_h = 0, clk_i = 0, ck = 0, rst_n = 0;
    always #(HP / 2) clk_h = ~clk_h;
    always #(IP / 2) clk_i = ~clk_i;
    always #(CP / 2) ck = ~ck;
    reg [255:0] dmem [0:ND-1];
    reg [511:0] pmem [0:NP-1];
    reg [31:0]  nbm  [0:ND-1];
    integer nd, np, stall, maxcyc, seed, nfence, i, fd;
    initial begin
        if (!$value$plusargs("ND=%d", nd)) nd = ND;
        if (!$value$plusargs("NP=%d", np)) np = NP;
        if (!$value$plusargs("WQSTALL=%d", stall)) stall = 0;
        if (!$value$plusargs("MAXCYC=%d", maxcyc)) maxcyc = 4000000;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        $readmemh("desc.mem", dmem); $readmemh("pay.mem", pmem); $readmemh("nb.mem", nbm);
        nfence = 0;
        for (i = 0; i < nd; i = i + 1) if (dmem[i][7]) nfence = nfence + 1;
        fd = $fopen("wq.txt", "w");
        #(20 * HP) rst_n = 1;
    end
    reg h_v; reg [1:0] h_cls; reg [511:0] h_d; wire [4:0] h_crn; wire t_v; wire [63:0] t_d; reg t_cr;
    wire wq_v, eop_v, fault; wire [1:0] wq_stack; wire [4:0] wq_pc, wq_bank, wq_col; wire [18:0] wq_row; wire [255:0] wq_data;
    wire [63:0] eop_d; reg wq_r;
    hfd_host_ingest dut (.rst_n(rst_n), .clk_h(clk_h), .h_v(h_v), .h_cls(h_cls), .h_d(h_d), .h_crn(h_crn), .t_v(t_v),
        .t_d(t_d), .t_cr(t_cr), .clk_i(clk_i), .ck(ck), .wq_v(wq_v), .wq_stack(wq_stack), .wq_pc(wq_pc), .wq_bank(wq_bank),
        .wq_row(wq_row), .wq_col(wq_col), .wq_data(wq_data), .wq_r(wq_r), .eop_v(eop_v), .eop_d(eop_d), .fault(fault));
    // host
    integer hcred = 16, di = 0, pi = 0, pleft = 0, hup = 0, dones = 0, fwords = 0;
    reg [31:0] rnd_h;
    wire host_done = di == nd && pleft == 0;
    always @(posedge clk_h) begin
        rnd_h = $random(seed);
        h_v <= 1'b0; t_cr <= 1'b0;
        if (rst_n) hup <= hup + 1;
        if (rst_n && hup >= 8) begin
            if (hcred + h_crn > 0 && !host_done) begin
                h_v <= 1'b1;
                if (pleft > 0) begin h_cls <= 2'd2; h_d <= pmem[pi]; pi <= pi + 1; pleft <= pleft - 1; end
                else begin h_cls <= 2'd1; h_d <= {256'd0, dmem[di]}; pleft <= nbm[di]; di <= di + 1; end
                hcred <= hcred + h_crn - 1;
            end else hcred <= hcred + h_crn;
            if (t_v) begin t_cr <= 1'b1; if (t_d[63:56] == 8'h01) dones <= dones + 1; else fwords <= fwords + 1; end
        end
    end
    // fabric
    integer ccyc = 0, writes = 0, idle = 0;
    reg [31:0] rnd_c;
    always @(posedge ck) begin
        ccyc <= ccyc + 1;
        rnd_c = $random(seed);
        wq_r <= (rnd_c % 100) >= stall;
        if (wq_v && wq_r) begin
            writes <= writes + 1;
            $fwrite(fd, "%0d %0d %0d %0d %0d %h\n", wq_stack, wq_pc, wq_bank, wq_row, wq_col, wq_data);
        end
        idle <= (host_done && dones >= nfence && !wq_v) ? idle + 1 : 0;
        if (rst_n && (idle >= 400 || ccyc > maxcyc || (fwords > 0 && idle >= 50))) begin
            $fclose(fd);
            $display("HHING descs=%0d beats=%0d/%0d writes=%0d dones=%0d/%0d fault_words=%0d fault=%0d ck_cycles=%0d timeout=%0d",
                     di, pi, np, writes, dones, nfence, fwords, fault, ccyc, ccyc > maxcyc);
            $finish;
        end
    end
endmodule

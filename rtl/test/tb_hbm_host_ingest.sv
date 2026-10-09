`timescale 1ps/1ps
// Bench of the HBM die's KV-ingest master hfd_host_ingest (stream ingest 2026-10-08): host stream -> ot_rom_host_ingest
// -> ot_hbm_ingest_xlat -> stack write requests.  Every write request is logged to wq.txt as "stack pc bank row col
// data"; tools/rtl_hbm_host_ingest_bench.py compares the set with the independent golden of the dskv_wb decode layout
// (tools/hbm_accel_dskv_wb.py sector_addr / owner_k).  Files: desc.mem, pay.mem, nb.mem.  +WQSTALL % of cycles the
// fabric is not ready.  Posted writes LAND (wq.txt) and are ACKed (ack_n) +ACKDLY (+ up to ACKJ) ck cycles after the
// handshake, in order.  Decode model: at every slot_done_v (the fenced completion) it reads the slot: a read is STALE if
// fewer writes have landed than the cumulative sectors of the fenced descriptors so far (cum.mem).  fence_stall = ck
// cycles a completion waited in the fence.
// Prints: HHING descs=.. beats=.. writes=.. dones=../.. fault_words=.. fault=.. ck_cycles=.. timeout=.. landed=.. stale=.. fence_stall=..
module tb_hbm_host_ingest #(parameter integer ND = 16, parameter integer NP = 4096, parameter integer FENCE = 1,
                            parameter integer HP = 1000, parameter integer IP = 1666, parameter integer CP = 833) ();
    reg clk_h = 0, clk_i = 0, ck = 0, rst_n = 0;
    always #(HP / 2) clk_h = ~clk_h;
    always #(IP / 2) clk_i = ~clk_i;
    always #(CP / 2) ck = ~ck;
    reg [255:0] dmem [0:ND-1];
    reg [511:0] pmem [0:NP-1];
    reg [31:0]  nbm  [0:ND-1];
    reg [31:0]  cum  [0:ND-1];
    integer nd, np, stall, maxcyc, seed, nfence, i, fd, ackdly, ackj;
    initial begin
        if (!$value$plusargs("ND=%d", nd)) nd = ND;
        if (!$value$plusargs("NP=%d", np)) np = NP;
        if (!$value$plusargs("WQSTALL=%d", stall)) stall = 0;
        if (!$value$plusargs("MAXCYC=%d", maxcyc)) maxcyc = 4000000;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        if (!$value$plusargs("ACKDLY=%d", ackdly)) ackdly = 2;
        if (!$value$plusargs("ACKJ=%d", ackj)) ackj = 1;
        $readmemh("cum.mem", cum);
        $readmemh("desc.mem", dmem); $readmemh("pay.mem", pmem); $readmemh("nb.mem", nbm);
        nfence = 0;
        for (i = 0; i < nd; i = i + 1) if (dmem[i][7]) nfence = nfence + 1;
        fd = $fopen("wq.txt", "w");
        #(20 * HP) rst_n = 1;
    end
    reg h_v; reg [1:0] h_cls; reg [511:0] h_d; wire [4:0] h_crn; wire t_v; wire [63:0] t_d; reg t_cr;
    wire wq_v, eop_v, fault; wire [1:0] wq_stack; wire [4:0] wq_pc, wq_bank, wq_col; wire [18:0] wq_row; wire [255:0] wq_data;
    wire [63:0] eop_d; reg wq_r; reg [5:0] ack_n; wire slot_done_v; wire [7:0] slot_done_tag;
    hfd_host_ingest #(.FENCE(FENCE)) dut (.rst_n(rst_n), .clk_h(clk_h), .h_v(h_v), .h_cls(h_cls), .h_d(h_d), .h_crn(h_crn), .t_v(t_v),
        .t_d(t_d), .t_cr(t_cr), .clk_i(clk_i), .ck(ck), .wq_v(wq_v), .wq_stack(wq_stack), .wq_pc(wq_pc), .wq_bank(wq_bank),
        .wq_row(wq_row), .wq_col(wq_col), .wq_data(wq_data), .wq_r(wq_r), .ack_n(ack_n), .slot_done_v(slot_done_v), .slot_done_tag(slot_done_tag), .eop_v(eop_v), .eop_d(eop_d), .fault(fault));
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
    integer ccyc = 0, writes = 0, idle = 0, landed = 0, sdone = 0, stale = 0, fstall = 0;
    reg [31:0] rnd_c;
    reg [299:0] pq [0:16383];
    integer     pt [0:16383];
    always @(posedge ck) begin
        ccyc <= ccyc + 1;
        rnd_c = $random(seed);
        wq_r <= (rnd_c % 100) >= stall;
        ack_n <= 6'd0;
        if (wq_v && wq_r) begin
            pq[writes % 16384] <= {wq_stack, wq_pc, wq_bank, wq_row, wq_col, wq_data};
            pt[writes % 16384] <= ccyc + ackdly + (rnd_c[23:8] % ackj);
            writes <= writes + 1;
        end
        // land + ACK in order, one a cycle
        if (landed < writes && pt[landed % 16384] <= ccyc) begin
            $fwrite(fd, "%0d %0d %0d %0d %0d %h\n", pq[landed % 16384][291:290], pq[landed % 16384][289:285],
                    pq[landed % 16384][284:280], pq[landed % 16384][279:261], pq[landed % 16384][260:256], pq[landed % 16384][255:0]);
            landed <= landed + 1; ack_n <= 6'd1;
        end
        // decode reads the slot at its fenced completion
        if (slot_done_v) begin
            if (landed < cum[sdone]) stale <= stale + 1;
            sdone <= sdone + 1;
        end
        if (!dut.a_empty && dut.is_done && !dut.a_pop) fstall <= fstall + 1;
        idle <= (host_done && dones >= nfence && !wq_v && landed == writes) ? idle + 1 : 0;
        if (rst_n && (idle >= 400 || ccyc > maxcyc || (fwords > 0 && idle >= 50))) begin
            $fclose(fd);
            $display("HHING descs=%0d beats=%0d/%0d writes=%0d dones=%0d/%0d fault_words=%0d fault=%0d ck_cycles=%0d timeout=%0d landed=%0d stale=%0d fence_stall=%0d slot_dones=%0d",
                     di, pi, np, writes, dones, nfence, fwords, fault, ccyc, ccyc > maxcyc, landed, stale, fstall, sdone);
            $finish;
        end
    end
endmodule

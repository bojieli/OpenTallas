`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Bench of the KV ingest engine (ot_hdc_kv_ingest) behind the HBM port arbiter
// (ot_hdc_ingest_arb), for tools/rtl_hdc_kv_ingest_campaign.py.
//
// Files (in the run directory, written by the campaign):
//   desc.mem  256-bit descriptors, in order        (ND of them)
//   pay.mem   512-bit payload beats, in order      (NP of them)
//   init.mem  the HBM image before ingest          (MEMW sectors)
//   exp.mem   the HBM image the golden expects     (MEMW sectors)
// The source posts descriptors and payload beats with random gaps (+DGAP,
// +PGAP: percent of cycles idle); a decode reader issues sector reads to its
// own region at +DUTY percent in bursts of +DON cycles (the decode chain's KV
// streams), so the arbiter's flow control is exercised; the memory takes a
// request when not stalled (+MSTALL percent) and returns reads after LAT
// cycles in order.  At the end every sector of the image is compared.
// Prints one line:  ING ... errors=E ...
// ---------------------------------------------------------------------------
module tb_hdc_kv_ingest #(
    parameter integer MEMW   = 65536,
    parameter integer ND     = 64,
    parameter integer NP     = 4096,
    parameter integer HDMAX  = 128,
    parameter integer KVHMAX = 8,
    parameter integer BURST  = 16,
    parameter integer LAT    = 40
) (input wire clk);
    localparam integer AW = 32;
    reg rst_n = 1'b0;
    reg [255:0] dmem [0:ND-1];
    reg [511:0] pmem [0:NP-1];
    reg [255:0] hbm  [0:MEMW-1];
    reg [255:0] expm [0:MEMW-1];
    integer share, idle_n = 0;
    integer nd, np, dgap, pgap, duty, don, mstall, seed, maxcyc, dec_base, dec_len;
    initial begin
        if (!$value$plusargs("ND=%d", nd)) nd = ND;
        if (!$value$plusargs("NP=%d", np)) np = NP;
        if (!$value$plusargs("DGAP=%d", dgap)) dgap = 0;
        if (!$value$plusargs("PGAP=%d", pgap)) pgap = 0;
        if (!$value$plusargs("DUTY=%d", duty)) duty = 0;
        if (!$value$plusargs("DON=%d", don)) don = 64;
        if (!$value$plusargs("MSTALL=%d", mstall)) mstall = 0;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        if (!$value$plusargs("SHARE=%d", share)) share = 64;
        if (!$value$plusargs("MAXCYC=%d", maxcyc)) maxcyc = 50000000;
        if (!$value$plusargs("DECBASE=%d", dec_base)) dec_base = 0;
        if (!$value$plusargs("DECLEN=%d", dec_len)) dec_len = 1024;
        $readmemh("desc.mem", dmem);
        $readmemh("pay.mem", pmem);
        $readmemh("init.mem", hbm);
        $readmemh("exp.mem", expm);
    end

    // -- source -------------------------------------------------------------------
    integer di = 0, pi = 0;
    reg [31:0] rnd_d, rnd_p, rnd_m, rnd_o;
    wire d_v = rst_n && di < nd && (rnd_d % 100) >= dgap;
    wire p_v = rst_n && pi < np && (rnd_p % 100) >= pgap;
    wire d_rdy, in_rdy;

    // -- DUT ------------------------------------------------------------------------
    wire          iw_v, iw_rdy, ir_v, ir_rdy, done_v, busy;
    wire [AW-1:0] iw_addr, ir_addr;
    wire [255:0]  iw_data;
    reg           rd_v;
    reg  [255:0]  rd_data;
    wire [7:0]    done_tag;
    wire [31:0]   n_sectors, n_beats;
    ot_hdc_kv_ingest #(.AW(AW), .HDMAX(HDMAX), .KVHMAX(KVHMAX)) dut (
        .clk(clk), .rst_n(rst_n),
        .d_v(d_v), .d_rdy(d_rdy), .d_data(dmem[di]),
        .in_v(p_v), .in_rdy(in_rdy), .in_data(pmem[pi]),
        .w_v(iw_v), .w_rdy(iw_rdy), .w_addr(iw_addr), .w_data(iw_data),
        .r_v(ir_v), .r_rdy(ir_rdy), .r_addr(ir_addr), .rd_v(rd_v), .rd_data(rd_data),
        .done_v(done_v), .done_tag(done_tag), .busy(busy), .n_sectors(n_sectors), .n_beats(n_beats));

    // the ingest side's single request stream: writes, else RMW reads
    wire          i_v = iw_v || ir_v;
    wire          i_we = iw_v;
    wire [AW-1:0] i_addr = iw_v ? iw_addr : ir_addr;
    wire          i_rdy;
    assign iw_rdy = i_rdy && iw_v;
    assign ir_rdy = i_rdy && !iw_v;

    // decode reader: DUTY percent of cycles requesting, in bursts of DON cycles
    reg           dec_on;
    integer       dec_ph, dec_ptr;
    wire          dec_v = rst_n && dec_on;
    wire          dec_rdy;
    wire          m_v, m_we, m_src;
    wire [AW-1:0] m_addr;
    wire [255:0]  m_wdata;
    wire [31:0]   c_dec, c_ing, c_dwait;
    wire          m_rdy = (rnd_m % 100) >= mstall;
    ot_hdc_ingest_arb #(.AW(AW), .BURST(BURST)) arb (
        .clk(clk), .rst_n(rst_n), .share(share[8:0]),
        .d_v(dec_v), .d_rdy(dec_rdy), .d_addr(dec_base + dec_ptr),
        .i_v(i_v), .i_rdy(i_rdy), .i_we(i_we), .i_addr(i_addr), .i_wdata(iw_data),
        .m_v(m_v), .m_rdy(m_rdy), .m_we(m_we), .m_addr(m_addr), .m_wdata(m_wdata), .m_src(m_src),
        .c_dec(c_dec), .c_ing(c_ing), .c_dwait(c_dwait));

    // memory: writes land at once; ingest reads return in order after LAT
    reg [255:0] rq_d [0:1023];
    integer     rq_t [0:1023];
    integer     rq_w = 0, rq_r = 0;
    integer     cyc = 0, t_first = -1, t_last = 0, errors = 0, i, dec_req = 0, oob = 0, dones = 0;
    integer     dec_burst_n = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        rnd_d <= $random; rnd_p <= $random; rnd_m <= $random; rnd_o <= $random;
        // decode duty cycle: bursts of DON cycles on, spaced to average DUTY %
        if (!rst_n) begin dec_on <= 1'b0; dec_ph <= 0; dec_ptr <= 0; end
        else begin
            if (duty > 0) begin
                dec_ph <= (dec_ph + 1 >= don * 100 / duty) ? 0 : dec_ph + 1;
                dec_on <= (dec_ph < don);
            end else dec_on <= 1'b0;
            if (dec_v) dec_req <= dec_req + 1;
            if (dec_v && dec_rdy) dec_ptr <= (dec_ptr + 1) % dec_len;
        end
        if (d_v && d_rdy) di <= di + 1;
        if (p_v && in_rdy) begin
            pi <= pi + 1;
            if (t_first < 0) t_first <= cyc;
        end
        if (m_v && m_rdy && m_src) begin
            if (m_addr >= MEMW) oob <= oob + 1;
            else if (m_we) hbm[m_addr] <= m_wdata;
            else begin rq_d[rq_w % 1024] <= hbm[m_addr]; rq_t[rq_w % 1024] <= cyc + LAT; rq_w <= rq_w + 1; end
            if (m_we) t_last <= cyc;
        end
        rd_v <= 1'b0;
        if (rq_r != rq_w && rq_t[rq_r % 1024] <= cyc) begin
            rd_v <= 1'b1; rd_data <= rq_d[rq_r % 1024]; rq_r <= rq_r + 1;
        end
        if (done_v) dones <= dones + 1;
        // finished: everything posted, the engine idle for 4 cycles (the last done pulse seen)
        idle_n <= (di == nd && pi == np && !busy && rq_r == rq_w) ? idle_n + 1 : 0;
        if (rst_n && ((idle_n >= 4 && cyc > 20) || cyc > maxcyc)) begin
            for (i = 0; i < MEMW; i = i + 1)
                if (hbm[i] !== expm[i]) begin
                    if (errors < 4) $display("MISMATCH sector=%0d got=%h exp=%h", i, hbm[i], expm[i]);
                    errors = errors + 1;
                end
            $writememh("final.mem", hbm);
            $display("ING descs=%0d beats=%0d/%0d sectors=%0d errors=%0d oob=%0d dones=%0d cycles=%0d first=%0d last=%0d dec_req=%0d dec_grant=%0d ing_grant=%0d dec_wait=%0d timeout=%0d",
                     di, n_beats, np, n_sectors, errors, oob, dones, cyc, t_first, t_last, dec_req, c_dec, c_ing,
                     c_dwait, cyc > maxcyc);
            $finish;
        end
    end
endmodule

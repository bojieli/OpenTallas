`timescale 1ns/1ps
// TLOAD-ROMSTAGE bench (DIE-QC-97 11-11).  Old = qfd_dv_slice_tload as the flattened kits synthesise it today (default
// parameters: CAPTURE_STAGE 0, LOCAL_JOIN 0, NWC 34).  New = OT_QC_TLCAP (CAPTURE_STAGE 1, LOCAL_JOIN 1, the closed ns4
// profile the OT_S6_SIM benches simulate).  Same inputs every edge (requests, illegal stages, early requests while busy,
// random stream writes = other_table_write, periodic resets).  Claim checked every edge:
//   loader bundle  new.u_ld.{tw_we,tw_kind,tw_addr,tw_data,done}(E+1) == old.u_ld.{...}(E)   (exactly +1 edge)
//   sticky fault   old(E-1) <= new(E) <= old(E): request-reject faults same edge, ROM-data faults +1 edge
//   kept copies    every tw_we_k copy == tw_we (34 old / 67 new)
//   joined face    new.tw_*(E+1) == old.tw_*(E) on loader-write edges with no stream write at E / E+1; with no loader
//                  write in either form both faces equal (stream bundle, s_we on a stream-only edge)
// MUT (must FAIL): 1 = new CAPTURE_MUT 1 (metadata bypass), 2 = new CAPTURE_MUT 2 (early done), 9 = claim +0 edges.
// Behavioural ROM (bench only): hashed payload, metadata field [265:226] of every macro = {13 zero, addr 24, kind 2, we 1}
// legal for its kind except ~1/32 rows (forced invalid).
module ot_rom_4096x266_m8 #(parameter string VIAMAP = "", parameter string INSTANCE = "") (
    input wire clk, input wire ce_in, input wire [11:0] addr_in, output reg [265:0] rd_out);
    function automatic [31:0] h32(input [31:0] x);
        reg [31:0] y; begin y = x * 32'h9E3779B1; y = y ^ (y >> 15); y = y * 32'h85EBCA77; h32 = y ^ (y >> 13); end
    endfunction
    function automatic [265:0] word(input [11:0] a);
        reg [265:0] w; reg [31:0] r; reg [1:0] k; reg [23:0] la; integer i;
        begin
            for (i = 0; i < 9; i = i + 1) begin r = h32({a, 4'(i), 16'h5a3c}); w[32*i +: 32] = r; end
            r = h32({a, 20'hc0ffe});
            k = (r[1:0] == 0) ? 2'd1 : r[1:0];
            la = (k == 3) ? {18'd0, r[13:8]} : (k == 2) ? {17'd0, 7'(r[14:8] % 72) & 7'h7c} : {17'd0, r[14:8]};
            w[265:226] = {13'd0, la, k, r[3] | r[4]};
            if (r[20:16] == 0) w[265] = 1'b1;             // forced invalid metadata (top bit non-zero)
            word = w;
        end
    endfunction
    always @(posedge clk) if (ce_in) rd_out <= word(addr_in);
endmodule

module tb_tload_romstage #(parameter integer MUT = 0, parameter integer EDGES = 200000) ();
    reg ck = 0; always #0.4165 ck = ~ck;
    reg rst_n = 0;
    reg [8:0] treq = 0;
    reg s_we = 0; reg [1:0] s_kind = 0; reg [23:0] s_addr = 0; reg [1023:0] s_data = 0;
    wire a_we, b_we; wire [1:0] a_kind, b_kind; wire [23:0] a_addr, b_addr; wire [1023:0] a_data, b_data;
    wire a_busy, b_busy, a_done, b_done, a_fault, b_fault;
    localparam integer BMUT = (MUT == 1 || MUT == 2) ? MUT : 0;
    qfd_dv_slice_tload A (.ck(ck), .rst_n(rst_n), .treq(treq), .s_we(s_we), .s_kind(s_kind), .s_addr(s_addr),
        .s_data(s_data), .tw_we(a_we), .tw_kind(a_kind), .tw_addr(a_addr), .tw_data(a_data), .busy(a_busy),
        .done(a_done), .fault(a_fault));
    qfd_dv_slice_tload #(.CAPTURE_STAGE(1), .LOCAL_JOIN(1), .CAPTURE_MUT(BMUT)) B (.ck(ck), .rst_n(rst_n), .treq(treq),
        .s_we(s_we), .s_kind(s_kind), .s_addr(s_addr), .s_data(s_data), .tw_we(b_we), .tw_kind(b_kind), .tw_addr(b_addr),
        .tw_data(b_data), .busy(b_busy), .done(b_done), .fault(b_fault));
    // loader bundles (u_ld outputs)
    wire [1+2+24+1024+1-1:0] la = {A.l_we, A.l_kind, A.l_addr, A.l_data, A.done};
    wire [1+2+24+1024+1-1:0] lb = {B.l_we, B.l_kind, B.l_addr, B.l_data, B.done};
    wire [1+2+24+1024-1:0] fa = {a_we, a_kind, a_addr, a_data};
    wire [1+2+24+1024-1:0] fb = {b_we, b_kind, b_addr, b_data};
    reg [1+2+24+1024+1-1:0] la_q; reg [1+2+24+1024-1:0] fa_q; reg s_we_q = 0;
    reg [31:0] s = 32'h2468ace1; reg [5:0] stg; integer wcls = 0;
    integer e, last_req = -1000, skip_until = 0, n_chk = 0, n_wr = 0, n_done = 0, n_fault_ev = 0, n_req = 0,
            n_early = 0, n_fault_same = 0, n_fault_late = 0, n_bad_stage = 0, n_sonly = 0, n_face = 0, n_rst = 0, n_lat = 0;
    reg pa_fault = 0, a_lwe_q = 0, a_fault_q = 0;
    // latency probe (first legal request after each reset)
    integer t_req = -1, a_first = -1, b_first = -1, a_last = -1, b_last = -1, a_dn = -1, b_dn = -1, probe = 0;
    task automatic fail(input [8*40-1:0] what); begin
        $display("TLOAD_ROMSTAGE MISMATCH %0s edge %0d MUT %0d", what, e, MUT); $fatal(1); end endtask
    function automatic [31:0] xs(input [31:0] x); reg [31:0] y; begin
        y = x ^ (x << 13); y = y ^ (y >> 17); xs = y ^ (y << 5); end endfunction
    initial begin
        for (e = 0; e < EDGES; e = e + 1) begin
            @(negedge ck);
            s = xs(s); wcls = (e / 4000) % 3;
            // periodic reset (idle loader), compare window skipped around it
            if (e == 3) rst_n = 1;      // (last_req after a reset: no "early" request may land in an idle loader)
            if (e > 100 && e % 4000 == 0) begin rst_n = 0; n_rst = n_rst + 1; skip_until = e + 12; probe = 0; last_req = e - 60; end
            if (e > 100 && e % 4000 == 3) rst_n = 1;
            treq = 0;
            if (rst_n && e > skip_until + 6) begin
                if (e - last_req >= 110 && s[5:0] < 6) begin
                    // reset window class (e / 4000) % 3: 0 = illegal stages only (0, 37..39: same-edge rejects);
                    // 1 = legal stages, no stream writes, a request while busy (same-edge reject unless a ROM-data
                    // fault came first); 2 = legal stages, random stream writes (ROM-data faults, +1 edge)
                    stg = (wcls == 0) ? ((s[9:8] == 0) ? 6'd0 : 6'd36 + 6'(s[9:8])) : (6'd1 + (s[13:8] % 6'd36));
                    treq = {1'b1, stg, s[15:14]}; last_req = e; n_req = n_req + 1;
                    if (stg == 0 || stg > 36) n_bad_stage = n_bad_stage + 1;
                    else if (probe == 0) begin probe = 1; t_req = e; a_first = -1; b_first = -1; a_dn = -1; b_dn = -1; end
                end else if ((wcls == 1 && e - last_req == 12) || (wcls == 2 && e - last_req > 8 && e - last_req < 70 && s[17:6] == 0)) begin
                    treq = {1'b1, 6'd5, s[15:14]}; n_early = n_early + 1;   // request while busy: both must fault
                end
            end
            s_we = (wcls != 1) && (s[31:27] == 0); s_kind = s[26:25]; s_addr = {s[24:18], s[31:15]};
            s_data = {32{s ^ 32'(e)}};
            @(posedge ck); #0.01;
            if (MUT == 77 && e >= 24990 && e <= 25040)
                $display("TR %0d rst %b treq %b rqv %b/%b ps %b/%b st %0d/%0d busy %b/%b r2 %b/%b cr %b act %b/%b f %b/%b lreq %0d", e, rst_n, treq[8],
                    A.rq_v, B.rq_v, A.u_ld.p_start, B.u_ld.p_start, A.u_ld.p_stage, B.u_ld.p_stage, A.busy, B.busy,
                    A.u_ld.r2, B.u_ld.r2, B.u_ld.ctrl_reset, A.u_ld.active, B.u_ld.active, A.l_fault, B.l_fault, last_req);
            if (probe == 1) begin
                if (A.l_we && a_first < 0) a_first = e; if (B.l_we && b_first < 0) b_first = e;
                if (A.l_we) a_last = e; if (B.l_we) b_last = e;
                if (A.done && a_dn < 0) a_dn = e; if (B.done && b_dn < 0) b_dn = e;
                if (b_dn >= 0 && e > b_dn + 2) begin
                    probe = 2; n_lat = n_lat + 1;
                    if (n_lat <= 3 || b_first - a_first != 1 || b_last - a_last != 1 || b_dn - a_dn != 1)
                        $display("TLOAD_ROMSTAGE LAT req_edge %0d: old first/last write +%0d/+%0d done +%0d; new +%0d/+%0d done +%0d",
                                 t_req, a_first - t_req, a_last - t_req, a_dn - t_req, b_first - t_req, b_last - t_req, b_dn - t_req);
                    if (b_first - a_first != 1 || b_last - a_last != 1 || b_dn - a_dn != 1) fail("latency delta");
                end
            end
            // kept copies
            if (A.l_we_k !== {34{A.l_we}}) fail("old tw_we_k copy");
            if (B.l_we_k !== {67{B.l_we}}) fail("new tw_we_k copy");
            if (e > 4 && e > skip_until) begin
                if (MUT == 9) begin if (lb !== la) fail("+0 edge claim"); end
                else if (lb !== la_q) begin
                    fail("loader bundle +1"); end
                if (!s_we && !s_we_q && MUT != 9 && (B.l_we || a_lwe_q)) begin
                    if (fb !== fa_q) fail("joined face +1"); n_face = n_face + 1; end
                if (!A.l_we && !B.l_we && fb !== fa) fail("idle/stream edge face");
                if (s_we && !A.l_we && !B.l_we) begin
                    if (fa !== {1'b1, s_kind, s_addr, s_data} || fb !== {1'b1, s_kind, s_addr, s_data}) fail("stream-only edge");
                    n_sonly = n_sonly + 1;
                end
                // sticky fault: request-reject faults (busy / bad stage) rise on the same edge in both forms (the p_start
                // check is not behind the ROM), ROM-data faults (invalid metadata / stream write on a loader read) one
                // edge later in the new form: old(E-1) <= new(E) <= old(E) on every edge.
                if (MUT != 9 && ((a_fault_q && !B.l_fault) || (B.l_fault && !A.l_fault))) fail("fault window");
                if (B.l_fault && !pa_fault) begin
                    if (A.l_fault && !a_fault_q) n_fault_same = n_fault_same + 1; else n_fault_late = n_fault_late + 1; end
                n_chk = n_chk + 1;
                if (B.l_we) n_wr = n_wr + 1;
                if (B.done) n_done = n_done + 1;
                if (B.l_fault && !pa_fault) n_fault_ev = n_fault_ev + 1;
            end
            pa_fault = B.l_fault;
            la_q = la; fa_q = fa; s_we_q = s_we; a_lwe_q = A.l_we; a_fault_q = A.l_fault;
        end
        if (n_wr < 1000 || n_done < 10 || n_fault_same < 2 || n_fault_late < 2 || n_lat < 1) begin
            $display("COVERAGE writes %0d done %0d same %0d late %0d lat %0d", n_wr, n_done, n_fault_same, n_fault_late, n_lat);
            fail("coverage"); end
        $display("TLOAD_ROMSTAGE_EQ PASS edges %0d checks %0d new_writes %0d done %0d fault_events %0d (same-edge reject %0d, +1 data %0d) requests %0d early %0d bad_stage %0d stream_only %0d face_checks %0d resets %0d lat_probes %0d",
                 EDGES, n_chk, n_wr, n_done, n_fault_ev, n_fault_same, n_fault_late, n_req, n_early, n_bad_stage, n_sonly, n_face, n_rst, n_lat);
        $finish;
    end
endmodule

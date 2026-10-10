`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81_boot_seq (stream ds-control, 2026-10-08): the boot load of the S81 die's HBM-resident tables (gap B03 / C09
// of the T2 coverage ledger: nothing loaded the HBM RoPE table at boot, so ot_chip_v41x_rope_hbm_cache read an empty
// region).  It sits on the die face of the host / ingest block (dsfd_host = ot_rom_host_ingest, stream ingest) and
// splits that face's sector writes:
//   * o_addr[31] = 0: the KV ingest image (GPU prefill) -> kv_* (the die's KV write fabric, unchanged);
//   * o_addr[31] = 1: a static boot region, logical sector E = o_addr[30:0] (RAW descriptors).  E0 .. E0 + 16 * MAX_POS
//     is the RoPE region: two tables (kind 0 plain, kind 1 YaRN), each MAX_POS positions x 8 sectors; sector
//     E = E0 + kind * 8 * MAX_POS + 8 * pos + 2 * s + j is pair-sector j of position pos on HBM stack s (stack s owns
//     pair indices 8s .. 8s+7, 2 sectors a position: the ot_chip_v41x_rope_hbm_cache layout), written to stack s at
//     (kind ? yarn_base : plain_base)[s] + 2 * pos + j (the die region ledger's bases, ot_chip_v41x_rope_region_guard).
//     Writes leave on the per-stack boot write ports w_* (into the stack's SECDED write encoder, ot_s81_hbm_secded_wr);
//   * the BOOT_END marker (o_addr all ones, o_d[63:0] = {checksum, expected sectors}, emitted by ot_rom_host_ingest in
//     order behind every sector of the descriptors before it): the boot sequencer compares the sectors it routed since
//     the previous marker and their checksum -- the sum mod 2^32 of zlib.crc32({E as 4 bytes LE, the 32 data bytes}),
//     the emb-hbm boot convention -- and requires every table it touched to be COMPLETE (8 * MAX_POS sectors).  On a
//     match the tables become present (table_present -> the RoPE cache's table_present, the region guard); boot_ok
//     = every table this die NEEDs is present.  boot_ok gates the die's job acceptance (ot_s81_pkg_ctrl) and, on the
//     stage-0 die, the host queue's LAUNCH.
// Flow control: an input FIFO of OCRED entries (= ot_rom_host_ingest's OCRED die-fabric credits); one credit (i_cr)
// returns per entry popped.  The checksum pipeline is 2 registers deep (CRC-32 over 288 bits, then the sum).
// Faults (sticky, first code): 1 static sector outside every boot table (or a table this die does not need), 2 marker
// checksum / count mismatch, 3 marker over an incomplete table, 4 input FIFO overflow (credits violated), 5 static read rejected.
// MUT (bench negative controls): 1 = the marker is accepted without the checksum compare.
// Boot cost (full scale, 1M positions): 2 tables x 8 x 2^20 sectors x 32 B = 512 MiB per die (128 MiB a stack), at
// the die face's 1 sector / cycle = 38.4 GB/s: 14.0 ms per die, all dies in parallel.  Off the token path.
// ---------------------------------------------------------------------------
module ot_s81_boot_seq #(
    parameter integer HAW     = 30,
    parameter integer MAX_POS = 1048576,     // power of two
    parameter integer E0      = 0,
    parameter [1:0]   NEED    = 2'b11,       // tables this die needs (bit 0 plain, bit 1 YaRN)
    parameter integer OCRED   = 8,
    parameter integer MUT     = 0
) (
    input  wire               ck,
    input  wire               rst_n,
    // die face of the host / ingest block
    input  wire               i_v,
    input  wire               i_we,
    input  wire [31:0]        i_addr,
    input  wire [255:0]       i_d,
    output reg                i_cr,
    // KV ingest sectors (o_addr[31] = 0) to the die's KV write fabric
    output wire               kv_v,
    output wire               kv_we,
    output wire [30:0]        kv_a,
    output wire [255:0]       kv_d,
    input  wire               kv_rdy,
    // region ledger
    input  wire [4*HAW-1:0]   plain_base,
    input  wire [4*HAW-1:0]   yarn_base,
    // boot writes, per HBM stack
    output reg  [3:0]         w_v,
    output reg  [4*HAW-1:0]   w_a,
    output reg  [4*256-1:0]   w_d,
    input  wire [3:0]         w_rdy,
    // status
    output reg  [1:0]         table_present,
    output wire               boot_ok,
    output reg                fault,
    output reg  [3:0]         fault_code,
    output reg  [31:0]        st_sectors,
    output reg  [31:0]        st_markers
);
    localparam integer PB = $clog2(MAX_POS);
    localparam [31:0]  TSEC = 32'(MAX_POS) * 8;            // sectors of one table
    localparam integer FB = $clog2(OCRED);
`ifndef SYNTHESIS
    initial if ((1 << PB) != MAX_POS || (1 << FB) != OCRED) $fatal(1, "ot_s81_boot_seq: MAX_POS, OCRED powers of two");
`endif
    // ---- input FIFO ----
    reg [288:0] fq [0:OCRED-1];                            // {we, addr, data}
    reg [FB-1:0] fw, fr;
    reg [FB:0]   fn;
    wire [288:0] hd = fq[fr];
    wire         h_we = hd[288];
    wire [31:0]  h_a  = hd[287:256];
    wire [255:0] h_d  = hd[255:0];
    wire         h_mark = (fn != 0) && h_we && (h_a == 32'hFFFF_FFFF);
    wire         h_stat = (fn != 0) && !h_mark && h_a[31];
    wire         h_kv   = (fn != 0) && !h_mark && !h_a[31];
    wire [30:0]  h_e    = h_a[30:0] - 31'(E0);
    wire         h_kind = h_e[PB+3];
    wire         h_inr  = (h_a[30:0] >= 31'(E0)) && (h_e < 31'(2 * TSEC)) && NEED[h_kind];
    wire [PB-1:0] h_pos = h_e[PB+2:3];
    wire [1:0]   h_s    = h_e[2:1];
    wire         h_j    = h_e[0];
    // w_rdy transfers ownership to an ordered write service: subsequently accepted
    // reads must observe accepted writes. If the service does not provide that
    // ordering, its adapter must withhold w_rdy until the write is committed.
    // ---- marker handling: wait for both checksum and stack writes to drain ----
    reg  [1:0]   mk_wait;                                  // marker popped, cycles until the sum is final
    reg  [63:0]  mk_d;
    reg          a_v; reg [30:0] a_e; reg [255:0] a_d;     // checksum stage A
    reg          b_v; reg [31:0] b_crc;                    // stage B
    reg  [31:0]  sum, cnt; reg [31:0] cnt_k [0:1];
    // Ordered sectors within each table make the completion count a coverage proof.
    wire         h_order = h_e[PB+2:0] == cnt_k[h_kind];
    wire         w_free = !w_v[h_s] || w_rdy[h_s];
    wire         pop = (mk_wait == 0) &&
                       ((h_mark && !a_v && !b_v && !(|w_v)) ||
                        (h_stat && (!h_we || !h_inr || w_free)) ||
                        (h_kv && kv_rdy));
    assign kv_v = h_kv && (mk_wait == 0); assign kv_we = h_we; assign kv_a = h_a[30:0]; assign kv_d = h_d;
    assign boot_ok = !fault && ((table_present & NEED) == NEED);

    function automatic [31:0] crc_sector(input [30:0] e, input [255:0] d);
        reg [287:0] m; reg [31:0] c; integer i;
        begin
            m = {d, 1'b0, e}; c = 32'hffffffff;
            for (i = 0; i < 288; i = i + 1) c = (c >> 1) ^ ((c[0] ^ m[i]) ? 32'hedb88320 : 32'h0);
            crc_sector = ~c;
        end
    endfunction
    function automatic [HAW-1:0] base_of(input k, input [1:0] s);
        base_of = k ? yarn_base[s*HAW +: HAW] : plain_base[s*HAW +: HAW];
    endfunction

    integer s;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            fw <= 0; fr <= 0; fn <= 0; i_cr <= 1'b0;
            w_v <= 4'b0; w_a <= 0; w_d <= 0;
            table_present <= 2'b00; fault <= 1'b0; fault_code <= 0; st_sectors <= 0; st_markers <= 0;
            mk_wait <= 0; mk_d <= 0; a_v <= 1'b0; a_e <= 0; a_d <= 0; b_v <= 1'b0; b_crc <= 0;
            sum <= 0; cnt <= 0; cnt_k[0] <= 0; cnt_k[1] <= 0;
        end else begin
            i_cr <= pop;
            // FIFO
            if (i_v) begin
                if (fn == OCRED[FB:0] && !pop) begin fault <= 1'b1; if (fault_code == 0) fault_code <= 4'd4; end
                else begin fq[fw] <= {i_we, i_addr, i_d}; fw <= fw + 1'b1; end
            end
            if (pop) fr <= fr + 1'b1;
            fn <= fn + ((i_v && !(fn == OCRED[FB:0] && !pop)) ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
            // stack write ports: a write is held until taken
            for (s = 0; s < 4; s = s + 1) if (w_v[s] && w_rdy[s]) w_v[s] <= 1'b0;
            // static sector
            a_v <= 1'b0;
            if (pop && h_stat) begin
                if (!h_we) begin fault <= 1'b1; if (fault_code == 0) fault_code <= 4'd5; end
                else if (!h_inr || !h_order) begin fault <= 1'b1; if (fault_code == 0) fault_code <= 4'd1; end
                else begin
                    w_v[h_s] <= 1'b1;
                    w_a[h_s*HAW +: HAW] <= base_of(h_kind, h_s) + {{(HAW-PB-1){1'b0}}, h_pos, h_j};
                    w_d[h_s*256 +: 256] <= h_d;
                    cnt_k[h_kind] <= cnt_k[h_kind] + 1;
                end
                a_v <= 1'b1; a_e <= h_a[30:0]; a_d <= h_d;
                st_sectors <= st_sectors + 1;
            end
            // checksum pipeline
            b_v <= a_v;
            if (a_v) b_crc <= crc_sector(a_e, a_d);
            if (b_v) begin sum <= sum + b_crc; cnt <= cnt + 1; end
            // marker
            if (pop && h_mark) begin mk_wait <= 2'd1; mk_d <= h_d[63:0]; end
            else if (mk_wait == 2'd1) begin : mark
                reg ok_sum, inc0, inc1;
                ok_sum = (MUT == 1) || (sum == mk_d[63:32] && cnt == mk_d[31:0]);
                inc0 = cnt_k[0] != 0 && cnt_k[0] != TSEC;
                inc1 = cnt_k[1] != 0 && cnt_k[1] != TSEC;
                st_markers <= st_markers + 1;
                if (!ok_sum) begin fault <= 1'b1; if (fault_code == 0) fault_code <= 4'd2; end
                else if (inc0 || inc1) begin fault <= 1'b1; if (fault_code == 0) fault_code <= 4'd3; end
                else table_present <= table_present | {cnt_k[1] == TSEC, cnt_k[0] == TSEC};
                sum <= 0; cnt <= 0; cnt_k[0] <= 0; cnt_k[1] <= 0; mk_wait <= 0;
            end
        end
    end
endmodule

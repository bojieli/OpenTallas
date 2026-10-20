`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsdv_sh_sd (RTL-BUILD-S81 10-18): a FORK of rtl/dsrom_sys/s81_ingest/dsfd_host_sd.sv (kept byte-identical there for the
// closed dsfd_host views) with the HALF route below; everything else verbatim.
// dsfd_host_sd (s81-svceng-1011 host side, 2026-10-11): per-stack decode of the S81 host block's ONE die-face sector
// stream (dsfd_host o_v / o_we / o_addr 32 / o_d 256; the host holds OCRED = 8 credits, o_cr returns one a pulse)
// into one host-write port per HBM stack client (svc_<st> / eng_SE): hw<s> / hc<s>.
//   class   marker (o_addr == 32'hffffffff): o_d[65:64] 3 Engram, 2 RoPE, other = fault;
//           else o_addr[31] = 0 KV, o_addr[31:30] = 2'b10 RoPE, 2'b11 Engram.  o_we = 0 (an RMW read; the DS dies run
//           RMW_EN 0) = fault.
//   route   KV sector -> the k-th KV stack (set bits of KVS, ascending), k = (o_addr >> 5) mod #KV stacks;
//           RoPE sector -> the first KV stack; RoPE marker -> every KV stack; Engram sector / marker -> stack ENG only
//           (ENG < 0: Engram class is a fault).  A faulting word is dropped (its credit returned) and fault is sticky.
//   flow    registered input pins -> 8-entry FIFO (the host's 8 credits; o_cr pulses on every pop) -> one word a cycle
//           in order to its stack(s), only against that stack's credits (SCRED, hc cr returns one); a multicast marker
//           waits for a credit in every destination.
//   hw<s>   = {cls 2 (0 KV, 1 RoPE, 2 Engram), we, addr 32, d 256, v} (292 b) from flops (markers keep addr ffffffff and
//           d; Engram aperture CSR words are Engram markers with d[255] = 1);  hc<s> = {ack 8, cr} (9 b) into pin flops: ack = host
//           sector physical write completions of the cycle (count), summed into host_ack_n (registered; > 255 = fault)
//           for the host's visibility fence (dsfd_host_native ack_n).
// MUT (negative controls): 1 KV stack from o_addr >> 6, 2 every 50th stack credit return dropped, 3 Engram -> stack 0.
// ---------------------------------------------------------------------------------------------------------------
module dsdv_sh_sd #(
    parameter integer NS = 2,
    parameter integer KVS = 1,          // bit s: stack s holds KV / RoPE
    parameter integer ENG = 1,          // Engram client stack (-1: none)
    parameter integer SCRED = 8,
    // Static on-chip service: a missing reserved return faults; it never
    // postpones the head service edge. Legacy init-boundary mode is default.
    parameter integer STATIC = 0,
    // HALF (RTL-BUILD-S81 10-18, default 0 = unchanged): S81-DV per-half host writes (NS = 2: stack 0 = W entry rsv_05,
    // stack 1 = E entry rsv_11).  A KV / RoPE sector goes to the half that owns its HBM PC: pc = the svc PC hash of
    // addr[29:0] (dsdv_svc_att pcmap: (a >> 2) ^ (a >> 7) ^ (a >> 12), bits [4:0]; PCs 0..15 = slices 0..7 = W); a marker
    // goes to every KV stack (KVS), as before.  HALF = 2 is a bench negative control only (routes by pc bit 3).
    parameter integer HALF = 0,
    parameter integer MUT = 0
) (
    input  wire              ck,
    input  wire              rst_n,
    input  wire              o_v,
    input  wire              o_we,
    input  wire [31:0]       o_addr,
    input  wire [255:0]      o_d,
    output reg               o_cr,
    output reg  [292*NS-1:0] hw,
    input  wire [9*NS-1:0]   hc,
    output reg  [7:0]        host_ack_n,
    output reg               fault
);
    // ---- reset: the port drives only the relay (design standard); release 3 cycles after the port
    wire rn;
`ifdef OT_S81_SH_APIPE9
    wire [7:0] reset_regions__ot_rlv;
    ot_rst_relay #(.REGIONS(8)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(reset_regions__ot_rlv));
    assign rn = reset_regions__ot_rlv[0];
`else
    ot_rst_relay #(.REGIONS(1)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rn));
`endif
    // ---- pin flops
    reg iv; reg iwe; reg [31:0] ia; reg [255:0] id; reg [9*NS-1:0] hc_q;
    always @(posedge ck or negedge rn)
        if (!rn) begin iv <= 1'b0; hc_q <= {9*NS{1'b0}}; end
        else begin iv <= o_v; hc_q <= hc; end
    always @(posedge ck) begin iwe <= o_we; ia <= o_addr; id <= o_d; end
    // ---- FIFO
    reg [2:0] wp, rp; reg [3:0] n;
`ifdef OT_S81_SH_SRAM
    wire [288:0] h;
    reg head_v;
    wire head_ready=head_v;
    wire sd_pop;
    wire [2:0] read_next=rp+sd_pop;
    wire have_next=n>{3'd0,sd_pop};
    wire [545:0] mem_q;
`ifdef OT_S81_SH_RSZ
    // S81-SHLK s10: one right-sized 16x289 dual-clock master (both clocks ck), rows 8..15 unused, address zero-extended
`ifdef OT_S81_SH_P192
    // Same synchronous dual-clock contract; source-pinned p192 contact master.
    ot_sram_1r1w2c_16x289_m1_p192 u_mem(
`else
    ot_sram_1r1w2c_16x289_m1 u_mem(
`endif
.wclk(ck),.rclk(ck),.r_ce_in(rn&&have_next),.r_addr_in({1'b0,read_next}),.rd_out(mem_q[288:0]),
      .w_ce_in(rn&&iv),.w_addr_in({1'b0,wp}),.wd_in({iwe,ia,id}),.w_mask_in({289{1'b1}}));
    assign mem_q[545:289] = 257'd0;
`elsif OT_S81_SH_BANK64
    // S81-SHLK s10: four native 32x64 banks for the 256 data bits (see ot_dsdv_host_afifo_sram) instead of the
    // pin-limited 16x546 macro; {we, addr} (33 b) in an 8 x 33 flop array with the same synchronous held read
    genvar mb;
    for (mb = 0; mb < 4; mb = mb + 1) begin : g_bank
        ot_sram_1r1w2c_32x64_m1 u_mem(.wclk(ck),.rclk(ck),.r_ce_in(rn&&have_next),.r_addr_in({2'b0,read_next}),
          .rd_out(mem_q[mb*64+:64]),.w_ce_in(rn&&iv),.w_addr_in({2'b0,wp}),.wd_in(id[mb*64+:64]),.w_mask_in({64{1'b1}}));
    end
    reg [32:0] sd_tm [0:7];
    reg [32:0] sd_tq;
    always @(posedge ck) if (rn && iv) sd_tm[wp] <= {iwe, ia};
    always @(posedge ck) if (rn && have_next) sd_tq <= sd_tm[read_next];
    assign mem_q[288:256] = sd_tq;
    assign mem_q[545:289] = 257'd0;
`else
    ot_sram_1r1w2c_16x546_m1 u_mem(.wclk(ck),.rclk(ck),.r_ce_in(rn&&have_next),.r_addr_in({1'b0,read_next}),.rd_out(mem_q),
      .w_ce_in(rn&&iv),.w_addr_in({1'b0,wp}),.wd_in({257'd0,iwe,ia,id}),.w_mask_in({546{1'b1}}));
`endif
`ifdef OT_S81_SH_APIPE10
    // S81-SHLK s10 (sr9 gate: u_mem rd_out (TT clk->q 310 ps) -> head decode / credit check -> fault, macro->reg -233 ps):
    // the popped head is registered straight from the macro (h_q); its decode, credit reserve, fault check and the
    // stack write act one edge after the pop, from h_q.  That edge replaces the APIPE 9 payload hop, so hw leaves on
    // the same edge as before (HSH 6).  The pop itself never reads the head (STATIC).
    reg [288:0] h_q;
    reg pop_q;
    always @(posedge ck) if (sd_pop) h_q <= mem_q[288:0];
    always @(posedge ck or negedge rn) if (!rn) pop_q <= 1'b0; else pop_q <= sd_pop;
    assign h = h_q;
`ifndef SYNTHESIS
    initial if (STATIC == 0) $error("dsdv_sh_sd: OT_S81_SH_APIPE10 requires STATIC != 0 (the pop must not read the head)");
`endif
`else
    wire pop_q = sd_pop;
    assign h=mem_q[288:0];
`endif
    always @(posedge ck or negedge rn) if(!rn)head_v<=0;else head_v<=have_next;
`ifndef SYNTHESIS
    always @(posedge ck)if(rn&&have_next&&iv&&read_next==wp)$fatal(1,"SH_SD_SRAM_COLLISION");
`endif
`else
    reg [288:0] f [0:7];
    wire [288:0] h = f[rp];
    wire head_ready=1'b1;
`endif
    wire hwe = h[288]; wire [31:0] ha = h[287:256]; wire [255:0] hd = h[255:0];
    // ---- KV stack list
    function automatic integer nkv(input integer m); integer i, c; begin c = 0; for (i = 0; i < NS; i = i + 1) if (m[i]) c = c + 1; nkv = c; end endfunction
    function automatic integer kth(input integer m, input integer k); integer i, c; begin kth = 0; c = 0;
        for (i = 0; i < NS; i = i + 1) if (m[i]) begin if (c == k) kth = i; c = c + 1; end end endfunction
    function automatic integer first(input integer m); integer i; begin first = 0; for (i = NS - 1; i >= 0; i = i - 1) if (m[i]) first = i; end endfunction
    localparam integer NKV = nkv(KVS);
    localparam integer KV0 = first(KVS);
    // ---- head decode
    wire marker = (ha == 32'hffffffff);
    reg [1:0] cls; reg bad; reg [NS-1:0] dst; integer s;
    wire [31:0] kidx = (MUT == 1) ? (ha >> 6) : (ha >> 5);
    wire [29:0] hpx = (ha[29:0] >> 2) ^ (ha[29:0] >> 7) ^ (ha[29:0] >> 12);
    wire [4:0] hpc = hpx[4:0];
    integer kk;
    always @* begin
        bad = 1'b0; cls = 2'd0; dst = {NS{1'b0}};
        if (marker) begin
            if (hd[65:64] == 2'd3) cls = 2'd3; else if (hd[65:64] == 2'd2) cls = 2'd2; else bad = 1'b1;
        end else cls = ha[31] ? (ha[30] ? 2'd3 : 2'd2) : 2'd0;
        if (!hwe) bad = 1'b1;
        if (cls == 2'd3) begin
            if (ENG < 0 || ENG >= NS) bad = 1'b1;
            else dst[(MUT == 3) ? 0 : ENG] = 1'b1;
        end else if (NKV == 0) bad = 1'b1;
        else if (cls == 2'd2) begin
            if (marker) dst = KVS[NS-1:0]; else dst[KV0] = 1'b1;
        end else begin
            kk = kidx % NKV;
            dst[kth(KVS, kk)] = 1'b1;
        end
        if (HALF != 0 && NS == 2 && cls != 2'd3 && !marker) begin
            dst = {NS{1'b0}};
            dst[(HALF == 2) ? hpc[3] : hpc[4]] = 1'b1;
        end
        if (bad) dst = {NS{1'b0}};
    end
    // ---- per-stack credits
    reg [4:0] cr [0:NS-1]; reg [6:0] crn;
    reg ok;
    always @* begin ok = 1'b1; for (s = 0; s < NS; s = s + 1) if (dst[s] && cr[s] == 0) ok = 1'b0; end
    wire pop = (n != 0) && head_ready && (STATIC != 0 || bad || ok);
`ifdef OT_S81_SH_SRAM
    assign sd_pop=pop;
`endif
`ifdef OT_S81_SH_APIPE10
    // (no payload hop: the h_q edge above)
`elsif OT_S81_SH_SRAM
    // One physical payload hop between the upper SRAM and the stack faces.
    // Credits are reserved at pop; the following edge emits that reserved word.
    (* keep = "true" *) reg [290:0] sd_hop_payload;
    (* keep = "true" *) reg [NS-1:0] sd_hop_dst;
    reg sd_hop_v;
    always @(posedge ck or negedge rn)
        if (!rn) begin sd_hop_v<=0; sd_hop_dst<=0; end
        else begin sd_hop_v<=pop; sd_hop_dst<=dst; end
`ifdef OT_S81_SH_MUT_HOPSTALE
    always @(posedge ck) if(pop && !sd_hop_v)
`else
    always @(posedge ck) if(pop)
`endif
        sd_hop_payload <= {(cls == 2'd3) ? 2'd2 : ((cls == 2'd2) ? 2'd1 : 2'd0), hwe, ha, hd};
`endif
    reg [8:0] asum;
    always @* begin asum = 9'd0; for (s = 0; s < NS; s = s + 1) asum = asum + hc_q[9*s + 1 +: 8]; end
    always @(posedge ck or negedge rn)
        if (!rn) begin
            wp <= 0; rp <= 0; n <= 0; o_cr <= 1'b0; fault <= 1'b0; host_ack_n <= 8'd0; crn <= 0;
            for (s = 0; s < NS; s = s + 1) begin cr[s] <= SCRED[4:0]; hw[292*s] <= 1'b0; end
        end else begin
            if (iv) begin
`ifndef OT_S81_SH_SRAM
                f[wp] <= {iwe, ia, id};
`endif
                wp <= wp + 1'b1; if (n == 8 && !pop) fault <= 1'b1; end
            if (pop) rp <= rp + 1'b1;
            n <= n + iv - pop;
            o_cr <= pop;
`ifdef OT_S81_SH_APIPE10
            if (pop_q && (bad || (STATIC != 0 && !ok))) fault <= 1'b1;
            for (s = 0; s < NS; s = s + 1) begin
                hw[292*s] <= pop_q && dst[s];
                cr[s] <= cr[s] - (pop_q && dst[s]) + (hc_q[9*s] && !(MUT == 2 && crn == 49 && s == 0));
                if (cr[s] - (pop_q && dst[s]) + hc_q[9*s] > SCRED) fault <= 1'b1;
            end
`else
            if (pop && (bad || (STATIC != 0 && !ok))) fault <= 1'b1;
            for (s = 0; s < NS; s = s + 1) begin
`ifdef OT_S81_SH_SRAM
                hw[292*s] <= sd_hop_v && sd_hop_dst[s];
`else
                hw[292*s] <= pop && dst[s];
`endif
                cr[s] <= cr[s] - (pop && dst[s]) + (hc_q[9*s] && !(MUT == 2 && crn == 49 && s == 0));
                if (cr[s] - (pop && dst[s]) + hc_q[9*s] > SCRED) fault <= 1'b1;
            end
`endif
            if (hc_q[0]) crn <= (crn == 49) ? 0 : crn + 1'b1;
            host_ack_n <= asum[8] ? 8'hff : asum[7:0];
            if (asum[8]) fault <= 1'b1;
        end
`ifdef OT_S81_SH_APIPE10
    always @(posedge ck)
`ifdef OT_S81_SH_MUT_HQSTALE
        for (s = 0; s < NS; s = s + 1) if (sd_pop && dst[s]) hw[292*s + 1 +: 291] <= {(cls == 2'd3) ? 2'd2 : ((cls == 2'd2) ? 2'd1 : 2'd0), hwe, ha, hd};   // mutant: emits on the pop edge (previous head)
`else
        for (s = 0; s < NS; s = s + 1) if (pop_q && dst[s]) hw[292*s + 1 +: 291] <= {(cls == 2'd3) ? 2'd2 : ((cls == 2'd2) ? 2'd1 : 2'd0), hwe, ha, hd};
`endif
`elsif OT_S81_SH_SRAM
    always @(posedge ck)
        for (integer t=0;t<NS;t=t+1) if(sd_hop_v&&sd_hop_dst[t]) hw[292*t+1+:291]<=sd_hop_payload;
`else
    always @(posedge ck)
        for (s = 0; s < NS; s = s + 1) if (pop && dst[s]) hw[292*s + 1 +: 291] <= {(cls == 2'd3) ? 2'd2 : ((cls == 2'd2) ? 2'd1 : 2'd0), hwe, ha, hd};
`endif
endmodule


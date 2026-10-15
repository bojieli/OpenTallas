`timescale 1ns/1ps
`default_nettype none
// HBM B2 (owner 2026-10-12: 4 clusters, one per HBM stack, distributed VM) -- the command processor's record dispatcher
// for the PER-CLUSTER units (el1011-hbm-b2-cp).  One control plane (one ot_hgi_seq), no global barrier:
//   * input: cp_die's ONE shared record register for units 1 SM, 2 SU, 3 SFU, 5 ATT, 8 DMA (the unit's packed record,
//     zero-extended to 2,198 b, + a one-hot valid pulse; at most one record a cycle: the sequencer's BE dispatches in
//     order); cp_die runs with B2 = 1 (its one-record credit bypassed; the 5 per-unit registers are not used);
//   * route (at FIFO write, from the cp_die flops; per-unit decode in parallel, then a one-hot 5:1 of 4-bit masks):
//       SM / ATT  -> all four clusters (each cluster's SMs / heads clip to their quarter);
//       SU / SFU  -> the HOME slice of O (owner computes): VM word address [SSH+1:SSH]; O not VM or in the mirror window
//                    [mlo, mhi) or the REPL window (word addr >= 2^18, SPEC v0.4 D-B2-6) -> the home of the first VM non-mirror operand of A, B, C, D; none -> cluster 0;
//                    (remote operands travel the slice ring: legal, slower; HGI-1 unchanged);
//       DMA       -> the HBM-side descriptor (A if A is HBM, else O): STRIPE4 (base[39:37] == 1) -> all four (each
//                    cluster serves the rows on its stack), else the stack base[SBIT+1:SBIT]; no HBM side -> home(O);
//   * a 4-entry FIFO {unit, mask, payload}; ready to cp_die is registered from the occupancy (room for the two records
//     that can be in flight between the ready and the push);
//   * credits per (unit, cluster) = the station queue depth D; the head leaves when EVERY targeted cluster has a credit
//     and the unit's completion FIFO has room (only the targeted clusters gate it);
//   * ONE command bus cb = {payload beat BW, qmask 4, unit 3, last, v}, a record's beats back to back (SM 1, SU 3,
//     SFU 2, ATT 2, DMA 1 beats at BW 1024), registered;
//   * returns rb = 4 x {fault 5, done 5} (registered at the input); a station returns its credit with the done / fault;
//   * retire (registered pulse to cp_die's ret): the unit's oldest record retires when every cluster of its mask has a
//     pending completion; fault if any of them faulted.  Clusters finish a unit's records in order (station FIFO).
// MUT (bench mutants): 1 the slice decode uses bit SSH-1 (off by one); 3 retire on the FIRST targeted cluster's done.
// Unit index here: 0 SM, 1 SU, 2 SFU, 3 ATT, 4 DMA.
module ot_hgi_b2_disp #(
    parameter integer D    = 4,       // station queue depth = credits per (unit, cluster)
    parameter integer CF   = 8,       // completion FIFO depth per unit (records outstanding per unit)
    parameter integer BW   = 1024,    // command bus payload beat
    parameter integer SSH  = 16,      // VM slice = word address [SSH+1:SSH]
    parameter integer SBIT = 35,      // HBM stack = byte address [SBIT+1:SBIT]
    parameter integer MUT  = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    // cp_die side (B2 = 1): ONE shared record register (the unit's packed record, zero-extended) + a one-hot valid
    input  wire [4:0]        r_v,         // {DMA, ATT, SFU, SU, SM} valid pulse
    input  wire [1098:0]     r_pa,        // r_p[1098:0]  (W face)
    input  wire [1098:0]     r_pb,        // r_p[2197:1099] (N face)
    output wire [2:0]        sm_ret,
    output wire [2:0]        su_ret,
    output wire [2:0]        sfu_ret,
    output wire [2:0]        att_ret,
    output wire [2:0]        dma_ret,
    input  wire [17:0]       mlo,         // mirror window [mlo, mhi) (VM words; cfg)
    input  wire [17:0]       mhi,
    // cluster side
    output wire [BW+8:0]     cb,          // {payload BW, qmask 4, unit 3, last, v}
    input  wire [39:0]       rb,          // cluster q: rb[q*10 +: 10] = {fault 5, done 5}
    output reg               busy
);
    wire [2197:0] r_p = {r_pb, r_pa};
    reg [8:0] cbc; reg [BW-1:0] cbd;           // the bus: control flops (reset) / payload flops (no reset)
    assign cb = {cbd, cbc};
    localparam integer PW = 2198;                           // widest record (SU)
    localparam integer FD = 4;
    localparam integer CFB = $clog2(CF + 1);
    localparam integer CW = $clog2(D + 1);
    localparam [CW-1:0] DCR = D;
    localparam [CFB-1:0] CFV = CF;
    localparam integer NB0 = (939 + BW - 1) / BW - 1, NB1 = (2198 + BW - 1) / BW - 1, NB2 = (1174 + BW - 1) / BW - 1,
                       NB3 = (1472 + BW - 1) / BW - 1, NB4 = (704 + BW - 1) / BW - 1;
    localparam [1:0] NBB0 = NB0, NBB1 = NB1, NBB2 = NB2, NBB3 = NB3, NBB4 = NB4;
    // ------------------------------------------------------------------ route decode (per unit, from cp_die flops)
    localparam integer SB = (MUT == 1) ? SSH - 1 : SSH;
    function automatic [3:0] oh(input [1:0] s); oh = 4'b0001 << s; endfunction
    function automatic is_vm(input [255:0] d); is_vm = (d[1:0] == 2'd1); endfunction
    function automatic in_mir(input [255:0] d, input [17:0] lo, input [17:0] hi);
        in_mir = !d[8 + 18] && (d[8 +: 18] >= lo) && (d[8 +: 18] < hi);
    endfunction
    function automatic [1:0] home(input [255:0] d); home = d[8 + SB +: 2]; endfunction
    function automatic own(input [255:0] d, input [17:0] lo, input [17:0] hi); own = is_vm(d) && !in_mir(d, lo, hi) && d[8 + 18] == 1'b0; endfunction   // SPEC v0.4: >= 2^18 = REPL (local everywhere), never an owner
    // owner-computes mask from O, then A, B, C, D
    function automatic [3:0] m_owner(input [255:0] o, input [255:0] a, input [255:0] b, input [255:0] c, input [255:0] dd,
                                     input [17:0] lo, input [17:0] hi);
        if (own(o, lo, hi)) m_owner = oh(home(o));
        else if (own(a, lo, hi)) m_owner = oh(home(a));
        else if (own(b, lo, hi)) m_owner = oh(home(b));
        else if (own(c, lo, hi)) m_owner = oh(home(c));
        else if (own(dd, lo, hi)) m_owner = oh(home(dd));
        else m_owner = 4'b0001;
    endfunction
    function automatic [3:0] m_dma(input [255:0] a, input [255:0] o, input [17:0] lo, input [17:0] hi);
        reg [255:0] h;
        begin : md
            h = (a[1:0] == 2'd0) ? a : o;
            if (a[1:0] != 2'd0 && o[1:0] != 2'd0) m_dma = own(o, lo, hi) ? oh(home(o)) : 4'b0001;
            else if (h[8 + 37 +: 3] == 3'd1) m_dma = 4'b1111;
            else m_dma = oh(h[8 + SBIT +: 2]);
        end
    endfunction
    // pin flops (v2, gate: register every boundary): the record (no reset), its valid, the mirror window
    reg [4:0] pv; reg [PW-1:0] pp; reg [17:0] plo, phi;
    always @(posedge clk) begin pp <= r_p; plo <= mlo; phi <= mhi; end
    always @(posedge clk or negedge rst_n) if (!rst_n) pv <= 5'd0; else pv <= r_v;
    // record layouts (cp_die): bit 0 valid, header [128:1], then descriptors (256 b each)
    wire [3:0] mk_su  = m_owner(pp[1409 +: 256], pp[385 +: 256], pp[641 +: 256], pp[897 +: 256], pp[1153 +: 256], plo, phi);
    wire [3:0] mk_sfu = m_owner(pp[897 +: 256], pp[129 +: 256], pp[385 +: 256], pp[641 +: 256], 256'd0, plo, phi);
    wire [3:0] mk_dma = m_dma(pp[129 +: 256], pp[385 +: 256], plo, phi);
    wire [4:0] in_v = pv;
    reg  [3:0] in_m; reg [2:0] in_u; reg [PW-1:0] in_p;
    always @* begin
        in_m = ({4{in_v[0] | in_v[3]}} & 4'b1111) | ({4{in_v[1]}} & mk_su) | ({4{in_v[2]}} & mk_sfu) | ({4{in_v[4]}} & mk_dma);
        in_u = {in_v[4], in_v[3] | in_v[2], in_v[3] | in_v[1]};   // one-hot -> index (0 SM .. 4 DMA)
        in_p = pp;
    end
    // beats a unit's record takes
    function automatic [1:0] nbeats(input [2:0] u);
        case (u)
            3'd0: nbeats = NBB0;
            3'd1: nbeats = NBB1;
            3'd2: nbeats = NBB2;
            3'd3: nbeats = NBB3;
            default: nbeats = NBB4;
        endcase
    endfunction
    // ------------------------------------------------------------------ input FIFO
    reg [3:0]    f_m [0:FD-1];
    reg [2:0]    f_u [0:FD-1];
    reg [1:0] wp, rp; reg [2:0] cnt; reg rdy_q;
    wire push = |in_v;
    // ------------------------------------------------------------------ credits / completion FIFOs / retire
    reg [CW-1:0] cred [0:4][0:3]; // per (unit, cluster), 0..D
    reg [3:0]  cfm  [0:4][0:CF-1];         // completion FIFO: target masks
    reg [$clog2(CF)-1:0] cwp [0:4], crp [0:4];
    reg [CFB-1:0] ccnt [0:4];
    reg [CFB-1:0] pc   [0:4][0:3];         // pending completions per (unit, cluster)
    reg [CF-1:0]  pf   [0:4][0:3];         // their fault bits, oldest at bit 0
    reg [39:0] rb_q;
    reg [4:0] rt_d, rt_f;                  // registered retire pulses
    // head eligibility
    wire [2:0] hu = f_u[rp]; wire [3:0] hm = f_m[rp];
    reg hok;
    integer q, u, k;
    always @* begin
        hok = (cnt != 3'd0) && (ccnt[hu] != CFV);
        for (q = 0; q < 4; q = q + 1) if (hm[q] && cred[hu][q] == '0) hok = 1'b0;
    end
    reg [1:0] bt; reg sending;             // beat index of the record on the bus
    wire start = !sending && hok;
    wire last_b = (sending ? bt : 2'd0) == nbeats(hu);
    wire pop = (start || sending) && last_b;
    // retire conditions
    reg [4:0] rt_ok, rt_fl;
    always @* begin
        for (u = 0; u < 5; u = u + 1) begin : rtc
            reg [3:0] m; reg all, any;
            m = cfm[u][crp[u]];
            all = (ccnt[u] != 0); any = 1'b0; rt_fl[u] = 1'b0;
            for (q = 0; q < 4; q = q + 1) begin
                if (m[q] && pc[u][q] == 0) all = 1'b0;
                if (m[q] && pc[u][q] != 0) any = 1'b1;
                if (m[q] && pc[u][q] != 0 && pf[u][q][0]) rt_fl[u] = 1'b1;
            end
            rt_ok[u] = (MUT == 3) ? ((ccnt[u] != 0) && any) : all;
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wp <= 2'd0; rp <= 2'd0; cnt <= 3'd0; rdy_q <= 1'b0; bt <= 2'd0; sending <= 1'b0; cbc <= 9'd0; rb_q <= 40'd0;
            rt_d <= 5'd0; rt_f <= 5'd0;
            for (u = 0; u < 5; u = u + 1) begin
                cwp[u] <= '0; crp[u] <= '0; ccnt[u] <= '0;
                for (q = 0; q < 4; q = q + 1) begin cred[u][q] <= DCR; pc[u][q] <= '0; pf[u][q] <= '0; end
            end
        end else begin
            rb_q <= rb;
            // FIFO
            if (push) begin f_m[wp] <= in_m; f_u[wp] <= in_u; wp <= wp + 2'd1; end
            if (pop) rp <= rp + 2'd1;
            cnt <= cnt + {2'd0, push} - {2'd0, pop};
            rdy_q <= (cnt + {2'd0, push} - {2'd0, pop}) <= 3'd1;   // 3 records can be in flight (decision, cp_die reg, pin flop)
            // bus
            cbc[0] <= start || sending;
            if (start || sending) begin
                cbc[1] <= last_b; cbc[4:2] <= hu; cbc[8:5] <= hm;
                sending <= !last_b; bt <= last_b ? 2'd0 : ((sending ? bt : 2'd0) + 2'd1);
            end
            // credits (consumed at the start; returned with each cluster's done / fault)
            for (u = 0; u < 5; u = u + 1)
                for (q = 0; q < 4; q = q + 1)
                    cred[u][q] <= cred[u][q] - {{(CW-1){1'b0}}, (start && hu == u[2:0] && hm[q])}
                                             + {{(CW-1){1'b0}}, (rb_q[q*10 + u] || rb_q[q*10 + 5 + u])};
            // completion FIFOs and pending completions
            rt_d <= 5'd0; rt_f <= 5'd0;
            for (u = 0; u < 5; u = u + 1) begin : cfu
                reg pu, ru;
                pu = start && hu == u[2:0];
                ru = rt_ok[u];
                if (pu) begin cfm[u][cwp[u]] <= hm; cwp[u] <= cwp[u] + 1'b1; end
                if (ru) begin crp[u] <= crp[u] + 1'b1; rt_d[u] <= !rt_fl[u]; rt_f[u] <= rt_fl[u]; end
                ccnt[u] <= ccnt[u] + {{(CFB-1){1'b0}}, pu} - {{(CFB-1){1'b0}}, ru};
                for (q = 0; q < 4; q = q + 1) begin : pcu
                    reg inc, dec; reg [CF-1:0] f;
                    inc = rb_q[q*10 + u] || rb_q[q*10 + 5 + u];
                    dec = ru && cfm[u][crp[u]][q] && pc[u][q] != 0;
                    f = pf[u][q];
                    if (dec) f = f >> 1;
                    if (inc) f[pc[u][q] - {{(CFB-1){1'b0}}, dec}] = rb_q[q*10 + 5 + u];
                    pf[u][q] <= f;
                    pc[u][q] <= pc[u][q] + {{(CFB-1){1'b0}}, inc} - {{(CFB-1){1'b0}}, dec};
                end
            end
        end
    end
    assign sm_ret  = {rt_f[0], rt_d[0], rdy_q};
    assign su_ret  = {rt_f[1], rt_d[1], rdy_q};
    assign sfu_ret = {rt_f[2], rt_d[2], rdy_q};
    assign att_ret = {rt_f[3], rt_d[3], rdy_q};
    assign dma_ret = {rt_f[4], rt_d[4], rdy_q};
    reg bz;
    always @* begin bz = (cnt != 0) || sending; for (u = 0; u < 5; u = u + 1) if (ccnt[u] != 0) bz = 1'b1; end
    always @(posedge clk or negedge rst_n) if (!rst_n) busy <= 1'b0; else busy <= bz;
    // ------------------------------------------------------------------ v2 datapath: FIFO payload in 128-b slices, each
    // with its OWN copy of the write / read pointers and the beat select (no pointer net over ~600 loads; gate high-fanout)
    localparam integer SLW = 128, NSL = (PW + SLW - 1) / SLW, SPB = BW / SLW;     // 18 slices, 8 a beat
    genvar gs;
    reg [SLW-1:0] fm [0:NSL-1][0:FD-1];
    wire [NSL*SLW-1:0] ppx = {{(NSL*SLW-PW){1'b0}}, pp};
    generate for (gs = 0; gs < NSL; gs = gs + 1) begin : sl
        (* keep *) reg [1:0] wpc;
        always @(posedge clk or negedge rst_n) if (!rst_n) wpc <= 2'd0; else if (push) wpc <= wpc + 2'd1;
        always @(posedge clk) if (|pv) fm[gs][wpc] <= ppx[gs * SLW +: SLW];
    end endgenerate
    // the bus beat, 8 x 128 b; slice t of beat b is FIFO slice b*SPB + t (beat 2 exists for the first NSL - 2 SPB)
    generate for (gs = 0; gs < SPB; gs = gs + 1) begin : ob
        (* keep *) reg [1:0] rpc, btc; (* keep *) reg sdc;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin rpc <= 2'd0; btc <= 2'd0; sdc <= 1'b0; end
            else begin
                if (pop) rpc <= rpc + 2'd1;
                if (start || sending) begin sdc <= !last_b; btc <= last_b ? 2'd0 : ((sending ? bt : 2'd0) + 2'd1); end
            end
        wire [1:0] bs = sdc ? btc : 2'd0;
        wire [SLW-1:0] b0 = fm[gs][rpc], b1 = fm[SPB + gs][rpc];
        wire [SLW-1:0] b2 = (2 * SPB + gs < NSL) ? fm[(2 * SPB + gs < NSL) ? 2 * SPB + gs : 0][rpc] : {SLW{1'b0}};
        always @(posedge clk) if (start || sending) cbd[gs * SLW +: SLW] <= (bs == 2'd0) ? b0 : (bs == 2'd1) ? b1 : b2;
    end endgenerate
endmodule
`default_nettype wire

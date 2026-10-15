`timescale 1ns/1ps
`default_nettype none
// =====================================================================================================================
// ot_hgi_sv_unit.sv -- the SU.VOP redesign (el1013-hbm-redesign-suvop): 4-frame local memory with a per-sector
// {epoch, mask} column, forward by frame reference, in-place sink, frontier-following drain.
//   ot_hgi_sv_lmem   local memory model (4 frames x 2^16 words + the R file)
//   ot_hgi_sv_lane2  leaf: 2 VM wide lanes + their 2 banks' stage-write / drain-read ports
//   ot_hgi_sv_ctl    head controller
//   ot_hgi_sv_unit   the unit (port list of ot_hgi_su_unit WIDE = 1)
// =====================================================================================================================
// =====================================================================================================================
// ot_hgi_sv_lmem: local memory model of the SU.VOP redesign (behavioural, flat array; DESIGN.md section 2)
//   word a (LWB+1 bits used): a[LWB] = 0 local memory (frame a[17:16], sector a[17:3], bank a[7:3]); a[LWB] = 1 the R file
//   (256 words: slot a[7:6]).  Per sector em = {epoch 4, mask 8}.  A vec / res write of local word a under wep[frame]:
//   same epoch -> mask |= bit, other epoch -> {wep, bit}.  Stage writes (lsw_v) never touch em; lsw_scrub: em := 0.
//   Order inside one edge: every read sees the pre-edge state; scrub, then vm_we lanes, then res lanes; rf_clr before
//   the rfile writes of the same edge (a write wins over a clear).
// =====================================================================================================================
module ot_hgi_sv_lmem #(parameter integer N = 16, LWB = 18, AW = 24, NR = N / 8, RLAT = 1) (
  input wire clk, input wire rst_n,
  input wire [N-1:0] vi_re, input wire [N*AW-1:0] vi_addr, output reg [N*32-1:0] vi_q,
  input wire [4*N-1:0] rd_re, input wire [4*N*AW-1:0] rd_addr, output reg [4*N*32-1:0] rd_q,
  input wire [N-1:0] vm_we, input wire [N*AW-1:0] vm_waddr, input wire [N*32-1:0] vm_wdata,
  input wire [NR-1:0] res_we, input wire [NR*AW-1:0] res_addr, input wire [NR*32-1:0] res_data,
  input wire [15:0] wep,                                   // write epoch of frame f = wep[4f +: 4]
  input wire [31:0] lsw_v, input wire [32*15-1:0] lsw_sec, input wire [32*256-1:0] lsw_d, input wire [31:0] lsw_scrub,
  input wire [31:0] ldr_v, input wire [32*15-1:0] ldr_sec, output wire [31:0] ldr_rv, output wire [32*256-1:0] ldr_d, output wire [32*12-1:0] ldr_em,
  input wire [3:0] rf_clr, input wire rf_rv, input wire [4:0] rf_rsec, output wire rf_rrv, output wire [255:0] rf_rd, output wire [7:0] rf_rm,
  output reg bank_err);
`ifndef SYNTHESIS
`ifdef SV_PORT_CENSUS
    ot_hbm_su_port_census #(.N(N),.LWB(LWB),.AW(AW),.NR(NR)) u_port_census(
      .clk(clk),.rst_n(rst_n),.vi_re(vi_re),.vi_addr(vi_addr),.rd_re(rd_re),.rd_addr(rd_addr),
      .vm_we(vm_we),.vm_waddr(vm_waddr),.res_we(res_we),.res_addr(res_addr),
      .lsw_v(lsw_v),.lsw_sec(lsw_sec),.ldr_v(ldr_v),.ldr_sec(ldr_sec));
`endif
`endif
    localparam integer LW = 1 << LWB, LS = 15, NSEC = LW / 8;
    /* verilator lint_off BLKSEQ */
    reg [31:0] lm [0:LW-1];
    reg [11:0] em [0:NSEC-1];
    reg [31:0] rf [0:255];
    reg [255:0] rfw;
    initial rfw = 256'd0;                                   // written bits start clear (the head also rf_clr's a slot before use)
    // read delay lines (RLAT edges, valid alongside the data)
    reg [32*256-1:0] ld_p [1:4]; reg [32*12-1:0] le_p [1:4]; reg [31:0] lv_p [1:4];
    reg [255:0] fd_p [1:4]; reg [7:0] fm_p [1:4]; reg fv_p [1:4];
    assign ldr_rv = lv_p[RLAT]; assign ldr_d = ld_p[RLAT]; assign ldr_em = le_p[RLAT];
    assign rf_rrv = fv_p[RLAT]; assign rf_rd = fd_p[RLAT]; assign rf_rm = fm_p[RLAT];
    function automatic [LWB:0] aw(input [AW-1:0] a); aw = a[LWB:0]; endfunction
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            bank_err <= 1'b0;
            for (integer q = 1; q <= 4; q = q + 1) begin lv_p[q] <= 32'd0; fv_p[q] <= 1'b0; end
        end else begin
            lv_p[1] <= ldr_v; fv_p[1] <= rf_rv;
            for (integer q = 2; q <= 4; q = q + 1) begin lv_p[q] <= lv_p[q-1]; fv_p[q] <= fv_p[q-1]; end
            for (integer l = 0; l < 32; l = l + 1)
                if ((lsw_v[l] || lsw_scrub[l]) && lsw_sec[l*LS +: 5] != 5'(l) || ldr_v[l] && ldr_sec[l*LS +: 5] != 5'(l))
                    begin
                        bank_err <= 1'b1;
`ifdef SVDBG
                        if (!bank_err) $display("SV lmem bank_err lane %0d lsw %b scrub %b sec %0d ldr %b sec %0d", l, lsw_v[l], lsw_scrub[l], lsw_sec[l*LS +: LS], ldr_v[l], ldr_sec[l*LS +: LS]);
`endif
                    end
        end
    always @(posedge clk) begin : mem
        reg [LWB:0] a; reg [14:0] s; reg [3:0] e;
        // ---- reads (pre-edge state)
        for (integer l = 0; l < N; l = l + 1) begin
            a = aw(vi_addr[l*AW +: AW]);
            if (vi_re[l]) vi_q[32*l +: 32] <= a[LWB] ? rf[a[7:0]] : lm[a[LWB-1:0]];
            for (integer s2 = 0; s2 < 4; s2 = s2 + 1) begin
                a = aw(rd_addr[(4*l + s2)*AW +: AW]);
                if (rd_re[4*l + s2]) rd_q[(4*l + s2)*32 +: 32] <= a[LWB] ? rf[a[7:0]] : lm[a[LWB-1:0]];
            end
        end
        for (integer l = 0; l < 32; l = l + 1)
            if (ldr_v[l]) begin
                s = ldr_sec[l*LS +: LS];
                for (integer q = 0; q < 8; q = q + 1) ld_p[1][l*256 + 32*q +: 32] <= lm[{s, 3'(q)}];
                le_p[1][l*12 +: 12] <= em[s];
            end
        if (rf_rv) begin
            for (integer q = 0; q < 8; q = q + 1) fd_p[1][32*q +: 32] <= rf[{rf_rsec, 3'(q)}];
            fm_p[1] <= rfw[{rf_rsec, 3'd0} +: 8];
        end
        for (integer q = 2; q <= 4; q = q + 1) begin ld_p[q] <= ld_p[q-1]; le_p[q] <= le_p[q-1]; fd_p[q] <= fd_p[q-1]; fm_p[q] <= fm_p[q-1]; end
        // ---- lane stage writes / scrubs
        for (integer l = 0; l < 32; l = l + 1) begin
            s = lsw_sec[l*LS +: LS];
            if (lsw_scrub[l]) em[s] = 12'd0;
            else if (lsw_v[l]) for (integer q = 0; q < 8; q = q + 1) lm[{s, 3'(q)}] <= lsw_d[l*256 + 32*q +: 32];
        end
        // ---- vec / res writes (rfile: a[LWB])
        for (integer k = 0; k < 4; k = k + 1) if (rf_clr[k]) rfw[64*k +: 64] = 64'd0;
        for (integer l = 0; l < N + NR; l = l + 1) begin : wr
            reg we; reg [31:0] d;
            if (l < N) begin we = vm_we[l]; a = aw(vm_waddr[l*AW +: AW]); d = vm_wdata[32*l +: 32]; end
            else begin we = res_we[l-N]; a = aw(res_addr[(l-N)*AW +: AW]); d = res_data[32*(l-N) +: 32]; end
            if (we) begin
                if (a[LWB]) begin rf[a[7:0]] <= d; rfw[a[7:0]] = 1'b1; end
                else begin
                    lm[a[LWB-1:0]] <= d;
                    s = a[LWB-1:3]; e = wep[4*a[LWB-1:LWB-2] +: 4];
                    if (em[s][11:8] == e) em[s][{1'b0, a[2:0]}] = 1'b1;
                    else em[s] = {e, 8'd1 << a[2:0]};
                end
            end
        end
    end
    /* verilator lint_on BLKSEQ */
endmodule

// =====================================================================================================================
// ot_hgi_sv_lane2: 2 VM wide lanes (L0, L0 + 1) + their 2 banks' stage-write / drain-read ports (DESIGN.md section 3)
//   cmd pin flop (edge 1) -> load stage ld_* with the two lane offsets (edge 2) -> lane-slot state (edge 3) -> first
//   wrq / ldr flop (edge 4).  Status flops show a load from edge 2 on (done cleared, prefix 0).
//   An ssel change shows in the stage prefix 6 edges after the cmd pin, a dsel change in the drain prefix after 5.
//   Every pin is a flop here; payload flops (wrr, lsw_d, ldr_d, wwq data) have no reset.
//   HARDENED ONCE, x16: the leaf index is the pin strap lid (lanes 2 lid, 2 lid + 1; tied by the parent, registered
//   here), not a parameter.  RELAY (hop <= 500 um by construction): cmd_r = the registered copy of cmd for the next
//   leaf of the chain (+2 edges: pin flop, output flop); st_in = the status of the leaf farther from the head, pin
//   flop, folded into this leaf's status register (AND / min / OR).  A chain end ties st_in to the neutral word
//   {err 0, dpre 3FFF, spre 3FFF, dhome 1, shome 1, ddone 11, sdone 1..1}.
// =====================================================================================================================
module ot_hgi_sv_lane2 #(parameter integer LQ = 8, NSJ = 6, MUT_V = 0) (
  input wire clk, input wire rst_n,
  input wire [3:0] lid,
  output wire [2*16-1:0] wrq, input wire [1:0] wrq_cr, input wire [2*257-1:0] wrr,
  output wire [2*280-1:0] wwq, input wire [1:0] wwq_cr, input wire [1:0] wwq_done,
  output wire [1:0] lsw_v, output wire [2*15-1:0] lsw_sec, output wire [2*256-1:0] lsw_d, output wire [1:0] lsw_scrub,
  output wire [1:0] ldr_v, output wire [2*15-1:0] ldr_sec, input wire [1:0] ldr_rv, input wire [2*256-1:0] ldr_d, input wire [2*12-1:0] ldr_em,
  // {dsel, ssel[NSJ], dfr1[14], dfr0[14], jb_flag, jb_ep[4], jb_lsec[15], jb_n[14], jb_vsec[15], jb_slot[3], jb_kind, jb_v}
  input wire [54+28+NSJ+1-1:0] cmd,
  output wire [54+28+NSJ+1-1:0] cmd_r,
  // {err, dpre[14], spre[14], dhome, shome, ddone[2], sdone[NSJ]}
  input wire [NSJ+33-1:0] st_in,
  output wire [NSJ+33-1:0] status);
    // Claude hbm-group-B 10-14 (native pin audit: raw rst_n fanned out before its first flop, lf 460+ ps): the
    // rst_n PORT drives only this relay (rtl/lib/ot_rst_relay.sv); every region resets from its own registered copy.
    // Head and leaves use the SAME relay depth, so they still release on one common edge (3 cycles after the port).
    wire [5:0] rr_lf;
    ot_rst_relay #(.REGIONS(6), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr_lf (.clk(clk), .rst_n_in(rst_n), .rst_n(rr_lf));
    localparam integer CW = 54 + 28 + NSJ + 1;
    localparam integer QB = $clog2(LQ + 1);                 // credit counter bits (0..LQ)
    localparam integer FB = $clog2(2 * LQ + 32), FD = 1 << FB;   // stage in-flight FIFO (slot ids)
    localparam integer DB = $clog2(LQ), DD = 1 << DB;       // drain in-flight FIFO (slot ids)
    localparam [13:0] PMAX = 14'h3FFF;

    // ---------------- cmd pin flop + load stage
    reg [CW-1:0] cmd_q, cmd_o; reg [3:0] lid_q; reg [NSJ+33-1:0] sti_q;
    always @(posedge clk or negedge rr_lf[0])
        if (!rr_lf[0]) begin cmd_q <= '0; cmd_o <= '0; sti_q <= {1'b0, 14'h3FFF, 14'h3FFF, 4'b1111, {NSJ{1'b1}}}; end
        else begin cmd_q <= cmd; cmd_o <= cmd_q; sti_q <= st_in; end
    always @(posedge clk) lid_q <= lid;
    assign cmd_r = cmd_o;
    wire        c_v    = cmd_q[0];
    wire        c_kind = cmd_q[1];
    wire [2:0]  c_slot = cmd_q[4:2];
    wire [14:0] c_vsec = cmd_q[19:5];
    wire [13:0] c_n    = cmd_q[33:20];
    wire [14:0] c_lsec = cmd_q[48:34];
    wire [3:0]  c_ep   = cmd_q[52:49];
    wire        c_flag = cmd_q[53];
    wire [13:0] dfr0   = cmd_q[67:54];
    wire [13:0] dfr1   = cmd_q[81:68];
    wire [NSJ-1:0] ssel = cmd_q[82 +: NSJ];
    wire        dsel   = cmd_q[82 + NSJ];
    reg ld_v, ld_kind, ld_flag; reg [2:0] ld_slot; reg [14:0] ld_vsec, ld_lsec; reg [13:0] ld_n; reg [3:0] ld_ep;
    reg [4:0] ld_off [0:1];
    always @(posedge clk or negedge rr_lf[1])
        if (!rr_lf[1]) ld_v <= 1'b0; else ld_v <= c_v;
    always @(posedge clk) begin
        ld_kind <= c_kind; ld_flag <= c_flag; ld_slot <= c_slot; ld_vsec <= c_vsec; ld_lsec <= c_lsec; ld_n <= c_n; ld_ep <= c_ep;
        for (integer g = 0; g < 2; g = g + 1) ld_off[g] <= {lid_q, 1'(g)} - c_vsec[4:0];
    end
    // slot-shared job attributes
    reg [NSJ-1:0] s_flag;                                   // stage slot is a scrub job
    reg [3:0] d_ep [0:1]; reg [1:0] d_chk;
    always @(posedge clk) if (ld_v) begin
        if (!ld_kind) begin for (integer q = 0; q < NSJ; q = q + 1) if (ld_slot == 3'(q)) s_flag[q] <= ld_flag; end
        else begin d_ep[ld_slot[0]] <= ld_ep; d_chk[ld_slot[0]] <= ld_flag; end
    end

    // ---------------- pin flops (VM / bank side)
    reg [1:0] wrq_cr_q, wwq_cr_q, wwq_done_q, wrr_vq, ldr_rv_q;
    reg [2*256-1:0] wrr_dq, ldr_d_q; reg [2*12-1:0] ldr_em_q;
    always @(posedge clk or negedge rr_lf[2])
        if (!rr_lf[2]) begin wrq_cr_q <= 2'd0; wwq_cr_q <= 2'd0; wwq_done_q <= 2'd0; wrr_vq <= 2'd0; ldr_rv_q <= 2'd0; end
        else begin
            wrq_cr_q <= wrq_cr; wwq_cr_q <= wwq_cr; wwq_done_q <= wwq_done; ldr_rv_q <= ldr_rv;
            wrr_vq <= {wrr[513], wrr[256]};
        end
    always @(posedge clk) begin
        wrr_dq <= {wrr[512:257], wrr[255:0]}; ldr_d_q <= ldr_d; ldr_em_q <= ldr_em;
    end
    reg [1:0] wrq_vf, lsw_v_f, lsw_scrub_f, ldr_v_f, wwq_vf;
    reg [9:0] wrq_sf [0:1]; reg [14:0] lsw_sec_f [0:1]; reg [255:0] lsw_d_f [0:1]; reg [14:0] ldr_sec_f [0:1];
    reg [9:0] wwq_sf [0:1]; reg [255:0] wwq_df [0:1]; reg [7:0] wwq_mf [0:1];

    // ---------------- per-lane state and status terms
    wire [NSJ-1:0] ln_sbusy [0:1]; wire [1:0] ln_dbusy [0:1];
    reg [13:0] ln_sp [0:1], ln_dp [0:1]; reg [1:0] ln_shome, ln_dhome, ln_err;
    // slots being loaded (cmd flop or load stage): reported busy / prefix 0
    reg [NSJ-1:0] sl_c, sl_l; reg [1:0] dl_c, dl_l;
    always @* begin
        for (integer q = 0; q < NSJ; q = q + 1) begin
            sl_c[q] = c_v && !c_kind && c_slot == 3'(q); sl_l[q] = ld_v && !ld_kind && ld_slot == 3'(q);
        end
        for (integer q = 0; q < 2; q = q + 1) begin
            dl_c[q] = c_v && c_kind && c_slot == 3'(q); dl_l[q] = ld_v && ld_kind && ld_slot == 3'(q);
        end
    end

    for (genvar g = 0; g < 2; g = g + 1) begin : g_ln
        wire [4:0] B = {lid_q, 1'(g)};
        // load arithmetic (from the load stage registers)
        wire [4:0]  l_off = ld_off[g];
        wire        l_has = {9'd0, l_off} < ld_n;
        wire [13:0] l_dn  = ld_n - 14'd1 - {9'd0, l_off};
        wire [8:0]  l_cnt = l_has ? l_dn[13:5] + 9'd1 : 9'd0;
        wire [14:0] l_va  = ld_vsec + {10'd0, l_off};
        wire [14:0] l_la  = ld_lsec + {10'd0, l_off};
        // ---- stage
        reg [9:0] s_iv [0:NSJ-1];       // next VM sector to issue, bits [14:5] (bits [4:0] = B)
        reg [8:0] s_rem [0:NSJ-1];      // sectors still to issue (scrub: to scrub)
        reg [14:0] s_ll [0:NSJ-1];      // next local sector to land (scrub: to scrub)
        reg [8:0] s_lc [0:NSJ-1];       // landed count
        reg [FB:0] s_out [0:NSJ-1];     // issued, not landed
        reg [4:0] s_off [0:NSJ-1];
        reg [2:0] rr; reg [QB-1:0] cr;
        reg [2:0] ff [0:FD-1]; reg [FB:0] fn;
        // ---- drain
        reg [4:0] d_off [0:1]; reg [8:0] d_k [0:1], d_rem [0:1]; reg [14:0] d_ll [0:1]; reg [9:0] d_rv [0:1];
        reg [DB:0] d_out [0:1]; reg [5:0] d_need [0:1];
        reg [QB-1:0] wcr; reg [5:0] wpend; reg [DD-1:0] dff; reg [DB:0] dfn;
        // Local bank reads reserve local storage, never a remote VM credit. Four sectors cover the local
        // read/pin pipeline; the eight VM credits are consumed only when a write enters the VM wire.
        localparam integer PF = 4;
        reg [1:0] pf_wp, pf_rp; reg [2:0] pf_n;
        reg [255:0] pf_d [0:PF-1]; reg [7:0] pf_m [0:PF-1]; reg [9:0] pf_s [0:PF-1]; reg [PF-1:0] pf_slot;
        for (genvar q = 0; q < NSJ; q = q + 1) begin : g_sb
            assign ln_sbusy[g][q] = s_rem[q] != 9'd0 || s_out[q] != '0;
        end
        for (genvar q = 0; q < 2; q = q + 1) begin : g_db
            assign ln_dbusy[g][q] = d_rem[q] != 9'd0 || d_out[q] != '0 || d_need[q] != 6'd0;
        end
        wire [13:0] dfr_s [0:1]; assign dfr_s[0] = dfr0; assign dfr_s[1] = dfr1;

        always @(posedge clk or negedge rr_lf[4 + g])   // one relay copy per wide lane (gate: 1,588 loads on one copy)
            if (!rr_lf[4 + g]) begin
                for (integer q = 0; q < NSJ; q = q + 1) begin s_rem[q] <= 9'd0; s_out[q] <= '0; end
                for (integer q = 0; q < 2; q = q + 1) begin d_rem[q] <= 9'd0; d_out[q] <= '0; d_need[q] <= 6'd0; end
                rr <= 3'd0; cr <= QB'(LQ); fn <= '0; wcr <= QB'(LQ); wpend <= 6'd0; dfn <= '0;
                wrq_vf[g] <= 1'b0; lsw_v_f[g] <= 1'b0; lsw_scrub_f[g] <= 1'b0; ldr_v_f[g] <= 1'b0; wwq_vf[g] <= 1'b0;
                ln_err[g] <= 1'b0; ln_shome[g] <= 1'b1; ln_dhome[g] <= 1'b1; pf_wp <= 2'd0; pf_rp <= 2'd0; pf_n <= 3'd0;
            end else begin : ln
                reg iss, land, found, sfound, dr, ret, wsend, wfree, c0, c1, di, ds, ps, enq, ok;
                reg [2:0] qi, qq, lr, sq; reg [7:0] mk; reg [FB:0] wi; reg [DB:0] dwi;
                iss = 1'b0; land = 1'b0; found = 1'b0; sfound = 1'b0; qi = 3'd0; sq = 3'd0;
                wrq_vf[g] <= 1'b0; lsw_v_f[g] <= 1'b0; lsw_scrub_f[g] <= 1'b0; ldr_v_f[g] <= 1'b0; wwq_vf[g] <= 1'b0;
                // ================= STAGE: one request an edge, round robin over the active (non-scrub) slots
                if (cr != '0 && fn != (FB+1)'(FD))
                    for (integer k = 0; k < NSJ; k = k + 1) begin
                        qq = (32'(rr) + k >= NSJ) ? 3'(32'(rr) + k - NSJ) : 3'(32'(rr) + k);
                        for (integer q = 0; q < NSJ; q = q + 1)
                            if (!found && qq == 3'(q) && s_rem[q] != 9'd0 && !s_flag[q]) begin found = 1'b1; qi = 3'(q); end
                    end
                if (found) begin
                    iss = 1'b1; wrq_vf[g] <= 1'b1;
                    rr <= (qi == 3'(NSJ - 1)) ? 3'd0 : qi + 3'd1;
                    for (integer q = 0; q < NSJ; q = q + 1) if (qi == 3'(q)) begin
                        wrq_sf[g] <= s_iv[q]; s_iv[q] <= s_iv[q] + 10'd1; s_rem[q] <= s_rem[q] - 9'd1;
                    end
                end
                // a response lands at its slot's next local sector; else one scrub of a scrub slot
                lr = ff[0];
                for (integer q = NSJ - 1; q >= 0; q = q - 1) if (s_flag[q] && s_rem[q] != 9'd0) begin sfound = 1'b1; sq = 3'(q); end
                if (wrr_vq[g]) begin
                    land = 1'b1; lsw_v_f[g] <= 1'b1; lsw_d_f[g] <= wrr_dq[g*256 +: 256];
                    if (fn == '0) ln_err[g] <= 1'b1;                              // a response nobody asked for
                    for (integer q = 0; q < NSJ; q = q + 1) if (lr == 3'(q)) begin
                        lsw_sec_f[g] <= s_ll[q]; s_ll[q] <= s_ll[q] + 15'd32; s_lc[q] <= s_lc[q] + 9'd1;
                    end
                end else if (sfound) begin
                    lsw_scrub_f[g] <= 1'b1;
                    for (integer q = 0; q < NSJ; q = q + 1) if (sq == 3'(q)) begin
                        lsw_sec_f[g] <= s_ll[q]; s_ll[q] <= s_ll[q] + 15'd32; s_rem[q] <= s_rem[q] - 9'd1;
                    end
                end
                for (integer q = 0; q < NSJ; q = q + 1)
                    s_out[q] <= s_out[q] + (FB+1)'(iss && qi == 3'(q)) - (FB+1)'(land && lr == 3'(q));
                // shift FIFO of slot ids (head = ff[0])
                wi = fn - (FB+1)'(land);
                for (integer k = 0; k < FD; k = k + 1) begin
                    if (iss && wi == (FB+1)'(k)) ff[k] <= qi;
                    else if (land && k < FD - 1) ff[k] <= ff[(k + 1) % FD];
                end
                fn <= fn + (FB+1)'(iss) - (FB+1)'(land && fn != '0);
                cr <= cr - QB'(iss) + QB'(wrq_cr_q[g]);
                if (wrq_cr_q[g] && !iss && cr == QB'(LQ)) ln_err[g] <= 1'b1;      // credit overflow
                ln_shome[g] <= (cr == QB'(LQ)) && (fn == '0);
                // ================= DRAIN: one read an edge under the slot's frontier, slot 0 first
                dr = 1'b0; ret = 1'b0; wsend = 1'b0; wfree = 1'b0; di = 1'b0; enq = 1'b0; ps = pf_slot[pf_rp];
                c0 = d_rem[0] != 9'd0 && ((MUT_V == 5) ? {d_k[0], d_off[0]} <= dfr_s[0] : {d_k[0], d_off[0]} < dfr_s[0]);
                c1 = d_rem[1] != 9'd0 && ((MUT_V == 5) ? {d_k[1], d_off[1]} <= dfr_s[1] : {d_k[1], d_off[1]} < dfr_s[1]);
                if ((MUT_V == 9 || (32'(pf_n) + 32'(dfn)) < PF) && (c0 || c1)) begin
                    dr = 1'b1; di = !c0;
                    ldr_v_f[g] <= 1'b1; ldr_sec_f[g] <= d_ll[di];
                    d_ll[di] <= d_ll[di] + 15'd32; d_k[di] <= d_k[di] + 9'd1; d_rem[di] <= d_rem[di] - 9'd1;
                end
                // read return (valid-driven), identity from the in-flight FIFO
                ds = dff[0];
                ok = ldr_em_q[g*12 + 8 +: 4] == d_ep[ds];
                mk = (MUT_V == 2) ? 8'hFF : (ok || MUT_V == 1) ? ldr_em_q[g*12 +: 8] : 8'd0;
                if (ldr_rv_q[g]) begin
                    ret = 1'b1;
                    if (dfn == '0) ln_err[g] <= 1'b1;
                    if (d_chk[ds] && (!ok || ldr_em_q[g*12 +: 8] == 8'd0)) ln_err[g] <= 1'b1;   // dense sink, unwritten sector
`ifdef SVDBG
                    if (d_chk[ds] && (!ok || ldr_em_q[g*12 +: 8] == 8'd0) && !ln_err[g])
                        $display("SV leaf lane %0d CHK drain slot %0d vm sector %0d em %h want ep %0d", {lid_q, 1'(g)}, ds, {d_rv[ds], B}, ldr_em_q[g*12 +: 12], d_ep[ds]);
`endif
                    if (mk != 8'd0) begin
                        enq = 1'b1;
                        pf_d[pf_wp] <= ldr_d_q[g*256 +: 256]; pf_m[pf_wp] <= mk;
                        pf_s[pf_wp] <= d_rv[ds]; pf_slot[pf_wp] <= ds; pf_wp <= pf_wp + 2'd1;
                    end else wfree = 1'b1;
                    d_rv[ds] <= d_rv[ds] + 10'd1;
                end
                if (pf_n != 3'd0 && wcr != '0) begin
                    wsend = 1'b1; wwq_vf[g] <= 1'b1;
                    wwq_sf[g] <= pf_s[pf_rp]; wwq_df[g] <= pf_d[pf_rp]; wwq_mf[g] <= pf_m[pf_rp];
                    pf_rp <= pf_rp + 2'd1;
                end
                pf_n <= pf_n + 3'(enq) - 3'(wsend);
                if (enq && pf_n == 3'(PF) && !wsend) ln_err[g] <= 1'b1;
                dwi = dfn - (DB+1)'(ret);
                for (integer k = 0; k < DD; k = k + 1) begin
                    if (dr && dwi == (DB+1)'(k)) dff[k] <= di;
                    else if (ret && k < DD - 1) dff[k] <= dff[(k + 1) % DD];
                end
                dfn <= dfn + (DB+1)'(dr) - (DB+1)'(ret && dfn != '0);
                for (integer q = 0; q < 2; q = q + 1) begin
                    d_out[q] <= d_out[q] + (DB+1)'(dr && di == 1'(q)) - (DB+1)'(wsend && ps == 1'(q)) - (DB+1)'(wfree && ds == 1'(q));
                    // writes still owed to this slot: every write up to its last one must be done (done is in order)
                    if (wsend && ps == 1'(q)) d_need[q] <= wpend + 6'd1 - 6'(wwq_done_q[g]);
                    else if (wwq_done_q[g] && d_need[q] != 6'd0) d_need[q] <= d_need[q] - 6'd1;
                end
                wcr <= wcr - QB'(wsend) + QB'(wwq_cr_q[g]);
                if (wwq_cr_q[g] && !wsend && wcr == QB'(LQ)) ln_err[g] <= 1'b1;
                wpend <= wpend + 6'(wsend) - 6'(wwq_done_q[g]);
                if (wpend == 6'd63 && wsend && !wwq_done_q[g]) ln_err[g] <= 1'b1;
                ln_dhome[g] <= (wcr == QB'(LQ)) && (wpend == 6'd0) && (dfn == '0) && (pf_n == 3'd0);
                // ================= job load (the slot is idle: nothing above touched it)
                if (ld_v && !ld_kind) begin
                    for (integer q = 0; q < NSJ; q = q + 1) if (ld_slot == 3'(q)) begin
                        if (ln_sbusy[g][q]) ln_err[g] <= 1'b1;
`ifdef SVDBG
                        if (ln_sbusy[g][q]) $display("SV leaf lane %0d stage load onto busy slot %0d", {lid_q, 1'(g)}, q);
`endif
                        s_iv[q] <= l_va[14:5]; s_rem[q] <= l_cnt; s_ll[q] <= l_la; s_lc[q] <= 9'd0; s_off[q] <= l_off; s_out[q] <= '0;
                    end
                end
                if (ld_v && ld_kind) begin
                    for (integer q = 0; q < 2; q = q + 1) if (ld_slot == 3'(q)) begin
                        if (ln_dbusy[g][q]) ln_err[g] <= 1'b1;
`ifdef SVDBG
                        if (ln_dbusy[g][q]) $display("SV leaf lane %0d drain load onto busy slot %0d", {lid_q, 1'(g)}, q);
`endif
                        d_off[q] <= l_off; d_k[q] <= 9'd0; d_rem[q] <= l_cnt; d_ll[q] <= l_la; d_rv[q] <= l_va[14:5];
                        d_out[q] <= '0; d_need[q] <= 6'd0;
                    end
                end
            end
        // ---- prefix terms of this lane (pre-edge state: one edge stale, never ahead of the memory)
        // TWO registered steps (10-13: the one-step form was a 27-level reg -> reg path, ~1,070 ps): step A = the
        // per-slot term (PMAX when not selected or idle, 0 while loading), step B = the minimum of the NSJ terms by
        // all-pairs compare and a one-hot select (lowest index wins a tie).
        reg [13:0] sv_q [0:NSJ-1]; reg [13:0] pmin; reg [NSJ-1:0] pwin;
        always @* begin
            pmin = 14'd0;
            for (integer a = 0; a < NSJ; a = a + 1) begin
                pwin[a] = 1'b1;
                for (integer b = 0; b < NSJ; b = b + 1)
                    if (b < a) pwin[a] = pwin[a] && (sv_q[a] < sv_q[b]);
                    else if (b > a) pwin[a] = pwin[a] && (sv_q[a] <= sv_q[b]);
                pmin = pmin | (pwin[a] ? sv_q[a] : 14'd0);
            end
        end
        always @(posedge clk) begin : pre
            for (integer q = 0; q < NSJ; q = q + 1)
                sv_q[q] <= !ssel[q] ? PMAX : (sl_c[q] || sl_l[q]) ? 14'd0 : ln_sbusy[g][q] ? {s_lc[q], s_off[q]} : PMAX;
            ln_sp[g] <= pmin;
            ln_dp[g] <= (dl_c[dsel] || dl_l[dsel]) ? 14'd0 : (d_rem[dsel] != 9'd0) ? {d_k[dsel], d_off[dsel]} : PMAX;
        end
        assign wrq[g*16 +: 16] = {wrq_vf[g], wrq_sf[g], B};
        assign wwq[g*280 +: 280] = {wwq_vf[g], wwq_sf[g], B, wwq_df[g], wwq_mf[g]};
        assign lsw_v[g] = lsw_v_f[g]; assign lsw_scrub[g] = lsw_scrub_f[g]; assign lsw_sec[g*15 +: 15] = lsw_sec_f[g];
        assign lsw_d[g*256 +: 256] = lsw_d_f[g];
        assign ldr_v[g] = ldr_v_f[g]; assign ldr_sec[g*15 +: 15] = ldr_sec_f[g];
    end

    // ---------------- status flops
    reg [NSJ-1:0] st_sdone; reg [1:0] st_ddone; reg st_shome, st_dhome, st_err; reg [13:0] st_spre, st_dpre;
    // own prefix of the two lanes: its own registered step (one compare a step).  The load override below covers the
    // edges the longer line still shows the slot's old term, so a load is reported (done 0, prefix 0) from edge 2 on
    // exactly as before; the true prefix follows 2 (stage) / 1 (drain) edges later (stale LOW meanwhile).
    reg [13:0] own_sp, own_dp; reg [NSJ-1:0] sl_2, sl_3; reg [1:0] dl_2, dl_3;
    always @(posedge clk) begin
        own_sp <= (ln_sp[0] < ln_sp[1]) ? ln_sp[0] : ln_sp[1];
        own_dp <= (ln_dp[0] < ln_dp[1]) ? ln_dp[0] : ln_dp[1];
        sl_2 <= sl_l; sl_3 <= sl_2; dl_2 <= dl_l; dl_3 <= dl_2;
    end
    always @(posedge clk or negedge rr_lf[0])
        if (!rr_lf[0]) begin
            st_sdone <= '1; st_ddone <= 2'b11; st_shome <= 1'b1; st_dhome <= 1'b1; st_err <= 1'b0; st_spre <= PMAX; st_dpre <= PMAX;
        end else begin
            st_sdone <= ~(ln_sbusy[0] | ln_sbusy[1] | sl_c | sl_l) & sti_q[NSJ-1:0];
            st_ddone <= ~(ln_dbusy[0] | ln_dbusy[1] | dl_c | dl_l) & sti_q[NSJ +: 2];
            st_shome <= (&ln_shome) && sti_q[NSJ+2]; st_dhome <= (&ln_dhome) && sti_q[NSJ+3];
            st_err <= st_err | (|ln_err) | sti_q[NSJ+32];
`ifdef SVDBG
            if (!st_err && (|ln_err)) $display("SV leaf %0d err %b", lid_q, ln_err);
`endif
            st_spre <= (|(ssel & (sl_c | sl_l | sl_2 | sl_3))) ? 14'd0 : (own_sp < sti_q[NSJ+4 +: 14]) ? own_sp : sti_q[NSJ+4 +: 14];
            st_dpre <= (dl_c[dsel] || dl_l[dsel] || dl_2[dsel] || dl_3[dsel]) ? 14'd0 : (own_dp < sti_q[NSJ+18 +: 14]) ? own_dp : sti_q[NSJ+18 +: 14];
        end
    assign status = {st_err, st_dpre, st_spre, st_dhome, st_shome, st_ddone, st_sdone};
endmodule

// =====================================================================================================================
// ot_hgi_sv_ctl  -- HEAD controller of the SU.VOP redesign (el1013-hbm-redesign-suvop, DESIGN.md section 4)
//
// Record life (ring of NS = 8 slots, ring order = program order):
//   take (adapter op) -> DECODE (3-edge span multiply, 2-edge classify against the REGION TABLE, in-place decision,
//   allocation walk O, R, A..D) -> word FIFO (wl = head, q1, the decode register w is the third place) ->
//   STAGE jobs (job queue -> NSJ leaf stage slots, lookahead LA = 2 records ahead of RUN) -> RUN (one record in the
//   vec; streamed x_cnt credits) -> DRAIN O (2 leaf drain slots, live frontier) / DRAIN R (packet client) -> RETIRE.
//
// Blocks (one always block each, single driver a register; they talk through ev_* event wires):
//   [RELAY]  cmd head reg (x2, one a side) -> near leaf -> far leaf ; status far -> near (folded) -> head pin flops ->
//            4:1 -> 2:1
//   [BOOK]   ring bookkeeping: per-slot dynamic flags, job counters, wait masks (consumes every ev_*)
//   [DECODE] decode pipeline + classify + alloc ; owns the region table, the frame table, the rfile slot table, the
//            job queue write side and the per-slot static descriptors
//   [STAGE]  stage dispatcher (job queue read side, leaf stage slots, scrub jobs, rg_req)
//   [CMD]    the head cmd register (one job load an edge: drain > stage > scrub)
//   [RUN]    word FIFO, go / idle handshake, wep, EXT stream credits (x_seq / x_cnt / x_dseq), ssel / dsel
//   [FRONT]  live write frontier -> dfr0 / dfr1
//   [DRAIN]  O drain dispatcher (wg_req) ; [RDRAIN] R drain through vmq / vmr ; [RETIRE] in-order rec_done
//
// LOOP LATENCY (cmd register write at edge E -> first status that reflects it usable in the head), every hop a pin
// register, <= 500 um by placement (head at the centre of the leaf row, 4 near + 4 far leaves a side):
//   near leaf pin register E+1, its relay output register E+2, far leaf pin register E+3, far leaf job state E+4, far
//   leaf done register E+4 / prefix (two registered steps) E+5, near leaf st_in pin flop E+6, near leaf status
//   register (folded) E+7, head pin flops E+8, 4:1 E+9, 2:1 E+10 -> first use at edge E+11.
//   (10-13: the leaf's stage prefix has two more registered steps: first use of a prefix at edge E+13.)
//   BL = 16 blanks a slot's done bit and the prefixes for 16 edges after the cmd register write (3 edges of margin).
//
// DELIBERATE CHOICES (correctness points of the brief):
//  * operands before writes: a staged source over an older live sink waits for that owner's RETIRE (swait mask);
//    a record's own O drain waits for its own stage if the sector spans overlap (o_ovs); a younger record cannot go
//    before the older one's compute is done, and that needs the older one's whole stage in.
//  * VM write order: a record's sinks that share a VM sector with an older live sink wait for that owner's RETIRE
//    (dwait mask, both the O job load and the R drain).  Drain jobs are loaded in ring order.
//  * wep[f] changes only at a record's go (ev_go), to that record's O epoch; RUN is strictly serial (go only after
//    the previous record's idle), so no record computes in any frame at that edge.
//  * frontier = floor(((lo & 7) + (cr_cnt << c_lvw)) / 8), only while cr_seq == the mirrored vec seq of this op:
//    a LOWER bound of fully written sectors (cr_cnt is monotone, the registers only add staleness).
//  * x_cnt: the blanked leaf prefix or the last value (hold); every hold is stale-LOW.  A stage slot is removed from
//    ssel the edge it is freed (it could be reloaded for another record), which re-blanks.
//  * taint: every table entry overlapping (word granularity) a sink of the decoded record loses fwd_ok, except the
//    in-place entry.  A SRC entry of the record itself is created tainted if the source overlaps its own sinks.
//  * forward only from an entry whose owner record has not retired (SRC, OSINK and RSINK alike): after rec_done the
//    VM words belong to the program again.  A hit classified before the owner's retire stands.
//  * pins: one increment an edge (decode walk); released once at ev_cd (per-slot count per frame: staged SRC
//    regions + forward readers) and once at ev_ret (the O sink).  A frame is freed only HELD && pins == 0 && no
//    increment this edge.
//  * reset: all 4 frames SCRUB; the 4 scrub jobs need no lane grant; allocation waits for a FREE frame, decode of
//    the first records proceeds up to the allocation walk meanwhile.
//  * lane groups: request when a job is loadable, load only under the registered grant, release only when no VM
//    job is busy and the blanked shome / dhome is seen, 5-edge cool-down before the next request.
//
// DEVIATIONS from DESIGN.md (stated, see the report):
//  D1 (closed 10-13) span multiply: 6 parallel pipelines of 8 x (4 x 24) nibble products, 4 edges.
//  D2 the word FIFO is {wl, q1} + the decode register w (three decoded words: RUN + 2 ahead = the stage lookahead).
//  D3 allocation order is O, R, then A..D (sink table entries are mandatory and are taken first); every region
//     takes two edges (decide / relocate).
//  D4 SRC table entries only for staged sources in a dedicated frame (the brief's "optional" form).
//  D5 an in-place sink is refused when another source of the record overlaps the entry (epoch 15 wraps to 1 in place:
//     the frame is closed to allocation and scrubbed when freed).
//  D6 RSINK forwards need a dense R (rso == 1 or one result).
//  D7 (closed 10-13) a region that does not fit one frame at its lo[7:0] offset takes two adjacent frames (the second
//     is the TAIL of the first: one epoch, freed together; fr_tail): no 256-word alignment rule for a 65,536-word
//     region.  The leaf is unchanged (one epoch a drain job, contiguous local sectors).
// KNOWN GAPS (record fault): STREAM records, a_ind != 0, a region longer than two frames at its lo[7:0] offset
//  (> 131,072 words: half the local memory), R span > 56 words, any operand word >= 2^18, a nop record while the
//  ring holds 7 entries.
// =====================================================================================================================
/* verilator lint_off UNUSEDSIGNAL */
/* verilator lint_off UNUSEDPARAM */
module ot_hgi_sv_head #(
    parameter integer N = 16, M = 8, LV = 6,
    parameter integer LWB = 18,
    parameter integer PAYLOAD_RESET = 1,
    parameter integer GLU = 0,
    parameter integer SLB = 16,
    parameter integer LQ = 8,              // ONE constant = ot_hgi_vm_unit LQ (VM lane queue depth, power of two) = the credits a lane holds
    parameter integer EP0 = 0,             // frame epoch after a scrub (bench: 14 makes the chain's in-place sink wrap 15 -> 1)
    parameter integer MUT_V = 0,          // 3 in-place gate off, 4 forward reader takes no pin, 6 scalar bypass slot ^ 1, 7 tail frame keeps its old write epoch, 8 no EXT stream credit (the vec runs ahead of the stage)
    parameter integer NSJ = 6
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          rec_v,
    output wire          rec_rdy,
    input  wire [127:0]  rec_hdr,
    input  wire [255:0]  rec_sut,
    input  wire [255:0]  rec_a, rec_b, rec_c, rec_d, rec_o, rec_r, rec_i,
    input  wire [20:0]   rec_n_a,
    output reg           rec_done,
    output reg           rec_fault,
    output reg           halted,
    output reg  [337:0]  vmq,
    input  wire [273:0]  vmr,
    input  wire          s0_v,
    input  wire [19:0]   s0_idx,
    input  wire [31:0]   s0_data,
    output wire [522:0]  am_stream,
    input  wire          am_rdy,
    // the vec
    output reg           go,
    input  wire          ready,
    input  wire          idle,
    input  wire          vfault,
    output wire [669:0]  wl,
    output reg  [7:0]    x_seq,
    output reg  [7:0]    x_dseq,
    output reg  [15:0]   x_cnt,
    input  wire [7:0]    cr_seq_i,
    input  wire [7:0]    cr_dseq,
    input  wire [15:0]   cr_cnt_i,
    // the local memory
    output reg  [15:0]   wep,
    output reg  [3:0]    rf_clr,
    output reg           rf_rv,
    output reg  [4:0]    rf_rsec,
    input  wire          rf_rrv,
    input  wire [255:0]  rf_rd,
    input  wire [7:0]    rf_rm,
    input  wire          lm_err,
    // shared lane groups
    output reg           rg_req,
    input  wire          rg_gnt,
    output reg           wg_req,
    input  wire          wg_gnt,
    // the leaves: two registered copies of the cmd word (one a side: 4 near leaves each, which relay it to their far
    // partner) and the 8 near leaves' status words (each already folded with its far partner's)
    output wire [2*(83+NSJ)-1:0] lf_cmd,
    input  wire [8*(NSJ+33)-1:0] lf_status,
    output reg  [15:0]   walks                // non-dense O drains (frame walks) since reset
);
    // Claude hbm-group-B 10-14 (native pin audit: raw rst_n fanned out before its first flop, hd 460+ ps): the
    // rst_n PORT drives only this relay (rtl/lib/ot_rst_relay.sv); every region resets from its own registered copy.
    // Head and leaves use the SAME relay depth, so they still release on one common edge (3 cycles after the port).
    wire [7:0] rr_hd;
    ot_rst_relay #(.REGIONS(8), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr_hd (.clk(clk), .rst_n_in(rst_n), .rst_n(rr_hd));
    localparam integer NS = 8, NE = 8, NJQ = 8;
    localparam integer BL = 16;                         // status blanking after a cmd register write (see header)
    localparam [2:0]   LA = 3'd2;                       // stage lookahead: records ahead of RUN
    localparam integer CW = 83 + NSJ, SW = NSJ + 33;
    localparam integer LN_ = $clog2(N), LM_ = $clog2(M);
    localparam [1:0] K_SRC = 2'd0, K_OS = 2'd1, K_RS = 2'd2;
    localparam [1:0] F_FREE = 2'd0, F_OPEN = 2'd1, F_HELD = 2'd2, F_SCRUB = 2'd3;
    localparam [13:0] PDONE = 14'h3FFF;
    localparam [4:0]  BLV = 5'd16;

    function automatic [7:0] oh8(input [2:0] i); oh8 = 8'd1 << i; endfunction
    function automatic [3:0] ff8(input [7:0] m);        // {valid, index of the first set bit}
        begin
            ff8 = 4'd0;
            for (integer i = 7; i >= 0; i = i - 1) if (m[i]) ff8 = {1'b1, 3'(i)};
        end
    endfunction
    function automatic [2:0] ff4(input [3:0] m);
        begin
            ff4 = 3'd0;
            for (integer i = 3; i >= 0; i = i - 1) if (m[i]) ff4 = {1'b1, 2'(i)};
        end
    endfunction
    // nibble x 24: four gated shifted addends (written out: a '*' of zero-extended operands synthesised 26 levels deep)
    function automatic [27:0] nib24(input [3:0] n, input [23:0] x);
        nib24 = (({28{n[0]}} & {4'd0, x}) + ({28{n[1]}} & {3'd0, x, 1'd0})) + (({28{n[2]}} & {2'd0, x, 2'd0}) + ({28{n[3]}} & {1'd0, x, 3'd0}));
    endfunction
    function automatic ovl18(input [17:0] a0, input [17:0] a1, input [17:0] b0, input [17:0] b1);
        ovl18 = (a0 <= b1) && (b0 <= a1);
    endfunction

    // ================================================================================================= [RELAY]
    // cmd: the head register hc and its twin hc2 are the two cmd pins (one a side); a near leaf registers it at its
    // pin and relays it (cmd_r) to its far partner.  status: far leaf register -> near leaf pin flop -> near leaf
    // status register (folded) -> head pin flops lsq -> gst[side] (4:1) -> hst (2:1).
    reg [CW-1:0] hc; (* keep *) reg [CW-1:0] hc2;
    reg [SW-1:0] lsq [0:7]; reg [SW-1:0] gst [0:1]; reg [SW-1:0] hst;
    function automatic [SW-1:0] scomb(input [SW-1:0] a, input [SW-1:0] b);
        reg [13:0] sa, sb, da, db;
        begin
            sa = a[NSJ+4 +: 14]; sb = b[NSJ+4 +: 14]; da = a[NSJ+18 +: 14]; db = b[NSJ+18 +: 14];
            scomb[NSJ+3:0] = a[NSJ+3:0] & b[NSJ+3:0];
            scomb[NSJ+4 +: 14] = (sa < sb) ? sa : sb;
            scomb[NSJ+18 +: 14] = (da < db) ? da : db;
            scomb[NSJ+32] = a[NSJ+32] | b[NSJ+32];
        end
    endfunction
    always @(posedge clk or negedge rr_hd[0]) begin
        if (!rr_hd[0]) begin
            for (integer g = 0; g < 8; g = g + 1) lsq[g] <= '0;
            gst[0] <= '0; gst[1] <= '0; hst <= '0;
        end else begin
            for (integer g = 0; g < 8; g = g + 1) lsq[g] <= lf_status[g*SW +: SW];
            for (integer g = 0; g < 2; g = g + 1)
                gst[g] <= scomb(scomb(lsq[4*g], lsq[4*g+1]), scomb(lsq[4*g+2], lsq[4*g+3]));
            hst <= scomb(gst[0], gst[1]);
        end
    end
    assign lf_cmd = {hc2, hc};
    // the vec's credit counters: pin flops (a stale count is a lower bound; cr_seq travels with it)
    reg [7:0] cr_seq; reg [15:0] cr_cnt;
    always @(posedge clk or negedge rr_hd[1])
        if (!rr_hd[1]) begin cr_seq <= 8'd0; cr_cnt <= 16'd0; end else begin cr_seq <= cr_seq_i; cr_cnt <= cr_cnt_i; end
    wire [NSJ-1:0] st_sdone = hst[NSJ-1:0];
    wire [1:0]     st_ddone = hst[NSJ +: 2];
    wire           st_shome = hst[NSJ+2], st_dhome = hst[NSJ+3];
    wire [13:0]    st_spre = hst[NSJ+4 +: 14], st_dpre = hst[NSJ+18 +: 14];
    wire           st_err = hst[NSJ+32];

    // ================================================================================================= input sync
    // r5 (native pin audit of CLOSED mul7: capture 229.9 ps on vmr[256] / vmr[273] = the AND in front of vr_ack): both
    // bits land in their own pin flops and vr_ack is their AND (same cycle as the registered AND).
    reg ready_q, idle_q, vfault_q, rg_q, wg_q, vr_v, vr_l, lm_err_q;
    wire vr_ack = vr_v && vr_l;
    always @(posedge clk or negedge rr_hd[2]) begin
        if (!rr_hd[2]) begin
            ready_q <= 1'b0; idle_q <= 1'b0; vfault_q <= 1'b0; rg_q <= 1'b0; wg_q <= 1'b0; vr_v <= 1'b0; vr_l <= 1'b0; lm_err_q <= 1'b0;
        end else begin
            ready_q <= ready; idle_q <= idle; vfault_q <= vfault; rg_q <= rg_gnt && rg_req; wg_q <= wg_gnt && wg_req;
            vr_v <= vmr[273]; vr_l <= vmr[256]; lm_err_q <= lm_err;
        end
    end
    assign am_stream = 523'd0;

    // ================================================================================================= adapter
    // The adapter's 3-in-flight limit is bypassed: su_ret one edge after each take.  Its rec_done one edge after our
    // su_ret is the echo (ignored); any other adapter rec_done is a nop record (ring entry, retires in order).
    wire op_v; wire [669:0] op_w; wire [1:0] strm; reg op_rdy_r, su_ret, ret_echo, su_fault_r;
    wire ad_done, ad_fault, ad_halted, ad_drained, ad_lg_rdy;      // (the last two are unused: LEGACY = 0)
    ot_hgi_su_record #(.LEGACY(0), .GLU(GLU), .STREAM_OK(0), .PAYLOAD_RESET(PAYLOAD_RESET), .PIPED(1), .RDY_REG(1)) u_rec (
        .clk(clk), .rst_n(rr_hd[7]), .hgi_en(1'b1), .rec_v(rec_v), .rec_rdy(rec_rdy),
        .rec_hdr(rec_hdr), .rec_sut(rec_sut), .rec_a(rec_a), .rec_b(rec_b), .rec_c(rec_c), .rec_d(rec_d), .rec_o(rec_o),
        .rec_r(rec_r), .rec_i(rec_i), .rec_n_a(rec_n_a), .rec_done(ad_done), .rec_fault(ad_fault), .halted(ad_halted),
        .drained(ad_drained), .op_strm(strm), .lg_v(1'b0), .lg_rdy(ad_lg_rdy), .lg_w(670'd0), .op_v(op_v), .op_rdy(op_rdy_r), .op_w(op_w),
        .su_idle(1'b1), .su_fault(su_fault_r), .su_ret(su_ret));

    // ================================================================================================= shared state
    // ---- ring pointers and per-slot dynamic flags ([BOOK] owns the flags; the pointers belong to their blocks)
    reg [2:0] rt, rh, rp, dp, rdp; reg [3:0] cnt;       // tail (take), head (retire), RUN, O-drain, R-drain pointers
    reg [7:0] s_v, s_nop, s_dd, s_gone, s_cd, s_odone, s_old, s_odsl, s_rdone, s_ipg, stc;
    reg [2:0] st_pend [0:7]; reg [2:0] ns_pend [0:7]; reg [2:0] unl [0:7]; reg [2:0] s_ipold [0:7];
    reg [7:0] swait [0:7]; reg [7:0] dwait [0:7]; reg [7:0] fdep [0:7];
    // ---- per-slot static descriptors ([DECODE] owns them; written before s_dd)
    reg [7:0] sl_ov, sl_odense, sl_olive, sl_oovs, sl_rv, sl_opin, sl_otwo;
    reg [14:0] sl_ovsec [0:7]; reg [13:0] sl_on [0:7]; reg [14:0] sl_olsec [0:7]; reg [3:0] sl_oep [0:7];
    reg [2:0] sl_olo3 [0:7]; reg [3:0] sl_lvw [0:7];
    reg [1:0] sl_rslot [0:7]; reg [14:0] sl_rvsec [0:7]; reg [3:0] sl_rns [0:7];
    reg [11:0] sl_cpin [0:7]; reg [3:0] sl_rpin [0:7];  // pins released at compute done: per frame (3 b), rfile slots
    // ---- job queue (stage jobs in creation order = oldest record first)
    reg [2:0] jq_slot [0:NJQ-1]; reg [14:0] jq_vsec [0:NJQ-1]; reg [13:0] jq_n [0:NJQ-1]; reg [14:0] jq_lsec [0:NJQ-1];
    reg [NJQ-1:0] jq_strm; reg [3:0] jq_wp, jq_rp;
    // ---- leaf stage / drain slots
    reg [NSJ-1:0] sj_busy, sj_strm, sj_scrub; reg [2:0] sj_own [0:NSJ-1]; reg [1:0] sj_fr [0:NSJ-1]; reg [4:0] sj_bl [0:NSJ-1];
    reg [1:0] dr_busy, dr_live; reg [2:0] dr_own [0:1]; reg [13:0] dr_n [0:1]; reg [4:0] dr_bl [0:1];
    reg [13:0] dfr [0:1];
    reg [NSJ-1:0] ssel; reg dsel;
    // ---- frames
    reg [1:0] fr_st [0:3]; reg [3:0] fr_ep [0:3]; reg [5:0] fr_pin [0:3]; reg [3:0] sc_ld; reg [3:0] fr_wrap;
    reg [3:0] fr_tail;                                  // frame f is the second frame of a region that starts in f - 1
    // ---- faults
    reg hfault, dfault, rnfault, bkfault;
    // ---- events
    wire take, nop_ev, ev_dd, jq_push, ev_fd, ev_ip, ev_dw;
    wire ev_go, ev_cd, ev_ret;
    wire ev_jl, ev_jd, jd_strm, ev_scd; wire [2:0] jl_slot, jd_slot; wire [1:0] scd_f;
    wire ev_dl, dl_d, ev_od; wire [2:0] od_slot;
    wire ev_rd;
    wire ld_dr, ld_st, ld_sc;
    wire [7:0] retmask = ev_ret ? oh8(rh) : 8'd0;
    reg [2:0] dslot;                                    // the ring slot of the record in DECODE

    // ================================================================================================= [DECODE] comb
    reg [627:0] w;                                      // the op word in DECODE, relocated in place
    wire [15:0] no = w[0 +: 16], ni = w[16 +: 16];
    wire [1:0]  dst = w[380 +: 2], red = w[478 +: 2];
    wire        bhalf = w[210], cpair = w[283], redwhole = w[481], redtree = w[482];
    wire [2:0]  m1 = w[360 +: 3], qm = w[365 +: 3], ad = w[368 +: 3], e1 = w[374 +: 3], sfu = w[371 +: 3];
    wire [1:0]  m2 = w[363 +: 2], e2 = w[377 +: 2];
    wire use_b = (m1 == 3'd1) || (m1 == 3'd4) || (m1 == 3'd6) || (ad == 3'd3) || (e2 == 2'd1);
    wire use_c = !cpair && ((m2 == 2'd1) || (qm != 3'd0) || (ad == 3'd1) || (ad == 3'd2) || (e1 == 3'd1) || (e1 == 3'd2));
    wire use_d = (qm != 3'd0) || (ad == 3'd5);
    // region k: 0 A, 1 B, 2 C, 3 D (sources), 4 O, 5 R (sinks)
    reg [23:0] c_base [0:5]; reg [23:0] c_so [0:5]; reg [23:0] c_si [0:5]; reg [15:0] c_nr [0:5]; reg [15:0] c_ni [0:5];
    reg [5:0] c_used, c_dense; reg [3:0] c_ipd;
    always @* begin
        for (integer k = 0; k < 6; k = k + 1) begin
            case (k)
                0: begin c_base[k] = w[40 +: 24];  c_so[k] = w[64 +: 24];  c_si[k] = w[88 +: 24];  c_used[k] = 1'b1; end
                1: begin c_base[k] = w[138 +: 24]; c_so[k] = w[162 +: 24]; c_si[k] = w[186 +: 24]; c_used[k] = use_b; end
                2: begin c_base[k] = w[211 +: 24]; c_so[k] = w[235 +: 24]; c_si[k] = w[259 +: 24]; c_used[k] = use_c; end
                3: begin c_base[k] = w[284 +: 24]; c_so[k] = w[308 +: 24]; c_si[k] = w[332 +: 24]; c_used[k] = use_d; end
                4: begin c_base[k] = w[382 +: 24]; c_so[k] = w[406 +: 24]; c_si[k] = w[430 +: 24]; c_used[k] = (dst == 2'd1); end
                default: begin c_base[k] = w[484 +: 24]; c_so[k] = w[508 +: 24]; c_si[k] = 24'd0; c_used[k] = (red != 2'd0); end
            endcase
            c_nr[k] = (k == 5) ? ((redwhole || redtree) ? 16'd1 : no) : no;
            c_ni[k] = (k == 5) ? 16'd1 : ((bhalf && (k == 1 || k == 3)) ? ((ni + 16'd1) >> 1) : ni);
        end
        // dense: element e = o ni + i at word base + e (streamable source / live-drainable O / forwardable sink)
        for (integer k = 0; k < 5; k = k + 1)
            c_dense[k] = c_si[k] == 24'd1 && (c_so[k] == {8'd0, ni} || no == 16'd1) &&
                         !((k == 1 || k == 3) && bhalf) && !((k == 0 || k == 2) && cpair);
        c_dense[5] = (c_so[5] == 24'd1) || (c_nr[5] == 16'd1);
        for (integer k = 0; k < 4; k = k + 1)            // in-place source: strictly si 1, so = ni
            c_ipd[k] = c_si[k] == 24'd1 && c_so[k] == {8'd0, ni} && !((k == 1 || k == 3) && bhalf) && !((k == 0 || k == 2) && cpair);
    end
    // the vec's lane width for the op (ot_hdc_v41x_vec c_lvw): scalar SFU 1, SFU / divide M, else N
    wire [3:0] c_lvw = (sfu == 3'd2 || sfu == 3'd3 || sfu == 3'd6 || sfu == 3'd7) ? 4'd0 :
                       (sfu == 3'd1 || sfu == 3'd4 || sfu == 3'd5 || m1 == 3'd4 || m1 == 3'd5) ? 4'(LM_) : 4'(LN_);
    wire c_pow2 = (ni != 16'd0) && ((ni & (ni - 16'd1)) == 16'd0);
    wire c_olive = c_dense[4] && c_pow2 && (red == 2'd0 || ni >= (16'd1 << c_lvw));

    // ---- decode registers
    localparam [3:0] D_IDLE = 4'd0, D_MUL = 4'd1, D_CL0 = 4'd2, D_CL1 = 4'd3, D_SK0 = 4'd4, D_SK1 = 4'd5, D_AA = 4'd6,
                     D_AB = 4'd7, D_HOLD = 4'd8, D_FAULT = 4'd9;
    reg [3:0] dstt; reg [3:0] mph; reg [2:0] rk; reg [3:0] stallc;
    // span multiply: 6 regions in parallel, 3 edges (partial products, sum, extent); the (n - 1) factors are
    // registered at take, so stage 1 is a 3:1 select and the 8 x 24 products only
    reg [15:0] no_m1, ni_m1, nih_m1;
    reg [27:0] pn [0:5][0:7];                           // nibble x 24 partial products (a nibbles 0-3, c nibbles 4-7)
    reg [27:0] pnl [0:5][0:7]; reg [27:0] pnh [0:5][0:7]; // B4: the two pair sums of each nibble product (one adder an edge)
    reg [31:0] pq0 [0:5]; reg [31:0] pq1 [0:5]; reg [31:0] pq2 [0:5]; reg [31:0] pq3 [0:5]; reg [39:0] pacc [0:5];
    reg [15:0] rm_a [0:5]; reg [15:0] rm_c [0:5]; reg [23:0] rso [0:5]; reg [23:0] rsi [0:5]; reg [39:0] s01 [0:5]; reg [39:0] s23 [0:5];
    reg [15:0] m_a [0:5]; reg [15:0] m_c [0:5]; reg [18:0] mhi [0:5]; reg [5:0] m_badv;
    always @* for (integer k = 0; k < 6; k = k + 1) begin
        m_a[k] = (k == 5 && (redwhole || redtree)) ? 16'd0 : no_m1;
        m_c[k] = (k == 5) ? 16'd0 : (bhalf && (k == 1 || k == 3)) ? nih_m1 : ni_m1;
        mhi[k] = {1'b0, c_base[k][17:0]} + {1'b0, pacc[k][17:0]};
        m_badv[k] = c_used[k] && (c_base[k][23:18] != 6'd0 || pacc[k][39:18] != 22'd0 || mhi[k][18]);
    end
    // SPAN multiply pipeline (B4): free-running, no reset, no state enable (see D_MUL); 6 edges operand -> pacc.
    always @(posedge clk) for (integer k = 0; k < 6; k = k + 1) begin
        rm_a[k] <= m_a[k]; rm_c[k] <= m_c[k]; rso[k] <= c_so[k]; rsi[k] <= c_si[k];
        for (integer h = 0; h < 4; h = h + 1) begin
            pnl[k][h]     <= ({28{rm_a[k][4*h]}}     & {4'd0, rso[k]}) + ({28{rm_a[k][4*h + 1]}} & {3'd0, rso[k], 1'd0});
            pnh[k][h]     <= ({28{rm_a[k][4*h + 2]}} & {2'd0, rso[k], 2'd0}) + ({28{rm_a[k][4*h + 3]}} & {1'd0, rso[k], 3'd0});
            pnl[k][4 + h] <= ({28{rm_c[k][4*h]}}     & {4'd0, rsi[k]}) + ({28{rm_c[k][4*h + 1]}} & {3'd0, rsi[k], 1'd0});
            pnh[k][4 + h] <= ({28{rm_c[k][4*h + 2]}} & {2'd0, rsi[k], 2'd0}) + ({28{rm_c[k][4*h + 3]}} & {1'd0, rsi[k], 3'd0});
        end
        for (integer h = 0; h < 8; h = h + 1) pn[k][h] <= pnl[k][h] + pnh[k][h];
        pq0[k] <= {4'd0, pn[k][0]} + {pn[k][1], 4'd0}; pq1[k] <= {4'd0, pn[k][2]} + {pn[k][3], 4'd0};
        pq2[k] <= {4'd0, pn[k][4]} + {pn[k][5], 4'd0}; pq3[k] <= {4'd0, pn[k][6]} + {pn[k][7], 4'd0};
        s01[k] <= {8'd0, pq0[k]} + {pq1[k], 8'd0}; s23[k] <= {8'd0, pq2[k]} + {pq3[k], 8'd0};
        pacc[k] <= s01[k] + s23[k];
    end
    reg [17:0] lo [0:5]; reg [17:0] hi [0:5]; reg [5:0] rv;
    // Parallel with the existing classification edges: no allocation-side subtract/add chain.
    // hi/lo already include the pair-mode alignment; these payload registers need no reset.
    reg [17:0] alloc_span [0:5]; reg [18:0] alloc_ext [0:5];
    reg [23:0] alloc_delta [0:5], fwd_delta [0:3]; reg [17:0] fwd_origin [0:3];
    always @(posedge clk) begin
        if (dstt == D_CL0) for (integer k = 0; k < 6; k = k + 1) begin
            alloc_span[k] <= hi[k] - lo[k]; alloc_delta[k] <= c_base[k] - {6'd0, lo[k]};
        end
        if (dstt == D_CL1) for (integer k = 0; k < 6; k = k + 1) alloc_ext[k] <= {1'b0, alloc_span[k]} + {11'd0, lo[k][7:0]};
        if (dstt == D_SK0) for (integer q = 0; q < 4; q = q + 1) fwd_origin[q] <= tb_lo[f_e[q]];
        if (dstt == D_SK1) for (integer q = 0; q < 4; q = q + 1) fwd_delta[q] <= c_base[q] - {6'd0, fwd_origin[q]};
    end
    reg [7:0] h_in [0:3]; reg [7:0] h_eq [0:3]; reg [7:0] h_ov [0:3]; reg [7:0] s_ov [0:1]; reg [7:0] s_ovs [0:1];
    reg [7:0] o_eq; reg [3:0] sv_s;
    reg [3:0] f_hit, f_ipc; reg [2:0] f_e [0:3]; reg ip_c, ip_on; reg [2:0] ip_e; reg [7:0] f_used;
    reg [23:0] a_delta; reg [18:0] a_lb; reg [3:0] a_ep; reg a_stg, a_big, a_tw;
    // ---- region table
    reg [7:0] tb_v, tb_fok, tb_live, tb_dense, tb_stg;
    reg [1:0] tb_kind [0:7]; reg [17:0] tb_lo [0:7]; reg [17:0] tb_hi [0:7]; reg [18:0] tb_lb [0:7]; reg [2:0] tb_own [0:7];
    // ---- bump allocator, rfile slots
    reg open_v; reg [1:0] opf; reg [16:0] bp;
    reg [3:0] rf_own; reg [2:0] rf_pin [0:3];

    wire st_aa = dstt == D_AA, st_ab = dstt == D_AB;
    wire        is_src = !rk[2];
    wire [1:0]  aq = rk[1:0];
    // B3 (Claude group-B3 10-14, preoffset CTS gate reg->reg -118.9 ps: rk -> tb_lb 22 levels = rk-indexed operands, the
    // 17-bit bump fit add / compare, ra_ok, aa_go and the victim decode in one D_AA edge): every rk-indexed operand of the
    // region and the bump-fit arithmetic are REGISTERED, loaded on the edge that sets rk (SK1 -> region 4, an AA skip, the
    // AB step) or that resets bp (frame turnover in AA), from registers that are stable from SK1 on.  D_AA selects only
    // registered terms.  Same edges, same decisions: no cycle added.
    reg [17:0] pr_lo, pr_hi, pr_span; reg [18:0] pr_ext; reg pr_used, pr_fhit, pr_large, pr_two, pr_toobig, pr_fits;
    reg [2:0] pr_fe; reg [16:0] pr_lbk, pr_bpn;
    task automatic pre(input [2:0] k, input [16:0] b);
        reg [16:0] lk;
        begin
            lk = {b[16:8] + 9'(lo[k][7:0] < b[7:0]), lo[k][7:0]};               // lb == lo (mod 256 words)
            pr_lo <= lo[k]; pr_hi <= hi[k]; pr_span <= alloc_span[k]; pr_ext <= alloc_ext[k]; pr_used <= rv[k];
            pr_fe <= f_e[k[1:0]]; pr_fhit <= f_hit[k[1:0]];
            pr_large <= alloc_span[k][17:15] != 3'd0;
            pr_two <= alloc_span[k][17:15] != 3'd0 && alloc_ext[k] > 19'd65535;
            pr_toobig <= alloc_ext[k] > 19'd131071;
            pr_lbk <= lk;
            pr_fits <= ({2'b00, lk} + {1'b0, alloc_span[k]}) <= 19'd65535;
            pr_bpn <= lk + alloc_span[k][16:0] + 17'd9;                            // + 1 + an 8-word gap: no shared sector
        end
    endtask
    wire        cur_used = pr_used;
    wire [17:0] cur_lo = pr_lo, cur_hi = pr_hi;
    wire [17:0] span = pr_span;
    wire        a_large = pr_large;                                               // > 32,767 words: a dedicated frame
    // a region placed at its lo[7:0] offset in a dedicated frame: past 65,535 it runs on into the NEXT frame (the
    // local address space is contiguous): frames f and f + 1 are taken together, f + 1 as the TAIL of f (same epoch,
    // freed with f, no pins or table entries of its own).  More than two frames does not fit (capacity gap).
    wire [18:0] ext = pr_ext;
    wire        a_two = pr_two;
    wire        too_big = pr_toobig;
    wire [2:0]  fe = pr_fe;
    wire        fw_ok = is_src && pr_fhit && tb_v[fe];                             // forward (entry still alive)
    wire        fw_rs = tb_kind[fe] == K_RS;
    wire        ipnow = (rk == 3'd4) && ip_on && tb_v[ip_e];
    // table victim: an invalid entry, else one that is not sink_live, not forwarded by this record, not the in-place one
    reg [7:0] evm;
    always @* for (integer e = 0; e < 8; e = e + 1)
        evm[e] = tb_v[e] && !tb_live[e] && !f_used[e] && !(ip_on && ip_e == 3'(e));
    // (an entry this record forwards from / takes in place is never the victim, even if its frame died meanwhile)
    wire [3:0] vic_i = ff8(~tb_v & ~f_used & ~((ip_c || ip_on) ? oh8(ip_e) : 8'd0)), vic_e = ff8(evm);
    wire       vic_v = vic_i[3] || vic_e[3];
    wire [2:0] vic = vic_i[3] ? vic_i[2:0] : vic_e[2:0];
    // frames: the lowest FREE one; the open bump frame
    wire [3:0] fr_free = {fr_st[3] == F_FREE, fr_st[2] == F_FREE, fr_st[1] == F_FREE, fr_st[0] == F_FREE};
    wire [2:0] ffr1 = ff4(fr_free);
    wire [2:0] ffr2 = ff4({1'b0, fr_free[3] && fr_free[2], fr_free[2] && fr_free[1], fr_free[1] && fr_free[0]});   // f and f + 1
    wire [2:0] ffr = a_two ? ffr2 : ffr1;               // the dedicated frame (pair) of a large region
    wire [1:0] ffn = ffr[1:0] + 2'd1;
    wire [3:0] ep_two = ((fr_ep[ffr2[1:0]] > fr_ep[ffr2[1:0] + 2'd1]) ? fr_ep[ffr2[1:0]] : fr_ep[ffr2[1:0] + 2'd1]) + 4'd1;
    // The old bp + ((lo - bp) mod 256) was an 8-bit subtract followed by a 17-bit add.
    // Same modulo-2^17 address: preserve the requested low byte and advance one page on wrap.
    wire [16:0] lbk = pr_lbk;                                                     // registered (pre)
    wire        fits = pr_fits;
    wire [16:0] bp_n = pr_bpn;
    wire        ra_ok = a_large ? ffr[2] : (open_v && fits);
    wire [1:0]  ra_f = a_large ? ffr[1:0] : opf;
    wire [18:0] ra_lb = a_large ? {1'b0, ffr[1:0], 8'd0, cur_lo[7:0]} : {1'b0, opf, lbk[15:0]};
    wire [3:0]  ra_ep = a_two ? ep_two : a_large ? (fr_ep[ffr[1:0]] + 4'd1) : fr_ep[opf];
    // rfile: a free slot (owner retired, no reader)
    wire [2:0] rfs = ff4({!rf_own[3] && rf_pin[3] == 3'd0, !rf_own[2] && rf_pin[2] == 3'd0,
                          !rf_own[1] && rf_pin[1] == 3'd0, !rf_own[0] && rf_pin[0] == 3'd0});
    wire need_ra = cur_used && ((rk == 3'd4 && !ipnow) || (is_src && !fw_ok));
    wire need_vic = cur_used && ((rk == 3'd4 && !ipnow) || rk == 3'd5);
    wire ra_req = st_aa && need_ra && (!need_vic || vic_v) && !too_big;
    wire aa_go = st_aa && cur_used && (ipnow || (rk == 3'd4 && vic_v && ra_ok && !too_big) || (rk == 3'd5 && vic_v && rfs[2]) ||
                                       (is_src && (fw_ok || (ra_ok && !too_big))));
    wire aa_fault = st_aa && need_ra && too_big;
    // one pin increment an edge
    wire       d_pin_v = aa_go && (rk == 3'd4 || (is_src && !fw_ok) || (is_src && fw_ok && !fw_rs && MUT_V != 4));
    wire [1:0] d_pin_f = ipnow ? tb_lb[ip_e][17:16] : (is_src && fw_ok) ? tb_lb[fe][17:16] : ra_f;
    wire jq_full = (jq_wp - jq_rp) == 4'd8;
    wire ab_go = st_ab && !(a_stg && jq_full);
    assign jq_push = st_ab && a_stg && !jq_full;
    wire push_take;                                                               // [RUN] takes the decoded word
    assign take = (dstt == D_IDLE) && op_v && op_rdy_r;
    assign nop_ev = ad_done && !ret_echo;
    assign ev_dd = (dstt == D_HOLD) && push_take;
    assign ev_fd = aa_go && is_src && fw_ok && tb_kind[fe] == K_SRC && !tb_stg[fe];
    assign ev_ip = aa_go && ipnow;
    assign ev_dw = dstt == D_SK1;
    wire ip_gate = tb_live[ip_e] && !(ev_ret && rh == tb_own[ip_e]);
    // wait masks (by ring slot): stage of source aq over live sinks ; drain of this record's sinks over older ones
    reg [7:0] msk_sw, msk_dw;
    always @* begin
        msk_sw = 8'd0; msk_dw = 8'd0;
        for (integer e = 0; e < 8; e = e + 1) begin
            if (h_ov[aq][e] && tb_v[e] && tb_live[e]) msk_sw = msk_sw | oh8(tb_own[e]);
            if ((s_ovs[0][e] || s_ovs[1][e]) && tb_v[e] && tb_live[e]) msk_dw = msk_dw | oh8(tb_own[e]);
        end
        msk_sw = msk_sw & ~retmask & ~oh8(dslot);
        msk_dw = msk_dw & ~retmask & ~oh8(dslot);
    end
    // in-place decision (D_SK1): the candidate, no other source of the record on that entry, epoch headroom
    reg ip_bad;
    always @* begin
        ip_bad = 1'b0;
        for (integer q = 0; q < 4; q = q + 1)
            if (rv[q] && !f_ipc[q] && ((f_hit[q] && f_e[q] == ip_e) || h_ov[q][ip_e])) ip_bad = 1'b1;
    end
    wire ip_on_n = ip_c && !ip_bad && tb_v[ip_e];
    // in-place epoch: +1, and 15 WRAPS to 1.  Safe: the in-place span was written whole at the previous epoch by its
    // dense owner (stored epoch != the new one in every sector of the span), the drain reads only behind the write
    // frontier, and the frame takes no further allocation (an open bump frame is closed at the wrap) and is
    // scrubbed when it is freed (fr_wrap), so no sector outside the span is ever read at a wrapped epoch.
    wire [1:0] ip_f = tb_lb[ip_e][17:16];
    wire [1:0] ip_fn = ip_f + 2'd1;
    wire       ip_two = ip_f != 2'd3 && fr_tail[ip_fn];                           // the entry's region has a tail frame
    wire       ip_wrap = fr_ep[ip_f] == 4'd15;
    wire [3:0] ip_ep = ip_wrap ? 4'd1 : fr_ep[ip_f] + 4'd1;
    // first-hit one-hots (D_CL1)
    reg [7:0] fh [0:3]; reg [7:0] tb_osd;
    always @* begin
        for (integer q = 0; q < 4; q = q + 1) begin : fhq
            reg [3:0] f; f = ff8(h_in[q]); fh[q] = f[3] ? oh8(f[2:0]) : 8'd0;
        end
        for (integer e = 0; e < 8; e = e + 1) tb_osd[e] = tb_kind[e] == K_OS && tb_dense[e];
    end
    // releases
    wire [11:0] relc = sl_cpin[rp];
    wire [3:0]  relp = sl_rpin[rp];
    reg [3:0] fr_rel;                                   // a HELD head frame with no pin left and none arriving
    always @* for (integer f = 0; f < 4; f = f + 1)
        fr_rel[f] = fr_st[f] == F_HELD && !fr_tail[f] && fr_pin[f] == 6'd0 && !(d_pin_v && d_pin_f == 2'(f));

    // ================================================================================================= [DECODE] seq
    always @(posedge clk or negedge rr_hd[3]) begin
        if (!rr_hd[3]) begin
            dstt <= D_IDLE; op_rdy_r <= 1'b0; su_ret <= 1'b0; ret_echo <= 1'b0; dfault <= 1'b0; mph <= 4'd0; rk <= 3'd0;
            stallc <= 4'd0; dslot <= 3'd0; jq_wp <= 4'd0; rf_clr <= 4'd0;
            tb_v <= 8'd0; tb_fok <= 8'd0; tb_live <= 8'd0; tb_dense <= 8'd0; tb_stg <= 8'd0;
            open_v <= 1'b0; opf <= 2'd0; bp <= 17'd0; rf_own <= 4'd0;
            for (integer f = 0; f < 4; f = f + 1) begin
                fr_st[f] <= F_SCRUB; fr_ep[f] <= 4'd0; fr_wrap[f] <= 1'b0; fr_tail[f] <= 1'b0; fr_pin[f] <= 6'd0; rf_pin[f] <= 3'd0;
            end
            sl_ov <= 8'd0; sl_odense <= 8'd0; sl_olive <= 8'd0; sl_oovs <= 8'd0; sl_rv <= 8'd0; sl_opin <= 8'd0; sl_otwo <= 8'd0;
            ip_on <= 1'b0; ip_c <= 1'b0; f_used <= 8'd0; f_hit <= 4'd0; f_ipc <= 4'd0; rv <= 6'd0; a_stg <= 1'b0; a_big <= 1'b0; a_tw <= 1'b0;
            for (integer s = 0; s < 8; s = s + 1) begin sl_cpin[s] <= 12'd0; sl_rpin[s] <= 4'd0; end
        end else begin
            su_ret <= take; ret_echo <= su_ret; dfault <= 1'b0; rf_clr <= 4'd0;
            // ---------------------------------------------------------------- frame table: pins, free, scrub done
            for (integer f = 0; f < 4; f = f + 1) begin : frm
                reg inc; reg [5:0] dec;
                inc = d_pin_v && d_pin_f == 2'(f);
                dec = (ev_cd ? {3'd0, relc[3*f +: 3]} : 6'd0) + ((ev_ret && sl_opin[rh] && sl_olsec[rh][14:13] == 2'(f)) ? 6'd1 : 6'd0);
                fr_pin[f] <= fr_pin[f] + {5'd0, inc} - dec;
                if (fr_rel[f] || (fr_tail[f] && f > 0 && fr_rel[(f + 3) % 4])) begin   // nobody left: FREE, its entries die
                    fr_st[f] <= (fr_ep[f] == 4'd15 || fr_wrap[f]) ? F_SCRUB : F_FREE;   // (a tail frame goes with its head)
                    fr_tail[f] <= 1'b0;
                    for (integer e = 0; e < 8; e = e + 1)
                        if (tb_kind[e] != K_RS && tb_lb[e][17:16] == 2'(f)) tb_v[e] <= 1'b0;
                end
                if (ev_scd && scd_f == 2'(f)) begin fr_st[f] <= F_FREE; fr_ep[f] <= 4'(EP0); fr_wrap[f] <= 1'b0; end
                // rfile slot f: reader pins released at compute done, the owner at retire
                if (ev_cd && relp[f]) rf_pin[f] <= rf_pin[f] - 3'd1;
                if (ev_ret && sl_rv[rh] && sl_rslot[rh] == 2'(f)) rf_own[f] <= 1'b0;
            end
            // ---------------------------------------------------------------- table: retire, staged
            for (integer e = 0; e < 8; e = e + 1) begin
                // the owner retires: rec_done hands the VM words back to the program (another unit may write them),
                // so the local copy is a forward source only for records decoded while the owner is in the ring
                if (ev_ret && tb_own[e] == rh) begin tb_live[e] <= 1'b0; tb_fok[e] <= 1'b0; end
                if (tb_kind[e] == K_SRC && stc[tb_own[e]]) tb_stg[e] <= 1'b1;
            end
            // ---------------------------------------------------------------- decode pipeline
            case (dstt)
                D_IDLE: begin
                    op_rdy_r <= (cnt <= 4'd4) && !hfault && !take;
                    if (take) begin
                        w <= op_w[627:0]; dslot <= rt; mph <= 4'd0;
                        no_m1 <= op_w[0 +: 16] - 16'd1; ni_m1 <= op_w[16 +: 16] - 16'd1; nih_m1 <= ((op_w[16 +: 16] + 16'd1) >> 1) - 16'd1; f_used <= 8'd0; ip_on <= 1'b0; stallc <= 4'd0;
                        sl_ov[rt] <= 1'b0; sl_rv[rt] <= 1'b0; sl_opin[rt] <= 1'b0; sl_oovs[rt] <= 1'b0; sl_odense[rt] <= 1'b0;
                        sl_olive[rt] <= 1'b0; sl_cpin[rt] <= 12'd0; sl_rpin[rt] <= 4'd0;
                        if (strm != 2'd0 || op_w[136 +: 2] != 2'd0) begin dfault <= 1'b1; dstt <= D_FAULT; end   // known gaps
                        else dstt <= D_MUL;
                    end
                end
                // SPAN: (nr - 1) so + (ni - 1) si, all 6 regions at once: 4 x 24 nibble products, byte products, sum,
                // extent (4 edges; 10-13: the 8 x 24 product in one edge was a 27-level stage, ~995 ps)
                D_MUL: begin
                    // B3 (head gate r4-pre: m_a -> pn 21 levels, pq -> pacc 4-input 40-b add -64 ps): operand selects
                    // registered first (rm_*), the 4-input sum split into two pair sums (s01 / s23) and their add.
                    // B4 (head gate r4-pre2: rm_a -> pn 21 levels -38 ps; one OR2 enable net with 3,008 loads = the D_MUL
                    // decode enabling every pipeline register): the pipeline below is FREE-RUNNING (no state enable; its
                    // operands are registers that hold still from take through D_MUL, so mph == 6 sees the same values)
                    // and each nibble product is two registered pair sums plus their add.  MUL 7 edges a record (mph 0..6).
                    if (mph == 4'd6) begin
                        for (integer k = 0; k < 6; k = k + 1) begin lo[k] <= c_base[k][17:0]; hi[k] <= mhi[k][17:0]; end
                        if (cpair) begin lo[0] <= c_base[0][17:0] & ~18'd1; hi[0] <= mhi[0][17:0] | 18'd1; end
                        if (m_badv != 6'd0) begin dfault <= 1'b1; dstt <= D_FAULT; end   // an operand word >= 2^18
                        else begin dstt <= D_CL0; rv <= c_used; end
                    end
                    mph <= mph + 4'd1;
                end
                // CLASSIFY edge 1: every comparator against the 8 table entries, registered
                D_CL0: begin
                    for (integer e = 0; e < 8; e = e + 1) begin
                        for (integer q = 0; q < 4; q = q + 1) begin
                            h_in[q][e] <= rv[q] && tb_v[e] && tb_fok[e] && (tb_kind[e] == K_SRC || tb_dense[e]) &&
                                          lo[q] >= tb_lo[e] && hi[q] <= tb_hi[e];
                            h_eq[q][e] <= lo[q] == tb_lo[e] && hi[q] == tb_hi[e];
                            h_ov[q][e] <= rv[q] && tb_v[e] && tb_live[e] && ovl18(lo[q], hi[q], tb_lo[e], tb_hi[e]);
                        end
                        for (integer k = 0; k < 2; k = k + 1) begin
                            s_ov[k][e] <= rv[4+k] && tb_v[e] && ovl18(lo[4+k], hi[4+k], tb_lo[e], tb_hi[e]);
                            s_ovs[k][e] <= rv[4+k] && tb_v[e] && tb_live[e] &&
                                           lo[4+k][17:3] <= tb_hi[e][17:3] && tb_lo[e][17:3] <= hi[4+k][17:3];
                        end
                        o_eq[e] <= lo[4] == tb_lo[e] && hi[4] == tb_hi[e];
                    end
                    for (integer q = 0; q < 4; q = q + 1)       // the source shares a VM sector with an own sink
                        sv_s[q] <= rv[q] && ((rv[4] && lo[q][17:3] <= hi[4][17:3] && lo[4][17:3] <= hi[q][17:3]) ||
                                             (rv[5] && lo[q][17:3] <= hi[5][17:3] && lo[5][17:3] <= hi[q][17:3]));
                    if (rv[5] && (hi[5] - lo[5]) > 18'd55) begin dfault <= 1'b1; dstt <= D_FAULT; end   // R span > 56 words
                    else dstt <= D_CL1;
                end
                // CLASSIFY edge 2: the first containing entry a source; the in-place candidates
                D_CL1: begin
                    for (integer q = 0; q < 4; q = q + 1) begin : c1q
                        reg [3:0] f; f = ff8(h_in[q]);
                        f_hit[q] <= f[3]; f_e[q] <= f[2:0];
                        f_ipc[q] <= ((fh[q] & h_eq[q] & o_eq & tb_osd) != 8'd0) && c_ipd[q] && rv[4] && c_dense[4];
                    end
                    dstt <= D_SK0;
                end
                D_SK0: begin
                    begin : sk0
                        reg [2:0] f; f = ff4(f_ipc);
                        ip_c <= f[2]; ip_e <= f_e[f[1:0]];
                    end
                    f_used <= (f_hit[0] ? oh8(f_e[0]) : 8'd0) | (f_hit[1] ? oh8(f_e[1]) : 8'd0) |
                              (f_hit[2] ? oh8(f_e[2]) : 8'd0) | (f_hit[3] ? oh8(f_e[3]) : 8'd0);
                    dstt <= D_SK1;
                end
                // SINKS: in-place decision ; TAINT every entry a sink of this record overlaps (not the in-place one)
                D_SK1: begin
                    ip_on <= ip_on_n;
                    for (integer e = 0; e < 8; e = e + 1)
                        if ((s_ov[0][e] || s_ov[1][e]) && !(ip_on_n && ip_e == 3'(e))) tb_fok[e] <= 1'b0;
                    sl_lvw[dslot] <= c_lvw;                    // EVERY record (the EXT stream credit needs it without an O sink)
                    rk <= 3'd4; dstt <= D_AA; pre(3'd4, bp);
                end
                // ALLOC edge A (region rk, order O R A B C D): decide forward / in place / allocate, pin
                D_AA: begin
                    if (!cur_used) begin
                        if (rk == 3'd3) dstt <= D_HOLD;
                        else begin rk <= (rk == 3'd5) ? 3'd0 : rk + 3'd1; pre((rk == 3'd5) ? 3'd0 : rk + 3'd1, bp); end
                    end else if (aa_fault) begin dfault <= 1'b1; dstt <= D_FAULT; end
                    else if (aa_go) begin
                        dstt <= D_AB; stallc <= 4'd0;
                        a_stg <= is_src && !fw_ok; a_big <= a_large; a_delta <= alloc_delta[rk]; a_tw <= ipnow ? ip_two : a_two;
                        if (ipnow) begin                                           // IN PLACE: e's local words, a new epoch
                            a_lb <= tb_lb[ip_e]; a_ep <= ip_ep; fr_ep[ip_f] <= ip_ep;
                            if (ip_two) begin fr_ep[ip_fn] <= ip_ep; if (ip_wrap) fr_wrap[ip_fn] <= 1'b1; end
                            if (ip_wrap) begin
                                fr_wrap[ip_f] <= 1'b1;
                                if (open_v && opf == ip_f) begin fr_st[ip_f] <= F_HELD; open_v <= 1'b0; end
                            end
                            tb_own[ip_e] <= dslot; tb_live[ip_e] <= 1'b1; tb_fok[ip_e] <= 1'b1;
                        end else if (rk == 3'd5) begin                             // R: an rfile slot, lb == lo (mod 8)
                            a_lb <= {1'b1, 10'd0, rfs[1:0], 3'd0, cur_lo[2:0]};
                            rf_own[rfs[1:0]] <= 1'b1; rf_clr[rfs[1:0]] <= 1'b1;
                            for (integer e = 0; e < 8; e = e + 1)
                                if (tb_kind[e] == K_RS && tb_lb[e][7:6] == rfs[1:0]) tb_v[e] <= 1'b0;
                            tb_v[vic] <= 1'b1; tb_fok[vic] <= 1'b1; tb_live[vic] <= 1'b1; tb_dense[vic] <= c_dense[5];
                            tb_stg[vic] <= 1'b1; tb_kind[vic] <= K_RS; tb_lo[vic] <= cur_lo; tb_hi[vic] <= cur_hi;
                            tb_lb[vic] <= {1'b1, 10'd0, rfs[1:0], 3'd0, cur_lo[2:0]}; tb_own[vic] <= dslot;
                        end else if (fw_ok) begin                                  // FORWARD: e's local words, pinned
                            a_delta <= fwd_delta[aq];
                            a_lb <= (fw_rs && MUT_V == 6) ? (tb_lb[fe] ^ 19'h00040) : tb_lb[fe];
                            if (fw_rs) begin
                                if (!sl_rpin[dslot][tb_lb[fe][7:6]] && MUT_V != 4) begin
                                    sl_rpin[dslot][tb_lb[fe][7:6]] <= 1'b1;
                                    // an rfile slot's release (ev_cd) and this pin never hit the same slot's last
                                    // reference in a way that frees it: the slot is free only at pin 0 AND !own
                                    rf_pin[tb_lb[fe][7:6]] <= rf_pin[tb_lb[fe][7:6]] + 3'd1 -
                                                              ((ev_cd && relp[tb_lb[fe][7:6]]) ? 3'd1 : 3'd0);
                                end
                            end else if (MUT_V != 4)
                                sl_cpin[dslot][3*tb_lb[fe][17:16] +: 3] <= sl_cpin[dslot][3*tb_lb[fe][17:16] +: 3] + 3'd1;
                        end else begin                                             // ALLOCATE (O or a staged source)
                            a_lb <= ra_lb; a_ep <= ra_ep;
                            if (a_large) begin
                                fr_st[ffr[1:0]] <= F_HELD; fr_ep[ffr[1:0]] <= ra_ep;
                                if (a_two) begin fr_st[ffn] <= F_HELD; fr_ep[ffn] <= ra_ep; fr_tail[ffn] <= 1'b1; end
                            end else bp <= bp_n;
                            if (is_src) sl_cpin[dslot][3*ra_f +: 3] <= sl_cpin[dslot][3*ra_f +: 3] + 3'd1;
                            else begin                                             // the O sink's table entry (mandatory)
                                tb_v[vic] <= 1'b1; tb_fok[vic] <= 1'b1; tb_live[vic] <= 1'b1; tb_dense[vic] <= c_dense[4];
                                tb_stg[vic] <= 1'b1; tb_kind[vic] <= K_OS; tb_lo[vic] <= cur_lo; tb_hi[vic] <= cur_hi;
                                tb_lb[vic] <= ra_lb; tb_own[vic] <= dslot;
                            end
                        end
                    end else begin
                        // no room: turn the bump frame over (close it, then open the lowest FREE frame), or wait for a
                        // retire / scrub.  A record that is alone in the ring and still cannot allocate is a fault.
                        if (ra_req && !a_large) begin
                            if (open_v) begin fr_st[opf] <= F_HELD; open_v <= 1'b0; end
                            else if (ffr1[2]) begin
                                fr_st[ffr1[1:0]] <= F_OPEN; fr_ep[ffr1[1:0]] <= fr_ep[ffr1[1:0]] + 4'd1; opf <= ffr1[1:0];
                                open_v <= 1'b1; bp <= 17'd0; pre(rk, 17'd0);
                            end
                        end else if (ra_req && a_large && !ra_ok && open_v && fr_pin[opf] == 6'd0 && !d_pin_v) begin
                            fr_st[opf] <= F_HELD; open_v <= 1'b0;          // an empty bump frame gives way to a large region
                        end
                        if (cnt == 4'd1 && fr_st[0] != F_SCRUB && fr_st[1] != F_SCRUB && fr_st[2] != F_SCRUB && fr_st[3] != F_SCRUB) begin
                            stallc <= stallc + 4'd1;
                            if (stallc == 4'd15) begin dfault <= 1'b1; dstt <= D_FAULT; end
                        end
                    end
                end
                // Relocation is split across the existing A/B edges: A registers base - origin, B adds local base.
                // ALLOC edge B: relocate the region's base, write the descriptors, push the stage job
                D_AB: if (ab_go) begin
                    case (rk)
                        3'd0: w[40 +: 24]  <= a_delta + {5'd0, a_lb};
                        3'd1: w[138 +: 24] <= a_delta + {5'd0, a_lb};
                        3'd2: w[211 +: 24] <= a_delta + {5'd0, a_lb};
                        3'd3: w[284 +: 24] <= a_delta + {5'd0, a_lb};
                        3'd4: w[382 +: 24] <= a_delta + {5'd0, a_lb};
                        default: w[484 +: 24] <= a_delta + {5'd0, a_lb};
                    endcase
                    if (rk == 3'd4) begin
                        sl_ov[dslot] <= 1'b1; sl_opin[dslot] <= 1'b1; sl_ovsec[dslot] <= cur_lo[17:3];
                        sl_on[dslot] <= 14'(cur_hi[17:3] - cur_lo[17:3]) + 14'd1; sl_olsec[dslot] <= a_lb[17:3];
                        sl_oep[dslot] <= a_ep; sl_olo3[dslot] <= cur_lo[2:0]; sl_odense[dslot] <= c_dense[4];
                        sl_olive[dslot] <= c_olive; sl_oovs[dslot] <= sv_s != 4'd0; sl_otwo[dslot] <= a_tw;
                    end else if (rk == 3'd5) begin
                        sl_rv[dslot] <= 1'b1; sl_rslot[dslot] <= a_lb[7:6]; sl_rvsec[dslot] <= cur_lo[17:3];
                        sl_rns[dslot] <= 4'(cur_hi[17:3] - cur_lo[17:3]) + 4'd1;
                    end else if (a_stg) begin
                        jq_slot[jq_wp[2:0]] <= dslot; jq_vsec[jq_wp[2:0]] <= cur_lo[17:3];
                        jq_n[jq_wp[2:0]] <= 14'(cur_hi[17:3] - cur_lo[17:3]) + 14'd1; jq_lsec[jq_wp[2:0]] <= a_lb[17:3];
                        jq_strm[jq_wp[2:0]] <= c_dense[rk]; jq_wp <= jq_wp + 4'd1;
                        if (a_big && vic_v) begin                                  // optional SRC entry (dedicated frame)
                            tb_v[vic] <= 1'b1; tb_fok[vic] <= !sv_s[aq]; tb_live[vic] <= 1'b0; tb_dense[vic] <= 1'b1;
                            tb_stg[vic] <= 1'b0; tb_kind[vic] <= K_SRC; tb_lo[vic] <= cur_lo; tb_hi[vic] <= cur_hi;
                            tb_lb[vic] <= a_lb; tb_own[vic] <= dslot;
                        end
                    end
                    if (rk == 3'd3) dstt <= D_HOLD;
                    else begin rk <= (rk == 3'd5) ? 3'd0 : rk + 3'd1; dstt <= D_AA; pre((rk == 3'd5) ? 3'd0 : rk + 3'd1, bp); end
                end
                D_HOLD: if (push_take) dstt <= D_IDLE;                              // the word moved into the FIFO
                default: ;                                                          // D_FAULT: sticky
            endcase
            if (hfault) op_rdy_r <= 1'b0;
        end
    end

    // ================================================================================================= [BOOK]
    always @(posedge clk or negedge rr_hd[4]) begin
        if (!rr_hd[4]) begin
            rt <= 3'd0; cnt <= 4'd0; bkfault <= 1'b0;
            s_v <= 8'd0; s_nop <= 8'd0; s_dd <= 8'd0; s_gone <= 8'd0; s_cd <= 8'd0; s_odone <= 8'd0; s_old <= 8'd0;
            s_odsl <= 8'd0; s_rdone <= 8'd0; s_ipg <= 8'd0; stc <= 8'd0;
            for (integer s = 0; s < 8; s = s + 1) begin
                st_pend[s] <= 3'd0; ns_pend[s] <= 3'd0; unl[s] <= 3'd0; s_ipold[s] <= 3'd0;
                swait[s] <= 8'd0; dwait[s] <= 8'd0; fdep[s] <= 8'd0;
            end
        end else begin
            bkfault <= 1'b0;
            for (integer s = 0; s < 8; s = s + 1) begin
                stc[s] <= s_v[s] && s_dd[s] && st_pend[s] == 3'd0;              // the record's stage is complete
                st_pend[s] <= st_pend[s] + ((jq_push && dslot == 3'(s)) ? 3'd1 : 3'd0) - ((ev_jd && jd_slot == 3'(s)) ? 3'd1 : 3'd0);
                ns_pend[s] <= ns_pend[s] + ((jq_push && dslot == 3'(s) && !c_dense[rk]) ? 3'd1 : 3'd0)
                                         - ((ev_jd && jd_slot == 3'(s) && !jd_strm) ? 3'd1 : 3'd0);
                unl[s] <= unl[s] + ((jq_push && dslot == 3'(s)) ? 3'd1 : 3'd0) - ((ev_jl && jl_slot == 3'(s)) ? 3'd1 : 3'd0);
                fdep[s] <= fdep[s] & ~stc;
                swait[s] <= swait[s] & ~retmask; dwait[s] <= dwait[s] & ~retmask;
                if (ev_ret && s_ipold[s] == rh) s_ipg[s] <= 1'b0;
            end
            if (ev_dw) dwait[dslot] <= msk_dw;
            if (jq_push) swait[dslot] <= (swait[dslot] & ~retmask) | msk_sw;
            if (ev_fd) fdep[dslot] <= (fdep[dslot] & ~stc) | oh8(tb_own[fe]);
            if (ev_ip) begin s_ipg[dslot] <= ip_gate; s_ipold[dslot] <= tb_own[ip_e]; end
            if (ev_dd) s_dd[dslot] <= 1'b1;
            if (ev_go) s_gone[rp] <= 1'b1;
            if (ev_cd) s_cd[rp] <= 1'b1;
            if (ev_dl) begin s_old[dp] <= 1'b1; s_odsl[dp] <= dl_d; end
            if (ev_od) s_odone[od_slot] <= 1'b1;
            if (ev_rd) s_rdone[rdp] <= 1'b1;
            if (ev_ret) s_v[rh] <= 1'b0;
            if (take || nop_ev) begin
                s_v[rt] <= 1'b1; s_nop[rt] <= !take; s_dd[rt] <= !take; s_cd[rt] <= !take; s_gone[rt] <= 1'b0;
                s_odone[rt] <= 1'b0; s_old[rt] <= 1'b0; s_rdone[rt] <= 1'b0; s_ipg[rt] <= 1'b0; stc[rt] <= 1'b0;
                st_pend[rt] <= 3'd0; ns_pend[rt] <= 3'd0; unl[rt] <= 3'd0; swait[rt] <= 8'd0; dwait[rt] <= 8'd0; fdep[rt] <= 8'd0;
                rt <= rt + 3'd1;
            end
            cnt <= cnt + ((take || nop_ev) ? 4'd1 : 4'd0) - (ev_ret ? 4'd1 : 4'd0);
            if ((nop_ev && (take || cnt >= 4'd7)) || (take && cnt >= 4'd7)) bkfault <= 1'b1;   // ring overflow: never 8
        end
    end

    // ================================================================================================= [STAGE]
    // Job queue head -> a free leaf stage slot: oldest job first, its record at most LA ahead of RUN, its hazard
    // owners retired, the read lane group granted.  Scrub jobs (frame state SCRUB) need no grant.
    wire [2:0] jh = jq_rp[2:0];
    wire       jq_ne = jq_wp != jq_rp;
    wire [2:0] jh_own = jq_slot[jh];
    wire [2:0] jh_dist = jh_own - rp;
    reg        jh_ok; reg [4:0] sh_bl; reg [2:0] rcool;
    reg [NSJ-1:0] sdn;
    always @* for (integer j = 0; j < NSJ; j = j + 1) sdn[j] = sj_busy[j] && sj_bl[j] == 5'd0 && st_sdone[j];
    wire [3:0] fj = ff8({{(8-NSJ){1'b0}}, ~sj_busy});               // a free stage slot
    wire [3:0] fd = ff8({{(8-NSJ){1'b0}}, sdn});                    // a finished one (one an edge)
    wire [2:0] scp = ff4({fr_st[3] == F_SCRUB && !sc_ld[3], fr_st[2] == F_SCRUB && !sc_ld[2],
                          fr_st[1] == F_SCRUB && !sc_ld[1], fr_st[0] == F_SCRUB && !sc_ld[0]});
    wire st_can = jq_ne && jh_ok && rg_req && rg_q && fj[3] && !hfault;
    wire sc_can = scp[2] && fj[3] && !hfault;
    wire dr_can;
    assign ld_dr = dr_can;
    assign ld_st = !dr_can && st_can;
    assign ld_sc = !dr_can && !st_can && sc_can;
    assign ev_jl = ld_st; assign jl_slot = jh_own;
    assign ev_jd = fd[3] && !sj_scrub[fd[2:0]]; assign jd_slot = sj_own[fd[2:0]]; assign jd_strm = sj_strm[fd[2:0]];
    assign ev_scd = fd[3] && sj_scrub[fd[2:0]]; assign scd_f = sj_fr[fd[2:0]];
    wire vm_stg_busy = (sj_busy & ~sj_scrub) != '0;
    always @(posedge clk or negedge rr_hd[5]) begin
        if (!rr_hd[5]) begin
            jq_rp <= 4'd0; jh_ok <= 1'b0; sh_bl <= 5'd0; rcool <= 3'd0; rg_req <= 1'b0; sc_ld <= 4'd0;
            sj_busy <= '0; sj_strm <= '0; sj_scrub <= '0;
            for (integer j = 0; j < NSJ; j = j + 1) begin sj_own[j] <= 3'd0; sj_fr[j] <= 2'd0; sj_bl[j] <= 5'd0; end
        end else begin
            // the head job's gate, registered (false for one edge after a pop: it describes the old head)
            jh_ok <= jq_ne && !ld_st && jh_dist <= LA && (swait[jh_own] & ~retmask) == 8'd0;
            for (integer j = 0; j < NSJ; j = j + 1) if (sj_bl[j] != 5'd0) sj_bl[j] <= sj_bl[j] - 5'd1;
            if (sh_bl != 5'd0) sh_bl <= sh_bl - 5'd1;
            if (rcool != 3'd0) rcool <= rcool - 3'd1;
            if (fd[3]) begin                                           // a job is done (blanked sdone): free the slot
                sj_busy[fd[2:0]] <= 1'b0;
                if (sj_scrub[fd[2:0]]) sc_ld[sj_fr[fd[2:0]]] <= 1'b0;
            end
            if (ld_st) begin
                sj_busy[fj[2:0]] <= 1'b1; sj_strm[fj[2:0]] <= jq_strm[jh]; sj_scrub[fj[2:0]] <= 1'b0; sj_own[fj[2:0]] <= jh_own;
                sj_bl[fj[2:0]] <= BLV; sh_bl <= BLV; jq_rp <= jq_rp + 4'd1;
            end
            if (ld_sc) begin
                sj_busy[fj[2:0]] <= 1'b1; sj_strm[fj[2:0]] <= 1'b0; sj_scrub[fj[2:0]] <= 1'b1; sj_fr[fj[2:0]] <= scp[1:0];
                sj_bl[fj[2:0]] <= BLV; sc_ld[scp[1:0]] <= 1'b1;
            end
            // the read lane group: request when a job is loadable; release only with no VM stage job busy and the
            // blanked shome; then >= 5 edges before the next request
            if (!rg_req) begin
                if (jq_ne && jh_ok && rcool == 3'd0 && !hfault) rg_req <= 1'b1;
            end else if (rg_q && !(jq_ne && jh_ok) && !ld_st && !vm_stg_busy && sh_bl == 5'd0 && st_shome) begin
                rg_req <= 1'b0; rcool <= 3'd5;
            end
        end
    end

    // ================================================================================================= [DRAIN]
    // O drains in ring order into the 2 leaf drain slots.  A dense O loads at / after its go (frontier follows the
    // compute), a non-dense one after its compute (frame walk, chk 0).  Gates: older overlapping sinks retired
    // (dwait), own stage complete if the O sectors overlap own staged sources (o_ovs).
    reg [2:0] dv_tag; reg dv_v, dv_nop, dv_ov, dv_dense, dv_live, dv_rdy, dv_soon;
    reg [14:0] dv_vsec, dv_lsec; reg [13:0] dv_n; reg [3:0] dv_ep;
    reg [4:0] dh_bl; reg [2:0] wcool;
    wire dv_ok = dv_v && dv_tag == dp;
    wire fdr_v = !(&dr_busy); wire fdr = dr_busy[0];
    wire [1:0] ddn = {dr_busy[1] && dr_bl[1] == 5'd0 && st_ddone[1], dr_busy[0] && dr_bl[0] == 5'd0 && st_ddone[0]};
    wire dfin_v = ddn != 2'd0; wire dfin = !ddn[0];
    wire dr_want = dv_ok && !dv_nop && dv_ov && dv_rdy;
    assign dr_can = dr_want && fdr_v && wg_req && wg_q && !hfault;
    assign ev_dl = ld_dr; assign dl_d = fdr;
    assign ev_od = dfin_v; assign od_slot = dr_own[dfin];
    wire [1:0] rs;                                                      // RUN state (declared below)
    always @(posedge clk or negedge rr_hd[6]) begin
        if (!rr_hd[6]) begin
            dp <= 3'd0; dv_v <= 1'b0; dv_tag <= 3'd0; dv_nop <= 1'b0; dv_ov <= 1'b0; dv_rdy <= 1'b0; dv_soon <= 1'b0;
            dv_dense <= 1'b0; dv_live <= 1'b0;
            dr_busy <= 2'd0; dr_live <= 2'd0; dh_bl <= 5'd0; wcool <= 3'd0; wg_req <= 1'b0; walks <= 16'd0;
            for (integer d = 0; d < 2; d = d + 1) begin dr_own[d] <= 3'd0; dr_bl[d] <= 5'd0; dr_n[d] <= 14'd0; end
        end else begin
            // the registered view of slot dp (a slot is never retired before dp passed it)
            dv_tag <= dp; dv_v <= s_v[dp] && s_dd[dp]; dv_nop <= s_nop[dp]; dv_ov <= sl_ov[dp];
            dv_dense <= sl_odense[dp]; dv_live <= sl_olive[dp]; dv_vsec <= sl_ovsec[dp]; dv_n <= sl_on[dp];
            dv_lsec <= sl_olsec[dp]; dv_ep <= sl_oep[dp];
            dv_rdy <= (sl_odense[dp] ? s_gone[dp] : s_cd[dp]) && (dwait[dp] & ~retmask) == 8'd0 && (!sl_oovs[dp] || stc[dp]);
            dv_soon <= sl_odense[dp] && rp == dp && rs != 2'd0 && (dwait[dp] & ~retmask) == 8'd0;   // about to go
            for (integer d = 0; d < 2; d = d + 1) if (dr_bl[d] != 5'd0) dr_bl[d] <= dr_bl[d] - 5'd1;
            if (dh_bl != 5'd0) dh_bl <= dh_bl - 5'd1;
            if (wcool != 3'd0) wcool <= wcool - 3'd1;
            if (dfin_v) dr_busy[dfin] <= 1'b0;                          // drain done (blanked ddone)
            if (ld_dr) begin
                dr_busy[fdr] <= 1'b1; dr_own[fdr] <= dp; dr_n[fdr] <= dv_n; dr_live[fdr] <= dv_live; dr_bl[fdr] <= BLV;
                dh_bl <= BLV; dp <= dp + 3'd1; dv_v <= 1'b0;
                if (!dv_dense) walks <= walks + 16'd1;
            end else if (dv_ok && (dv_nop || !dv_ov)) begin dp <= dp + 3'd1; dv_v <= 1'b0; end
            // the write lane group
            if (!wg_req) begin
                if ((dr_want || (dv_ok && dv_ov && dv_soon)) && wcool == 3'd0 && !hfault) wg_req <= 1'b1;
            end else if (wg_q && !dr_want && !(dv_ok && dv_ov && dv_soon) && !ld_dr && dr_busy == 2'd0 && dh_bl == 5'd0 && st_dhome) begin
                wg_req <= 1'b0; wcool <= 3'd5;
            end
        end
    end

    // ================================================================================================= [CMD]
    // The head cmd register (and its twin): at most one job load an edge (drain > stage > scrub); dfr / ssel / dsel
    // are levels.
    reg [CW-1:0] hc_n;
    always @* begin
        hc_n[0] = ld_dr || ld_st || ld_sc;
        hc_n[1] = ld_dr;
        hc_n[4:2] = ld_dr ? {2'b00, fdr} : fj[2:0];
        hc_n[19:5] = ld_dr ? dv_vsec : ld_st ? jq_vsec[jh] : 15'd0;
        hc_n[33:20] = ld_dr ? dv_n : ld_st ? jq_n[jh] : 14'd8192;
        hc_n[48:34] = ld_dr ? dv_lsec : ld_st ? jq_lsec[jh] : {scp[1:0], 13'd0};
        hc_n[52:49] = dv_ep;
        hc_n[53] = ld_dr ? dv_dense : ld_sc;                            // drain: chk (dense sink) ; stage: scrub
        hc_n[54 +: 14] = dfr[0]; hc_n[68 +: 14] = dfr[1];
        hc_n[82 +: NSJ] = ssel; hc_n[82+NSJ] = dsel;
    end
    always @(posedge clk or negedge rr_hd[7]) begin
        if (!rr_hd[7]) begin hc <= '0; hc2 <= '0; end
        else begin hc <= hc_n; hc2 <= hc_n; end
    end

    // ================================================================================================= [RUN]
    // Word FIFO {wl, q1} (+ w in D_HOLD).  One record in the vec: go when ready (registered) and only after the
    // previous record's idle (R 1975-2010: idle is stale for 3 edges after go).  A record with a streamed job still
    // active, or with the in-place gate, runs with ch_src EXT on x_seq / x_cnt / x_dseq.
    localparam [1:0] R_IDLE = 2'd0, R_SET = 2'd1, R_GO = 2'd2, R_RUN = 2'd3;
    reg [1:0] rs_r; assign rs = rs_r;
    reg wl_v, q1_v; reg [627:0] q1;
    // the head word: payload wl_lo has no reset (its own clocked block: no async-load flops), the chain field wl_hi has
    reg [627:0] wl_lo; reg [41:0] wl_hi; assign wl = {wl_hi, wl_lo};
    reg [2:0] rvw_tag; reg rvw_ok, rvw_nop, rvw_sp, rvw_ipg, rvw_olive, rvw_ov, rvw_otwo; reg [2:0] rvw_ipold;
    reg [13:0] rvw_on; reg [2:0] rvw_lo3; reg [3:0] rvw_lvw, rvw_oep; reg [1:0] rvw_ofr;
    reg [2:0] ipv_tag; reg ipv_done, ipv_ld, ipv_dsl;
    reg [13:0] r_on; reg [2:0] r_lo3; reg [3:0] r_lvw, r_oep; reg [1:0] r_ofr; reg r_olive, r_ov, r_ext, r_otwo;
    reg [7:0] r_seq, xs, vseq, vseq_run; reg [1:0] idle_ph; reg vf_seen;
    reg [13:0] gs_r, gi_r; reg [4:0] sp_bl, dp_bl;
    wire rvw_cur = rvw_tag == rp;
    wire push_ok = !wl_v || !q1_v;
    assign push_take = (dstt == D_HOLD) && push_ok;
    assign ev_go = rs_r == R_GO && ready_q && !hfault;
    wire run_end = rs_r == R_RUN && idle_ph == 2'd3 && idle_q;
    assign ev_cd = run_end && !(vf_seen || vfault_q);
    always @(posedge clk) begin
        if (ev_cd || (run_end && (vf_seen || vfault_q))) wl_lo <= push_take ? w : q1;    // pop (a push fills the head)
        else if (push_take && !wl_v) wl_lo <= w;
    end
    reg [NSJ-1:0] ssel_n;
    reg [NSJ-1:0] fd_oh;                                               // the stage slot freed this edge, one-hot (no sized cast: yosys)
    always @* for (integer j = 0; j < NSJ; j = j + 1) fd_oh[j] = fd[3] && fd[2:0] == 3'(j);
    always @* for (integer j = 0; j < NSJ; j = j + 1) ssel_n[j] = sj_busy[j] && !sj_scrub[j] && sj_strm[j] && sj_own[j] == rp;
    wire ext_s = rvw_sp;                                               // a (streamed) stage job of the record is active
    wire ext_i = rvw_ipg && MUT_V != 3;                                // in place over an owner that still drains
    wire [15:0] f_lead = (rvw_lvw >= 4'd3) ? ((16'd1 << (rvw_lvw - 4'd3)) + 16'd1) : 16'd2;
    wire [15:0] f_mul = 16'd32 << rvw_lvw;
    wire ipv_ok = ipv_tag == rp && rvw_cur;
    always @(posedge clk or negedge rr_hd[0]) begin
        if (!rr_hd[0]) begin
            rs_r <= R_IDLE; rp <= 3'd0; wl_v <= 1'b0; q1_v <= 1'b0; go <= 1'b0; wep <= 16'd0; rnfault <= 1'b0;
            x_seq <= 8'd0; x_dseq <= 8'hFF; x_cnt <= 16'd0; xs <= 8'd0; vseq <= 8'd0; vseq_run <= 8'd0; r_seq <= 8'd0;
            idle_ph <= 2'd0; vf_seen <= 1'b0; ssel <= '0; dsel <= 1'b0; sp_bl <= 5'd0; dp_bl <= 5'd0; gs_r <= 14'd0; gi_r <= 14'd0;
            rvw_tag <= 3'd0; rvw_ok <= 1'b0; rvw_nop <= 1'b0; rvw_sp <= 1'b0; rvw_ipg <= 1'b0; rvw_ipold <= 3'd0;
            rvw_olive <= 1'b0; rvw_ov <= 1'b0; rvw_otwo <= 1'b0; r_otwo <= 1'b0; ipv_tag <= 3'd0; ipv_done <= 1'b0; ipv_ld <= 1'b0; ipv_dsl <= 1'b0;
            r_ext <= 1'b0; r_olive <= 1'b0; r_ov <= 1'b0; wl_hi <= 42'd0;
            r_on <= 14'd0; r_lo3 <= 3'd0; r_lvw <= 4'd0; r_oep <= 4'd0; r_ofr <= 2'd0;
        end else begin
            go <= 1'b0; rnfault <= 1'b0;
            // ---- registered view of slot rp (1 edge stale; every field is monotone toward "ready" once s_dd)
            rvw_tag <= rp;
            rvw_ok <= s_v[rp] && s_dd[rp] && !s_nop[rp] && ns_pend[rp] == 3'd0 && unl[rp] == 3'd0 && (fdep[rp] & ~stc) == 8'd0;
            rvw_nop <= s_v[rp] && s_nop[rp];
            rvw_sp <= st_pend[rp] != 3'd0; rvw_ipg <= s_ipg[rp]; rvw_ipold <= s_ipold[rp];
            rvw_on <= sl_on[rp]; rvw_lo3 <= sl_olo3[rp]; rvw_lvw <= sl_lvw[rp]; rvw_oep <= sl_oep[rp];
            rvw_ofr <= sl_olsec[rp][14:13]; rvw_olive <= sl_olive[rp]; rvw_ov <= sl_ov[rp]; rvw_otwo <= sl_otwo[rp];
            ipv_tag <= rvw_tag; ipv_done <= s_odone[rvw_ipold]; ipv_ld <= s_old[rvw_ipold]; ipv_dsl <= s_odsl[rvw_ipold];
            // ---- word FIFO
            if (ev_cd || (run_end && (vf_seen || vfault_q))) begin         // pop
                if (push_take) wl_v <= 1'b1;                                // (q1 is empty when a push is allowed)
                else begin wl_v <= q1_v; q1_v <= 1'b0; end
            end else if (push_take) begin
                if (!wl_v) wl_v <= 1'b1;
                else begin q1 <= w; q1_v <= 1'b1; end
            end
            if (push_take && wl_v && q1_v) rnfault <= 1'b1;                  // cannot happen (push_ok)
            // ---- blank counters
            if (sp_bl != 5'd0) sp_bl <= sp_bl - 5'd1;
            if (dp_bl != 5'd0) dp_bl <= dp_bl - 5'd1;
            if (vfault_q && rs_r == R_RUN) vf_seen <= 1'b1;
            // a freed stage slot leaves ssel (it may be reloaded for another record): re-blank the prefix
            if (fd[3] && ssel[fd[2:0]]) begin ssel[fd[2:0]] <= 1'b0; sp_bl <= BLV; end
            case (rs_r)
                R_IDLE: if (rvw_cur && rvw_nop) rp <= rp + 3'd1;          // a nop entry: nothing to run
                        else if (rvw_cur && rvw_ok && wl_v && !hfault) rs_r <= R_SET;
                R_SET: begin                                               // latch the record, choose EXT or free run
                    r_on <= rvw_on; r_lo3 <= rvw_lo3; r_lvw <= rvw_lvw; r_oep <= rvw_oep; r_ofr <= rvw_ofr;
                    r_olive <= rvw_olive; r_ov <= rvw_ov; r_ext <= ext_s || ext_i; r_otwo <= rvw_otwo;
                    if (ext_s || ext_i) begin
                        wl_hi <= (MUT_V == 8) ? 42'd0 : {f_mul, f_lead, xs, 2'd3}; x_seq <= xs; r_seq <= xs; xs <= xs + 8'd1;
                    end else wl_hi <= 42'd0;
                    x_cnt <= 16'd0; gs_r <= 14'd0; gi_r <= 14'd0;
                    ssel <= ssel_n & ~fd_oh; sp_bl <= BLV;   // (a slot freed this edge is out)
                    rs_r <= R_GO;
                end
                R_GO: if (ev_go) begin
                    go <= 1'b1; idle_ph <= 2'd0; vf_seen <= 1'b0; vseq_run <= vseq; vseq <= vseq + 8'd1;
                    if (r_ov) begin                                        // the O frame's write epoch: only here
                        wep[4*r_ofr +: 4] <= r_oep;
                        if (r_otwo && MUT_V != 7) wep[4*(r_ofr + 2'd1) +: 4] <= r_oep;   // and its tail frame's
                    end
                    rs_r <= R_RUN;
                end
                default: begin                                             // R_RUN
                    if (idle_ph != 2'd3) idle_ph <= idle_ph + 2'd1;
                    else if (idle_q) begin
                        if (vf_seen || vfault_q) rnfault <= 1'b1;
                        if (r_ext) x_dseq <= r_seq;
                        rp <= rp + 3'd1; rs_r <= R_IDLE;
                    end
                end
            endcase
            // ---- EXT credits (R_GO / R_RUN): x_cnt = min(stage prefix, in-place gate); each term holds while blanked
            if (rs_r == R_GO || rs_r == R_RUN) begin
                if (rvw_cur && !rvw_sp) gs_r <= PDONE;                     // every stage job of the record accepted done
                else if (sp_bl == 5'd0) gs_r <= st_spre;
                if (MUT_V == 3 || !s_ipg[rp]) gi_r <= PDONE;               // the old owner retired (or never gated)
                else if (ipv_ok && ipv_done) gi_r <= PDONE;                // its drain is done
                else if (ipv_ok && ipv_ld && dsel == ipv_dsl && dp_bl == 5'd0) gi_r <= st_dpre;
                if (r_ext) begin
                    x_cnt <= {2'b00, (gs_r < gi_r) ? gs_r : gi_r};
                    if (gs_r == PDONE && gi_r == PDONE) x_dseq <= r_seq;
                end
                // the old owner's drain slot on dsel (blank after the change)
                if (s_ipg[rp] && ipv_ok && ipv_ld && !ipv_done && dsel != ipv_dsl) begin dsel <= ipv_dsl; dp_bl <= BLV; end
            end
            if (ev_dl) dp_bl <= BLV;                                       // any drain load re-blanks dpre
        end
    end

    // ================================================================================================= [FRONT]
    // The live write frontier of the RUN record's O: region sectors [0, frontier) are completely written.
    reg f1_v; reg [23:0] f1; reg [13:0] fr_run;
    wire [26:0] f_words = {24'd0, r_lo3} + ({11'd0, cr_cnt} << r_lvw);
    always @(posedge clk or negedge rr_hd[1]) begin
        if (!rr_hd[1]) begin
            f1_v <= 1'b0; f1 <= 24'd0; fr_run <= 14'd0; dfr[0] <= 14'd0; dfr[1] <= 14'd0;
        end else begin
            f1_v <= rs_r == R_RUN && r_olive && cr_seq == vseq_run && !ev_go;
            f1 <= f_words[26:3];
            if (ev_go) begin fr_run <= 14'd0; f1_v <= 1'b0; end
            else if (f1_v) fr_run <= (f1 >= {10'd0, r_on}) ? r_on : f1[13:0];
            for (integer d = 0; d < 2; d = d + 1) begin
                if (!dr_busy[d] || (ld_dr && fdr == d[0])) dfr[d] <= 14'd0;                     // a load starts at 0
                else if (s_cd[dr_own[d]]) dfr[d] <= dr_n[d];                                    // compute done: all
                else if (dr_live[d] && dr_own[d] == rp && rs_r == R_RUN && !ev_go) dfr[d] <= fr_run;
            end
            if (dfin_v) dfr[dfin] <= 14'd0;
        end
    end

    // ================================================================================================= [RDRAIN]
    // R results (rfile) to VM through the packet client, sector by sector, word mask rf_rm; ring order; after the
    // record's compute and after the older overlapping sinks retired (dwait).  <= 4 writes outstanding.
    localparam [1:0] Q_IDLE = 2'd0, Q_RD = 2'd1, Q_WT = 2'd2, Q_ACK = 2'd3;
    reg [1:0] qs; reg [2:0] qv_tag; reg qv_v, qv_nop, qv_rv, qv_rdy; reg [3:0] q_i; reg [2:0] outst;
    wire qv_ok = qv_v && qv_tag == rdp;
    wire [14:0] q_vs = sl_rvsec[rdp] + {11'd0, q_i};
    // rfile read return: pin flops (10-13: the return went straight into the packet register and the FSM)
    reg rrv_q; reg [255:0] rrd_q; reg [7:0] rrm_q;
    always @(posedge clk or negedge rr_hd[2]) if (!rr_hd[2]) rrv_q <= 1'b0; else rrv_q <= rf_rrv;
    always @(posedge clk) begin rrd_q <= rf_rd; rrm_q <= rf_rm; end
    wire q_iss = qs == Q_WT && rrv_q && rrm_q != 8'd0;
    assign ev_rd = qs == Q_ACK && outst == 3'd0;
    always @(posedge clk or negedge rr_hd[3]) begin
        if (!rr_hd[3]) begin
            qs <= Q_IDLE; rdp <= 3'd0; qv_v <= 1'b0; qv_tag <= 3'd0; qv_nop <= 1'b0; qv_rv <= 1'b0; qv_rdy <= 1'b0;
            q_i <= 4'd0; outst <= 3'd0; rf_rv <= 1'b0; rf_rsec <= 5'd0; vmq <= 338'd0;
        end else begin
            vmq[337] <= 1'b0; rf_rv <= 1'b0;
            qv_tag <= rdp; qv_v <= s_v[rdp] && s_dd[rdp]; qv_nop <= s_nop[rdp]; qv_rv <= sl_rv[rdp];
            qv_rdy <= s_cd[rdp] && (dwait[rdp] & ~retmask) == 8'd0;
            outst <= outst + (q_iss ? 3'd1 : 3'd0) - (vr_ack ? 3'd1 : 3'd0);
            case (qs)
                Q_IDLE: if (qv_ok) begin
                    if (qv_nop || !qv_rv) begin rdp <= rdp + 3'd1; qv_v <= 1'b0; end
                    else if (qv_rdy && !hfault) begin q_i <= 4'd0; qs <= Q_RD; end
                end
                Q_RD: if (outst < 3'd4) begin rf_rv <= 1'b1; rf_rsec <= {sl_rslot[rdp], q_i[2:0]}; qs <= Q_WT; end
                Q_WT: if (rrv_q) begin
                    if (rrm_q != 8'd0)
                        vmq <= {1'b1, 1'b1, {12'd0, q_vs}, 5'd0, rrd_q,
                                {{4{rrm_q[7]}}, {4{rrm_q[6]}}, {4{rrm_q[5]}}, {4{rrm_q[4]}},
                                 {4{rrm_q[3]}}, {4{rrm_q[2]}}, {4{rrm_q[1]}}, {4{rrm_q[0]}}}, 16'h5357};
                    q_i <= q_i + 4'd1;
                    qs <= (q_i + 4'd1 == sl_rns[rdp]) ? Q_ACK : Q_RD;
                end
                default: if (outst == 3'd0) begin rdp <= rdp + 3'd1; qv_v <= 1'b0; qs <= Q_IDLE; end   // every write acknowledged
            endcase
        end
    end

    // ================================================================================================= [RETIRE]
    // In ring order: compute done, O drain done, R writes acknowledged; the RUN / drain pointers have passed the slot.
    reg ret_ok; reg [2:0] ret_tag;
    assign ev_ret = ret_ok && ret_tag == rh;
    always @(posedge clk or negedge rr_hd[4]) begin
        if (!rr_hd[4]) begin
            rh <= 3'd0; ret_ok <= 1'b0; ret_tag <= 3'd0; rec_done <= 1'b0; rec_fault <= 1'b0; halted <= 1'b0;
            hfault <= 1'b0; su_fault_r <= 1'b0;
        end else begin
            ret_tag <= rh;
            ret_ok <= !ev_ret && s_v[rh] && s_cd[rh] && stc[rh] && (s_nop[rh] || ((!sl_ov[rh] || s_odone[rh]) && (!sl_rv[rh] || s_rdone[rh]))) &&
                      rp != rh && dp != rh && rdp != rh && !hfault;
            rec_done <= ev_ret && !hfault;
            if (ev_ret) rh <= rh + 3'd1;
            // faults: decode gaps, vec fault, ring overflow, local memory bank error, a leaf error -> sticky halt
            if (dfault || rnfault || bkfault || lm_err_q || st_err) hfault <= 1'b1;
            su_fault_r <= (dfault || rnfault || bkfault || lm_err_q || st_err) && !hfault;
            rec_fault <= ad_fault || ((dfault || rnfault || bkfault || lm_err_q || st_err) && !hfault);
            halted <= ad_halted || hfault;
        end
    end

    // ================================================================================================= census
    wire a_span = dstt != D_IDLE && dstt != D_HOLD && dstt != D_FAULT;   // a record in DECODE
    wire a_stage = vm_stg_busy;                                           // any (VM) stage job busy
    wire a_run = rs_r == R_RUN;                                           // the vec computes
    wire a_drain = dr_busy != 2'd0 || qs != Q_IDLE;                       // any drain busy

`ifdef SVDBG
    // integration trace (sim only): every head event, the fault causes, a stall dump
    integer dg_cyc, dg_quiet; reg dg_on;
    initial dg_on = !$test$plusargs("svquiet");
    always @(posedge clk or negedge rr_hd[5]) begin
        if (!rr_hd[5]) begin dg_cyc <= 0; dg_quiet <= 0; end
        else begin
            dg_cyc <= dg_cyc + 1;
            dg_quiet <= (cnt == 4'd0 || take || ev_go || ev_cd || ev_ret || ev_jl || ev_dl || ev_jd || ev_od || ev_rd) ? 0 : dg_quiet + 1;
            if (dg_on) begin
                if (take) $display("SV %0d take slot %0d no %0d ni %0d m1 %0d m2 %0d qm %0d ad %0d sfu %0d e1 %0d e2 %0d dst %0d red %0d strm %0d",
                    dg_cyc, rt, op_w[0 +: 16], op_w[16 +: 16], op_w[360 +: 3], op_w[363 +: 2], op_w[365 +: 3], op_w[368 +: 3],
                    op_w[371 +: 3], op_w[374 +: 3], op_w[377 +: 2], op_w[380 +: 2], op_w[478 +: 2], strm);
                if (nop_ev) $display("SV %0d nop slot %0d", dg_cyc, rt);
                if (dstt == D_CL0) for (integer k = 0; k < 6; k = k + 1) if (rv[k])
                    $display("SV %0d  region %0d lo %0d hi %0d base %0d so %0d si %0d dense %0d", dg_cyc, k, lo[k], hi[k], c_base[k],
                             c_so[k], c_si[k], c_dense[k]);
                if (dstt == D_SK1) $display("SV %0d  classify slot %0d hit %b e %0d %0d %0d %0d ipc %b ip_on %0d ip_e %0d lvw %0d olive %0d tb_v %b fok %b live %b",
                    dg_cyc, dslot, f_hit, f_e[0], f_e[1], f_e[2], f_e[3], f_ipc, ip_on_n, ip_e, c_lvw, c_olive, tb_v, tb_fok, tb_live);
                if (aa_go) $display("SV %0d  alloc slot %0d rk %0d %s lb %0d frame %0d ep %0d vic %0d rfs %0d bp %0d", dg_cyc, dslot, rk,
                    ipnow ? "INPLACE" : rk == 3'd5 ? "RFILE" : fw_ok ? (fw_rs ? "BYPASS" : "FWD") : is_src ? "STAGE" : "SINK",
                    ipnow ? tb_lb[ip_e] : rk == 3'd5 ? {1'b1, 10'd0, rfs[1:0], 3'd0, cur_lo[2:0]} : fw_ok ? tb_lb[fe] : ra_lb,
                    d_pin_f, ipnow ? ip_ep : ra_ep, vic, rfs, bp);
                if (ev_dd) $display("SV %0d decoded slot %0d", dg_cyc, dslot);
                if (ld_st) $display("SV %0d load STAGE leaf slot %0d rec slot %0d vsec %0d n %0d lsec %0d strm %0d", dg_cyc, fj[2:0], jh_own,
                    jq_vsec[jh], jq_n[jh], jq_lsec[jh], jq_strm[jh]);
                if (ld_sc) $display("SV %0d load SCRUB leaf slot %0d frame %0d", dg_cyc, fj[2:0], scp[1:0]);
                if (ld_dr) $display("SV %0d load DRAIN leaf slot %0d rec slot %0d vsec %0d n %0d lsec %0d ep %0d dense %0d live %0d", dg_cyc,
                    fdr, dp, dv_vsec, dv_n, dv_lsec, dv_ep, dv_dense, dv_live);
                if (fd[3]) $display("SV %0d stage slot %0d done (scrub %0d rec slot %0d)", dg_cyc, fd[2:0], sj_scrub[fd[2:0]], sj_own[fd[2:0]]);
                if (rs_r == R_SET) $display("SV %0d set slot %0d ext_s %0d ext_i %0d ssel_n %b", dg_cyc, rp, ext_s, ext_i, ssel_n);
                if (ev_go) $display("SV %0d go slot %0d ext %0d oep %0d ofr %0d A %0d B %0d C %0d D %0d O %0d R %0d", dg_cyc, rp, r_ext, r_oep,
                    r_ofr, wl[40 +: 24], wl[138 +: 24], wl[211 +: 24], wl[284 +: 24], wl[382 +: 24], wl[484 +: 24]);
                if (run_end) $display("SV %0d idle slot %0d vf %0d x_cnt %0d gs %0d gi %0d", dg_cyc, rp, vf_seen || vfault_q, x_cnt, gs_r, gi_r);
                if (ev_od) $display("SV %0d drain slot %0d done rec slot %0d", dg_cyc, dfin, od_slot);
                if (q_iss) $display("SV %0d rdrain rec slot %0d sector %0d mask %b", dg_cyc, rdp, q_vs, rf_rm);
                if (ev_rd) $display("SV %0d rdrain done rec slot %0d", dg_cyc, rdp);
                if (ev_ret) $display("SV %0d retire slot %0d", dg_cyc, rh);
                for (integer f = 0; f < 4; f = f + 1)
                    if (fr_st[f] == F_HELD && fr_pin[f] == 6'd0 && !(d_pin_v && d_pin_f == 2'(f))) $display("SV %0d frame %0d freed ep %0d", dg_cyc, f, fr_ep[f]);
            end
            if ((dfault || rnfault || bkfault || lm_err_q || st_err) && !hfault)
                $display("SV %0d FAULT dfault %0d rnfault %0d bkfault %0d lm_err %0d leaf_err %0d dstt %0d rk %0d mph %0d slot %0d", dg_cyc, dfault,
                         rnfault, bkfault, lm_err_q, st_err, dstt, rk, mph, dslot);
            if (dg_quiet == 40000) begin
                $display("SV %0d STALL cnt %0d rt %0d rh %0d rp %0d dp %0d rdp %0d dstt %0d rk %0d rs %0d qs %0d hfault %0d", dg_cyc, cnt, rt, rh,
                         rp, dp, rdp, dstt, rk, rs_r, qs, hfault);
                $display("SV   s_v %b nop %b dd %b gone %b cd %b odone %b old %b rdone %b ipg %b stc %b | sl_ov %b rv %b", s_v, s_nop, s_dd, s_gone,
                         s_cd, s_odone, s_old, s_rdone, s_ipg, stc, sl_ov, sl_rv);
                for (integer q = 0; q < 8; q = q + 1) if (s_v[q])
                    $display("SV   slot %0d st_pend %0d ns_pend %0d unl %0d swait %b dwait %b fdep %b", q, st_pend[q], ns_pend[q], unl[q],
                             swait[q], dwait[q], fdep[q]);
                $display("SV   jq wp %0d rp %0d jh_ok %0d rg_req %0d rg_q %0d wg_req %0d wg_q %0d sj_busy %b strm %b scrub %b dr_busy %b dfr %0d %0d",
                         jq_wp, jq_rp, jh_ok, rg_req, rg_q, wg_req, wg_q, sj_busy, sj_strm, sj_scrub, dr_busy, dfr[0], dfr[1]);
                $display("SV   status sdone %b ddone %b shome %0d dhome %0d spre %0d dpre %0d err %0d | wl_v %0d q1_v %0d rvw_ok %0d ready %0d idle %0d x_cnt %0d gs %0d gi %0d ssel %b dsel %0d r_ext %0d",
                         st_sdone, st_ddone, st_shome, st_dhome, st_spre, st_dpre, st_err, wl_v, q1_v, rvw_ok, ready_q, idle_q, x_cnt, gs_r, gi_r,
                         ssel, dsel, r_ext);
                $display("SV   frames st %0d %0d %0d %0d ep %0d %0d %0d %0d pin %0d %0d %0d %0d open %0d f %0d bp %0d | tb_v %b fok %b live %b rf_own %b",
                         fr_st[0], fr_st[1], fr_st[2], fr_st[3], fr_ep[0], fr_ep[1], fr_ep[2], fr_ep[3], fr_pin[0], fr_pin[1], fr_pin[2],
                         fr_pin[3], open_v, opf, bp, tb_v, tb_fok, tb_live, rf_own);
                $display("SV   outst %0d cr_seq %0d vseq_run %0d cr_cnt %0d fr_run %0d", outst, cr_seq, vseq_run, cr_cnt, fr_run);
                $finish;
            end
        end
    end
`endif

`ifdef PHTRACE
    // one line a record at retire: edge counts since reset (-1 = phase absent) + fwd / in-place / live flags
    integer ph_cyc, ph_num;
    integer ph_rec [0:7]; integer ph_dec [0:7]; integer ph_st0 [0:7]; integer ph_st1 [0:7]; integer ph_go [0:7];
    integer ph_idle [0:7]; integer ph_dr0 [0:7]; integer ph_dr1 [0:7]; reg [7:0] ph_fwd, ph_ip, ph_stc;
    always @(posedge clk or negedge rr_hd[6]) begin
        if (!rr_hd[6]) begin ph_cyc <= 0; ph_num <= 0; ph_fwd <= 8'd0; ph_ip <= 8'd0; ph_stc <= 8'd0; end
        else begin
            ph_cyc <= ph_cyc + 1;
            if (take || nop_ev) begin
                ph_rec[rt] <= ph_num; ph_num <= ph_num + 1; ph_dec[rt] <= take ? ph_cyc : -1; ph_st0[rt] <= -1; ph_st1[rt] <= -1;
                ph_go[rt] <= -1; ph_idle[rt] <= -1; ph_dr0[rt] <= -1; ph_dr1[rt] <= -1; ph_fwd[rt] <= 1'b0; ph_ip[rt] <= 1'b0;
                ph_stc[rt] <= 1'b0;
            end
            if (ev_jl && ph_st0[jl_slot] == -1) ph_st0[jl_slot] <= ph_cyc;
            for (integer s = 0; s < 8; s = s + 1)
                if (stc[s] && !ph_stc[s] && ph_st0[s] != -1) begin ph_st1[s] <= ph_cyc; ph_stc[s] <= 1'b1; end
            if (aa_go && is_src && fw_ok) ph_fwd[dslot] <= 1'b1;
            if (ev_ip) ph_ip[dslot] <= 1'b1;
            if (ev_go) ph_go[rp] <= ph_cyc;
            if (ev_cd) ph_idle[rp] <= ph_cyc;
            if (ev_dl) ph_dr0[dp] <= ph_cyc;
            if (ev_od) ph_dr1[od_slot] <= ph_cyc;
            if (ev_ret)
                $display("PH rec %0d dec %0d st0 %0d st1 %0d go %0d idle %0d dr0 %0d dr1 %0d ret %0d fwd %0d inplace %0d live %0d",
                         ph_rec[rh], ph_dec[rh], ph_st0[rh], ph_st1[rh], ph_go[rh], ph_idle[rh], ph_dr0[rh], ph_dr1[rh], ph_cyc,
                         ph_fwd[rh], ph_ip[rh], sl_ov[rh] && sl_olive[rh]);
        end
    end
`endif
endmodule
/* verilator lint_on UNUSEDPARAM */
/* verilator lint_on UNUSEDSIGNAL */

// =====================================================================================================================
// ot_hgi_sv_unit: EXACTLY ot_hgi_su_unit's port list.  u_ctl (head), g_leaf[16].u_leaf (2 VM lanes + their 2 banks
// each), u_vec (the stream unit), u_mem (4-frame local memory + rfile).  am_stream = 0.
// =====================================================================================================================
/* verilator lint_off UNUSEDSIGNAL */
/* verilator lint_off UNUSEDPARAM */
module ot_hgi_sv_unit #(
    parameter integer N = 16, M = 8, LV = 6,
    parameter integer LWB = 18,
    parameter integer PAYLOAD_RESET = 1,
    parameter integer GLU = 0,
    parameter integer SLB = 16,
    parameter integer LQ = 8,              // ONE constant = ot_hgi_vm_unit LQ (VM lane queue depth, power of two) = the credits a lane holds
    parameter integer EP0 = 0,             // frame epoch after a scrub (bench: 14 makes the chain's in-place sink wrap 15 -> 1)
    parameter integer MUT_V = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          rec_v,
    output wire          rec_rdy,
    input  wire [127:0]  rec_hdr,
    input  wire [255:0]  rec_sut,
    input  wire [255:0]  rec_a, rec_b, rec_c, rec_d, rec_o, rec_r, rec_i,
    input  wire [20:0]   rec_n_a,
    output wire          rec_done,
    output wire          rec_fault,
    output wire          halted,
    output wire [337:0]  vmq,
    input  wire [273:0]  vmr,
    input  wire          s0_v,
    input  wire [19:0]   s0_idx,
    input  wire [31:0]   s0_data,
    output wire [522:0]  am_stream,
    input  wire          am_rdy,
    output wire [32*16-1:0]  wrq,
    input  wire [31:0]       wrq_cr,
    input  wire [32*257-1:0] wrr,
    output wire [32*280-1:0] wwq,
    input  wire [31:0]       wwq_cr,
    input  wire [31:0]       wwq_done,
    output wire              rg_req,
    input  wire              rg_gnt,
    output wire              wg_req,
    input  wire              wg_gnt
);
    localparam integer AW = 24, NR = N / 8, NSJ = 6, CW = 83 + NSJ, SW = NSJ + 33;
    initial if (LWB != 18) begin $display("ot_hgi_sv_unit: LWB must be 18 (4 frames of 2^16 words + rfile at a[18])"); $finish; end
    wire go, ready, idle, vfault, ofault, ro; wire [669:0] wl;
    generate if ((1 << $clog2(LQ)) != LQ) begin : g_lq_must_be_pow2
        ot_hgi_sv_unit_LQ_must_equal_the_VM_lane_queue_depth_a_power_of_two u_trap ();
    end endgenerate
    wire [7:0] x_seq, x_dseq; wire [15:0] x_cnt;
    wire [15:0] wep; wire [3:0] rf_clr; wire rf_rv, rf_rrv; wire [4:0] rf_rsec; wire [255:0] rf_rd; wire [7:0] rf_rm;
    wire lm_bank_err; wire [15:0] walks;
    wire [2*CW-1:0] lf_cmd; wire [8*SW-1:0] lf_status;
    wire [CW-1:0] l_cmd [0:15]; wire [CW-1:0] l_cmdr [0:15]; wire [SW-1:0] l_st [0:15]; wire [SW-1:0] l_sti [0:15];
    localparam [SW-1:0] ST_NEUTRAL = {1'b0, 14'h3FFF, 14'h3FFF, 4'b1111, {NSJ{1'b1}}};
    wire [31:0] lsw_v, lsw_scrub, ldr_v, ldr_rv; wire [32*15-1:0] lsw_sec, ldr_sec; wire [32*256-1:0] lsw_d, ldr_d;
    wire [32*12-1:0] ldr_em;
    wire [N-1:0] vi_re, vm_we, kv_we; wire [N*AW-1:0] vi_addr, vm_waddr, kv_waddr; wire [N*32-1:0] vi_q;
    wire [4*N*AW-1:0] rd_addr; wire [4*N-1:0] rd_re; wire [8*N-1:0] rd_src; wire [4*N*32-1:0] rd_q;
    wire [N*32-1:0] vm_wdata, kv_wdata; wire [NR-1:0] res_we; wire [NR*AW-1:0] res_addr; wire [NR*32-1:0] res_data;
    wire [7:0] cr_seq, cr_dseq, cr_rseq; wire [15:0] cr_cnt, emitted; wire de, dr, ds; wire [7:0] es, rsq, ss;

    ot_hgi_sv_head #(.N(N), .M(M), .LV(LV), .LWB(LWB), .PAYLOAD_RESET(PAYLOAD_RESET), .GLU(GLU), .SLB(SLB), .LQ(LQ), .EP0(EP0),
                    .MUT_V(MUT_V), .NSJ(NSJ)) u_ctl (
        .clk(clk), .rst_n(rst_n), .rec_v(rec_v), .rec_rdy(rec_rdy), .rec_hdr(rec_hdr), .rec_sut(rec_sut), .rec_a(rec_a),
        .rec_b(rec_b), .rec_c(rec_c), .rec_d(rec_d), .rec_o(rec_o), .rec_r(rec_r), .rec_i(rec_i), .rec_n_a(rec_n_a),
        .rec_done(rec_done), .rec_fault(rec_fault), .halted(halted), .vmq(vmq), .vmr(vmr), .s0_v(s0_v),
        .s0_idx(s0_idx), .s0_data(s0_data), .am_stream(am_stream), .am_rdy(am_rdy), .go(go), .ready(ready),
        .idle(idle), .vfault(vfault), .wl(wl), .x_seq(x_seq), .x_dseq(x_dseq), .x_cnt(x_cnt), .cr_seq_i(cr_seq),
        .cr_dseq(cr_dseq), .cr_cnt_i(cr_cnt), .wep(wep), .rf_clr(rf_clr), .rf_rv(rf_rv), .rf_rsec(rf_rsec),
        .rf_rrv(rf_rrv), .rf_rd(rf_rd), .rf_rm(rf_rm), .lm_err(lm_bank_err), .rg_req(rg_req), .rg_gnt(rg_gnt),
        .wg_req(wg_req), .wg_gnt(wg_gnt), .lf_cmd(lf_cmd), .lf_status(lf_status), .walks(walks));

    // LEAF ROW (placement order = leaf index, head at the centre): near leaves 4..7 (cmd copy 0) and 8..11 (copy 1)
    // take the head's cmd; far leaf j takes the relay output of its partner (j + 4 for 0..3, j - 4 for 12..15: 4 leaf
    // pitches = 380 um) and returns its status to that partner; the head sees the 8 near leaves' folded status.
    genvar gi;
    generate for (gi = 0; gi < 16; gi = gi + 1) begin : g_leaf
        localparam integer NEAR = (gi >= 4 && gi < 12);
        localparam integer PART = (gi < 4) ? gi + 4 : (gi >= 12) ? gi - 4 : (gi < 8) ? gi - 4 : gi + 4;
        assign l_cmd[gi] = NEAR ? lf_cmd[(gi / 8)*CW +: CW] : l_cmdr[PART];
        assign l_sti[gi] = NEAR ? l_st[PART] : ST_NEUTRAL;
        if (NEAR) begin : g_near
            assign lf_status[(gi - 4)*SW +: SW] = l_st[gi];
        end
        ot_hgi_sv_lane2 #(.LQ(LQ), .NSJ(NSJ), .MUT_V(MUT_V)) u_leaf (
            .clk(clk), .rst_n(rst_n), .lid(4'(gi)),
            .wrq(wrq[2*gi*16 +: 2*16]), .wrq_cr(wrq_cr[2*gi +: 2]), .wrr(wrr[2*gi*257 +: 2*257]),
            .wwq(wwq[2*gi*280 +: 2*280]), .wwq_cr(wwq_cr[2*gi +: 2]), .wwq_done(wwq_done[2*gi +: 2]),
            .lsw_v(lsw_v[2*gi +: 2]), .lsw_sec(lsw_sec[2*gi*15 +: 2*15]), .lsw_d(lsw_d[2*gi*256 +: 2*256]),
            .lsw_scrub(lsw_scrub[2*gi +: 2]),
            .ldr_v(ldr_v[2*gi +: 2]), .ldr_sec(ldr_sec[2*gi*15 +: 2*15]), .ldr_rv(ldr_rv[2*gi +: 2]),
            .ldr_d(ldr_d[2*gi*256 +: 2*256]), .ldr_em(ldr_em[2*gi*12 +: 2*12]),
            .cmd(l_cmd[gi]), .cmd_r(l_cmdr[gi]), .st_in(l_sti[gi]), .status(l_st[gi]));
    end endgenerate

`ifdef SVCUT
    // CUT CENSUS (sim only, el1013 step 4): which word column does vec lane l touch?  d = (a - l) mod min(N, 256):
    // 0 = the lane's own column of its bank (bank = a[7:3], 16 lanes a bank at N = 512).  One line a record (at the
    // next go / at $finish): accesses and accesses with d != 0 a port class, and the largest |d| seen.
    localparam integer CM = (N < 256) ? N : 256;
    integer cu_n [0:5]; integer cu_x [0:5]; integer cu_m [0:5]; integer cu_rf [0:5]; integer cu_rec;
    task automatic cu_acc(input integer cls, input integer l, input [AW-1:0] a);
        integer d;
        begin
            if (a[LWB]) cu_rf[cls] = cu_rf[cls] + 1;
            else begin
                d = (int'(a[7:0]) - l) % CM; if (d < 0) d = d + CM; if (d > CM / 2) d = CM - d;
                cu_n[cls] = cu_n[cls] + 1; if (d != 0) cu_x[cls] = cu_x[cls] + 1; if (d > cu_m[cls]) cu_m[cls] = d;
            end
        end
    endtask
    task automatic cu_dump;
        begin
            $display("CUT rec %0d vi %0d/%0d/%0d rd0 %0d/%0d/%0d rd1 %0d/%0d/%0d rd2 %0d/%0d/%0d rd3 %0d/%0d/%0d wr %0d/%0d/%0d (acc/off-column/max |d|) rfile %0d %0d %0d %0d %0d %0d",
                     cu_rec, cu_n[0], cu_x[0], cu_m[0], cu_n[1], cu_x[1], cu_m[1], cu_n[2], cu_x[2], cu_m[2], cu_n[3], cu_x[3], cu_m[3],
                     cu_n[4], cu_x[4], cu_m[4], cu_n[5], cu_x[5], cu_m[5], cu_rf[0], cu_rf[1], cu_rf[2], cu_rf[3], cu_rf[4], cu_rf[5]);
            for (integer q = 0; q < 6; q = q + 1) begin cu_n[q] = 0; cu_x[q] = 0; cu_m[q] = 0; cu_rf[q] = 0; end
        end
    endtask
    initial begin cu_rec = -1; for (integer q = 0; q < 6; q = q + 1) begin cu_n[q] = 0; cu_x[q] = 0; cu_m[q] = 0; cu_rf[q] = 0; end end
    always @(posedge clk) begin
        if (go) begin if (cu_rec >= 0) cu_dump; cu_rec = cu_rec + 1; end
        for (integer l = 0; l < N; l = l + 1) begin
            if (vi_re[l]) cu_acc(0, l, vi_addr[l*AW +: AW]);
            for (integer q = 0; q < 4; q = q + 1) if (rd_re[4*l + q]) cu_acc(1 + q, l, rd_addr[(4*l + q)*AW +: AW]);
            if (vm_we[l]) cu_acc(5, l, vm_waddr[l*AW +: AW]);
        end
    end
    final cu_dump;
`endif

`ifdef OT_SU_C12
    ot_hdc_v41x_vec #(.N(N), .M(M), .LV(LV), .BCAST_STAGES(7), .RET_STAGES(8), .MLAT(6), .ALAT(6), .OPR(1), .DDIV(21),
                      .SIDEX(4), .FSQ(1), .CAPR(1), .RPAD(1), .RSL(2), .RTAP(1), .ROUT(1), .RSLICE(`OT_SU_C12_RSLICE),
                      .CTL12(1), .DENR(`OT_SU_C12_DENR), .SFUT(`OT_SU_C12_SFUT))
                    u_vec (.clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle),
`else
    ot_hdc_v41x_vec #(.N(N), .M(M), .LV(LV)) u_vec (.clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle),
`endif
        .i_nout(wl[0 +: 16]), .i_nin(wl[16 +: 16]), .i_asrc(wl[32 +: 2]), .i_bsrc(wl[34 +: 2]), .i_csrc(wl[36 +: 2]),
        .i_dsrc(wl[38 +: 2]), .i_abase(wl[40 +: 24]), .i_aso(wl[64 +: 24]), .i_asi(wl[88 +: 24]),
        .i_aibase(wl[112 +: 24]), .i_aind(wl[136 +: 2]), .i_bbase(wl[138 +: 24]), .i_bso(wl[162 +: 24]),
        .i_bsi(wl[186 +: 24]), .i_bhalf(wl[210]), .i_cbase(wl[211 +: 24]), .i_cso(wl[235 +: 24]),
        .i_csi(wl[259 +: 24]), .i_cpair(wl[283]), .i_dbase(wl[284 +: 24]), .i_dso(wl[308 +: 24]),
        .i_dsi(wl[332 +: 24]), .i_arnd(wl[356]), .i_arelu(wl[357]), .i_amin(wl[358]), .i_cclip(wl[359]),
        .i_m1(wl[360 +: 3]), .i_m2(wl[363 +: 2]), .i_qm(wl[365 +: 3]), .i_ad(wl[368 +: 3]), .i_sfu(wl[371 +: 3]),
        .i_e1(wl[374 +: 3]), .i_e2(wl[377 +: 2]), .i_rnd(wl[379]), .i_dst(wl[380 +: 2]), .i_obase(wl[382 +: 24]),
        .i_oso(wl[406 +: 24]), .i_osi(wl[430 +: 24]), .i_orow(wl[454 +: 24]), .i_red(wl[478 +: 2]),
        .i_redsq(wl[480]), .i_redwhole(wl[481]), .i_redtree(wl[482]), .i_redrnd(wl[483]), .i_rbase(wl[484 +: 24]),
        .i_rso(wl[508 +: 24]), .i_imm1(wl[532 +: 32]), .i_imm2(wl[564 +: 32]), .i_imm3(wl[596 +: 32]),
        .i_ch_src(wl[628 +: 2]), .i_ch_seq(wl[630 +: 8]), .i_ch_lead(wl[638 +: 16]), .i_ch_mul(wl[654 +: 16]),
        .x_seq(x_seq), .x_dseq(x_dseq), .x_cnt(x_cnt), .cr_seq(cr_seq), .cr_dseq(cr_dseq), .cr_rseq(cr_rseq),
        .cr_cnt(cr_cnt), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_addr(rd_addr), .rd_re(rd_re),
        .rd_src(rd_src), .rd_q(rd_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .kv_we(kv_we),
        .kv_waddr(kv_waddr), .kv_wdata(kv_wdata), .res_we(res_we), .res_addr(res_addr), .res_data(res_data),
        .fault(vfault), .order_fault(ofault), .emitted(emitted), .retire_o(ro), .dbg_emit(de), .dbg_eseq(es),
        .dbg_ret(dr), .dbg_rseq(rsq), .dbg_res(ds), .dbg_sseq(ss));

    ot_hgi_sv_lmem #(.N(N), .LWB(LWB), .AW(AW)) u_mem (
        .clk(clk), .rst_n(rst_n), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_re(rd_re), .rd_addr(rd_addr),
        .rd_q(rd_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .res_we(res_we), .res_addr(res_addr),
        .res_data(res_data), .wep(wep), .lsw_v(lsw_v), .lsw_sec(lsw_sec), .lsw_d(lsw_d), .lsw_scrub(lsw_scrub),
        .ldr_v(ldr_v), .ldr_sec(ldr_sec), .ldr_rv(ldr_rv), .ldr_d(ldr_d), .ldr_em(ldr_em), .rf_clr(rf_clr),
        .rf_rv(rf_rv), .rf_rsec(rf_rsec), .rf_rrv(rf_rrv), .rf_rd(rf_rd), .rf_rm(rf_rm), .bank_err(lm_bank_err));
endmodule
/* verilator lint_on UNUSEDPARAM */
/* verilator lint_on UNUSEDSIGNAL */
`default_nettype wire

// Legacy source name; the die contract and physical kit publish ot_hgi_sv_head.
module ot_hgi_sv_ctl #(
    parameter integer N = 16, M = 8, LV = 6,
    parameter integer LWB = 18,
    parameter integer PAYLOAD_RESET = 1,
    parameter integer GLU = 0,
    parameter integer SLB = 16,
    parameter integer LQ = 8,              // ONE constant = ot_hgi_vm_unit LQ (VM lane queue depth, power of two) = the credits a lane holds
    parameter integer EP0 = 0,             // frame epoch after a scrub (bench: 14 makes the chain's in-place sink wrap 15 -> 1)
    parameter integer MUT_V = 0,          // 3 in-place gate off, 4 forward reader takes no pin, 6 scalar bypass slot ^ 1, 7 tail frame keeps its old write epoch, 8 no EXT stream credit (the vec runs ahead of the stage)
    parameter integer NSJ = 6
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          rec_v,
    output wire          rec_rdy,
    input  wire [127:0]  rec_hdr,
    input  wire [255:0]  rec_sut,
    input  wire [255:0]  rec_a, rec_b, rec_c, rec_d, rec_o, rec_r, rec_i,
    input  wire [20:0]   rec_n_a,
    output wire           rec_done,
    output wire           rec_fault,
    output wire           halted,
    output wire  [337:0]  vmq,
    input  wire [273:0]  vmr,
    input  wire          s0_v,
    input  wire [19:0]   s0_idx,
    input  wire [31:0]   s0_data,
    output wire [522:0]  am_stream,
    input  wire          am_rdy,
    // the vec
    output wire           go,
    input  wire          ready,
    input  wire          idle,
    input  wire          vfault,
    output wire [669:0]  wl,
    output wire  [7:0]    x_seq,
    output wire  [7:0]    x_dseq,
    output wire  [15:0]   x_cnt,
    input  wire [7:0]    cr_seq_i,
    input  wire [7:0]    cr_dseq,
    input  wire [15:0]   cr_cnt_i,
    // the local memory
    output wire  [15:0]   wep,
    output wire  [3:0]    rf_clr,
    output wire           rf_rv,
    output wire  [4:0]    rf_rsec,
    input  wire          rf_rrv,
    input  wire [255:0]  rf_rd,
    input  wire [7:0]    rf_rm,
    input  wire          lm_err,
    // shared lane groups
    output wire           rg_req,
    input  wire          rg_gnt,
    output wire           wg_req,
    input  wire          wg_gnt,
    // the leaves: two registered copies of the cmd word (one a side: 4 near leaves each, which relay it to their far
    // partner) and the 8 near leaves' status words (each already folded with its far partner's)
    output wire [2*(83+NSJ)-1:0] lf_cmd,
    input  wire [8*(NSJ+33)-1:0] lf_status,
    output wire  [15:0]   walks                // non-dense O drains (frame walks) since reset
);
    ot_hgi_sv_head #(.N(N), .M(M), .LV(LV), .LWB(LWB), .PAYLOAD_RESET(PAYLOAD_RESET), .GLU(GLU), .SLB(SLB), .LQ(LQ), .EP0(EP0), .MUT_V(MUT_V), .NSJ(NSJ)) u_impl (.*);
endmodule

`timescale 1ns/1ps
// Structural extraction: wires-only parent, sequencer own root, one entry per immutable CLOSED tile.
// Broadcast/return stations and legal die-pin placement remain required before parent qualification.
module ot_hgi_coll_tkm_cluster #(
    parameter integer KMAX = 64,      // the die instance sets 2,048 (ot_hgi_coll_ep TKM_KMAX); a small default keeps read-time elaboration cheap
    parameter integer DEL  = 4,
    parameter integer FW   = 512,
    parameter integer PWT  = FW + 33,
    parameter integer CAP  = 64,
    parameter integer MUT  = 0
) (
    input wire [((KMAX+63)/64)-1:0] tile_clk,
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 start,          // one edge: configuration below valid
    input  wire [11:0]          cfg_n,          // this rank's n (informational: validity is the sender's pad marker)
    input  wire [12:0]          cfg_k,          // k: O.n must equal min(k, elements received)
    input  wire [7:0]           cfg_g,          // group size
    input  wire [7:0]           cfg_gbase,      // the group's first rank (flit src - gbase = q)
    input  wire [15:0]          cfg_pf,         // ceil(n / 8)
    input  wire [12:0]          cfg_nout,       // O.n = min(k, the group's elements), 1 .. KMAX
    input  wire [39:0]          cfg_obase,      // O: VM word address (16-word aligned)
    input  wire [39:0]          cfg_rbase,      // R: VM word address (16-word aligned)
    input  wire                 cfg_has_r,
    input  wire [DEL-1:0]       del_reserve,
    output wire [DEL-1:0]       del_permit,
    input  wire [DEL-1:0]       del_valid,
    input  wire [DEL*PWT-1:0]   del_flit,
    output wire                  w_v,
    output wire  [39:0]          w_addr,
    output wire  [15:0]          w_mask,
    output wire  [FW-1:0]        w_data,
    input  wire                 w_rdy,
    output wire                 busy,
    output wire                  done,           // one edge: every output line accepted
    output wire                  fault,
    output wire  [31:0]          stat_cycles,    // start -> done
    output wire  [31:0]          stat_ins,       // blocks inserted
    output wire  [31:0]          stat_surv       // survivors taken
);
    localparam integer NT = (KMAX+63)/64;
    wire [339:0] chain_entry, chain_up;
    wire chain_valid;
    wire [NT-1:0] chain_clr, chain_conv, chain_busy;
    wire [6*NT-1:0] chain_tt;
    wire [7*NT-1:0] chain_tl;
    wire [84*NT-1:0] chain_tau;
    wire [339:0] down [0:NT];
    wire [339:0] up [0:NT];
    wire [NT:0] down_v;
    assign down[0] = chain_entry;
    assign down_v[0] = chain_valid;
    assign up[NT] = '0;
    assign chain_up = up[0];
`ifdef OT_TKM_SEQ_HARD
    ot_hgi_coll_tkm_seq u_seq (
`else
    ot_hgi_coll_tkm_seq #(.KMAX(KMAX), .DEL(DEL), .FW(FW), .PWT(PWT), .CAP(CAP), .MUT(MUT)) u_seq (
`endif
        .chain_entry(chain_entry), .chain_valid(chain_valid), .chain_up(chain_up),
        .chain_clr(chain_clr), .chain_conv(chain_conv), .chain_tt(chain_tt), .chain_tl(chain_tl),
        .chain_tau(chain_tau), .chain_busy(chain_busy),
        .clk(clk),
        .rst_n(rst_n),
        .start(start),
        .cfg_n(cfg_n),
        .cfg_k(cfg_k),
        .cfg_g(cfg_g),
        .cfg_gbase(cfg_gbase),
        .cfg_pf(cfg_pf),
        .cfg_nout(cfg_nout),
        .cfg_obase(cfg_obase),
        .cfg_rbase(cfg_rbase),
        .cfg_has_r(cfg_has_r),
        .del_reserve(del_reserve),
        .del_permit(del_permit),
        .del_valid(del_valid),
        .del_flit(del_flit),
        .w_v(w_v),
        .w_addr(w_addr),
        .w_mask(w_mask),
        .w_data(w_data),
        .w_rdy(w_rdy),
        .busy(busy),
        .done(done),
        .fault(fault),
        .stat_cycles(stat_cycles),
        .stat_ins(stat_ins),
        .stat_surv(stat_surv));
    for (genvar t=0; t<NT; t=t+1) begin : g_t
`ifdef OT_TKM_TILE_HARD
        ot_hgi_coll_tkm_tile u_t (
`else
        ot_hgi_coll_tkm_tile #(.PT((KMAX<64)?KMAX:64)) u_t (
`endif
          .clk(tile_clk[t]), .tid(6'(t)), .clr(chain_clr[t]), .conv(chain_conv[t]),
          .tau_t(chain_tt[6*t +: 6]), .tau_l(chain_tl[7*t +: 7]),
          .ins_v(down_v[t]), .ins_b(down[t]), .ovf_v(down_v[t+1]), .ovf_b(down[t+1]),
          .up_in(up[t+1]), .up_out(up[t]), .tau_o(chain_tau[84*t +: 84]), .busy(chain_busy[t]));
    end
endmodule

module ot_hgi_coll_tkm_seq #(
    parameter integer KMAX = 64,      // the die instance sets 2,048 (ot_hgi_coll_ep TKM_KMAX); a small default keeps read-time elaboration cheap
    parameter integer DEL  = 4,
    parameter integer FW   = 512,
    parameter integer PWT  = FW + 33,
    parameter integer CAP  = 64,
    parameter integer MUT  = 0
) (
    output wire [339:0] chain_entry,
    output wire chain_valid,
    input wire [339:0] chain_up,
    output wire [((KMAX+63)/64)-1:0] chain_clr, chain_conv,
    output wire [6*((KMAX+63)/64)-1:0] chain_tt,
    output wire [7*((KMAX+63)/64)-1:0] chain_tl,
    input wire [84*((KMAX+63)/64)-1:0] chain_tau,
    input wire [((KMAX+63)/64)-1:0] chain_busy,
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 start,          // one edge: configuration below valid
    input  wire [11:0]          cfg_n,          // this rank's n (informational: validity is the sender's pad marker)
    input  wire [12:0]          cfg_k,          // k: O.n must equal min(k, elements received)
    input  wire [7:0]           cfg_g,          // group size
    input  wire [7:0]           cfg_gbase,      // the group's first rank (flit src - gbase = q)
    input  wire [15:0]          cfg_pf,         // ceil(n / 8)
    input  wire [12:0]          cfg_nout,       // O.n = min(k, the group's elements), 1 .. KMAX
    input  wire [39:0]          cfg_obase,      // O: VM word address (16-word aligned)
    input  wire [39:0]          cfg_rbase,      // R: VM word address (16-word aligned)
    input  wire                 cfg_has_r,
    input  wire [DEL-1:0]       del_reserve,
    output wire [DEL-1:0]       del_permit,
    input  wire [DEL-1:0]       del_valid,
    input  wire [DEL*PWT-1:0]   del_flit,
    output reg                  w_v,
    output reg  [39:0]          w_addr,
    output reg  [15:0]          w_mask,
    output reg  [FW-1:0]        w_data,
    input  wire                 w_rdy,
    output wire                 busy,
    output reg                  done,           // one edge: every output line accepted
    output reg                  fault,
    output reg  [31:0]          stat_cycles,    // start -> done
    output reg  [31:0]          stat_ins,       // blocks inserted
    output reg  [31:0]          stat_surv       // survivors taken
);
    localparam integer W  = 4;
    localparam integer C  = KMAX / W;
    localparam integer EW = 85;               // {region, valid, okey, ~id, ~q, ~j, nz}
    localparam integer KW = 83;
    localparam integer VB = 83;               // the valid bit (bit EW-1 is the region tag)
    localparam integer CB = $clog2(C + 1);
    localparam integer QW = 8 * EW;            // FIFO word: 8 elements
    // ---------------------------------------------------------------- element helpers
    function automatic [31:0] okey(input [31:0] x);
        reg [31:0] c;
        begin
            c = (x == 32'h8000_0000) ? 32'h0 : x;
            okey = c[31] ? ~c : (c | 32'h8000_0000);
        end
    endfunction
    function automatic [31:0] unkey(input [31:0] k, input nz);
        unkey = nz ? 32'h8000_0000 : (k[31] ? (k & 32'h7FFF_FFFF) : ~k);
    endfunction
    function automatic [KW-1:0] vkey(input [EW-1:0] e);
        vkey = e[VB:1];
    endfunction
    function automatic [KW-1:0] ikey(input [EW-1:0] e);
        ikey = {e[83], e[50:19], e[82:51], e[18:1]};
    endfunction
    // insertion key (84 bits): {valid, ~region, body}: region 0 = the value order (selection phase), region 1 = the id
    // order (re-insertion phase, always below region 0); an invalid element is 0 (the lowest)
    function automatic [KW:0] key2(input [EW-1:0] e);
        reg [KW-1:0] b_;
        begin
            b_ = e[84] ? ikey(e) : vkey(e);
            key2 = e[83] ? {1'b1, ~e[84], b_[KW-2:0]} : {(KW+1){1'b0}};
        end
    endfunction
    // KEY FORM (r3, the chain's storage format): T = {key2(e), nz} -- T[EW-1:1] is the 84-bit insertion key, so the
    // tiles compare stored bits with no key mux; tinv restores the element (an invalid element is 0 in both forms)
    function automatic [EW-1:0] tform(input [EW-1:0] e);
        tform = e[83] ? {key2(e), e[0]} : {EW{1'b0}};
    endfunction
    function automatic [EW-1:0] tinv(input [EW-1:0] t);
        reg [81:0] b_;
        begin
            b_ = t[82:1];
            tinv = !t[84] ? {EW{1'b0}} : (!t[83] ? {1'b1, 1'b1, b_[49:18], b_[81:50], b_[17:0], t[0]} : {1'b0, 1'b1, b_, t[0]});
        end
    endfunction
    // ---------------------------------------------------------------- configuration
    reg [11:0] n_q; reg [7:0] g_q, gb_q; reg [15:0] pf_q; reg [12:0] nout_q; reg [39:0] ob_q, rb_q; reg hr_q;
    reg [23:0] tot_q;                          // G pf flits expected
    reg [CB-1:0] cact_q;                       // ceil(nout / 4) active cells
    reg [CB-1:0] tc_q; reg [1:0] ts_q;         // tau position (nout - 1) -> cell, slot
    // ---------------------------------------------------------------- phases
    localparam [3:0] P_IDLE = 4'd0, P_INS = 4'd1, P_DRAIN = 4'd2, P_CONV1 = 4'd3, P_CLR2 = 4'd4, P_INS2 = 4'd5,
                     P_DRAIN2 = 4'd6, P_OUT = 4'd7, P_FLUSH = 4'd8, P_CLR0 = 4'd9;
    reg [3:0] ph;
    assign busy = (ph != P_IDLE);
    // ---------------------------------------------------------------- delivery credits + decode + FIFO
    reg [7:0] cr [0:DEL-1];
    reg [DEL-1:0] res_q;                       // del_reserve pin flop (debited one edge later)
    for (genvar l = 0; l < DEL; l = l + 1) begin : g_perm
        assign del_permit[l] = (cr[l] > 8'(res_q[l])) && (ph == P_INS);   // the registered reserve not yet debited     // flops only (no start -> permit path)
    end
    reg [DEL-1:0] d1_v, d2_v;
    // reset standard (ot_rst_relay): the port drives only the relay; FIFO l from region l, the control from region DEL
    wire [DEL:0] rr;
    ot_rst_relay #(.REGIONS(DEL + 1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    wire rn = rr[DEL];
    reg [DEL-1:0] rfault;  // credit-underflow term from the del_reserve pin, registered
    // el1011-hbm-idx 10-11: pin-flop stage d0 on the delivery lanes and on start / cfg (rtl_boundary: the (src - gbase) x pf
    // decode was 85 gate levels from del_flit; start cleared the 2,048-entry array straight from the pin)
    reg [DEL-1:0] d0_v; reg [PWT-1:0] d0_f [0:DEL-1];
    reg start_p; reg [11:0] cfg_n_p; reg [12:0] cfg_k_p, cfg_nout_p; reg [7:0] cfg_g_p, cfg_gbase_p; reg [15:0] cfg_pf_p;
    reg [39:0] cfg_obase_p, cfg_rbase_p; reg cfg_has_r_p;
    always @(posedge clk) begin
        for (int l = 0; l < DEL; l = l + 1) d0_f[l] <= del_flit[l*PWT +: PWT];
        cfg_n_p <= cfg_n; cfg_k_p <= cfg_k; cfg_nout_p <= cfg_nout; cfg_g_p <= cfg_g; cfg_gbase_p <= cfg_gbase; cfg_pf_p <= cfg_pf;
        cfg_obase_p <= cfg_obase; cfg_rbase_p <= cfg_rbase; cfg_has_r_p <= cfg_has_r;
    end
    reg [7:0] d1_q [0:DEL-1]; reg [15:0] d1_gi [0:DEL-1]; reg [FW-1:0] d1_d [0:DEL-1];
    reg [23:0] d1_qpf [0:DEL-1];
    reg [QW-1:0] d2_e [0:DEL-1];
    wire [DEL-1:0] fe, fo; wire [QW-1:0] fd [0:DEL-1]; wire [6:0] fcnt [0:DEL-1];
    reg [DEL-1:0] fpop, fpop_q;
    for (genvar l = 0; l < DEL; l = l + 1) begin : g_fifo
        (* keep_hierarchy *) ot_hcoll_sfifo #(.W(QW), .AW(6)) u_q (.clk(clk), .rst_n(rr[l]), .push(d2_v[l]),
            .din(d2_e[l]), .pop(fpop[l]), .empty(fe[l]), .dout(fd[l]), .ovf(fo[l]), .count(fcnt[l]));
    end
    reg [23:0] rcv;                            // flits received (decoded)
    reg [18:0] nel;                            // valid (non-pad) elements received
    reg [12:0] k_q;
    reg [7:0]  occ [0:DEL-1];                  // FIFO occupancy (pushed - popped; the sfifo count misses its pipeline)
    // ---------------------------------------------------------------- tau
    reg [KW-1:0] tau;
    // ---------------------------------------------------------------- staging (3 a lane) + select
    reg [8*EW-1:0] st_e [0:DEL-1][0:2];          // packed 8-element words (yosys: no unpacked sub-array copies)
    reg [7:0]    st_m [0:DEL-1][0:2];
    reg [1:0]    st_n [0:DEL-1];
    reg [DEL-1:0] ld_v;
    reg [8*EW-1:0] ld_e [0:DEL-1];
    reg [7:0]    ld_m [0:DEL-1];
    reg [7:0]    dn [0:DEL-1];                 // survivors of the head already taken
    // entry pipeline
    reg          e1_v; reg [EW-1:0] e1 [0:3];
    reg          e2_v; reg [EW-1:0] e2 [0:3]; reg [5:0] e2_ge;   // pairwise compares for the rank sort
    // ---------------------------------------------------------------- the chain of hardened tiles (el1011-hbm-idx rebuild)
    // textbook audit (owner 10-11): the flat 2,048 x 85-b array (one clock root over 1,800 um, one entry bus to every
    // cell, 8,192 key compares in one edge) is now NT tiles of PT positions (ot_hgi_coll_tkm_tile, ~12k flops, own clock
    // tree): a tile keeps its best PT of what reached it and passes its bottom 4 down on a registered seam; an upward
    // conveyor (one presented-top register a seam) empties the chain from the top.  Two passes: value key, top nout ->
    // an SRAM cell buffer, chain cleared, id key, conveyed out as O / R lines.  Control reaches every tile at equal depth.
    localparam integer PT = (KMAX < 64) ? KMAX : 64;
    localparam integer NT = KMAX / PT;
    localparam integer NG2 = (NT + 3) / 4;
    localparam integer TW = 6, LW = 7;
    localparam integer BD = KMAX / 4;
    localparam integer BA = (BD <= 2) ? 1 : $clog2(BD);
    reg  [TW-1:0] tau_t; reg [LW-1:0] tau_l;
    reg  ctl_conv, ctl_clr;
    reg  [NG2-1:0] g_conv, g_clr; reg [TW-1:0] g_tt [0:NG2-1]; reg [LW-1:0] g_tl [0:NG2-1];
    reg  dconv1, dconv2, dconv3;
    reg  eb_v; reg [4*EW-1:0] eb;
    wire [4*EW-1:0] t_ovf [0:NT]; wire t_ovf_v [0:NT]; wire [4*EW-1:0] t_up [0:NT];
    wire [KW:0] t_tau [0:NT-1]; wire t_busy [0:NT-1];
    assign t_ovf[0] = eb; assign t_ovf_v[0] = eb_v; assign t_up[NT] = '0;
    assign chain_entry = eb;
    assign chain_valid = eb_v;
    assign t_up[0] = chain_up;
    for (genvar t = 0; t < NT; t = t + 1) begin : g_face
        assign chain_clr[t] = g_clr[t / 4];
        assign chain_conv[t] = g_conv[t / 4];
        assign chain_tt[6*t +: 6] = g_tt[t / 4];
        assign chain_tl[7*t +: 7] = g_tl[t / 4];
        assign t_tau[t] = chain_tau[84*t +: 84];
        assign t_busy[t] = chain_busy[t];
    end
    reg [NG2-1:0] gb_busy; reg [KW:0] g_tau [0:NG2-1]; reg any_busy; reg [KW:0] tau_b;
    always @(posedge clk) begin : trees
        reg [KW:0] o_; reg b_;
        for (integer g = 0; g < NG2; g = g + 1) begin
            g_conv[g] <= ctl_conv; g_clr[g] <= ctl_clr; g_tt[g] <= tau_t; g_tl[g] <= tau_l;
            o_ = '0; b_ = 1'b0;
            for (integer x = 0; x < 4; x = x + 1) if (g * 4 + x < NT) begin o_ = o_ | t_tau[g * 4 + x]; b_ = b_ | t_busy[g * 4 + x]; end
            g_tau[g] <= o_; gb_busy[g] <= b_;
        end
        o_ = '0; for (integer g = 0; g < NG2; g = g + 1) o_ = o_ | g_tau[g];
        tau_b <= o_; any_busy <= |gb_busy;
        dconv1 <= ctl_conv; dconv2 <= dconv1; dconv3 <= dconv2;   // r3: the tiles shift 3 edges after ctl_conv: capture t_up[0] then
    end
    // the SRAM cell buffer (pass 1 -> pass 2): BD cells of 4 elements, registered write port, captured read
    reg  bw_v; reg [BA-1:0] bw_a; reg [4*EW-1:0] bw_d;
    reg  br_v; reg [BA-1:0] br_a; reg br_q, rd2_v; reg [4*EW-1:0] rd2;
    wire [511:0] b_q;
    wire [511:0] bw_w = 512'(bw_d);
    for (genvar m = 0; m < 2; m = m + 1) begin : g_bm
        ot_sram_1r1w_1024x256_m2_r2c2 u_b (.clk(clk), .r_ce_in(br_v), .r_addr_in(10'(br_a)), .rd_out(b_q[256*m +: 256]),
            .w_ce_in(bw_v), .w_addr_in(10'(bw_a)), .wd_in(bw_w[256*m +: 256]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b0), .rr_addr(18'd0), .cr_en(2'b0), .cr_sel(16'd0));
    end
    reg [BA:0] cnv, cap, rdn; reg [12:0] cneed; reg [3:0] qcnt; reg [3:0] wcnt;
    reg [EW-1:0] lb [0:15]; reg [9:0] lp;               // output line buffer, lines pushed
    integer c, s, a, b, l, i;
    // ---------------------------------------------------------------- output packer
    reg [12:0] outn;                           // elements shifted out
    reg [12:0] wrn;                            // elements written (O lines)
    reg [8:0]  line;                           // output line index
    // ---------------------------------------------------------------- main sequential
    // output step: one 16-element line an edge (the array shifts up 4 cells); O line (+ R line) into a 4-line queue that
    // the write port drains one line an edge; a step needs room for its lines
    reg [FW-1:0] lq_d [0:7]; reg [39:0] lq_a [0:7]; reg [15:0] lq_m [0:7]; reg [3:0] lq_n; reg [2:0] lq_h, lq_t;
    wire lq_pop = (lq_n != 4'd0) && (!w_v || w_rdy);
    // P_OUT conveyor: a cell (4 elements) an edge while the 8-line queue has room for every line issued and not yet
    // pushed (registered counts only; the cells reach the packer 2 edges after the decision)
    wire [10:0] lines_iss = 11'((cnv + 1 + 3) >> 2);
    wire [11:0] lq_need = 12'(lq_n) + 12'(lines_iss - 11'(lp)) * (hr_q ? 12'd2 : 12'd1);
    wire pgo = (ph == P_OUT) && (13'(cnv) < cneed) && (lq_need <= 12'd8);
    // select (combinational over the registered staging heads)
    reg [EW-1:0] sel_e [0:3]; reg [2:0] sel_n; reg [7:0] sel_take [0:DEL-1]; reg [DEL-1:0] sel_pop;
    always @* begin : selc
        integer r_, idx;
        reg [7:0] hm;
        r_ = 0;
        for (s = 0; s < 4; s = s + 1) sel_e[s] = {EW{1'b0}};
        for (l = 0; l < DEL; l = l + 1) begin
            sel_take[l] = 8'd0;
            hm = (st_n[l] != 2'd0) ? (st_m[l][0] & ~dn[l]) : 8'd0;
            for (i = 0; i < 8; i = i + 1) if (hm[i]) begin
                if (r_ < 4) begin if (!(MUT == 2 && r_ == 3)) sel_e[r_] = st_e[l][0][EW*i +: EW]; sel_take[l][i] = 1'b1; end
                r_ = r_ + 1;
            end
            sel_pop[l] = (st_n[l] != 2'd0) && ((hm & ~sel_take[l]) == 8'd0);
        end
        sel_n = (r_ > 4) ? 3'd4 : 3'(r_);
    end
    wire ins_live = (ph == P_INS);
    always @(posedge clk or negedge rn) begin
        if (!rn) begin
            ph <= P_IDLE; fault <= 1'b0; done <= 1'b0; w_v <= 1'b0; w_addr <= 40'd0; w_mask <= 16'd0; w_data <= '0;
            stat_cycles <= 32'd0; stat_ins <= 32'd0; stat_surv <= 32'd0;
            n_q <= 12'd1; k_q <= 13'd1; nel <= 19'd0; g_q <= 8'd1; gb_q <= 8'd0; pf_q <= 16'd1; nout_q <= 13'd1; ob_q <= 40'd0; rb_q <= 40'd0; hr_q <= 1'b0;
            tot_q <= 24'd0; cact_q <= '0; tc_q <= '0; ts_q <= 2'd0; rcv <= 24'd0; tau <= '0;
            rfault <= '0; res_q <= '0; d0_v <= '0; start_p <= 1'b0; d1_v <= '0; d2_v <= '0; fpop_q <= '0; ld_v <= '0; e1_v <= 1'b0; e2_v <= 1'b0;
            outn <= 13'd0; wrn <= 13'd0; line <= 9'd0; lq_n <= 4'd0; lq_h <= 3'd0; lq_t <= 3'd0;
            ctl_conv <= 1'b0; ctl_clr <= 1'b0; eb_v <= 1'b0; bw_v <= 1'b0; br_v <= 1'b0; br_q <= 1'b0; rd2_v <= 1'b0;
            cnv <= '0; cap <= '0; rdn <= '0; cneed <= 13'd0; qcnt <= 4'd0; wcnt <= 4'd0; lp <= 10'd0; tau_t <= '0; tau_l <= '0;
            for (l = 0; l < DEL; l = l + 1) begin cr[l] <= 8'(CAP); st_n[l] <= 2'd0; dn[l] <= 8'd0; occ[l] <= 8'd0; end
        end else begin
            done <= 1'b0;
            if (busy) stat_cycles <= stat_cycles + 32'd1;
            fpop_q <= fpop;
            start_p <= start; d0_v <= del_valid; res_q <= del_reserve;
            tot_q <= 24'(g_q) * 24'(pf_q);           // from the registered configuration (no input -> logic paths)
            cact_q <= CB'((nout_q + 13'd3) >> 2);
            tc_q <= CB'((nout_q - 13'd1) >> 2); ts_q <= 2'(nout_q - 13'd1);
            tau_t <= TW'((nout_q - 13'd1) / PT); tau_l <= LW'((nout_q - 13'd1) % PT);
            cneed <= (nout_q + 13'd3) >> 2;
            // ---- credits: reserve at dispatch, return one edge after a FIFO pop
            for (l = 0; l < DEL; l = l + 1) begin
                cr[l] <= cr[l] - ((MUT == 3) ? 8'd0 : 8'(res_q[l])) + 8'(fpop_q[l]);
                rfault[l] <= res_q[l] && cr[l] == 8'd0;
                if (rfault[l]) fault <= 1'b1;
                if (fo[l]) fault <= 1'b1;
                occ[l] <= occ[l] + 8'(d2_v[l]) - 8'(fpop[l]);
            end
            // ---- decode
            for (l = 0; l < DEL; l = l + 1) begin
                d1_v[l] <= d0_v[l];
                d1_q[l] <= d0_f[l][FW + 16 +: 8] - gb_q;
                d1_gi[l] <= d0_f[l][FW +: 16];
                d1_d[l] <= d0_f[l][FW-1:0];
                d1_qpf[l] <= 24'(8'(d0_f[l][FW + 16 +: 8] - gb_q)) * 24'(pf_q);
                if (d0_v[l] && !d0_f[l][PWT - 1]) fault <= 1'b1;
                d2_v[l] <= d1_v[l];
                begin : dec
                    reg [23:0] f_; reg [31:0] vv, id_; reg [23:0] j_; reg [EW-1:0] e_;
                    f_ = 24'(d1_gi[l]) - d1_qpf[l];
                    if (d1_v[l] && (d1_q[l] >= g_q || f_ >= 24'(pf_q))) fault <= 1'b1;
                    for (s = 0; s < 8; s = s + 1) begin
                        vv = d1_d[l][32*s +: 32]; id_ = d1_d[l][32*(8+s) +: 32];
                        j_ = {f_[20:0], 3'(s)};
                        e_ = {1'b1, okey(vv), (MUT == 1) ? id_ : ~id_, ~d1_q[l][6:0], ~j_[10:0], (vv == 32'h8000_0000)};
                        if (vv == 32'hFFFF_FFFF) e_ = {EW{1'b0}};                       // the sender's pad slot
                        else if (d1_v[l] && vv[30:23] == 8'hFF && vv[22:0] != 23'd0) fault <= 1'b1;
                        d2_e[l][EW*s +: EW] <= e_;
                    end
                end
            end
            if (ph == P_INS) begin : cnt
                reg [18:0] a_;
                a_ = nel;
                for (l = 0; l < DEL; l = l + 1) if (d2_v[l]) for (s = 0; s < 8; s = s + 1) a_ = a_ + 19'(d2_e[l][EW*s + VB]);
                nel <= a_;
            end
            if (ph == P_INS) rcv <= rcv + 24'(d2_v[0]) + 24'(d2_v[1]) + 24'(d2_v[2]) + 24'(d2_v[3]);
            if ((rcv + 24'(d2_v[0]) + 24'(d2_v[1]) + 24'(d2_v[2]) + 24'(d2_v[3])) > tot_q && ph == P_INS) fault <= 1'b1;
            // ---- tau (2 edges behind the array)
            tau <= vkey(tinv({tau_b, 1'b0}));
            // ---- staging: land (mask against tau), then slots; select consumes slot 0
            for (l = 0; l < DEL; l = l + 1) begin
                ld_v[l] <= fpop[l];
                for (s = 0; s < 8; s = s + 1) begin
                    ld_e[l][EW*s +: EW] <= fd[l][EW*s +: EW];
                    ld_m[l][s] <= fd[l][EW*s + VB] && (vkey(fd[l][EW*s +: EW]) > tau);
                end
                begin : stg
                    reg [1:0] n_;
                    n_ = st_n[l];
                    if (sel_pop[l] && ins_live) begin
                        st_e[l][0] <= st_e[l][1]; st_m[l][0] <= st_m[l][1];
                        st_e[l][1] <= st_e[l][2]; st_m[l][1] <= st_m[l][2];
                        n_ = n_ - 2'd1; dn[l] <= 8'd0;
                    end else if (ins_live) dn[l] <= dn[l] | sel_take[l];
                    if (ld_v[l]) begin
                        // the new entry lands at index n_ (after this edge's shift)
                        if (n_ == 2'd0) begin st_e[l][0] <= ld_e[l]; st_m[l][0] <= ld_m[l]; end
                        else if (n_ == 2'd1) begin st_e[l][1] <= ld_e[l]; st_m[l][1] <= ld_m[l]; end
                        else begin st_e[l][2] <= ld_e[l]; st_m[l][2] <= ld_m[l]; end
                        n_ = n_ + 2'd1;
                    end
                    st_n[l] <= n_;
                end
            end
            // ---- entry: select -> e1 -> (compares) e2 -> rank-sorted block -> broadcast insertion
            // (re-insertion: the top cell, tagged region 1 -- the id order)
            e1_v <= (ins_live && (sel_n != 3'd0)) || rd2_v;
            for (s = 0; s < 4; s = s + 1) e1[s] <= rd2_v ? rd2[EW*s +: EW] : sel_e[s];
            if (ins_live && sel_n != 3'd0) stat_surv <= stat_surv + 32'(sel_n);
            e2_v <= e1_v;
            for (s = 0; s < 4; s = s + 1) e2[s] <= e1[s];
            e2_ge[0] <= key2(e1[0]) >= key2(e1[1]); e2_ge[1] <= key2(e1[0]) >= key2(e1[2]); e2_ge[2] <= key2(e1[0]) >= key2(e1[3]);
            e2_ge[3] <= key2(e1[1]) >= key2(e1[2]); e2_ge[4] <= key2(e1[1]) >= key2(e1[3]); e2_ge[5] <= key2(e1[2]) >= key2(e1[3]);
            // ---- the array (X / bk: reset-free data flops in their own block below)
            begin : entry
                reg [1:0] r0, r1, r2, r3;
                r0 = 2'(!e2_ge[0]) + 2'(!e2_ge[1]) + 2'(!e2_ge[2]);
                r1 = 2'(e2_ge[0]) + 2'(!e2_ge[3]) + 2'(!e2_ge[4]);
                r2 = 2'(e2_ge[1]) + 2'(e2_ge[3]) + 2'(!e2_ge[5]);
                r3 = 2'(e2_ge[2]) + 2'(e2_ge[4]) + 2'(e2_ge[5]);
                eb_v <= e2_v;
                for (s = 0; s < 4; s = s + 1)
                    eb[EW*s +: EW] <= tform(((r0 == 2'(s)) ? e2[0] : {EW{1'b0}}) | ((r1 == 2'(s)) ? e2[1] : {EW{1'b0}}) |
                                            ((r2 == 2'(s)) ? e2[2] : {EW{1'b0}}) | ((r3 == 2'(s)) ? e2[3] : {EW{1'b0}}));
                if (e2_v && (ph == P_INS || ph == P_DRAIN)) stat_ins <= stat_ins + 32'd1;
            end
            // ---- the chain controls (one-edge pulses / levels; the tiles act 2 edges later)
            ctl_clr <= 1'b0; bw_v <= 1'b0;
            ctl_conv <= ((ph == P_CONV1) && (13'(cnv) < cneed)) || pgo;
            if (((ph == P_CONV1) && (13'(cnv) < cneed)) || pgo) cnv <= cnv + 1'b1;
            qcnt <= (!e1_v && !e2_v && !eb_v && !any_busy && !br_v && !br_q && !rd2_v) ? ((qcnt == 4'd15) ? qcnt : qcnt + 4'd1) : 4'd0;
            // pass-1 capture: the top cell leaving the chain -> the buffer, id order tag (region 1), positions >= nout dropped
            if (ph == P_CONV1 && dconv3) begin
                for (s = 0; s < 4; s = s + 1) begin : c1
                    reg [EW-1:0] e_;
                    e_ = tinv(t_up[0][EW*s +: EW]);
                    bw_d[EW*s +: EW] <= (13'({cap, 2'(s)}) < nout_q) ? (e_ | {e_[83], {(EW-1){1'b0}}}) : {EW{1'b0}};
                end
                bw_v <= 1'b1; bw_a <= BA'(cap); cap <= cap + 1'b1;
            end
            // pass-2 feed: buffer cells read one an edge, captured, then into the entry sorter
            br_v <= (ph == P_INS2) && (13'(rdn) < cneed);
            if ((ph == P_INS2) && (13'(rdn) < cneed)) begin br_a <= BA'(rdn); rdn <= rdn + 1'b1; end
            br_q <= br_v; rd2_v <= br_q; rd2 <= b_q[4*EW-1:0];
            // ---- output (P_OUT): conveyed cells -> a 16-element line every 4 cells -> O line (+ R line) into the queue
            begin : pk
                reg [3:0] n_; reg [2:0] t_; reg [12:0] cnt_; reg [FW-1:0] od_, rd_; reg [15:0] m_; reg [EW-1:0] e_;
                reg [EW-1:0] lx [0:15];
                n_ = lq_n; t_ = lq_t;
                if (lq_pop) begin
                    w_v <= 1'b1; w_addr <= lq_a[lq_h]; w_mask <= lq_m[lq_h]; w_data <= lq_d[lq_h];
                    lq_h <= lq_h + 3'd1; n_ = n_ - 4'd1;
                end else if (w_v && w_rdy) w_v <= 1'b0;
                if (ph == P_OUT && dconv3) begin
                    for (i = 0; i < 16; i = i + 1) lx[i] = lb[i];
                    for (s = 0; s < 4; s = s + 1) begin lx[4 * cap[1:0] + s] = tinv(t_up[0][EW*s +: EW]); lb[4 * cap[1:0] + s] <= tinv(t_up[0][EW*s +: EW]); end
                    cap <= cap + 1'b1;
                    if (cap[1:0] == 2'd3 || 13'(cap) + 13'd1 == cneed) begin
                        cnt_ = ((nout_q - outn) >= 13'd16) ? 13'd16 : (nout_q - outn);
                        m_ = (cnt_ == 13'd16) ? 16'hFFFF : 16'((17'd1 << cnt_[4:0]) - 17'd1);
                        for (i = 0; i < 16; i = i + 1) begin
                            e_ = lx[i];
                            od_[32*i +: 32] = (13'(i) < cnt_) ? ((MUT == 1) ? e_[50:19] : ~e_[50:19]) : 32'd0;
                            rd_[32*i +: 32] = (13'(i) < cnt_) ? unkey(e_[82:51], e_[0]) : 32'd0;
                        end
                        lq_d[t_] <= od_; lq_a[t_] <= ob_q + {27'd0, line, 4'd0}; lq_m[t_] <= m_; t_ = t_ + 3'd1; n_ = n_ + 4'd1;
                        if (hr_q) begin lq_d[t_] <= rd_; lq_a[t_] <= rb_q + {27'd0, line, 4'd0}; lq_m[t_] <= m_; t_ = t_ + 3'd1; n_ = n_ + 4'd1; end
                        line <= line + 9'd1; outn <= outn + cnt_; lp <= lp + 10'd1;
                        for (i = 0; i < 16; i = i + 1) lb[i] <= {EW{1'b0}};
                    end
                end
                lq_n <= n_; lq_t <= t_;
            end
            // ---- phase control
            case (ph)
                P_IDLE: if (start_p) begin
                    n_q <= cfg_n_p; k_q <= cfg_k_p; nel <= 19'd0; g_q <= cfg_g_p; gb_q <= cfg_gbase_p; pf_q <= cfg_pf_p; nout_q <= cfg_nout_p;
                    ob_q <= cfg_obase_p; rb_q <= cfg_rbase_p; hr_q <= cfg_has_r_p;
                    rcv <= 24'd0; tau <= '0;
                    stat_ins <= 32'd0; stat_surv <= 32'd0; stat_cycles <= 32'd0;
                    outn <= 13'd0; wrn <= 13'd0; line <= 9'd0; lp <= 10'd0;
                    ctl_clr <= 1'b1; wcnt <= 4'd0;
                    ph <= P_CLR0;
                end
                // the chain clears 2 edges after ctl_clr; the tau tree settles 3 more
                P_CLR0: begin wcnt <= wcnt + 4'd1; tau <= '0; if (wcnt == 4'd7) ph <= P_INS; end
                P_INS: if (rcv == tot_q && d0_v == '0 && d1_v == '0 && d2_v == '0 && occ[0] == 8'd0 && occ[1] == 8'd0 && occ[2] == 8'd0 && occ[3] == 8'd0 && ld_v == '0 &&
                           st_n[0] == 2'd0 && st_n[1] == 2'd0 && st_n[2] == 2'd0 && st_n[3] == 2'd0)
                    ph <= P_DRAIN;
                P_DRAIN: if (qcnt >= 4'd4) begin
                    // O.n must be min(k, the group's elements): a record whose O.n disagrees faults (E_RANGE)
                    if (19'(nout_q) != ((19'(k_q) < nel) ? 19'(k_q) : nel)) fault <= 1'b1;
                    cnv <= '0; cap <= '0;
                    ph <= (MUT == 4) ? P_OUT : P_CONV1;
                end
                P_CONV1: if (13'(cap) == cneed) begin ctl_clr <= 1'b1; wcnt <= 4'd0; ph <= P_CLR2; end
                P_CLR2: begin wcnt <= wcnt + 4'd1; if (wcnt == 4'd4) begin rdn <= '0; ph <= P_INS2; end end
                P_INS2: if (13'(rdn) == cneed) ph <= P_DRAIN2;
                P_DRAIN2: if (qcnt >= 4'd4) begin cnv <= '0; cap <= '0; ph <= P_OUT; end
                P_OUT: if (13'(cap) == cneed && lq_n == 4'd0 && !dconv1 && !dconv2 && !dconv3) ph <= P_FLUSH;
                P_FLUSH: if (!w_v) begin ph <= P_IDLE; done <= 1'b1; end
                default: ph <= P_IDLE;
            endcase
        end
    end
    // FIFO pop into the landing register: room counted on registered state (3 slots + landing)
    always @* for (integer l2 = 0; l2 < DEL; l2 = l2 + 1)
        fpop[l2] = !fe[l2] && (ph == P_INS) && ({1'b0, st_n[l2]} + 3'(ld_v[l2]) < 3'd3);
endmodule

// Existing shared control/PHY state, cut without adding protocol epochs.
module ot_lkep_ctrl_phy #(
 parameter integer NS=3,W=545,TXQ=32,FCR=256,SQ=4,IDLE_P=1024,LW=487,RL=2,PBD=4,TFD=4,OFD=4,SL=64,XR=2,
 parameter integer MUT_PHY=0
)(input wire clk,rst_n,input wire [23:0] session,input wire t_v,input wire [W-1:0] t_flit,
 output reg t_cr,input wire r_cr,input wire [LW-1:0] x_rx,output wire [LW-1:0] x_tx,
 input wire [NS-1:0] icr_ret,sf_t,sd_t,input wire [NS*37-1:0] ak_flat,input wire [NS*32-1:0] rp_flat,
 input wire b_v,input wire [596:0] b_f,
 output reg [W-1:0] w_d,output reg [NS*((W+SL-1)/SL)*(1<<$clog2((TXQ+NS-1)/NS))-1:0] w_oh,
 output reg [NS-1:0] l0_v,fbv,rx_v,output reg fb_nak,output reg [11:0] fb_seq,
 output reg [2+12+24+W-1:0] c_h,output reg fault,output wire locked,
 output reg [31:0] st_replays,output reg [15:0] st_drops);
    localparam integer SW = 12, EW = 24;
    localparam integer FFW = 597, RFW = 35;
    localparam integer HB = 2 + SW + EW + W;           // 583: {session, seq, sub, data} before the CRC
    localparam integer TW = EW + SW + W;               // 581: {session, seq, data} at a macro port
    localparam integer QB = $clog2(TXQ);
    localparam integer QD = 1 << $clog2((TXQ + NS - 1) / NS);   // per-sub TX queue depth (flit k -> sub k mod NS)
    localparam integer NSL = (W + SL - 1) / SL;
    localparam integer CI = $clog2(PBD + 2);
    // Link round trip seen by a retry pipeline (its rewind -> the last stale NAK of that sequence), measured with the
    // tb_hfd_lk_ep trace: 48 / 52 / 56 edges at XR 0 / 1 / 2 (RL 2) -- 4 edges per relay stage (forward + reverse, both
    // ends).  NAKH (> RTT by two feedback phases) is the retry pipeline's NAK re-arm hold (NAK_HOLD): a NAK still standing
    // after it is a lost replay, replayed again instead of waiting for the 8,192-edge TIMEOUT.  The hardened retry macro
    // view is built with NAK_HOLD = NAKH_HW (physical/hbm_link_retry_pipeline_20261009 route_cl.sh NAK_HOLD=...).
    localparam integer RTT = 40 + 4 * RL + 4 * XR;
    localparam integer NAKH = RTT + 8;
    localparam integer NAKH_HW = 64;
    // ---------------------------------------------------------------- reset: synchronised, replicated per region
    // rst_n reaches only the 2-flop synchroniser (async assert, sync release); every region owns a registered copy (keep):
    // [g] sub g (its macro's rst_n pin, pin buffers / captures, relays), [NS] TX queue, [NS+1] TX out, [NS+2] RX / merge,
    // [NS+3] gearbox.
    localparam integer NR = NS + 4;
    reg  [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    (* keep *) reg [NR-1:0] rl;
    always @(posedge clk) rl <= {NR{rs[1]}};
    wire rtq = rl[NS], rto = rl[NS+1], rrx = rl[NS+2], rgb = rl[NS+3];
    // session: the reverse-frame check copy (each tile holds its macro's copy)
    reg  [EW-1:0] ses_c;
    always @(posedge clk) ses_c <= session;

    wire [SW+EW:0] ak[0:NS-1]; wire [31:0] rp_t[0:NS-1];
    genvar g; generate for(g=0;g<NS;g=g+1) begin:g_inputs
      assign ak[g]=ak_flat[g*37 +:37]; assign rp_t[g]=rp_flat[g*32 +:32];
    end endgenerate
    reg  [1:0]          esel;
    reg  [NS*QD-1:0]    tl;
    reg                 w_v;
    reg                 w_v2;
    reg           p_v, c_v; reg [HB-1:0] p_h; reg [13:0] p_c;
    wire [1:0]    c_sub = c_h[W +: 2];
    // ---------------------------------------------------------------- TX queue control (banks live in the tiles)
    // Flit k goes to sub k mod NS (esel); admission in striping order from wsel (stopping at the first sub without a
    // flit, a far credit or a pin-buffer credit) = one shared queue's order.  l0_v[g] (registered admission) tells tile g
    // to advance its bank head; the bank read happens in the tile two edges later (ot_lkep_sub).
    reg  [QB:0]         qn;                             // written, not yet admitted
    reg  [8:0]          fc;                             // far-end credits held (FCR <= 511)
    reg  [1:0]          wsel;                           // sub of the next admitted flit
    reg                 q_ovf;
    reg  [QB+1:0]       crp;                            // die-side credits owed
    reg  [NS*CI-1:0]    icr;                            // pin-buffer credits by sub
    reg  [NS-1:0]       admv;                           // admitted this edge, by sub
    reg  [2:0]          nadm;
    reg  [7:0]          fc_add;                         // credits returned by the far end this edge (from the rev path)
    integer             a, sa, gg, ss;
    reg                 go;
    always @(*) begin
        admv = 0; nadm = 0; go = 1'b1;
        for (a = 0; a < NS; a = a + 1) begin
            sa = (wsel + a) % NS;
            if (go && (a < qn) && (a < fc) && (icr[sa*CI +: CI] != 0)) begin admv[sa] = 1'b1; nadm = nadm + 1'b1; end
            else go = 1'b0;
        end
    end
    always @(posedge clk) w_d <= t_flit;
    always @(posedge clk or negedge rtq)
        if (!rtq) begin
            esel <= 0; w_v <= 1'b0; w_oh <= 0; l0_v <= 0; w_v2 <= 1'b0;
            for (gg = 0; gg < NS; gg = gg + 1) begin
                tl[gg*QD +: QD] <= {{(QD-1){1'b0}}, 1'b1};
                icr[gg*CI +: CI] <= PBD + 1;
            end
            qn <= 0; fc <= FCR[8:0]; wsel <= 0; t_cr <= 1'b0; q_ovf <= 1'b0; crp <= 0;
        end else begin
            w_v <= t_v;
            w_v2 <= w_v;
            for (gg = 0; gg < NS; gg = gg + 1) begin
                for (ss = 0; ss < NSL; ss = ss + 1)
                    w_oh[(gg*NSL+ss)*QD +: QD] <= (t_v && esel == gg) ? tl[gg*QD +: QD] : {QD{1'b0}};
                if (t_v && esel == gg) tl[gg*QD +: QD] <= {tl[gg*QD +: QD], tl[gg*QD+QD-1]};
                icr[gg*CI +: CI] <= icr[gg*CI +: CI] - (admv[gg] ? 1'b1 : 1'b0) + (icr_ret[gg] ? 1'b1 : 1'b0);
            end
            if (t_v) esel <= (esel == NS - 1) ? 2'd0 : esel + 1'b1;
            l0_v <= admv;
            qn <= qn + (w_v2 ? 1'b1 : 1'b0) - nadm;
            wsel <= (wsel + nadm) % NS;
            if ({1'b0, qn} + w_v2 + w_v + t_v > TXQ + nadm) q_ovf <= 1'b1;
`ifndef OT_LKEP_MUT_CREDIT
            t_cr <= (crp + nadm) != 0;
            crp <= crp + nadm - (((crp + nadm) != 0) ? 1'b1 : 1'b0);
`else
            t_cr <= t_v;                                // mutant: credit returned on arrival, not on admission
`endif
            fc <= fc + {1'b0, fc_add} - {6'b0, nadm};
        end

    // ---------------------------------------------------------------- reverse frame out (acks + credit count)
    reg  [1:0]    rsub;
    reg  [7:0]    ccnt;
    reg  [RFW-1:0] r_tx;
    wire [SW+EW:0] akr = ak[rsub];
    wire [22:0]   rbody = {ccnt, akr[0], akr[SW:1], rsub};
    always @(posedge clk or negedge rto)
        if (!rto) begin rsub <= 0; ccnt <= 0; end
        else begin
            rsub <= (rsub == NS - 1) ? 2'd0 : rsub + 1'b1;
            if (r_cr) ccnt <= ccnt + 1'b1;
        end
    wire [11:0] r_crc;
    ot_crc_par #(.W(47), .N(12), .POLY(12'h80F), .INIT(12'hFFF)) u_crc_r (.d({akr[SW+EW:SW+1], rbody}), .crc(r_crc));
    always @(posedge clk) r_tx <= {r_crc, rbody};

    // ---------------------------------------------------------------- gearbox (closed S81 lane format, FMT 1)
    reg  [LW-1:0] x_rx_p; reg x_rx_vp;                 // pin capture (io_flop_at_pins), then XR relay stages
    always @(posedge clk) x_rx_p <= x_rx;
    always @(posedge clk or negedge rgb) if (!rgb) x_rx_vp <= 1'b0; else x_rx_vp <= 1'b1;
    wire [LW-1:0] x_rx_q; wire x_rx_vq;
    ot_lkep_relay #(.W(LW), .N(XR)) u_xrr (.clk(clk), .rst_n(rgb), .i_v(x_rx_vp), .i_d(x_rx_p), .o_v(x_rx_vq), .o_vr(), .o_d(x_rx_q));
    wire [LW-1:0] x_tx_g; wire x_tx_gv;
    ot_lkep_relay #(.W(LW), .N(XR)) u_xtr (.clk(clk), .rst_n(rgb), .i_v(1'b1), .i_d(x_tx_g), .o_v(x_tx_gv), .o_vr(), .o_d(x_tx));
    wire          f_rx_v, r_rx_v, gbx_fault;
    wire [FFW-1:0] f_rx;
    wire [RFW-1:0] r_rx;
    ot_s81ph_link_gbx #(.FMT(1), .FFW(FFW), .RFW(RFW), .IDLE_P(IDLE_P), .BW(LW)) u_gbx (
        .clk(clk), .rst_n(rgb), .f_tx_v(b_v), .f_tx(b_f), .r_tx_v(1'b1), .r_tx(r_tx), .beat_tx(x_tx_g),
        .beat_rx_v(x_rx_vq), .beat_rx(x_rx_q), .f_rx_v(f_rx_v), .f_rx(f_rx), .r_rx_v(r_rx_v), .r_rx(r_rx),
        .locked(locked), .fault(gbx_fault));

    // ---------------------------------------------------------------- reverse frame in -> feedback, credits
    reg  [7:0]    ccnt_far;
    wire [11:0]   r_crc_rx;
    ot_crc_par #(.W(47), .N(12), .POLY(12'h80F), .INIT(12'hFFF)) u_crc_rr (.d({ses_c, r_rx[22:0]}), .crc(r_crc_rx));
    wire          r_ok = r_rx_v && (r_crc_rx == r_rx[34:23]);
    always @(posedge clk) begin fb_nak <= r_rx[14]; fb_seq <= r_rx[13:2]; end
    always @(posedge clk or negedge rgb)
        if (!rgb) begin fbv <= 0; ccnt_far <= 0; fc_add <= 0; end
        else begin
            fbv <= r_ok ? ({{(NS-1){1'b0}}, 1'b1} << r_rx[1:0]) & {NS{1'b1}} : {NS{1'b0}};
            fc_add <= r_ok ? r_rx[22:15] - ccnt_far : 8'd0;
            if (r_ok) ccnt_far <= r_rx[22:15];
        end

    // ---------------------------------------------------------------- forward frame in -> CRC (pipelined) -> tiles
    wire [13:0]   p_crc;                                // CRC of the frame now in p_h
    ot_crc_pipe #(.W(HB), .N(14), .POLY(14'h0805), .INIT(14'h3FFF), .NP(4)) u_crc_f (.clk(clk), .d(f_rx[HB-1:0]), .crc(p_crc));
    wire          p_ok = (p_crc == p_c);
    always @(posedge clk) begin p_h <= f_rx[HB-1:0]; p_c <= f_rx[FFW-1:HB]; c_h <= p_h ^ ((MUT_PHY != 0 && p_v && p_ok) ? {{(HB-1){1'b0}},1'b1} : {HB{1'b0}}); end
    always @(posedge clk or negedge rrx)
        if (!rrx) begin p_v <= 1'b0; c_v <= 1'b0; rx_v <= 0; end
        else begin
            p_v <= f_rx_v;
`ifndef OT_LKEP_MUT_NOCRC
            c_v <= p_v && p_ok;
            rx_v <= (p_v && p_ok) ? ({{(NS-1){1'b0}},1'b1} << p_h[W +:2]) : {NS{1'b0}};
`else
            c_v <= p_v;
            rx_v <= p_v ? ({{(NS-1){1'b0}},1'b1} << p_h[W +:2]) : {NS{1'b0}};
`endif
        end
    reg           drop;
    always @(posedge clk or negedge rrx)
        if (!rrx) drop <= 1'b0;
        else drop <= (|sd_t) || (c_v && (c_sub >= NS)) || (p_v && !p_ok);

    // ---------------------------------------------------------------- status (tile status registers)
    // Three counters sum on the original status capture edge. Carry-save
    // reduction and parallel prefix avoid two serial ripple additions.
    function automatic [31:0] add32_prefix(input [31:0] a,input [31:0] b);
      reg [31:0] p,g,base; integer d;
      begin
        base=a^b; p=base; g=a&b;
        for(d=1;d<32;d=d*2) begin
          g=g|(p&(g<<d));
          p=p&((p<<d)|((32'h1<<d)-1));
        end
        add32_prefix=base^(g<<1);
      end
    endfunction
    wire [31:0] rep_sum;
    generate if(NS==3) begin:g_sum3
      wire [31:0] sx=rp_t[0]^rp_t[1]^rp_t[2];
      wire [31:0] sy=((rp_t[0]&rp_t[1])|(rp_t[0]&rp_t[2])|(rp_t[1]&rp_t[2]))<<1;
      assign rep_sum=add32_prefix(sx,sy);
    end else begin:g_sum_other
      integer v; reg [31:0] sum;
      always @(*) begin sum=0;for(v=0;v<NS;v=v+1) sum=sum+rp_t[v];end
      assign rep_sum=sum;
    end endgenerate
    always @(posedge clk or negedge rto)
        if (!rto) begin fault <= 1'b0; st_replays <= 0; st_drops <= 0; end
        else begin
            fault <= fault | (|sf_t) | gbx_fault | q_ovf;
            st_replays <= rep_sum;
            if (drop) st_drops <= st_drops + 1'b1;
        end
endmodule

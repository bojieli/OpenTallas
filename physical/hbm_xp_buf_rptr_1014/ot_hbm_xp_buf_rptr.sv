`timescale 1ps/1fs
`default_nettype none
// BUF with a READ POINTER instead of the shifting unit image (A2 HBM group A 2026-10-14, after two GRT-0116 failures of
// ot_hbm_xp_buf_predecode: each emit beat shifted slice c <- c+1 (BF16) / c+2 (block-dot), so every inter-slice cut
// carried ~3,600 b of shift data against 3,728 tracks; widening never helped).  The image is now STATIC after its write;
// beat e emits slice e (BF16) or slices 2e..2e+1 (block-dot) through a registered 8:1 / 4:1 select into ob_d, the same
// words the shifted image presented at bit 0 on that beat.  The image is no longer zeroed by the shift-out: every unit
// opens with its first wave (w_t[0]), which clears every chunk it does not write (clear_chunk), so legal traffic sees
// identical outputs cycle for cycle (bench: tb_buf_rptr vs the original ot_hgi_xp_buf).  Same write decode as predecode.
module ot_hbm_xp_buf_rptr #(parameter integer TW = 25, parameter integer MUT_LANE = 0) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              tok0,       // strap: this buffer holds the ring token after reset (buffer 0)
    input  wire              w_v_i,
    input  wire [TW-1:0]     w_t_i,
    input  wire [1023:0]     w_d_i,
    input  wire              tok_i,
    output reg               tok_o,
    output reg               ob_v,
    output reg               ob_eop,
    output reg  [6:0]        ob_addr,
    output reg  [6:0]        ob_grp,
    output reg  [2047:0]     ob_d,
    output reg               fault
);
    reg rs; always @(posedge clk) rs <= !rst_n;
    reg t0_q, ti_q, w_v; reg [TW-1:0] w_t; reg [1023:0] w_d;
    reg [8191:0] fl; reg [1:0] st;                  // st 0 free, 1 filling, 2 complete (waiting / emitting)
    reg [6:0] mab; reg [1:0] mtp; reg mbf, mlc, have_tok, e_act; reg [2:0] ecnt;
    // kept copies of the emit enable and the format bit, one a 1,024-b slice of the unit image (+ one for the beat
    // register): one copy each drove 15,400 loads
    (* keep = 1 *) reg [8:0] mbf_c;
    // read pointer: one kept copy of the beat count and the format bit per 128-b chunk of ob_d (select fan-out <= 128 x 8)
    (* keep = 1 *) reg [2:0] ecnt_o [0:15]; (* keep = 1 *) reg [15:0] mbf_o;
    // READ SELECT AS SHARED COLUMN MUXES (A3 HBM group A 2026-10-14, after rptr1-19de62865 GRT-0116: 91 horizontal
    // markers at the N face).  Cut arithmetic of rptr1: image bit fl[i] with i mod 2048 >= 1024 fed ob_d[i mod 2048]
    // (block-dot) AND ob_d[80 + i mod 1024] (BF16), 944 bits apart (~101 um), so ~4 x 944 = 3,776 wires crossed a mid
    // vertical cut against 3,728 horizontal tracks (108 um x 46.4 tr/um x 0.744) before the writes.  Here every image bit
    // has ONE load: column r (0..1023) keeps m_lo[r] = fl[r + 2048 s] and m_hi[r] = fl[1024 + r + 2048 s] (4:1, s = the
    // slice pair: block-dot e[1:0], BF16 e[2:1]); ob_d[r] = m_lo[r], ob_d[1024 + r] = m_hi[r] (block-dot) and
    // ob_d[80 + r] = e[0] ? m_hi[r] : m_lo[r] (BF16) -- the same words, one wire a column (the N-face pin file interleaves
    // ob_d[r] / ob_d[1024 + r] so the BF16 80-bit offset is the only horizontal traffic: ~160 + 80 wires a cut).
    wire [1023:0] m_lo, m_hi;
    genvar gr;
    generate for (gr = 0; gr < 1024; gr = gr + 1) begin : g_col
        localparam integer CL = gr / 128;
        wire [1:0] s_lo = mbf_o[CL] ? ecnt_o[CL][2:1] : ecnt_o[CL][1:0];
        wire [1:0] s_hi = mbf_o[8 + CL] ? ecnt_o[8 + CL][2:1] : ecnt_o[8 + CL][1:0];
        assign m_lo[gr] = (s_lo == 2'd0) ? fl[gr] : (s_lo == 2'd1) ? fl[2048 + gr] : (s_lo == 2'd2) ? fl[4096 + gr] : fl[6144 + gr];
        assign m_hi[gr] = (s_hi == 2'd0) ? fl[1024 + gr] : (s_hi == 2'd1) ? fl[3072 + gr] : (s_hi == 2'd2) ? fl[5120 + gr] : fl[7168 + gr];
    end endgenerate
    wire [2047:0] ob_n;                 // next ob_d of an emit beat
    generate for (gr = 0; gr < 2048; gr = gr + 1) begin : g_ob
        localparam integer OC = gr / 128;
        if (gr >= 80 && gr < 1104) begin : g_bf
            wire bfv = ecnt_o[OC][0] ? m_hi[gr - 80] : m_lo[gr - 80];
            assign ob_n[gr] = mbf_o[OC] ? bfv : ((gr < 1024) ? m_lo[gr % 1024] : m_hi[gr % 1024]);
        end else begin : g_bd
            assign ob_n[gr] = mbf_o[OC] ? 1'b0 : ((gr < 1024) ? m_lo[gr % 1024] : m_hi[gr % 1024]);
        end
    end endgenerate
    (* keep=1 *) reg [63:0] bf_write,clear_chunk;
    (* keep=1 *) reg [15:0] flat_lo_write,flat_hi_write;
    integer c;
    wire [2:0] elast = mbf ? 3'd7 : 3'd3;
    wire start = !e_act && (have_tok || ti_q) && st == 2'd2;
    integer j, t;
    always @(posedge clk) begin
        t0_q <= tok0; ti_q <= tok_i; w_v <= w_v_i; w_t <= w_t_i; w_d <= w_d_i;
        for(integer dt=0;dt<8;dt=dt+1)for(integer dj=0;dj<8;dj=dj+1)begin
            bf_write[dt*8+dj] <= w_v_i && w_t_i[3] && w_t_i[8:6]==3'(dj);
            clear_chunk[dt*8+dj] <= w_v_i && w_t_i[0] && (!w_t_i[3] || w_t_i[8:6]!=3'(dj));
        end
        for(integer dh=0;dh<2;dh=dh+1)for(integer dj=0;dj<8;dj=dj+1)begin
            flat_lo_write[dh*8+dj] <= w_v_i && !w_t_i[3] && w_t_i[4] && (w_t_i[8:6]^3'(MUT_LANE!=0))==3'(dj);
            flat_hi_write[dh*8+dj] <= w_v_i && !w_t_i[3] && w_t_i[5] && (w_t_i[8:6]^3'(MUT_LANE!=0))==3'(dj);
        end
        // emission (block-dot 2,048 b a beat, BF16 1,024 b at bit 80)
        ob_v <= 1'b0; ob_d <= 2048'd0; tok_o <= 1'b0;
        if (e_act) begin
            ob_v <= 1'b1; ob_eop <= (ecnt == elast) && mlc;
            ob_addr <= mbf ? mab + {4'd0, ecnt} : mab + {4'd0, mtp, ecnt[1]};
            ob_grp <= mbf ? 7'd1 : {6'd0, ecnt[0]};
            ob_d <= ob_n;
            if (ecnt == elast - 3'd2) tok_o <= 1'b1;                       // the next buffer may follow with no gap
            if (ecnt == elast) begin st <= 2'd0; e_act <= 1'b0; ecnt <= 3'd0; for (integer oc = 0; oc < 16; oc = oc + 1) ecnt_o[oc] <= 3'd0; end
            else begin ecnt <= ecnt + 3'd1; for (integer oc = 0; oc < 16; oc = oc + 1) ecnt_o[oc] <= ecnt + 3'd1; end
        end else if (start) begin e_act <= 1'b1; ecnt <= 3'd0; for (integer oc = 0; oc < 16; oc = oc + 1) begin ecnt_o[oc] <= 3'd0; mbf_o[oc] <= mbf; end end
        if (ti_q) have_tok <= 1'b1;
        if (start) have_tok <= 1'b0;
        // buffer write (a unit's first wave opens the buffer cleared)
        if (w_v) begin
            if (w_t[0]) begin
                if (st != 2'd0) fault <= 1'b1;
                mab <= w_t[22:16]; mtp <= w_t[24:23]; mbf <= w_t[3]; mbf_c <= {9{w_t[3]}}; mlc <= 1'b0;
            end else if (st != 2'd1) fault <= 1'b1;
            if (w_t[2]) mlc <= 1'b1;
            st <= w_t[1] ? 2'd2 : 2'd1;

        end
        // Same wave/shift priority as the original body, with each decode
        // captured alongside the original w_d input station, not one edge later.
        for(t=0;t<8;t=t+1)for(j=0;j<8;j=j+1)
            if(bf_write[t*8+j])fl[t*1024+j*128+:128] <= w_d[t*128+:128];
            else if(clear_chunk[t*8+j])fl[t*1024+j*128+:128] <= 0;
        for(t=0;t<2;t=t+1)for(j=0;j<8;j=j+1)begin
            if(flat_lo_write[t*8+j])fl[266*j+t*133+:133] <= w_d[t*133+:133];
            if(flat_hi_write[t*8+j])fl[4096+266*j+t*133+:133] <= w_d[266+t*133+:133];
        end
        if (rs) begin
            ti_q <= 1'b0; w_v <= 1'b0; e_act <= 1'b0; ecnt <= 3'd0; st <= 2'd0; ob_v <= 1'b0; ob_eop <= 1'b0; tok_o <= 1'b0;
            bf_write<=0;clear_chunk<=0;flat_lo_write<=0;flat_hi_write<=0;
            have_tok <= t0_q; fault <= 1'b0; mbf <= 1'b0; mbf_c <= 9'd0; mlc <= 1'b0;
        end
    end
endmodule
`default_nettype wire

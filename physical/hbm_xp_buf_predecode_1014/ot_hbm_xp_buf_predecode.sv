`timescale 1ps/1fs
`default_nettype none
// Distinct original-source-bound write decoder repair; no new payload stage.
module ot_hbm_xp_buf_predecode #(parameter integer TW = 25, parameter integer MUT_LANE = 0) (
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
    (* keep = 1 *) reg [8:0] e_act_c; (* keep = 1 *) reg [8:0] mbf_c;
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
            ob_d <= mbf_c[8] ? {944'd0, fl[1023:0], 80'd0} : fl[2047:0];
            if (ecnt == elast - 3'd2) tok_o <= 1'b1;                       // the next buffer may follow with no gap
            if (ecnt == elast) begin st <= 2'd0; e_act <= 1'b0; e_act_c <= 9'd0; ecnt <= 3'd0; end
            else ecnt <= ecnt + 3'd1;
        end else if (start) begin e_act <= 1'b1; e_act_c <= 9'h1FF; ecnt <= 3'd0; end
        // the unit image shifts a beat out while emitting (slice i by its own copies; before the buffer write below)
        for (c = 0; c < 8; c = c + 1) if (e_act_c[c])
            fl[1024*c +: 1024] <= mbf_c[c] ? ((c < 7) ? fl[(1024*(c+1)) % 8192 +: 1024] : 1024'd0)
                                           : ((c < 6) ? fl[(1024*(c+2)) % 8192 +: 1024] : 1024'd0);
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
            have_tok <= t0_q; fault <= 1'b0; mbf <= 1'b0; mbf_c <= 9'd0; e_act_c <= 9'd0; mlc <= 1'b0;
        end
    end
endmodule
`default_nettype wire

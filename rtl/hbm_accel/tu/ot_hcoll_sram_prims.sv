`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// SRAM-backed primitives of the switched-tier collective endpoint (stream hbm-coll-rtl, 2026-10-08).
// They replace the HA2 flop primitives inside ot_hbm_accel_tu_endpoint_sr (the hfd_coll die view):
//   ot_ha2_delay (circular buffer, D-way x W read mux, D x W flops)  -> ot_hcoll_sdelay (SRAM, fixed read offset)
//                                                                       or ot_hcoll_shdelay (plain shift line)
//   ot_ha2_fifo  (2^AW x W flops + 2^AW-way read mux)                 -> ot_hcoll_sfifo (SRAM + 4-entry flop head)
// Storage is the ASAP7 1R1W macro ot_sram_1r1w_128x256_m1_r2c2 (the one hfd_vm uses: physical/asap7_memory_macros),
// NB = ceil(W / 256) macros side by side.  Design rules (REDESIGN_RULES): the word reaching a macro comes from a flop
// (input pin flop, no logic between it and the macro), every macro output is captured in a flop with no logic before
// it, and the head a consumer sees is a flop.
// ---------------------------------------------------------------------------

// NB macros of 128 x 256 as one 128 x (256 NB) array (unused high bits tied off)
module ot_hcoll_sram128 #(parameter integer W = 545) (
    input  wire         clk,
    input  wire         r_ce,
    input  wire [6:0]   r_addr,
    output wire [W-1:0] rd,
    input  wire         w_ce,
    input  wire [6:0]   w_addr,
    input  wire [W-1:0] wd
);
    localparam integer NB = (W + 255) / 256;
    wire [NB*256-1:0] q;
    wire [NB*256-1:0] d = {{(NB*256-W){1'b0}}, wd};
    for (genvar m = 0; m < NB; m = m + 1) begin : g_m
        ot_sram_1r1w_128x256_m1_r2c2 u_sram (.clk(clk), .r_ce_in(r_ce), .r_addr_in(r_addr), .rd_out(q[m*256 +: 256]),
            .w_ce_in(w_ce), .w_addr_in(w_addr), .wd_in(d[m*256 +: 256]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
    end
    assign rd = q[W-1:0];
endmodule

// Qualified W6 payload codec; no control-state or flop protection.
// A codeword is stored in actual macro payload columns, not a sidecar mirror.
module ot_hcoll_payload_codec #(parameter integer W=545, parameter integer ECC=0,
    parameter integer CW=ECC ? ((W+63)/64)*72 : W)(
    input wire [W-1:0] payload, output wire [CW-1:0] code,
    input wire [CW-1:0] sampled, output wire [W-1:0] decoded,
    output wire ce, output wire ue
);
  function automatic logic [71:0] encode64(input logic [63:0] data);
    logic [71:0] c; logic [70:0] mask; integer p, k, j;
    begin
      c='0; j=0;
      for (p=1;p<=71;p=p+1)
        if ((p & (p-1)) != 0) begin c[p-1]=data[j]; j=j+1; end
      // Same qualified Hamming equations, expressed as balanced reduction XORs.
      for (k=0;k<7;k=k+1) begin
        mask='0;
        for (p=1;p<=71;p=p+1)
          if ((p & (1<<k)) != 0 && p!=(1<<k)) mask[p-1]=1'b1;
        c[(1<<k)-1]=^(c[70:0]&mask);
      end
      c[71]=^c[70:0]; encode64=c;
    end
  endfunction
  // {uncorrectable, corrected, data64}; overall parity is bit71.
  function automatic logic [65:0] decode64(input logic [71:0] code);
    logic [71:0] c; logic [6:0] syndrome; logic overall, ue, corrected;
    logic [63:0] data; logic [70:0] mask; integer p,k,j;
    begin
      c=code; syndrome='0; overall=^code; ue=0; corrected=0;
      for (k=0;k<7;k=k+1) begin
        mask='0;
        for (p=1;p<=71;p=p+1)
          if ((p & (1<<k)) != 0) mask[p-1]=1'b1;
        syndrome[k]=^(code[70:0]&mask);
      end
      if (syndrome!=0) begin
        if (overall && syndrome<=71) begin
`ifndef OT_COLL_MUT_ECC_NO_CORRECT
          for(p=1;p<=71;p=p+1) if(syndrome==p) c[p-1]=~c[p-1];
`endif
          corrected=1; end
        else ue=1;
      end else if (overall) begin c[71]=~c[71]; corrected=1; end
      data='0; j=0;
      for (p=1;p<=71;p=p+1)
        if ((p & (p-1)) != 0) begin data[j]=c[p-1]; j=j+1; end
      decode64={ue,corrected,data};
    end
  endfunction
    if (ECC) begin : g_ecc
        localparam integer N=(W+63)/64;
        wire [N*64-1:0] padded={{(N*64-W){1'b0}},payload};
        wire [N*64-1:0] unpacked;
        wire [N-1:0] cs, us;
        for(genvar c=0;c<N;c=c+1) begin : g_c
            wire [65:0] result=decode64(sampled[c*72+:72]);
            assign code[c*72+:72]=encode64(padded[c*64+:64]);
            assign unpacked[c*64+:64]=result[63:0];
            assign cs[c]=result[64]; assign us[c]=
`ifdef OT_COLL_MUT_ECC_UE_PUBLISH
            1'b0;
`else
            result[65];
`endif
        end
        assign decoded=unpacked[W-1:0]; assign ce=|cs; assign ue=|us;
    end else begin : g_raw
        assign code=payload; assign decoded=sampled; assign ce=1'b0; assign ue=1'b0;
    end
endmodule

// Fixed-latency delay line in SRAM: same port list and the same latency D as ot_ha2_delay, exact on valid beats
// (d_out is defined only while v_out).  v_in at cycle t -> d_p (input flop, edge t) -> macro write (edge t+1, address
// cnt) -> macro read at the fixed offset cnt - (D-3) (edge t+D-2) -> capture flop q (edge t+D-1) -> d_out at t+D.
// Valid travels a D-flop shift line; the macro is only enabled on valid beats.  4 <= D <= 130.
module ot_hcoll_sdelay #(
    parameter integer W = 1,
    parameter integer D = 4,
    parameter integer PAYLOAD_ECC = 0
) (
    output wire         ecc_ce,
    output wire         ecc_ue,
    output wire         ecc_drop,
    input  wire         clk,
    input  wire         rst_n,
    input  wire         v_in,
    input  wire [W-1:0] d_in,
    output wire         v_out,
    output wire [W-1:0] d_out
);
    localparam integer CW = PAYLOAD_ECC ? ((W+63)/64)*72 : W;
`ifndef SYNTHESIS
    initial if (D < 4 || D - 3 >= 128) $fatal(1, "ot_hcoll_sdelay: D=%0d out of range 4..130", D);
`endif
    reg [D-1:0] vs;
    reg [6:0]   cnt;
    reg [CW-1:0] d_p, q;
    wire [CW-1:0] rd, encoded;
    wire [W-1:0] decoded;
    wire ce, ue;
    // with PAYLOAD_ECC the input is registered before the encoder (f380ff981: TT -224 on the sender's head FIFO read ->
    // arbiter -> SECDED encode -> d_p); the ECC line's latency is D + 2 (input register + decode register)
    reg vi_q; reg [W-1:0] di_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) vi_q <= 1'b0; else vi_q <= v_in;
    always @(posedge clk) di_q <= d_in;
    wire          v_line = (PAYLOAD_ECC != 0) ? vi_q : v_in;
    wire [W-1:0]  d_line = (PAYLOAD_ECC != 0) ? di_q : d_in;
    ot_hcoll_payload_codec #(.W(W),.ECC(PAYLOAD_ECC)) codec (.payload(d_line),.code(encoded),.sampled(q),.decoded(decoded),.ce(ce),.ue(ue));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin vs <= '0; cnt <= 7'd0; end
        else begin vs <= {vs[D-2:0], v_line}; cnt <= cnt + 7'd1; end
    always @(posedge clk) begin d_p <= encoded; q <= rd; end
    ot_hcoll_sram128 #(.W(CW)) u_m (.clk(clk), .r_ce(vs[D-3]), .r_addr(cnt - 7'(D - 3)), .rd(rd),
        .w_ce(vs[0]), .w_addr(cnt), .wd(d_p));
    // hgi-takeover (439ceed6b route: TT -246 on u_wtx q -> SECDED decode -> drop -> the port's credit counter): with
    // PAYLOAD_ECC the decoded word and its valid / ce / ue are registered (latency D + 1); without ECC unchanged (D).
    generate if (PAYLOAD_ECC != 0) begin : g_reg
        reg vo, ceo, ueo; reg [W-1:0] dq;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin vo <= 1'b0; ceo <= 1'b0; ueo <= 1'b0; end
            else begin vo <= vs[D-1] && !ue; ceo <= vs[D-1] && ce; ueo <= vs[D-1] && ue; end
        always @(posedge clk) dq <= decoded;
        assign v_out = vo; assign ecc_ce = ceo; assign ecc_ue = ueo; assign ecc_drop = ueo; assign d_out = dq;
    end else begin : g_comb
        assign v_out = vs[D-1] && !ue;
        assign ecc_ce = vs[D-1] && ce;
        assign ecc_ue = vs[D-1] && ue;
        assign ecc_drop = ecc_ue;
        assign d_out = decoded;
    end endgenerate
endmodule

// Plain shift-register delay (no read mux) for short / narrow lines; same ports and latency as ot_ha2_delay.
module ot_hcoll_shdelay #(
    parameter integer W = 1,
    parameter integer D = 1
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         v_in,
    input  wire [W-1:0] d_in,
    output wire         v_out,
    output wire [W-1:0] d_out
);
    reg [D-1:0] vs;
    reg [W-1:0] ds [0:D-1];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) vs <= '0;
        else vs <= {vs[D-2:0], v_in};
    always @(posedge clk) begin
        ds[0] <= d_in;
        for (integer i = 1; i < D; i = i + 1) ds[i] <= ds[i-1];
    end
    assign v_out = vs[D-1];
    assign d_out = ds[D-1];
endmodule

// SRAM FIFO with a first-word-fall-through flop head; the port list of ot_ha2_fifo (push/din/pop/empty/dout/ovf/count).
//   write: push, din -> pin flops push_p / din_p -> macro write (no logic between the flops and the macro)
//   read : a fixed pipeline that never stalls, gated by a local credit (ocr = free head slots, K):
//          fetch (r_ce) -> rd (macro) -> raw_q (capture flop, no logic before it) -> head FIFO (K flops, ot_ha2_fifo)
//   pop  : pops the head FIFO (as ot_ha2_fifo: pop && !empty) and returns its credit the same edge.
// Capacity 2^AW (SRAM) + K (head); overflow (a push_p while the SRAM part is full) is sticky in ovf.
// AW = 8: two 128-deep banks (bank = address MSB, one read and one write a cycle, either bank), each captured in its
// own flop; the bank select is applied after the capture flops, in front of the head FIFO.
// Latency push -> head visible: 5 edges (ot_ha2_fifo: 1).  K = 4 covers the 4-edge credit loop: full rate.
module ot_hcoll_sfifo #(
    parameter integer W  = 8,
    parameter integer AW = 7,
    parameter integer K  = 4,
    parameter integer PAYLOAD_ECC = 0
) (
    output wire         ecc_ce,
    output wire         ecc_ue,
    output wire         ecc_drop,
    input  wire         clk,
    input  wire         rst_n,
    input  wire         push,
    input  wire [W-1:0] din,
    input  wire         pop,
    output wire         empty,
    output wire [W-1:0] dout,
    output reg          ovf,
    output wire [AW:0]  count
);
    localparam integer CW = PAYLOAD_ECC ? ((W+63)/64)*72 : W;
`ifndef SYNTHESIS
    initial if (AW > 8 || AW < 1 || K != 4) $fatal(1, "ot_hcoll_sfifo: AW=%0d (1..8), K=%0d (4)", AW, K);
`endif
    localparam integer N = 1 << AW;
    localparam integer NBK = (AW > 7) ? 2 : 1;
    reg          push_p;
    reg [CW-1:0] din_p;
    reg [CW-1:0] rawb [0:NBK-1];
    wire [CW-1:0] rdb [0:NBK-1];
    wire [CW-1:0] encoded;
    wire [W-1:0] decoded;
    wire ce, ue;
    wire [CW-1:0] sampled=rawb[(NBK > 1) ? bs2 : 1'b0];
    ot_hcoll_payload_codec #(.W(W),.ECC(PAYLOAD_ECC)) codec (.payload(din),.code(encoded),.sampled(sampled),.decoded(decoded),.ce(ce),.ue(ue));
    // hgi-takeover (drive-0849 -616 ps rawb -> SECDED decode -> head FIFO write): with PAYLOAD_ECC the decoded word and
    // its ce / ue are registered (v3) before the head FIFO; the credit loop grows to 5 edges, so the head holds 8 and
    // KC = 5 credits keep full rate.  PAYLOAD_ECC = 0 is unchanged (no stage, K = 4, head 4).
    localparam integer ES = PAYLOAD_ECC ? 1 : 0;
    localparam integer KC = K + ES;
    reg v3; reg [W-1:0] dec_q; reg ce_q, ue_q;
    wire hv  = ES ? v3 : v2;
    wire hue = ES ? ue_q : ue;
    wire hce = ES ? ce_q : ce;
    assign ecc_ce=hv && hce; assign ecc_ue=hv && hue; assign ecc_drop=ecc_ue;
    reg          bs1, bs2;
    reg [AW:0]   scnt;
    reg [AW-1:0] wp, rp;
    reg [2:0]    ocr;
    reg          v1, v2;
    wire full  = scnt == (AW+1)'(N);
    wire put   = push_p && !full;
    wire fetch = (scnt != '0) && (ocr != 3'd0);
    wire hovf;
    wire [2+ES:0] hc;
    wire do_pop = pop && !empty;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            push_p <= 1'b0; scnt <= '0; wp <= '0; rp <= '0; ocr <= 3'(KC); v1 <= 1'b0; v2 <= 1'b0; v3 <= 1'b0; ovf <= 1'b0;
        end else begin
            push_p <= push;
            scnt <= scnt + (AW+1)'(put) - (AW+1)'(fetch);
            if (put) wp <= wp + 1'b1;
            if (fetch) rp <= rp + 1'b1;
            ocr <= ocr - 3'(fetch) + 3'(do_pop) + 3'(ecc_drop);
            v1 <= fetch; v2 <= v1; v3 <= v2;
            if ((push_p && full) || hovf) ovf <= 1'b1;
        end
    always @(posedge clk) begin
        din_p <= encoded;
        for (integer b = 0; b < NBK; b = b + 1) rawb[b] <= rdb[b];
        bs1 <= (NBK > 1) ? rp[AW-1] : 1'b0; bs2 <= bs1;
        dec_q <= decoded; ce_q <= ce; ue_q <= ue;
    end
    for (genvar b = 0; b < NBK; b = b + 1) begin : g_bk
        ot_hcoll_sram128 #(.W(CW)) u_m (.clk(clk), .r_ce(fetch && (NBK == 1 || rp[AW-1] == 1'(b))), .r_addr(7'(rp)),
            .rd(rdb[b]), .w_ce(put && (NBK == 1 || wp[AW-1] == 1'(b))), .w_addr(7'(wp)), .wd(din_p));
    end
    wire [W-1:0] raw_q = ES ? dec_q : decoded;
    ot_ha2_fifo #(.W(W), .AW(2 + ES)) u_head (.clk(clk), .rst_n(rst_n), .push(hv && !hue), .din(raw_q), .pop(pop),
        .empty(empty), .dout(dout), .ovf(hovf), .count(hc));
    assign count = scnt;
endmodule

// SRAM FIFO with an EXPORTED head (per-port split, 2026-10-08): ot_hcoll_sfifo whose head FIFO lives across a hard-
// macro boundary.  out_v / out_d leave an output flop (one beat per fetched word, in order); cr_in is a REGISTERED
// credit-return pulse (one per freed consumer head slot, K consumer slots).  The loop fetch -> rd -> capture -> out
// flop -> consumer in flop -> consumer head -> pop -> consumer credit flop -> cr_in flop -> ocr is 8 edges: K = 8.
module ot_hcoll_sfifo_x #(
    parameter integer W  = 8,
    parameter integer AW = 7,
    parameter integer K  = 8,
    parameter integer PAYLOAD_ECC = 0
) (
    output wire         ecc_ce,
    output wire         ecc_ue,
    output wire         ecc_drop,
    input  wire         clk,
    input  wire         rst_n,
    input  wire         push,
    input  wire [W-1:0] din,
    input  wire         cr_in,
    output reg          out_v,
    output reg  [W-1:0] out_d,
    output reg          ovf
);
    localparam integer CW = PAYLOAD_ECC ? ((W+63)/64)*72 : W;
`ifndef SYNTHESIS
    initial if (AW > 8 || AW < 1 || K < 1 || K > 15) $fatal(1, "ot_hcoll_sfifo_x: AW=%0d (1..8), K=%0d (1..15)", AW, K);
`endif
    localparam integer N = 1 << AW;
    localparam integer NBK = (AW > 7) ? 2 : 1;
    reg          push_p;
    reg [CW-1:0] din_p;
    reg [CW-1:0] rawb [0:NBK-1];
    wire [CW-1:0] rdb [0:NBK-1];
    wire [CW-1:0] encoded;
    wire [W-1:0] decoded;
    wire ce, ue;
    wire [CW-1:0] sampled=rawb[(NBK > 1) ? bs2 : 1'b0];
    ot_hcoll_payload_codec #(.W(W),.ECC(PAYLOAD_ECC)) codec (.payload(din),.code(encoded),.sampled(sampled),.decoded(decoded),.ce(ce),.ue(ue));
    // hgi-takeover (route hgi-coll-port-secded-577d24ba1 TT -222 on bs2 -> decode -> ue -> ocr): the decode lands in a
    // register stage (v3) before it drives out_v / out_d and the credit counter (+1 edge on the export; the credit loop
    // is 9 edges against K = 8 head slots: a full stream runs at 8 / 9, above the core's 4 delivery lanes per 8 ports)
    reg          v3, ueq, ceq; reg [W-1:0] dq;
    assign ecc_ce=v3 && ceq; assign ecc_ue=v3 && ueq; assign ecc_drop=ecc_ue;
    reg          bs1, bs2;
    reg [AW:0]   scnt;
    reg [AW-1:0] wp, rp;
    reg [3:0]    ocr;
    reg          v1, v2;
    wire full  = scnt == (AW+1)'(N);
    wire put   = push_p && !full;
    wire fetch = (scnt != '0) && (ocr != 4'd0);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            push_p <= 1'b0; scnt <= '0; wp <= '0; rp <= '0; ocr <= 4'(K); v1 <= 1'b0; v2 <= 1'b0; v3 <= 1'b0; ovf <= 1'b0; out_v <= 1'b0;
        end else begin
            push_p <= push;
            scnt <= scnt + (AW+1)'(put) - (AW+1)'(fetch);
            if (put) wp <= wp + 1'b1;
            if (fetch) rp <= rp + 1'b1;
            ocr <= ocr - 4'(fetch) + 4'(cr_in) + 4'(ecc_drop);
            v1 <= fetch; v2 <= v1; v3 <= v2; out_v <= v3 && !ueq;
            if (push_p && full) ovf <= 1'b1;
        end
    always @(posedge clk) begin
        din_p <= encoded;
        for (integer b = 0; b < NBK; b = b + 1) rawb[b] <= rdb[b];
        bs1 <= (NBK > 1) ? rp[AW-1] : 1'b0; bs2 <= bs1;
        dq <= decoded; ceq <= ce; ueq <= ue;
        out_d <= dq;
    end
    for (genvar b = 0; b < NBK; b = b + 1) begin : g_bk
        ot_hcoll_sram128 #(.W(CW)) u_m (.clk(clk), .r_ce(fetch && (NBK == 1 || rp[AW-1] == 1'(b))), .r_addr(7'(rp)),
            .rd(rdb[b]), .w_ce(put && (NBK == 1 || wp[AW-1] == 1'(b))), .w_addr(7'(wp)), .wd(din_p));
    end
endmodule

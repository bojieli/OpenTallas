`timescale 1ns/1ps
// dsfd_colt_mrgn (s81-die-rtl-bind 2026-10-14, die item F5): dsfd_colt_mrg (the CLOSED 4-lane collector merger) for a
// die with NQ stacks: the same frame-atomic merge, pacing, DONE / FAULT words and fault bits over the NQ PRESENT lanes
// (the DONE join waits for every present stack's DONE head; a 1-stack layer die has no other stack to wait for -- the
// 4-lane merger there would never emit a DONE: the col engine hang).  NQ 4 is cycle-identical to dsfd_colt_mrg
// (lockstep bench rtl/dsrom_sys/s81_ph/test/run_colt_mrgn_gate.sh).
module dsfd_colt_mrgn #(
    parameter integer NQ   = 1,               // lanes present (stacks of the die), lane 0 = SW
    parameter integer DM   = 8,
    parameter integer PACE = 2,
    parameter integer MUT  = 0                // bench negative control: 1 = the DONE join never fires
) (
    input  wire [0:0]       ck,
    input  wire [0:0]       rst,
    input  wire [NQ*513-1:0] f_w,            // per lane {data, valid}: lane 0 SW, 1 SE, 2 NW, 3 NE
    input  wire [NQ*4-1:0]  f_f,             // per lane sticky fault sideband
    output wire [NQ-1:0]    t_cr,            // per lane credit return
    output wire [513:0]     vd,
    output wire [0:0]       vf
);
    localparam integer Q = NQ;
    localparam integer QB = (NQ > 1) ? $clog2(NQ) : 1;
    localparam integer CW = $clog2(DM + 1);
`ifndef SYNTHESIS
    initial if (PACE < 2) $fatal(1, "dsfd_colt_mrg: PACE must be >= 2 (registered merge decision)");
`endif
    reg [1:0] rst_s;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    // pin flops
    reg [NQ*513-1:0] fw; reg [NQ*4-1:0] ff;
    always @(posedge ck[0]) fw <= f_w;
    always @(posedge ck[0] or negedge rst_n) if (!rst_n) ff <= {NQ*4{1'b0}}; else ff <= f_f;
    // ---- landing FIFOs (head at entry 0)
    reg  [511:0] lq [0:Q-1][0:DM-1];
    reg  [CW-1:0] lc [0:Q-1];
    reg  [Q-1:0] pop;
    wire [Q-1:0] hv;
    wire [512*Q-1:0] hd;
    integer l, e;
    genvar g;
    generate for (g = 0; g < Q; g = g + 1) begin : g_h
        assign hv[g] = lc[g] != 0;
        assign hd[512 * g +: 512] = lq[g][0];
    end endgenerate
    always @(posedge ck[0] or negedge rst_n)
        if (!rst_n) for (l = 0; l < Q; l = l + 1) lc[l] <= {CW{1'b0}};
        else for (l = 0; l < Q; l = l + 1) lc[l] <= lc[l] + (fw[513 * l] ? 1'b1 : 1'b0) - ((pop[l] && hv[l]) ? 1'b1 : 1'b0);
    always @(posedge ck[0])
        for (l = 0; l < Q; l = l + 1)
            for (e = 0; e < DM; e = e + 1) begin
                if (pop[l] && hv[l]) begin
                    if (fw[513 * l] && e == lc[l] - 1) lq[l][e] <= fw[513 * l + 1 +: 512];
                    else if (e + 1 < DM) lq[l][e] <= lq[l][(e + 1) % DM];
                end else if (fw[513 * l] && e == lc[l]) lq[l][e] <= fw[513 * l + 1 +: 512];
            end
    reg [Q-1:0] crq;
    always @(posedge ck[0] or negedge rst_n) if (!rst_n) crq <= {Q{1'b0}}; else crq <= pop & hv;
    assign t_cr = crq;

    wire [Q-1:0] hdone;
    wire [7:0]   htag [0:Q-1];
    generate for (g = 0; g < Q; g = g + 1) begin : g_t
        assign hdone[g] = hd[512 * g + 508 +: 4] == 4'd4;
        assign htag[g]  = hd[512 * g + 500 +: 8];
    end endgenerate
    // ---- merger (ot_s81ph_col_core on the landing heads: a head outside a frame is a complete frame's header)
    reg  [$clog2(PACE+1)-1:0] pc;
    wire          pre  = (pc == PACE - 1);
    wire          slot = (pc == 0);
    reg           busy;
    reg  [QB-1:0] cl;
    reg  [11:0]   rem;
    reg  [QB-1:0] rr;
    reg  [4:0]    flt, flt_rep;
    reg           halt;
    reg  [7:0]    ltag;
    localparam [2:0] D_NONE = 0, D_BEAT = 1, D_HDR = 2, D_DONE = 3, D_FAULT = 4, D_PAD = 5;
    reg  [2:0]    dec;
    reg  [QB-1:0] dl;
    wire [4:0]    flt_new = flt & ~flt_rep;
    reg           e_tag;
    reg  [QB-1:0] pk;
    reg           pk_ok;
    integer k;
    always @(*) begin
        pk = rr; pk_ok = 1'b0;
        for (k = Q; k >= 1; k = k - 1)
            if (hv[(rr + k) % Q] && !hdone[(rr + k) % Q]) begin
                pk = QB'((rr + k) % Q); pk_ok = 1'b1;
            end
    end
    // every PRESENT stack's DONE head, equal tags, OR of their DONE codes / lane faults (NQ 4 = dsfd_colt_mrg)
    wire all_done = &(hv & hdone) && (MUT != 1);
    reg tags_eq; reg [10:0] dcode; reg [3:0] lf;
    integer kk;
    always @(*) begin
        tags_eq = 1'b1; dcode = 11'd0; lf = 4'd0;
        for (kk = 0; kk < Q; kk = kk + 1) begin
            if (htag[kk] != htag[0]) tags_eq = 1'b0;
            dcode = dcode | hd[512 * kk +: 11]; lf = lf | ff[4 * kk +: 4];   // {svc, link, fmt, ovf}
        end
    end
    reg          ov;
    reg  [511:0] od;
    always @(*) begin
        pop = {Q{1'b0}};
        if (slot)
            case (dec)
                D_BEAT: if (hv[dl]) pop[dl] = 1'b1;
                D_HDR:  pop[dl] = 1'b1;
                D_DONE: pop = {Q{1'b1}};
                default: ;
            endcase
    end
    always @(posedge ck[0] or negedge rst_n) begin
        if (!rst_n) begin
            pc <= 0; busy <= 1'b0; cl <= {QB{1'b0}}; rem <= 12'd0; rr <= QB'(Q - 1); flt <= 5'd0; flt_rep <= 5'd0;
            halt <= 1'b0; ltag <= 8'd0; dec <= D_NONE; dl <= {QB{1'b0}}; e_tag <= 1'b0; ov <= 1'b0; od <= 512'd0;
        end else begin
            pc <= (pc == PACE - 1) ? 0 : pc + 1'b1;
            flt <= flt | {lf[3], lf[2], e_tag, lf[1], lf[0]};
            e_tag <= 1'b0;
            if (pre) begin
                dec <= D_NONE;
                if (busy) begin
`ifdef OT_S81PH_COLMUT1
                    if (!(|flt) && pk_ok && pk != cl) begin dec <= D_HDR; dl <= pk; end
                    else
`endif
                    begin dec <= (|flt && !hv[cl]) ? D_PAD : D_BEAT; dl <= cl; end
                end else if (|flt_new)
                    dec <= D_FAULT;
                else if (!halt && !(|flt)) begin
`ifdef OT_S81PH_COLMUT2
                    if (|(hv & hdone)) dec <= D_DONE;
`else
                    if (all_done) begin
                        if (tags_eq) dec <= D_DONE; else e_tag <= 1'b1;
                    end
`endif
                    else if (pk_ok) begin dec <= D_HDR; dl <= pk; end
                end
            end
            ov <= 1'b0;
            if (slot)
                case (dec)
                    D_BEAT, D_PAD: if (hv[dl] || dec == D_PAD) begin
                        ov <= 1'b1; od <= (dec == D_PAD) ? 512'd0 : hd[512 * dl +: 512];
                        rem <= rem - 1'b1;
                        if (rem == 12'd1) busy <= 1'b0;
                    end
                    D_HDR: begin
                        ov <= 1'b1; od <= hd[512 * dl +: 512];
                        rr <= dl; cl <= dl;
                        rem <= hd[512 * dl + 480 +: 12];
                        busy <= hd[512 * dl + 480 +: 12] != 12'd0;
                    end
                    D_DONE: begin
                        ov <= 1'b1; od <= {4'd4, htag[0], 484'd0, 5'd0, dcode};
                        ltag <= htag[0];
                    end
                    D_FAULT: begin
                        ov <= 1'b1; od <= {4'd5, ltag, 484'd0, flt, 11'd0};
                        flt_rep <= flt; halt <= 1'b1;
                    end
                    default: ;
                endcase
        end
    end
    reg [513:0] vd_q;
    always @(posedge ck[0]) vd_q <= {od, ov & rst_n, rst_n};
    assign vd = vd_q;
    ot_fwd_clk_inv u_vf (.a(ck[0]), .y(vf[0]));
endmodule

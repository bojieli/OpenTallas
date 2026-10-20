`timescale 1ns/1ps
`default_nettype none
// TOKSIM-HBM-idxdma 2026-10-19: production-shape IDX.TOPK / ARGMAX.LOCAL records on the die-bound IDX root
// hb_idx__ctl = ot_hbm_idx_rootctl_static_am (#VM_RT, CR_RT) and hb_argmax = ot_hbm_argmax_static_sw_vm_r2 #(TP 192,
// VMX, ACK) behind its argmax share (argmax_rq -> LAQ lane stages, argmax_m -> LAR lane stages), on a VM model that
// answers RD = 7 + VM_RT edges after the root's vm_rq port (bank 6 + pin 1 + lanes; the contract the root's VM_RT
// parameter states) and echoes writes ACKD edges after cq (TOPK 11 + CR_RT, ARGMAX ACK - 2), memory-backed: every
// cq write lands in the model memory, and after each record the O words are checked against the python golden
// (toksim_idx_vectors.py). Cycles = edge sampling done - edge sampling go (833 ps stream edge on the die).
// Defines: KIND_ARGMAX (else TOPK), VM_RT, CR_RT, VMX_P, ACK_P, LAQ, LAR.
module tb_toksim_idx;
`ifndef VM_RT
`define VM_RT 0
`endif
`ifndef CR_RT
`define CR_RT 0
`endif
`ifndef VMX_P
`define VMX_P (5 + `VM_RT + `LAQ + `LAR)
`endif
`ifndef ACK_P
`define ACK_P 13
`endif
`ifndef LAQ
`define LAQ 0
`endif
`ifndef LAR
`define LAR 0
`endif
    localparam integer RD = 7 + `VM_RT, ACKT = 11 + `CR_RT, ACKA = `ACK_P - 2, PD = 160;
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    reg go = 0, order = 0, a_mirror = 0, o_mirror = 0, has_r = 0; reg [3:0] k = 0; reg [19:0] n = 0, m = 0;
    reg [17:0] a_base = 0, a_str = 0, o_base = 0, o_str = 0, r_base = 0, r_str = 0;
    reg ago = 0; reg [17:0] an = 0, aa = 0, ao = 0, aimm = 0; reg [15:0] aois = 0;
    reg [2055:0] rr = 0; reg [273:0] crt = 0, cra = 0;
    wire [135:0] vq, arq, arq_l; wire [263:0] am_c, am; wire [337:0] cqt, cqa; wire [1:0] st, sa;
    wire tb_, td, tf, sf, ab, ad, af, an_f;
    reg [135:0] aq [0:15]; reg [263:0] ar [0:15];
    initial for (integer d = 0; d < 16; d = d + 1) begin aq[d] = 0; ar[d] = 0; end
    always @(posedge clk) begin aq[0] <= arq; ar[0] <= am_c; for (integer d = 1; d < 16; d = d + 1) begin aq[d] <= aq[d-1]; ar[d] <= ar[d-1]; end end
    assign arq_l = (`LAQ == 0) ? arq : aq[`LAQ-1];
    assign am = (`LAR == 0) ? am_c : ar[`LAR-1];
    ot_hbm_idx_rootctl_static_am #(.VM_RT(`VM_RT), .CR_RT(`CR_RT)) dut(.clk(clk), .rst_n(rst_n),
        .program_we(1'b0), .program_addr(8'd0), .program_data(256'd0), .start(1'b0), .length(12'd0),
        .sel_op(), .sel_pass(), .sel_addr(), .link_flush(), .link_emit(), .link_group(), .link_clear(), .selected_v(4'h0),
        .ingest_v(), .tree_ev(4'h0), .qfault(4'h0), .sf(1'b0), .lf(1'b0), .done(), .fault(),
        .topk_go(go), .topk_k(k), .topk_order(order), .topk_n(n), .topk_m(m), .topk_a_mirror(a_mirror), .topk_a_base(a_base),
        .topk_a_str(a_str), .topk_o_mirror(o_mirror), .topk_o_base(o_base), .topk_o_str(o_str), .topk_has_r(has_r),
        .topk_r_base(r_base), .topk_r_str(r_str), .cq(cqt), .cq_seq(st), .cr(crt), .topk_busy(tb_), .topk_done(td), .topk_fault(tf),
        .index_rq(136'd0), .index_rr(), .argmax_rq(arq_l), .argmax_m(am_c), .vm_rq(vq), .vm_rr(rr), .share_fault(sf));
    ot_hbm_argmax_static_sw_vm_r2 #(.TP(192), .VMX(`VMX_P), .ACK(`ACK_P)) amx(.clk(clk), .rst_n(rst_n), .die_id(8'd3), .go(ago),
        .mode(1'b0), .imm_a(aimm), .a_mirror(1'b1), .a_base(aa), .n(an), .o_base(ao), .o_is(aois), .vm_rq(arq), .vm_rr(am),
        .cq(cqa), .cq_seq(sa), .cr(cra), .busy(ab), .done(ad), .fault(af), .nan_flag(an_f));
    // ---------------- memory-backed VM model: {mirror, sector15}
    reg [255:0] mem [0:65535];
    reg [16:0] p [0:PD-1][0:7]; reg [16:0] ct [0:PD-1]; reg [16:0] ca [0:PD-1]; integer t, l;
    initial begin
        for (t = 0; t < 65536; t = t + 1) mem[t] = 0;
        $readmemh("mem.hex", mem);
        for (t = 0; t < PD; t = t + 1) begin ct[t] = 0; ca[t] = 0; for (l = 0; l < 8; l = l + 1) p[t][l] = 0; end
    end
    task automatic wr(input [337:0] c);
        reg [15:0] s; integer b; begin
            s = c[324:309];   // byte_addr32 [335:304] = {11 0, mirror, sector15, 5 0}
            for (b = 0; b < 32; b = b + 1) if (c[16 + b]) mem[s][8*b +: 8] = c[48 + 8*b +: 8];
        end endtask
    integer cyc = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        for (t = PD-1; t > 0; t = t - 1) begin ct[t] <= ct[t-1]; ca[t] <= ca[t-1]; for (l = 0; l < 8; l = l + 1) p[t][l] <= p[t-1][l]; end
        for (l = 0; l < 8; l = l + 1) p[0][l] <= {vq[17*l+16], vq[17*l +: 16]};
        ct[0] <= {cqt[337], cqt[15:0]}; ca[0] <= {cqa[337], cqa[15:0]};
        if (cqt[337] && cqt[336]) wr(cqt);
        if (cqa[337] && cqa[336]) wr(cqa);
    end
    always @(negedge clk) begin
        for (l = 0; l < 8; l = l + 1) begin
            rr[257*l +: 256] = mem[p[RD-1][l][15:0]]; rr[257*l+256] = p[RD-1][l][16];
        end
        crt = 0; crt[273] = ct[ACKT-1][16]; crt[272:257] = ct[ACKT-1][15:0]; crt[256] = ct[ACKT-1][16];
        cra = 0; cra[273] = ca[ACKA-1][16]; cra[272:257] = ca[ACKA-1][15:0]; cra[256] = ca[ACKA-1][16];
    end
    // ---------------- edges
    integer tg = -1, te = -1, evd = 0, evf = 0;
    always @(posedge clk) if (rst_n) begin
        if ((go && !tb_) || (ago && !ab)) tg = cyc;
        if (td || ad) begin te = cyc; evd = evd + 1; end
        if (tf || af) begin te = cyc; evf = evf + 1; end
    end
    integer fr, fe, nr, r, cnt, j, w, x, errs = 0, i0, i1, i2, i3, i4, i5, i6, i7, i8, rc, cmin = 1 << 30, cmax = 0;
    reg [31:0] got;
    initial begin
        fr = $fopen("rec.txt", "r"); fe = $fopen("exp.txt", "r");
        rc = $fscanf(fr, "%d", nr);
        repeat (6) @(negedge clk); rst_n = 1; repeat (10) @(negedge clk);
        for (r = 0; r < nr; r = r + 1) begin
`ifdef KIND_ARGMAX
            rc = $fscanf(fr, "%d %d %d %d %d %d", i0, i1, i2, i3, i4, i5);
            an = i0; aa = i2; aimm = i3; ao = i4; aois = i5; ago = 1;
            @(negedge clk) ago = 0;
            repeat (4) @(negedge clk); while (ab) @(negedge clk);
`else
            rc = $fscanf(fr, "%d %d %d %d %d %d %d %d %d", i0, i1, i2, i3, i4, i5, i6, i7, i8);
            k = i0; order = i1; n = i2; m = i3; a_mirror = i4; a_base = i5; a_str = i6; o_base = i7; o_str = i8; go = 1;
            @(negedge clk) go = 0;
            repeat (4) @(negedge clk); while (tb_) @(negedge clk);
`endif
            repeat (3) @(negedge clk);
            rc = $fscanf(fe, "%d", cnt);
            for (j = 0; j < cnt; j = j + 1) begin
                rc = $fscanf(fe, "%d %d", w, x);
                got = mem[w >> 3][32*(w & 7) +: 32];
                if (got !== 32'(x)) begin errs = errs + 1; if (errs < 8) $display("GOLDEN MISMATCH rec %0d word %0d got %0d expected %0d", r, w, got, x); end
            end
            $display("TOKSIM_REC rec %0d go_edge %0d done_edge %0d cycles %0d", r, tg, te, te - tg);
            if (te - tg < cmin) cmin = te - tg; if (te - tg > cmax) cmax = te - tg;
        end
        $display("TOKSIM_IDX kind %s VM_RT %0d CR_RT %0d VMX %0d ACK %0d LAQ %0d LAR %0d records %0d done %0d fault %0d share_fault %b errors %0d cycles_min %0d cycles_max %0d",
`ifdef KIND_ARGMAX
                 "ARGMAX",
`else
                 "TOPK",
`endif
                 `VM_RT, `CR_RT, `VMX_P, `ACK_P, `LAQ, `LAR, nr, evd, evf, sf, errs, cmin, cmax);
        if (errs == 0 && evd == nr && evf == 0 && !sf) $display("TOKSIM_IDX PASS"); else $display("TOKSIM_IDX FAIL");
        $finish;
    end
endmodule
`default_nettype wire

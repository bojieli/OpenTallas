#!/bin/bash
# KVR-LANDLAG 10-19: what latency does a KV forwarded lane DELIVER with the straps the KV GEN ties?  Behavioural bench of the
# KV lane masters exactly as the die binds them (rtl/qwen_sys/kv_fwd_lane_20261018/qkd_rlysh.sv: qkd_rlysh0_36 hop 0,
# qkd_rlysh_36 half-cycle stations, qkd_landsh_36 / qkd_landsh0_36 landing; rtl/qwen_split/qfd_fwd_lane.sv) -- Verilator 5.050.
# Lanes n = 1, 2, 5, 15, 40 (n 40: 0.1 ns forwarded clock legs, total 0.4 T) with the KV GEN strap (tools/qwen_kv_die/kv_fwd_lanes.py strap_k: E = planned_e(n) =
# max(2, ceil((n-1)/2)+1), K = (E + h0(n)) mod 8, h0 = 1 for n = 1 (QK-LANDEN en register)), source and receiver released on
# the same edge (the KV GEN calendar G = R0), small forwarded legs (0.4 T/10 clock, 0.2 data) and the receiver root 0.2 T
# after the source root.  Every receiver edge checks o = w(t - L):
#   hw       L = K + 1 - h0(n)   (tools/qwen_split/land_lag_sim.py kv-check L_hw)                                  -> PASS
#   compiled L = ceil(landed - 1), landed = E + 2 (kv_fwd_lanes.landed_cost, KVR-FWDAGE 10-19) -- the age the KV static
#            compiler charges (kv_static_ages.fwd_overlay, kv_static_params.lane_ages)                             -> PASS
#   oldgen   MUTANT: the KV GEN before KVR-FWDAGE (K = E for every n, landed = 1 + (n-2)/2 + 1 + E + 1 for n > 1)  -> FAIL
#   encomb   MUTANT: compiled ages + straps on a landing whose en is NOT registered (OT_QFD_LAND_MUT_ENCOMB): the n = 1
#            +1 strap edge belongs to the en register                                                             -> FAIL
# usage: bench_kv_fwd_lane.sh <hw|compiled|oldgen|encomb> <work dir>      last line KV_FWD_BENCH PASS|FAIL
set -u
mode=$1; O=$(mkdir -p "$2" && readlink -f "$2")
cd "$(dirname "$0")/../.."
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
DEF=
case $mode in hw) LM=0 ;; compiled) LM=1 ;; oldgen) LM=2 ;; encomb) LM=1; DEF=+define+OT_QFD_LAND_MUT_ENCOMB ;;
  *) echo "bad mode $mode"; exit 2 ;; esac
cat > "$O/tb.sv" <<'EOT'
`timescale 1ns/1ps
module tdly #(parameter integer W = 1, parameter real D = 1.0) (input wire [W-1:0] a, output wire [W-1:0] y);
    assign #(D) y = a;
endmodule
module lane #(parameter integer NF = 5, parameter integer LM = 0, parameter real CD = 0.4, DD = 0.2, parameter integer G = 10) (
    input wire cks, input wire ckd, input wire [31:0] es, input wire [31:0] ed, output integer err, output integer chk, output wire flt);
    localparam integer W = 36;
    localparam integer E = (NF <= 3) ? 2 : ((NF - 1 + 1) / 2 + 1);           // planned_e(n) = max(2, ceil((n-1)/2) + 1)
    localparam integer H0 = (NF == 1) ? 1 : 0;
    localparam integer K = (LM == 2) ? E % 8 : (E + H0) % 8;                  // kv_fwd_lanes.strap_k (8 ties 000); oldgen K = E
    localparam integer LHW = ((K - H0 - E + 4 + 64) % 8) - 4 + E + 1;         // land_lag_sim kv-check L_hw (rep nearest E)
    // compiled ceil(landed - 1), in half units: landed = E + 2 (kv_fwd_lanes.landed_cost); oldgen 1 + (n-2)/2 + 1 + E + 1
    localparam integer LANDED2 = (LM == 2 && NF > 1) ? (2 + (NF - 2) + 2 + 2 * E + 2) : 2 * (E + 2);
    localparam integer LCOMP = (LANDED2 - 2 + 1) / 2;
    localparam integer L = LM ? LCOMP : LHW;
    reg  [W-1:0] src = 0;
    reg en = 0, rs = 0;
    function automatic [W-1:0] w_of(input integer e); w_of = W'(e * 40503 + (e >>> 3) + 7); endfunction
    always @(posedge cks) begin src <= w_of(es); en <= (es >= G); end
    always @(posedge ckd) rs <= (ed >= G);                                    // G = R0 (KV GEN calendar)
    wire [W-1:0] d [0:NF];  wire e_ [0:NF];  wire c_ [0:NF];
    wire [W-1:0] o; wire hi, lo;
    wire [2:0] kk = K[2:0];
    assign d[0] = src;
    genvar j;
    generate
      if (NF == 1) begin : g1
        qkd_landsh0_36 u_l (.ck_s(cks), .en(en), .a(d[0]), .ck(ckd), .rs(rs), .k0(kk[0]), .k1(kk[1]), .k2(kk[2]),
                            .tie_hi(hi), .tie_lo(lo), .b(o), .fault(flt));
      end else begin : gn
        wire [W-1:0] b0; wire eb0, cko0;
        qkd_rlysh0_36 u_s0 (.ck(cks), .en(en), .a(d[0]), .b(b0), .eb(eb0), .ck_o(cko0));
        tdly #(W, DD) u_d1 (b0, d[1]);  tdly #(1, DD) u_e1 (eb0, e_[1]);  tdly #(1, CD) u_c1 (cko0, c_[1]);
        for (j = 1; j < NF - 1; j = j + 1) begin : g_st
          wire [W-1:0] bj; wire ebj, ckoj;
          qkd_rlysh_36 u_s (.ckf(c_[j]), .ea(e_[j]), .a(d[j]), .b(bj), .eb(ebj), .ck_o(ckoj));
          tdly #(W, DD) u_d (bj, d[j + 1]);  tdly #(1, DD) u_e (ebj, e_[j + 1]);  tdly #(1, CD) u_c (ckoj, c_[j + 1]);
        end
        qkd_landsh_36 u_l (.ckf(c_[NF - 1]), .ea(e_[NF - 1]), .a(d[NF - 1]), .ck(ckd), .rs(rs), .k0(kk[0]), .k1(kk[1]),
                           .k2(kk[2]), .tie_hi(hi), .tie_lo(lo), .b(o), .fault(flt));
      end
    endgenerate
    initial begin
        err = 0; chk = 0;
        $display("KV_FWD_LANE n=%0d E=%0d K=%0d L_hw=%0d L_compiled=%0d checking L=%0d", NF, E, K, LHW, LCOMP, L);
    end
    integer te_;
    reg [W-1:0] ex_;
    always @(negedge ckd) begin
        te_ = ed;
        te_ = te_ - 1 - L;
        ex_ = (te_ >= G + H0) ? w_of(te_) : {W{1'b0}};
        if (ed > G + 20) begin
            chk = chk + 1;
            if (o !== ex_) begin
                err = err + 1;
                if (err < 3) $display("KV_FWD_LANE MISMATCH n=%0d ed=%0d o=%h exp=%h", NF, ed, o, ex_);
            end
        end
    end
endmodule
module tb;
    reg cks = 0, ckd = 0;
    reg [31:0] es = 0, ed = 0;
    always #5 cks = ~cks;
    initial begin #0.2; forever #5 ckd = ~ckd; end
    always @(posedge cks) es <= es + 1;
    always @(posedge ckd) ed <= ed + 1;
    integer e [0:4], c [0:4]; wire f [0:4];
    lane #(.NF(1),  .LM(`LM)) l0 (cks, ckd, es, ed, e[0], c[0], f[0]);
    lane #(.NF(2),  .LM(`LM)) l1 (cks, ckd, es, ed, e[1], c[1], f[1]);
    lane #(.NF(5),  .LM(`LM)) l2 (cks, ckd, es, ed, e[2], c[2], f[2]);
    lane #(.NF(15), .LM(`LM)) l3 (cks, ckd, es, ed, e[3], c[3], f[3]);
    // n = 40: total forwarded insertion held at 0.4 T (0.1 ns a hop): the planned E is the zero-delay estimate; a lane
    // whose forwarded insertion exceeds the slot margin needs the die STA's measured E_sta (fwd_lanes.json 'owed')
    lane #(.NF(40), .LM(`LM), .CD(0.1)) l4 (cks, ckd, es, ed, e[4], c[4], f[4]);
    initial begin
        #3000;
        begin : sum
            integer i, te, tc, tf;
            te = 0; tc = 0; tf = 0;
            for (i = 0; i < 5; i = i + 1) begin
                te = te + e[i]; tc = tc + c[i]; tf = tf + (f[i] === 1'b1 ? 1 : 0);
                $display("KV_FWD_LANE lane %0d errors %0d checks %0d fault %b", i, e[i], c[i], f[i]);
            end
            $display("KV_FWD_BENCH %s %0d errors in %0d checks (faults %0d)", (te || tf || tc < 1000) ? "FAIL" : "PASS", te + tf, tc, tf);
        end
        $finish;
    end
endmodule
EOT
"$V" --version > "$O/verilator.version"
"$V" --binary --timing -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-COMBDLY -Wno-LATCH -Wno-INITIALDLY --top-module tb +define+LM=$LM $DEF \
  -Mdir "$O/obj" -o tb "$O/tb.sv" rtl/qwen_sys/kv_fwd_lane_20261018/qkd_rlysh.sv rtl/qwen_split/qfd_fwd_lane.sv rtl/hdc/ot_hdc_cg.sv \
  > "$O/build.log" 2>&1 || { echo BUILD_FAILED; tail -20 "$O/build.log"; exit 2; }
"$O/obj/tb" > "$O/bench.log" 2>&1
grep -E 'KV_FWD_(BENCH|LANE)' "$O/bench.log"
grep -q 'KV_FWD_BENCH PASS' "$O/bench.log"

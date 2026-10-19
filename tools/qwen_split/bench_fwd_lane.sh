#!/bin/bash
# Q-DIE11-RLY 10-18: behavioural bench of the Qwen forwarded-clock HALF-CYCLE lane + landing (rtl/qwen_split/qfd_fwd_lane.sv,
# LANDING-CONTRACT L1-L7) through the GENERATED die wrappers (tools/qwen_split/gen_relay_rtl.py) -- Verilator 5.050.
# usage: bench_fwd_lane.sh <pass|sel|naive|vld|full|hop0inv|encomb|rlyencomb> <work dir> [W]
#   pass : 8 lanes in parallel (n = 1, 2, 5, 5+2T lag, 8, 27 frames; source released before / after the receiver), each
#          hop with its own clock-leg and data-leg delay (clock leg longer: the hold-critical case), receiver root offset
#          from the source root.  Per lane the bench derives the latency L from the geometry (read 0.25..1.25 T after
#          the ring write; lane "lag2" reuses the K of "lag0" with 2 T more clock lag: same L, inside the D = 4 window),
#          K = (L - 1 - (R0 - G)) mod 8, and checks on every receiver edge: o = w(t - L) once written (0 bubbles before),
#          fault stays 0.  PASS line: FWD_BENCH PASS 0 errors in <checks> checks.
#          QK-LANDEN 10-19: an n = 1 lane (qfd_landh0) registers en on ck_s before its clock gate: its write epoch is source
#          edge G + 1 (the word launched at G is never written, 0 bubble) and K = (L - 1 - (R0 - (G + 1))) mod 8; lanes
#          l8 / l9 are n = 1 with the source / the receiver releasing late (l0 releases the source first).
#          RLYH0-EN 10-19: the multi-frame lanes' hop-0 station (qfd_rlyh0) registers en on the source root the same way:
#          EVERY lane's write epoch is G + 1 (HREG = 1 for all NF), K = (L - 1 - (R0 - (G + 1))) mod 8.
#   encomb: both hop-0 forms with en UNREGISTERED (the closed-view form, en -> ICG combinational) under the registered
#          calendar: FAIL.  rlyencomb: only the rlyh0 station's en unregistered (landh0 registered): FAIL (lanes n >= 2)
#   sel / naive / vld / full / hop0inv: the same bench on the RTL built with one mutant define (read slot one late; no
#          ring; every slot valid at once; full-cycle forwards; the first-form inverting hop-0 gate) -- each must FAIL.
set -u
mode=$1; O=$2; W=${3:-16}
cd "$(dirname "$0")/../.."; mkdir -p "$O"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
DEF=+define+OT_QFD_LAND_SAFE_REG
if [[ $mode = *_pipe ]]; then
  mode=${mode%_pipe}
  DEF="$DEF +define+OT_QFD_LAND_READ_PIPE"
fi
if [[ $mode = *_gated ]]; then
  mode=${mode%_gated}
  DEF="$DEF +define+OT_QFD_LAND_GATED_BANKS"
fi
if [[ $mode = phase ]]; then
  mode=pass
  DEF="$DEF +define+OT_QFD_LAND_PHASE_SWEEP"
fi
case $mode in
  pass) ;; wsel) DEF="$DEF +define+OT_QFD_LAND_MUT_WSEL" ;; rsel) DEF="$DEF +define+OT_QFD_LAND_MUT_RSEL" ;; sel) DEF="$DEF +define+OT_QFD_LAND_MUT_SEL" ;; naive) DEF="$DEF +define+OT_QFD_LAND_MUT_NAIVE" ;;
  vld) DEF="$DEF +define+OT_QFD_LAND_MUT_VLD" ;; full) DEF="$DEF +define+OT_QFD_LANE_MUT_FULL" ;; hop0inv) DEF="$DEF +define+OT_QFD_LANE_MUT_HOP0INV" ;;
  encomb) DEF="$DEF +define+OT_QFD_LAND_MUT_ENCOMB +define+OT_QFD_LANE_MUT_ENCOMB" ;;
  rlyencomb) DEF="$DEF +define+OT_QFD_LANE_MUT_ENCOMB" ;;
  *) echo "bad mode $mode"; exit 2 ;;
esac
# the die wrappers exactly as the die generator names / ports them (gen_relay_rtl.py on a mini die.v)
cat > "$O/mini_die.v" <<EOT
module qfd_die ();
$(for n in n_a n_b n_c n_d; do echo "  wire [$((W-1)):0] $n;"; done)
$(for n in n_ck n_en n_ckf1 n_ckf2 n_e1 n_e2 n_ck2 n_rs n_hi n_lo n_flt; do echo "  wire [0:0] $n;"; done)
  qfd_rlyh0_${W}_EW_65x30 rly_x_0 (.ck(n_ck), .en(n_en), .a(n_a), .b(n_b), .eb(n_e1), .ck_o(n_ckf1));
  qfd_rlyh_${W}_EW_65x30 rly_x_1 (.ckf(n_ckf1), .ea(n_e1), .a(n_b), .b(n_c), .eb(n_e2), .ck_o(n_ckf2));
  qfd_landh_${W}_EW_65x30 rly_x_2 (.ckf(n_ckf2), .ea(n_e2), .a(n_c), .ck(n_ck2), .rs(n_rs), .k0(n_hi), .k1(n_lo), .k2(n_lo), .tie_hi(n_hi), .tie_lo(n_lo), .b(n_d), .fault(n_flt));
  qfd_landh0_${W}_EW_65x30 rly_y_0 (.ck_s(n_ck), .en(n_en), .a(n_a), .ck(n_ck2), .rs(n_rs), .k0(n_hi), .k1(n_lo), .k2(n_lo), .tie_hi(n_hi), .tie_lo(n_lo), .b(n_d), .fault(n_flt));
endmodule
EOT
python3 tools/qwen_split/gen_relay_rtl.py "$O/mini_die.v" "$O/wrappers.sv" > "$O/wrappers.json" || { echo GEN_FAILED; exit 2; }
cat > "$O/tb.sv" <<'EOT'
`timescale 1ns/1ps
// wire leg of D ns: a chain of inertial segments of <= 4 ns each (an inertial #d longer than the 5-ns half period would
// swallow the clock; Verilator evaluates an intra-assignment NBA delay's right side late, so no y <= #d a)
module tdly #(parameter integer W = 1, parameter real D = 1.0) (input wire [W-1:0] a, output wire [W-1:0] y);
    localparam integer NS = (D <= 4.0) ? 1 : $rtoi($ceil(D / 4.0));
    wire [W-1:0] s [0:NS];
    assign s[0] = a;
    genvar i;
    generate for (i = 0; i < NS; i = i + 1) begin : g
        assign #(D / NS) s[i + 1] = s[i];
    end endgenerate
    assign y = s[NS];
endmodule
// one lane: NF frames (frame 0 hop-0, NF-1 the landing), per-hop clock leg CD / data leg DD, receiver root offset DOFF,
// source release edge G, receiver release edge R0, extra clock lag XL on the last hop
module lane #(parameter integer W = 16, NF = 5, parameter real CD = 3.6, DD = 1.2, XL = 0.0, DOFF = 2.0,
              parameter integer G = 10, R0 = 12, LADD = 0, KFROM = -1,
              parameter integer HREG = 2, RREG = 2,
`ifdef OT_QFD_LAND_GATED_BANKS
              parameter integer RPIPE = 1
`elsif OT_QFD_LAND_READ_PIPE
              parameter integer RPIPE = 1
`else
              parameter integer RPIPE = 0
`endif
              ) (       // hop-0 en registered on the source root (+1 edge): landh0 AND rlyh0
    input wire cks, input wire ckd, input wire [31:0] es, input wire [31:0] ed, output integer err, output integer chk, output wire flt);
    localparam real T = 10.0;
    reg  [W-1:0] src = 0;
    reg en = 0, rs = 0;
    function automatic [W-1:0] w_of(input integer e); w_of = W'(e * 40503 + (e >>> 3) + 7); endfunction
    always @(posedge cks) begin src <= w_of(es);
`ifdef OT_QFD_LAND_GATED_BANKS
        en <= (es >= G && es < 300) || (es >= G + 320);
`else
        en <= (es >= G);
`endif
    end           // the source launches w(e) at edge e
    always @(posedge ckd)
`ifdef OT_QFD_LAND_GATED_BANKS
        rs <= (ed >= R0 && ed < 300) || (ed >= R0 + 320);
`else
        rs <= (ed >= R0);
`endif
    // latency L (receiver edges): read 0.25..1.25 T after the ring write of the same word (+ LADD for the window lane)
    real lag; integer L, K;
    wire [W-1:0] d [0:NF];  wire e_ [0:NF];  wire c_ [0:NF];
    wire [W-1:0] o; wire hi, lo;
    wire [2:0] kk = K[2:0];
    assign d[0] = src;
    genvar j;
    generate
      if (NF == 1) begin : g1
        qfd_landh0_16_EW_65x30 u_l (.ck_s(cks), .en(en), .a(d[0]), .ck(ckd), .rs(rs), .k0(kk[0]), .k1(kk[1]), .k2(kk[2]),
                                    .tie_hi(hi), .tie_lo(lo), .b(o), .fault(flt));
      end else begin : gn
        wire [W-1:0] b0; wire eb0, cko0;
        qfd_rlyh0_16_EW_65x30 u_s0 (.ck(cks), .en(en), .a(d[0]), .b(b0), .eb(eb0), .ck_o(cko0));
        // XL: extra lag of the whole last hop (clock AND data leg: a longer wire, the lane stays source-synchronous)
        tdly #(W, DD + (NF == 2 ? XL : 0.0)) u_d1 (b0, d[1]);  tdly #(1, DD + (NF == 2 ? XL : 0.0)) u_e1 (eb0, e_[1]);
        tdly #(1, CD + (NF == 2 ? XL : 0.0)) u_c1 (cko0, c_[1]);
        for (j = 1; j < NF - 1; j = j + 1) begin : g_st
          wire [W-1:0] bj; wire ebj, ckoj;
          qfd_rlyh_16_EW_65x30 u_s (.ckf(c_[j]), .ea(e_[j]), .a(d[j]), .b(bj), .eb(ebj), .ck_o(ckoj));
          tdly #(W, DD + (j == NF - 2 ? XL : 0.0)) u_d (bj, d[j + 1]);  tdly #(1, DD + (j == NF - 2 ? XL : 0.0)) u_e (ebj, e_[j + 1]);
          tdly #(1, CD + (j == NF - 2 ? XL : 0.0)) u_c (ckoj, c_[j + 1]);
        end
        qfd_landh_16_EW_65x30 u_l (.ckf(c_[NF - 1]), .ea(e_[NF - 1]), .a(d[NF - 1]), .ck(ckd), .rs(rs), .k0(kk[0]), .k1(kk[1]),
                                   .k2(kk[2]), .tie_hi(hi), .tie_lo(lo), .b(o), .fault(flt));
      end
    endgenerate
`ifdef OT_QFD_LAND_GATED_BANKS
    wire [3:0] observed_w, observed_r;
    wire observed_we;
    generate if (NF == 1) begin : g_watch1
        assign observed_w=g1.u_l.u_land.u_gated.wbank_clk;
        assign observed_r=g1.u_l.u_land.u_gated.rbank_clk;
        assign observed_we=g1.u_l.u_land.u_gated.meta_we;
    end else begin : g_watchn
        assign observed_w=gn.u_l.u_land.u_gated.wbank_clk;
        assign observed_r=gn.u_l.u_land.u_gated.rbank_clk;
        assign observed_we=gn.u_l.u_land.u_gated.meta_we;
    end endgenerate
    bank_window_monitor u_window(.w(observed_w),.r(observed_r),.we(observed_we),.rs(rs),.k(kk));
`endif
    integer td = 0;
    initial begin
        err = 0; chk = 0;
        // ring write of w(e): source edge e + 1 (hop 0, full cycle) + (NF-1)/2 periods + the clock legs of the NF-1
        // forwarded hops (+ XL)
        lag = (NF - 1) * CD + XL;
        L = $rtoi($ceil(((NF + 1) * T / 2.0 + lag - DOFF) / T + 0.25)) + LADD;
        K = ((L - 1 - ((R0 + RREG) - (G + HREG))) % 8 + 8) % 8;
        if (KFROM >= 0) K = KFROM;
        $display("FWD_LANE NF=%0d CD=%0.2f XL=%0.2f DOFF=%0.2f G=%0d R0=%0d L=%0d K=%0d", NF, CD, XL, DOFF, G, R0, L, K);
    end
    integer te_;
    reg [W-1:0] ex_;
    integer epoch_add, first_ready, first_output, warm_set, ready_set;
    real full_time;
    always @(negedge ckd) begin
        // o after receiver edge ed - 1 (sampled half a period later): w(ed - 1 - L) once that word was written, else 0
        te_ = ed;
        te_ = te_ - 1 - L - RPIPE;
        ex_ = (te_ >= G + HREG) ? w_of(te_) : {W{1'b0}};
`ifdef OT_QFD_LAND_GATED_BANKS
        // Independent golden prologue: write of first epoch at source(G+HREG)
        // plus physical lane travel; four writes fill the ring. First read-root
        // edge STRICTLY after the fourth write starts two-stage ready release;
        // then one read-bank edge and one output edge. Boot repeats at+320T,
        // preserving static modulo8 straps while testing asynchronous abort/restart.
        epoch_add=(ed-1 > 300)?320:0;
        full_time=(G+HREG+epoch_add)*T+(NF+1)*T/2.0+lag+3*T;
        first_ready=$rtoi($floor((full_time-DOFF)/T))+1;
        ready_set=first_ready+1;
        warm_set=R0+epoch_add+RREG+((K==0)?8:K);
        first_output=((ready_set>warm_set)?ready_set:warm_set)+2;
        if ((ed-1>300 && ed-1<R0+320) || ed-1<first_output)
            ex_={W{1'b0}};
        if (ed>0) begin
`else
        if (ed > R0 + RREG + RPIPE + 10) begin
`endif
            chk = chk + 1;
            if (o !== ex_) begin
                err = err + 1;
                if (err < 4) $display("FWD_LANE MISMATCH %m NF=%0d ed=%0d o=%h exp=%h", NF, ed, o, ex_);
            end
        end
    end
endmodule

`ifdef OT_QFD_LAND_GATED_BANKS
module bank_window_monitor(input wire [3:0] w,r,input wire we,rs,input wire[2:0]k);
    genvar b;
    generate for(b=0;b<4;b=b+1) begin:g
        real last_w=-1.0,last_r=-1.0,age,min_age=1e9,max_age=-1.0,min_hold=1e9;
        real first_w=-1.0,first_r=-1.0,wrise=-1.0,rrise=-1.0;
        integer checks=0,phase_case;
        real phase_residual;
        always @(negedge w[b]) if(wrise>=0 && (($realtime-wrise<4.9999)||($realtime-wrise>5.0001))) begin
            $display("FWD_BENCH FAIL writepulse %m width=%f",$realtime-wrise);$fatal(1);
        end
        always @(negedge r[b]) if(rrise>=0 && (($realtime-rrise<4.9999)||($realtime-rrise>5.0001))) begin
            $display("FWD_BENCH FAIL readpulse %m width=%f",$realtime-rrise);$fatal(1);
        end
        always @(posedge w[b] or negedge we) begin
            if(!we) last_w=-1.0;
            else begin
                if(last_w>=0 && (($realtime-last_w<39.9999)||($realtime-last_w>40.0001))) begin
                    $display("FWD_BENCH FAIL nonperiod4 write %m delta=%f",$realtime-last_w);$fatal(1);
                end
                last_w=$realtime;wrise=$realtime;if(first_w<0)first_w=$realtime;
            end
        end
        always @(posedge r[b] or negedge we or negedge rs) begin
            if(!we||!rs) last_r=-1.0;
            else begin
                age=$realtime-last_w;
                if(last_w<0 || age<2.4999 || age>32.5001 || 40.0-age<7.4999) begin
                    $display("FWD_BENCH FAIL bankwindow %m K=%0d age=%f hold=%f",k,age,40.0-age);$fatal(1);
                end
                if(last_r>=0 && (($realtime-last_r<39.9999)||($realtime-last_r>40.0001))) begin
                    $display("FWD_BENCH FAIL nonperiod4 read %m delta=%f",$realtime-last_r);$fatal(1);
                end
                last_r=$realtime;rrise=$realtime;if(first_r<0)first_r=$realtime;checks=checks+1;
                if(age<min_age)min_age=age;if(age>max_age)max_age=age;if(40.0-age<min_hold)min_hold=40.0-age;
            end
        end
        final begin
            phase_case=$rtoi($ceil(min_age/10.0-0.25));if(phase_case<1)phase_case=1;if(phase_case>3)phase_case=3;
            phase_residual=min_age/10.0-phase_case;
            $display("GATED_BANK_WINDOW %m K=%0d checks=%0d min_age_T=%f max_age_T=%f min_overwrite_gap_T=%f E_case=%0d phase_residual_T=%f first_w_ns=%f first_r_ns=%f",k,checks,min_age/10.0,max_age/10.0,min_hold/10.0,phase_case,phase_residual,first_w,first_r);
        end
    end endgenerate
endmodule
`endif

`ifdef OT_QFD_LAND_PHASE_SWEEP
module gated_phase_case #(parameter integer P=0, KK=0, EXTRA=0, ORDER=0)(
    input wire cks,input wire[31:0]es,output integer err,chk,output wire flt);
    localparam real PH=P*1.25;
    localparam integer EB=(P<2?1:0)+EXTRA;
    localparam integer GG=16, RR=GG+EB-KK+(ORDER?16:-8);
    reg ckd=0;reg[31:0]ed=0;
    initial begin #(PH);forever #5 ckd=~ckd;end
    always @(posedge ckd)ed<=ed+1;
    lane #(.W(1),.NF(1),.CD(0),.DOFF(PH),.G(GG),.R0(RR),.LADD(EXTRA))
        u_lane(cks,ckd,es,ed,err,chk,flt);
endmodule
`endif

module tb;
    reg cks = 0, ckd = 0;
    reg [31:0] es = 0, ed = 0;
    always #5 cks = ~cks;
    initial begin #2.0; forever #5 ckd = ~ckd; end                     // receiver root 2.0 ns after the source root
    always @(posedge cks) es <= es + 1;
    always @(posedge ckd) ed <= ed + 1;
    integer e [0:11], c [0:11]; wire f [0:11];
    lane #(.NF(1),  .CD(0.0), .G(10), .R0(12))               l0 (cks, ckd, es, ed, e[0], c[0], f[0]);
    lane #(.NF(2),  .CD(3.6), .G(10), .R0(12))               l1 (cks, ckd, es, ed, e[1], c[1], f[1]);
    lane #(.NF(5),  .CD(3.6), .G(10), .R0(12), .LADD(2), .KFROM(-1)) l2 (cks, ckd, es, ed, e[2], c[2], f[2]);
    // the window lane: lane l2's K (same strap), 2 T more clock lag on the last hop -> the SAME latency L
    lane #(.NF(5),  .CD(3.6), .XL(20.0), .G(10), .R0(12), .LADD(0), .KFROM(-2)) l3 (cks, ckd, es, ed, e[3], c[3], f[3]);
    lane #(.NF(5),  .CD(4.4), .G(40), .R0(9), .LADD(2))      l4 (cks, ckd, es, ed, e[4], c[4], f[4]);   // source releases LATE (read 2.9 T behind)
    lane #(.NF(5),  .CD(4.4), .G(9),  .R0(45))               l5 (cks, ckd, es, ed, e[5], c[5], f[5]);   // receiver releases LATE
    lane #(.NF(8),  .CD(4.0), .DD(0.4), .G(10), .R0(14))     l6 (cks, ckd, es, ed, e[6], c[6], f[6]);
    lane #(.NF(27), .CD(4.5), .DD(2.0), .G(12), .R0(11))     l7 (cks, ckd, es, ed, e[7], c[7], f[7]);
    lane #(.NF(1),  .CD(0.0), .G(40), .R0(9))                l8 (cks, ckd, es, ed, e[8], c[8], f[8]);   // n = 1, source releases LATE
    lane #(.NF(1),  .CD(0.0), .G(9),  .R0(45))               l9 (cks, ckd, es, ed, e[9], c[9], f[9]);   // n = 1, receiver releases LATE
    lane #(.NF(1), .CD(0.0), .G(12), .R0(12)) l10 (cks, ckd, es, ed, e[10], c[10], f[10]);
    lane #(.NF(1), .CD(0.0), .G(9), .R0(12)) l11 (cks, ckd, es, ed, e[11], c[11], f[11]);
`ifdef OT_QFD_LAND_PHASE_SWEEP
    integer ep[0:255],cp[0:255];wire fp[0:255];
    genvar v;
    generate for(v=0;v<256;v=v+1)begin:g_phase
        gated_phase_case #(.P((v/8)%8),.KK(v%8),.EXTRA(2*((v/64)%2)),.ORDER(v/128))
            u_case(cks,es,ep[v],cp[v],fp[v]);
    end endgenerate
`endif
    initial begin
        #0.1; l3.K = l2.K; l3.L = l2.L;                                 // the window lane reuses lane 2's strap
        #6000;
        begin : sum
            integer i, te, tc, tf;
            te = 0; tc = 0; tf = 0;
            for (i = 0; i < 12; i = i + 1) begin te = te + e[i]; tc = tc + c[i]; tf = tf + (f[i] === 1'b1 ? 1 : 0);
                if (f[i] !== 1'b0) $display("FWD_LANE FAULT lane %0d", i); end
`ifdef OT_QFD_LAND_PHASE_SWEEP
            for(i=0;i<256;i=i+1)begin te=te+ep[i];tc=tc+cp[i];tf=tf+((fp[i] === 1'b1) ? 1 : 0);end
`endif
            if (l3.L != l2.L) te = te + 1;
            $display("FWD_BENCH %s %0d errors in %0d checks (faults %0d)", (te || tf || tc < 4000) ? "FAIL" : "PASS", te + tf, tc, tf);
        end
        $finish;
    end
endmodule
EOT
sed -i "s/_16_EW_65x30/_${W}_EW_65x30/g; s/parameter integer W = 16/parameter integer W = ${W}/" "$O/tb.sv"
verilator --binary --timing -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-COMBDLY -Wno-LATCH -Wno-INITIALDLY --top-module tb $DEF \
  -Mdir "$O/obj" -o tb "$O/tb.sv" "$O/wrappers.sv" rtl/qwen_split/qfd_fwd_lane.sv rtl/hdc/ot_hdc_cg.sv > "$O/build.log" 2>&1 || {
  echo BUILD_FAILED; tail -20 "$O/build.log"; exit 2; }
"$O/obj/tb" | tee "$O/bench.log" | grep -E 'FWD_BENCH|FWD_LANE (NF|FAULT)|GATED_BANK_WINDOW'
grep -q 'FWD_BENCH PASS' "$O/bench.log"

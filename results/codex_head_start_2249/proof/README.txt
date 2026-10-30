Actual D4 CAS receiver-only START delay proof candidate, 2026-10-29 23:03 PDT.
Unmodified actual ot_dp_clk_landing_cas/ot_meso_ring_ca, W32,D4,ARM12,
strapK width6, plus uniform R=1/2 receiver START relay chain. Writers and all
other signals unchanged. Candidate K=(oldK-R)mod64; control retains wrongK.
4572 cases (K=-63..63, R1/2,18 lag/phase cuts incl coincident edges +/-1ps),
438430 steady comparisons,0 mismatch,wrongK control CAUGHT4572/4572.
2794 baseline-ready cases; other1778 invalid cases both fault by end (checked).
Finite startup assertions: q/rv/lap/guards equal by R+2 cycles; ready/fault
in valid cases equal by R+ARM+2 cycles (R2=16 vs original ARM+2=14).
Observed last differences data3/status15. Steady data cycles0; +R boot bound.
This is a mechanism simulation proof, not physical or sign-off evidence.
Production relay raw resets must release early enough to flush the local
monotonic START tree before its first rising START, under the existing root
SETTLE contract. Physical sites/hops/raw source contracts require plan gating.
Run intel2:/srv/opentallas-scratch2/claude/codex-head-start-2249/ring3.sh.

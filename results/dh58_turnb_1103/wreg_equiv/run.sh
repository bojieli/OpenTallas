#!/bin/bash
# DH58-TURNB WREG-1/DSREP-1 equivalence bench (verilator 5.032). PASS = A(WREG=1,DSREP=4,K) == B(plain ring behind one
# t_rst_n flop, K) on every clk edge, and A == C(plain ring, raw t_rst_n, K-1) whenever ready. Mutant: +define+OT_MESO_CA_MUTANT_WREG.
# WFALL form (hd_turn_a/b writer on ~fclk): add +define+TB_WFALL (MUT="+define+TB_WFALL +define+OT_MESO_CA_MUTANT_WREG" for the mutant); run with +seed=N +n=400.
R=$(cd "$(dirname "$0")/../../.." && pwd)
docker run --rm --memory=8g --cpus=4 -v $R:/r -w /r/results/dh58_turnb_1103/wreg_equiv verilator/verilator:v5.032 --binary --timing -Wno-fatal -Wno-lint -Wno-style ${MUT:+$MUT} --top-module tb -o tbx tb_wreg_equiv.sv /r/rtl/common/ot_dp_clk_landing_ca.sv /r/rtl/common/ot_meso_fifo.sv /r/rtl/common/ot_dp_clk_landing.sv

#!/bin/bash
# TOK-FUNC-QW stage "ctx4u" (10-21): MU context real-link transport (4 users' context records host -> KV host record port
# -> D2D static link -> compute qfd_mu_ctx_rx), on the RTL-only SOURCE ASSEMBLY (RUNROOT/src), Verilator 5.050.
#
#   stage_ctx4u.sh RUNROOT [--die-netlist DIR]
#
# Bench = existing rtl/test/qwen_split/run_mu_context_real_link.sh + mu_context_real_link_sources.f + tb_mu_context_real_link.sv
# (c92c2be9d / tb f8f2d2f9a, branch codex/qw-token-pickup-takeover3-1019; bench files only, RUNROOT/ctx4u/fx), every RTL
# source in the .f from the assembly except the UCIe PHY model (modelled leg) and the SRAM behavioural model.
# Configs: 0 (PASS: every context word delivered = the SU host reference, slot/host/wire/load cycles), 1..5 (causal mutants,
# FAIL), full (whole-stream diagnostic: must end in MUCTX_FULL_STREAM_DIAGNOSTIC_NATIVE_FAULT = the documented unsupported
# later-producer scope, as on 10-19).  Cycles (stage_link.collect.py ctx4u): slot->HOST_TX, HOST_TX->WIRE, WIRE->LOAD,
# slot->load, token-period spacing.
#
# --die-netlist DIR: not applicable (pure link transport RTL; the KV host record port / compute ctx rx are hard tiles whose
#   netlists are proven by their own LEC); with DIR/ctx_sources.f the listed netlist files replace the .f (grade die-netlist).
set -u
RUNROOT=$(readlink -f "$1"); shift
NET=""
while [ $# -gt 0 ]; do case "$1" in --die-netlist) NET=$(readlink -f "$2"); shift 2;; *) echo "bad arg $1"; exit 2;; esac; done
SRC=$RUNROOT/src; S=$RUNROOT/ctx4u; FX=$S/fx; T=$S/tree; HERE=$(dirname "$(readlink -f "$0")")
export VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
$VERILATOR --version | grep -q '5.050' || { echo "need Verilator 5.050"; exit 2; }
[ -f "$FX/rtl/test/qwen_split/tb_mu_context_real_link.sv" ] || { echo "missing fixtures (stage_link_fixtures.sh)"; exit 2; }
GRADE="RTL-functional (source assembly)"
rm -rf "$T" "$S/runs"; mkdir -p "$T/physical" "$S/runs"
for d in rtl configs; do cp -as "$SRC/$d" "$T/"; done
cp -as "$SRC/physical/." "$T/physical/"; cp -as "$FX/physical/." "$T/physical/"
for f in rtl/test/qwen_split/run_mu_context_real_link.sh rtl/test/qwen_split/mu_context_real_link_sources.f rtl/test/qwen_split/tb_mu_context_real_link.sv; do
  rm -f "$T/$f"; cp "$FX/$f" "$T/$f"; done
if [ -n "$NET" ] && [ -f "$NET/ctx_sources.f" ]; then cp "$NET/ctx_sources.f" "$T/rtl/test/qwen_split/mu_context_real_link_sources.f"; GRADE="die-netlist"; fi
cd "$T" || exit 3
R=$S/runs
for s in 0 1 2 3 4 5 full; do
  ( bash rtl/test/qwen_split/run_mu_context_real_link.sh $R/c$s $s > $R/c$s.out 2>&1; echo "rc=$?" >> $R/c$s.out ) &
done
wait
for s in 0 1 2 3 4 5 full; do rm -rf $R/c$s/*/obj; echo "==== $s"; cat $R/c$s.out; done
python3 "$HERE/stage_link.collect.py" ctx4u "$RUNROOT" --grade "$GRADE"

#!/bin/bash
# DIE-KV-26: KV die reset contract bench (iverilog). usage: bench_kv_reset.sh OUTDIR MUT   (MUT 0 positive, 1/2 mutants)
set -eu; D=$(cd "$(dirname "$0")" && pwd); O=$1; M=$2; mkdir -p "$O"
iverilog -g2012 -P tb_kv_reset_contract.MUT=$M -o "$O/tb_$M" "$D/tb_kv_reset_contract.sv" "$D/bind26b_cells.sv"
vvp -n "$O/tb_$M" | grep -E "KVRST|FATAL" | head -n 12

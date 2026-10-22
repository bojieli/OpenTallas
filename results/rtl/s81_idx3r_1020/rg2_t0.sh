#!/bin/bash
# S81-IDX3R: T0 sweep of the RECORD in-line reader (L20RD3 b3 binary, unchanged) for the rg3 latency comparison
B=/srv/opentallas-scratch/claude/s81-l20rd3-1020/out/b3/obj/Vtb_dsdv_idx_rg2; O=/srv/opentallas-scratch/claude/s81-l20rd3-1020/out/idx3r_t0; mkdir -p $O
for c in "s220|+N=4096 +B=13 +T0=220 +P=3" "s240|+N=4096 +B=13 +T0=240 +P=3" "s260|+N=4096 +B=13 +T0=260 +P=3" "s280|+N=4096 +B=13 +T0=280 +P=3" "s300|+N=4096 +B=13 +T0=300 +P=3" "s340|+N=4096 +B=13 +T0=340 +P=3" "s200|+N=4096 +B=13 +T0=200 +P=3" \
         "g500|+GATHER=1 +N=2048 +T0=500 +P=4" "g600|+GATHER=1 +N=2048 +T0=600 +P=4" "g700|+GATHER=1 +N=2048 +T0=700 +P=4" "g800|+GATHER=1 +N=2048 +T0=800 +P=4" "g900|+GATHER=1 +N=2048 +T0=900 +P=4"; do
  n=${c%%|*}; a=${c#*|}; ( $B $a > $O/$n.log 2>&1; echo "RG2_T0 $n: $(grep -E '^TB_IDXRD (PASS|FAIL)$' $O/$n.log) | $(grep TB_IDXRD_STATS $O/$n.log)" ) &
done; wait

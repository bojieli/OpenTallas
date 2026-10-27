#!/bin/bash
# TOK-QK-KVL 10-27: launch the per-layer KV attention sims (B48 KV die + real compute far end), one ot-run unit each.
#   8 nominal heads (d0..3 x g0..1 = the 8 TP8 KV dies' heads, all 36 layers each, full token POST 300000)
#   4 negative controls on head d0_g0, layers 0..2 (POST 40000): m1 CMD late, m3 K-row swap in phy_WS_0, m4 q of layer n^1,
#   m5 HBM history of layers 0 / 1 swapped.  Each must FAIL its layers (m5: L0, L1 FAIL, L2 PASS).
#   launch_all.sh MEM HOSTS   (HOSTS for ot-run, e.g. localhost)
set -u
K=/srv/opentallas-scratch2/claude/tok-qk-kvl; B=$K/build/obj/Vtb_kvslice; MEM=$1; HO=$2
mkdir -p $K/runs $K/client
go() { local n=$1; shift; cd $K/client; nohup ~/.local/bin/ot-run --mem $MEM --threads 1 --dir $K --hosts $HO -- env "$@" > $K/runs/$n.otrun.log 2>&1 < /dev/null & }
for d in 0 1 2 3; do for g in 0 1; do h=d${d}_g${g}
  go nom_$h POST=300000 $K/run_kvl.sh $B $K/vec $K/runs nom_$h $h; done; done
go m1_cmdlate POST=40000 $K/run_kvl.sh $B $K/vec $K/runs m1_cmdlate d0_g0 +MUT_CMD_LATE
go m3_kswap POST=40000 MUT_KSWAP=phy_WS_0 $K/run_kvl.sh $B $K/vec $K/runs m3_kswap d0_g0
go m4_qswap POST=40000 $K/run_kvl.sh $B $K/vec $K/runs m4_qswap d0_g0 +MUT_QSWAP
go m5_l01 POST=40000 MUT_L01=1 $K/run_kvl.sh $B $K/vec $K/runs m5_l01 d0_g0
sleep 30; grep -h admitted $K/runs/*.otrun.log

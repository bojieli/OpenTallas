#!/bin/bash
# MU-DQ-TXDP 10-19 (COORD 0ki): paired compute<->KV D2D co-sim on the MU release seams with the TXDPs the GENs now bind:
# the committed pair image rtl/qwen_sys/d2d_static_20261015/d2d_cal_image.svh (D2D_TXDP_C -> die_params.gen_params,
# D2D_TXDP_K -> kv_static.d2d_txdp_k).  Compute seam = record_bundles.py seam-stages of the compute GEN's die.v (CDIE,
# default dv2f18mu); KV seam = kvs14r-mu BUNDLE_EQ (K.rx_record 11, K.tx_slot 9, K.tx_record 9; die NTX 3).
#   xdie_txdp_job.sh W [CDIE]   (repository root = W/src; fleet, Verilator 5.050)
set -u
W=$1; CDIE=${2:-/srv/opentallas-scratch/claude/mu-die-qw/dv2f18mu/out/case/die.v}; cd $W/src
IMG=rtl/qwen_sys/d2d_static_20261015/d2d_cal_image.svh
CS=$(python3 tools/qwen_split/record_bundles.py seam-stages "$CDIE" --out $W/seam_stages.json) || { echo "XDIE_TXDP seam-stages FAIL"; exit 1; }
KS=11,11,9,9,9,9,9
ports() { python3 -c "import re,sys;v=int(re.search(r\"$1 = 32'h([0-9a-f]+)\",open('$IMG').read()).group(1),16);print(','.join(str((v>>8*p)&255) for p in range(4)))"; }
TC=$(ports D2D_TXDP_C); TK=$(ports D2D_TXDP_K)
IST=$(grep -o "die stages {[^}]*}" $IMG)
echo "XDIE_TXDP compute seam $CS (from $CDIE) | KV seam $KS | image TXDP C [$TC] K [$TK] | image $IST"
python3 - "$CS" "$KS" "$TC" "$TK" <<'PY' || { echo "XDIE_TXDP image is not the compile of this seam"; exit 1; }
import sys; sys.path.insert(0, 'tools/qwen_split'); import d2d_link_calendar as L
cs, ks, tc, tk = sys.argv[1:5]
t = L.producer_txd(L.parse_stages(cs + '/' + ks))
want = {e: [x + p for x, p in zip(t[e], L.PINREG_EXT[e])] for e in t}
got = {'C': [int(x) for x in tc.split(',')], 'K': [int(x) for x in tk.split(',')]}
print('XDIE_TXDP compiled', want, 'image', got); sys.exit(0 if want == got else 1)
PY
export XQ_PLAN=$CS/$KS XQ_G=-GK_NTX=3 JOBS=4
C1=$(echo $TC | awk -F, '{print $1+1","$2","$3","$4}')
export XQ_TXDP_OFF1=$C1/$TK
# PASS set + mutants: image TXDPs bound (pair_gen_txdp PASS); compute off-by-one; the OLD GEN bindings (compute 0x09010308,
# KV 0x03030418) each alone FAIL
( XQ_GEN_TXDP=$TC/$TK XQ_GEN_TXDP_EXPECT=PASS bash rtl/test/qwen_split/run_xdie_exchange.sh $W/pair_img \
   pair pair_t8192 pair_phy9 pair_l0 pair_l0_phy9 pair_gen_txdp pair_mut_txdp_c_off1 pair_mut_kseam_rx_torn \
   pair_mut_kseam_tx_torn pair_mut_status_done pair_mut_result_bit pair_mut_phy_bit > $W/pair_img.out 2>&1 ) &
( XQ_GEN_TXDP=8,3,1,9/$TK XQ_GEN_TXDP_EXPECT=FAIL bash rtl/test/qwen_split/run_xdie_exchange.sh $W/mut_c_old pair_gen_txdp > $W/mut_c_old.out 2>&1 ) &
( XQ_GEN_TXDP=$TC/24,4,3,3 XQ_GEN_TXDP_EXPECT=FAIL bash rtl/test/qwen_split/run_xdie_exchange.sh $W/mut_k_old pair_gen_txdp > $W/mut_k_old.out 2>&1 ) &
wait
grep -h -E 'expect=' $W/pair_img.out $W/mut_c_old.out $W/mut_k_old.out
if grep -q UNEXPECTED $W/pair_img.out $W/mut_c_old.out $W/mut_k_old.out; then echo XDIE_TXDP_FAIL; else echo XDIE_TXDP_PASS; fi

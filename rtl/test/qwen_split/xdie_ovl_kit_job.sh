#!/bin/bash
# SAFE-QW-D2D 10-19: paired compute<->KV D2D co-sim with the compute end = the MU re-close kit master
# qfd_d2d_static_ovl (OVL 1, RC 1 equal-depth reset copies) at the bound TXDP of the committed pair image
# (D2D_TXDP_C 0x0a010308 [8,3,1,10] / D2D_TXDP_K 0x03030415 [21,4,3,3]); the image's own die-stage record is the seam
# (CS 2,2,2,3,2,2 = dv2f18 MU seam, KS 11,11,9,9,9,9,9 = kvs14r-mu).  RX calendar started with the TX one (user 0):
# the OVL master must then reproduce the as-built pair bit-exactly.  Also re-runs the as-built master (C_OVL 0, RC 0)
# 'pair' so the restructured reset fan-out (NRC 1) is shown unchanged.
#   xdie_ovl_kit_job.sh W   (repository root = W/src; fleet, Verilator 5.050).  Last line XDIE_OVL_KIT_PASS | _FAIL.
set -u
W=$1; cd $W/src
IMG=rtl/qwen_sys/d2d_static_20261015/d2d_cal_image.svh
CS=2,2,2,3,2,2; KS=11,11,9,9,9,9,9
ports() { python3 -c "import re,sys;v=int(re.search(r\"$1 = 32'h([0-9a-f]+)\",open('$IMG').read()).group(1),16);print(','.join(str((v>>8*p)&255) for p in range(4)))"; }
TC=$(ports D2D_TXDP_C); TK=$(ports D2D_TXDP_K)
echo "XDIE_OVL_KIT seam $CS/$KS | image TXDP C [$TC] K [$TK] | $(grep -o "die stages {[^}]*}" $IMG)"
python3 - "$CS" "$KS" "$TC" "$TK" <<'PY' || { echo "XDIE_OVL_KIT image is not the compile of this seam"; echo XDIE_OVL_KIT_FAIL; exit 1; }
import sys; sys.path.insert(0, 'tools/qwen_split'); import d2d_link_calendar as L
cs, ks, tc, tk = sys.argv[1:5]
t = L.producer_txd(L.parse_stages(cs + '/' + ks))
want = {e: [x + p for x, p in zip(t[e], L.PINREG_EXT[e])] for e in t}
got = {'C': [int(x) for x in tc.split(',')], 'K': [int(x) for x in tk.split(',')]}
print('XDIE_OVL_KIT compiled', want, 'image', got); sys.exit(0 if want == got else 1)
PY
export XQ_PLAN=$CS/$KS JOBS=4
export XQ_TXDP_OFF1=$(echo $TC | awk -F, '{print $1+1","$2","$3","$4}')/$TK
( XQ_G="-GK_NTX=3 -GC_OVL=1" XQ_GEN_TXDP=$TC/$TK XQ_GEN_TXDP_EXPECT=PASS bash rtl/test/qwen_split/run_xdie_exchange.sh $W/ovl \
   pair pair_t8192 pair_phy9 pair_l0 pair_gen_txdp pair_mut_txdp_c_off1 pair_mut_status_done pair_mut_result_bit \
   pair_mut_phy_bit pair_mut_kseam_rx_torn > $W/ovl.out 2>&1 ) &
( XQ_G="-GK_NTX=3 -GC_OVL=1" XQ_GEN_TXDP=8,3,1,9/$TK XQ_GEN_TXDP_EXPECT=FAIL bash rtl/test/qwen_split/run_xdie_exchange.sh $W/ovl_mut_c_old pair_gen_txdp > $W/ovl_mut_c_old.out 2>&1 ) &
( XQ_G="-GK_NTX=3 -GC_OVL=0" XQ_GEN_TXDP=$TC/$TK XQ_GEN_TXDP_EXPECT=PASS bash rtl/test/qwen_split/run_xdie_exchange.sh $W/asbuilt pair pair_gen_txdp > $W/asbuilt.out 2>&1 ) &
wait
grep -h -E 'expect=' $W/ovl.out $W/ovl_mut_c_old.out $W/asbuilt.out
if grep -q UNEXPECTED $W/ovl.out $W/ovl_mut_c_old.out $W/asbuilt.out || [ "$(grep -h -c 'expect=' $W/ovl.out $W/ovl_mut_c_old.out $W/asbuilt.out | awk "{s+=\$1} END{print s}")" != 13 ]; then
  echo XDIE_OVL_KIT_FAIL; exit 1; fi
echo XDIE_OVL_KIT_PASS

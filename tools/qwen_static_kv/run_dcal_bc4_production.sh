#!/bin/bash
# run_dcal_bc4_production.sh OUT [MUT] (KV-DCAL 10-19: bc4 = safe K22 tile; derived from run_dcal_bootcfg.sh)
# run_dcal_bootcfg.sh OUT [MUT] (KV-DCAL-BOOTCFG 2026-10-19): boot image target 11 -> qkd_d2d_cal_seq_pin_bc -> real
# ot_qwen_d2d_cal TX/RX pair, against the MU pin tile qkd_d2d_cal_seq_pin on its own pair (tb_kv_dcal_bootcfg.sv).
#   target 11 = the 66 link cfg words in the calendar sequencer's init order (TX i, RX i, then the TX / RX segment-1 bases
#   = SEG2), from d2d_cal_image_mu.svh (MUT 2: from the production d2d_cal_image.svh = a stale non-MU boot image).  The same
#   layout as kv_static_programme.link_cfg_words on the MU calendar compile (KV-LINKCFG-MU makes target 11 compile it);
#   with CAL=<calendar dir> the script also requires link_cfg_words(CAL) == these words.
#   MUT 0 must PASS (DCALBC_PASS); 1 sequencer writes dropped, 2 stale image, 3 collision, 4 boot write while running,
#   5 boot RX base masked: must FAIL (DCALBC_FAIL).  Verilator 5.050 (the closure daemon's), VERILATOR overrides.
set -uo pipefail
O=$(realpath -m "$1"); MUT=${2:-0}; mkdir -p "$O"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=rtl/qwen_sys/d2d_static_20261015; S=rtl/qwen_sys/static_kv_20261014
IMG=$D/d2d_cal_image_mu.svh; [ "$MUT" = 2 ] && IMG=$D/d2d_cal_image.svh
"$VL" --version
# KV-DCAL 10-19: the tile is generated only on the coherent codec2 K22 image (gen_dcal_bc4.py refuses others)
grep -q "localparam \[31:0\] D2D_TXDP_K = 32'h03030416;" $D/d2d_cal_image_mu.svh || { echo "DCALBC_FAIL image not codec2 K22"; exit 1; }
echo "image K22: $(sha256sum $D/d2d_cal_image_mu.svh)"
python3 - "$IMG" "$O/target11.hex" "${CAL:-}" <<'EOF' || { echo "DCALBC_FAIL image"; exit 1; }
import re, sys
txt = open(sys.argv[1]).read()
def lp(n):
    return int(re.search(r'localparam \[[^\]]*\] ' + n + r" = \d+'h([0-9a-f]+);", txt).group(1), 16)
tx, rx = lp('D2D_CAL_K_TX_IMG'), lp('D2D_CAL_K_RX_IMG')
m = (1 << 32) - 1
w = [x for i in range(32) for x in ((tx >> 32 * i) & m, (rx >> 32 * i) & m)] + [lp('D2D_CAL_K_TX_SEG2'), lp('D2D_CAL_K_RX_SEG2')]
assert len(w) == 66
if sys.argv[3]:
    sys.path.insert(0, 'tools/qwen_kv_die')
    import kv_static_programme as P
    if P.link_cfg_words(sys.argv[3]) != w:
        print('link_cfg_words(CAL) != the image words'); sys.exit(1)
    print('link_cfg_words(CAL) == image words')
open(sys.argv[2], 'w').write(''.join(f'{x:016x}\n' for x in w))
print(f'target11: {sys.argv[1]} SEG2 TX {w[64]} RX {w[65]}')
EOF
sha256sum $D/qkd_d2d_cal_seq_bc4.sv $D/ot_qwen_d2d_cal_seq_bc4.sv $D/qkd_d2d_cal_seq_pin.sv $D/ot_qwen_d2d_cal_seq.sv $D/ot_qwen_d2d_cal_seq_dies_mu.sv \
  $D/d2d_cal_image_mu.svh $D/d2d_cal_image.svh $D/ot_qwen_d2d_static.sv $S/qkd_static_kv_boot_dispatch.sv \
  rtl/test/qwen_static_kv/tb_kv_dcal_bc4.sv > "$O/source.sha256"
"$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING -Wno-TIMESCALEMOD -Wno-VARHIDDEN \
  -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-BLKSEQ -Wno-INITIALDLY -j 4 -I$D --top-module tb_kv_dcal_bootcfg -GMUT=$MUT \
  --Mdir "$O/obj" $S/qkd_static_kv_boot_dispatch.sv $D/ot_qwen_d2d_cal_seq.sv $D/ot_qwen_d2d_cal_seq_dies_mu.sv \
  $D/qkd_d2d_cal_seq_pin.sv $D/qkd_d2d_cal_seq_bc4.sv $D/ot_qwen_d2d_cal_seq_bc4.sv $D/ot_qwen_d2d_static.sv rtl/test/qwen_static_kv/tb_kv_dcal_bc4.sv \
  > "$O/build.log" 2>&1 || { tail -30 "$O/build.log"; echo "DCALBC_FAIL build"; exit 1; }
(cd "$O" && ./obj/Vtb_kv_dcal_bootcfg) > "$O/run.log" 2>&1; rc=$?
cat "$O/run.log"
if [ $rc = 0 ] && grep -q '^PASS kv_dcal_bootcfg' "$O/run.log"; then echo "DCALBC_PASS mut$MUT"; exit 0; fi
echo "DCALBC_FAIL mut$MUT: $(grep -m1 '^BAD' "$O/run.log")"; exit 1

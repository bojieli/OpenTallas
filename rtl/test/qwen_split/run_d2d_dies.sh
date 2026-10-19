#!/bin/bash
# Q-LINK static D2D link DIE-NAME bench. Usage: run_d2d_static.sh OUT [MUT]   (LOCK=1 [LMUT=1|2]: S-QTIES QC-12 NTX=3 lockstep; KDLY=n: KV port-0 seam stages, KDLY=21 = die TXDP_K 0x03030418, KDLY=18 = MU 0x03030415; OVLM=1 [OMUT=1|2]: KV end = qkd_d2d_static_ovl; KSF=1: the KV ends are the safe fan-out masters *_sf; KSF=2 [SRAMV=1|2]: the right-sized-storage masters *_sfm)
set -eu
OUT=$1; MUT=${2:-0}
W=$(cd "$(dirname "$0")/../.." && pwd); R=$(cd "$W/.." && pwd)
TXL=${TXL:-6}; PHY=${PHY:-5}
mkdir -p "$OUT"
CTXL=$TXL; [ "$MUT" = 4 ] && CTXL=$((TXL-1))
python3 "$R/tools/qwen_split/d2d_link_calendar.py" --out "$OUT/cal" --txl "$CTXL" --phy "$PHY" --profile dies_token --txd-c 1,2,1,2 --txd-k $((1 + ${KDLY:-0})),2,1,1 $([ "${PR:-1}" = 1 ] && echo --pinreg) > "$OUT/calendar.log"
SRC=("$W/lib/ot_rst_pipe.sv" "$W/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv" "$W/qwen_sys/split_20261014/ot_qwen_static_slot_link.sv"
 "$W/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv" "$W/qwen_sys/split_20261014/qkd_native_attention_record.sv"
 "$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv" "$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_services.sv" "$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv" "$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies_ovl.sv" "$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_safe_fo.sv" "$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies_sfo.sv" "$W/qwen_split/qfd_kvn_static_transport.sv"
 "$R/physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv"
 "$R/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
 $([ "${KSF:-0}" = 2 ] && echo "$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_sfm.sv $R/physical/asap7_memory_macros_v2/d2d_sram_1r1w_64x137_m1_r2c2_p192/d2d_sram_1r1w_64x137_m1_r2c2_p192.v $R/physical/asap7_memory_macros_v2/d2d_sram_1r1w_64x137_m1_r2c2_p288/d2d_sram_1r1w_64x137_m1_r2c2_p288.v")
 "$W/test/qwen_split/tb_qwen_d2d_dies.sv")
sha256sum "${SRC[@]}" "$R/tools/qwen_split/d2d_link_calendar.py" > "$OUT/source.sha256"
iverilog -g2012 -I"$OUT/cal" -DOT_MEM_NO_INIT $([ "${OVLM:-0}" = 1 ] && echo -DOVLM) $([ "${KSF:-0}" = 1 ] && echo -DKSF) $([ "${KSF:-0}" = 2 ] && echo "-DKSFM -DKSFM_SRAMV=${SRAMV:-1}") -Ptb_qwen_d2d_dies.KRC=${KRC:-0} -Ptb_qwen_d2d_dies.OMUT=${OMUT:-0} -s tb_qwen_d2d_dies -Ptb_qwen_d2d_dies.MUT=$MUT -Ptb_qwen_d2d_dies.PR=${PR:-1} -Ptb_qwen_d2d_dies.TXL=$TXL -Ptb_qwen_d2d_dies.LOCK=${LOCK:-0} -Ptb_qwen_d2d_dies.LMUT=${LMUT:-0} -Ptb_qwen_d2d_dies.KDLY=${KDLY:-0} -Ptb_qwen_d2d_dies.P=$((110 + ${KDLY:-0})) \
 -Ptb_qwen_d2d_dies.PHY=$PHY -Ptb_qwen_d2d_dies.CALDIR=\"$OUT/cal\" -o "$OUT/tb.vvp" "${SRC[@]}" > "$OUT/build.log" 2>&1 || { head -30 "$OUT/build.log"; exit 2; }
vvp -n "$OUT/tb.vvp" > "$OUT/run.log" 2>&1 || true
grep -E "D2D_DIES_|D2D_OVL_|D2D_LOCK|RECOVERY|frames" "$OUT/run.log"
grep -h QKD_D2D_TXDP "$OUT/cal/txdp.svh" || true
grep -q '^D2D_DIES_PASS' "$OUT/run.log"

#!/bin/bash
# kv-die: measure every ASSUMED KV-die frame (review-0528 item 4).  run_all.sh <src tree> <out dir>
S=$1; O=$2; H=$(dirname $(readlink -f $0)); cd $S
N=rtl/hdc/nearhbm; K=rtl/qwen_sys/kv_die_20261009
FP="rtl/hdc/ot_hdc_sfu_q.sv $N/ot_qwen_nearhbm_sfu_p.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv"
$H/synth_area.sh $S $O astk_r8 ot_qwen_nearhbm_attn_stack_p ot_qwen_nearhbm_row_engine_p HD=128,R=8 $N/ot_qwen_nearhbm_attn_stack_p.sv $N/ot_qwen_nearhbm_prod.sv $FP &
$H/synth_area.sh $S $O reng ot_qwen_nearhbm_row_engine_p - HD=128,R=8 $N/ot_qwen_nearhbm_attn_stack_p.sv $N/ot_qwen_nearhbm_prod.sv $FP &
$H/synth_area.sh $S $O hub_p ot_qwen_nearhbm_attn_hub_p - HD=128 $N/ot_qwen_nearhbm_attn_hub_p.sv $FP &
$H/synth_area.sh $S $O kv_seq ot_qkvd_kv_seq - - $K/ot_qkvd_kv_seq.sv $K/ot_qkvd_cbridge.sv $K/ot_qkvd_fifo.sv &
$H/synth_area.sh $S $O kv_end ot_qkvd_kv_end - - $K/ot_qkvd_kv_end.sv $K/ot_qkvd_d2d.sv $K/ot_qkvd_fifo.sv &
$H/synth_area.sh $S $O rom_end ot_qkvd_rom_end - - $K/ot_qkvd_rom_end.sv $K/ot_qkvd_d2d.sv $K/ot_qkvd_fifo.sv &
$H/synth_area.sh $S $O kv_merge8 ot_qkvd_kv_merge - E=8 $K/ot_qkvd_kv_merge.sv $K/ot_qkvd_fifo.sv &
$H/synth_area.sh $S $O emb_gw ot_qfd_emb_gw - - rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_gw.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pkg.sv &
wait
grep -H "Chip area" $O/*.stat

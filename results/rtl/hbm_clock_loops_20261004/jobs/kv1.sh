#!/bin/bash
# KV lifecycle: original controller (2078c269c baseline, 458 MHz) vs HA4 successor, 0.833 ns SS 60 ps.
J=$(dirname $0)/screens.sh
FKV='fsm=(^|\.)(state|pc|beat|cstage|op|reader_count|sector_cursor|writer_live|commit_sent|drain_sent|receipt_visible|receipt_reverse|reader_live|sel_q|row_sel|snap|flag_q|adm)(\[|$)'
NEED=12 $J kv1 kvlife_orig --source rtl/model/qwen_kv_lifecycle_20261003/ot_gpu_qwen_kv_lifecycle_controller.sv --top ot_gpu_qwen_kv_lifecycle_controller --param ENABLE=1 --period-ns 0.833 --domain 1.2GHz-SM --focus "$FKV" &
NEED=12 $J kv1 kvlife_ha4 --source rtl/hbm_accel/service/ot_hbm_accel_kv_lifecycle.sv --top ot_hbm_accel_kv_lifecycle --param ENABLE=1 --period-ns 0.833 --domain 1.2GHz-SM --focus "$FKV" &
wait

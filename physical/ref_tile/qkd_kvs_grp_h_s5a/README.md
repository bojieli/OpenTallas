# qkd_kvs_grp_h_s5a

Opt-in bounded-driver source; see results/rtl/qwen_kv_die/kvs_grp_s5_1020/SOURCE_PACKET.txt for exact source, primitive/state/behavioral evidence and complete pre-gate checklist.

Original source/leaf files unchanged; zero added cycles. Four exact SRAM wrapper instances are recorded in spec and generator metadata. Actual gate and layout review are pending; do not submit until all source prerequisites, mapped admission32, clocks and geometry pass.

FAIL/HOLD: unchanged response payload FF delay line >=3deep. This source is an evidence prototype, NOT eligible for gate/submit. See response_stage_map in io_storage/logical_storage.json.

/srv/opentallas/repos/laplace-qwen-tagged-accept1-a60af57e4/rtl/hdc/kv/ot_qwen_hbm_stream4_tagged.sv
Vot_hdc_fmul/ot_hdc_fmul.sv
Vot_hdc_vstream_lane_a/ot_hdc_vstream_lane_a.sv
Vot_hdc_qadd/ot_hdc_qadd.sv
/srv/opentallas-scratch/jobs/laplace-qwen-plainar-stream4-P8191-r1/reuse/gen/ot_qwen_rom_core.sv
/srv/opentallas-scratch/jobs/laplace-qwen-plainar-stream4-P8191-r1/reuse/gen/ot_hdc_vstream_rt.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_hdc_delay.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_hdc_fp32_mul_pipe.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_hdc_fpu.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_hdc_fastfp.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_hdc_sfu.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_hdc_sfu_q.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_hdc_reduce.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_hdc_reduce_q.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_hdc_matvec.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_hdc_stream.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_hdc_vstream_lane.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_hdc_vreduce.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_hdc_vstream.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/proto/ot_fp32_add_rne_pipe.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/proto/ot_fp32_mul_rne_pipe.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_hdc_dyn_ttiles.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_hdc_qwen_int8_arith.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_hdc_cg.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_qwen_me_array_w12.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_hdc_fp32_add_lat.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_hdc_prefix.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_qwen_w12_matvec.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_qwen_w12_arith.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_qwen_rt_rom_bank.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/ot_qwen_rt_embed_rom.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc/kv/ot_qwen_rt_kv_stream4_service.sv
/srv/opentallas/repos/laplace-qwen-tagged-accept1-a60af57e4/rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv
/srv/opentallas/repos/laplace-qwen-tagged-accept1-a60af57e4/rtl/model_ready_hbm_r14/ot_hbm_r14_stream_stack.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/rom/ot_rom_pkg_link.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/rom/ot_rom_pkg_ctrl.sv
/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/rom/ot_qwen_tp_seq_w12.sv
/srv/opentallas/repos/laplace-qwen-plainar-stream4-1d44fd09d/rtl/qwen_sys/baseline_ar_stream4/ot_qwen_rom_rt_die_w12_stream4_tagged_ar.sv
--top-module ot_qwen_rom_rt_die_w12_stream4_tagged_ar
--prefix Vdie
-Mdir /srv/opentallas-scratch/jobs/laplace-qwen-plainar-stream4-P8191-r1/die
--mod-prefix Vdie
--hierarchical-block ot_hdc_fmul,ot_hdc_fmul
--hierarchical-block ot_hdc_vstream_lane,ot_hdc_vstream_lane_a,WR,\'sh10,NW,32\'h12
--hierarchical-block ot_hdc_qadd,ot_hdc_qadd
--threads 1
--cc
"--cc" "-O3" "-Wno-fatal" "-Wno-TIMESCALEMOD" "-Wno-WIDTH" "-Wno-UNUSED" "-Wno-BLKSEQ" "-Wno-PINMISSING" "-Wno-LATCH" "-Wno-MULTIDRIVEN" "-I/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc" "-GG=6144" "-GNW=18" "-GSNW=18" "-GQWEN_FULLSHAPE=1" "-GME_IDLE_GATE=1" "-GD=4" "-GSW=64" "-GLV=7" "-GSCALE_LOCAL=0" "-GMEM_EXTRA=1" "-GSMIN=7" "-GSMAX=11" "-GTCUT=7" "-GBD=41" "-GXVM=1" "-GNWS=5" "-GTWS=38" "-GORD=7" "-GREAL_MEM=1" "-GENABLE_AR256=1" "-GNSTK=4" "-GSCALE_BANKS=13" "-GCROM_WORDS=1048576" "-GHBM_LAYERS=36" "-GEMBED_ROM=1" "-GFILL_LAT=8" "-GNRD=256" "-GLKA=512" "-GWBW=4" "-GHBM_PHASE=0" "-GHBM_PULLIN=16" "/srv/opentallas-scratch/jobs/laplace-qwen-plainar-stream4-P8191-r1/reuse/gen/public.vlt" "/srv/opentallas-scratch/jobs/laplace-qwen-plainar-stream4-P8191-r1/reuse/gen/hier.vlt"

-GBASELINE_AR=1

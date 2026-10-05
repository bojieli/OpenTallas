Vot_hdc_v41x_attn_staging_3/ot_hdc_v41x_attn_staging_3.sv
Vot_hdc_v41x_attn_tile_e/ot_hdc_v41x_attn_tile_e.sv
Vot_hdc_v41x_attn_merge_6/ot_hdc_v41x_attn_merge_6.sv
Vot_hdc_qadd/ot_hdc_qadd.sv
/home/ubuntu/w17work/attnsrc/ot_hdc_v41x_attn_tile.sv
/home/ubuntu/w17work/attnsrc/ot_hdc_v41x_attn.sv
/home/ubuntu/w17work/attnsrc/ot_hdc_v41x_attn_staging.sv
/home/ubuntu/w17work/attnsrc/ot_sram_1r1w_256x256_m2_r2c2.v
/home/ubuntu/w17work/attnsrc/ot_hdc_fastfp.sv
--top-module ot_hdc_v41x_attn
--prefix Vattn
-Mdir obj
--mod-prefix Vattn
--hierarchical-block ot_hdc_v41x_attn_staging,ot_hdc_v41x_attn_staging_3
--hierarchical-block ot_hdc_v41x_attn_tile,ot_hdc_v41x_attn_tile_e,TD,32\'h20
--hierarchical-block ot_hdc_v41x_attn_merge,ot_hdc_v41x_attn_merge_6,DPT,32\'h8,MLEV,32\'h5
--hierarchical-block ot_hdc_qadd,ot_hdc_qadd
--threads 1
--cc
"--cc" "-Wno-fatal" "-Wno-WIDTH" "-Wno-TIMESCALEMOD" "-Wno-lint" "-Wno-style" "--output-split" "20000" "--output-split-cfuncs" "2000" "--unroll-count" "1" "--unroll-limit" "131072" "-CFLAGS" "-O2" "-MAKEFLAGS" "OPT_FAST=-O2 OPT_SLOW=-O1 OPT_GLOBAL=-O2" "/home/ubuntu/w17work/attnsrc/v41_attention_hierarchy.vlt" "-GH=16" "-GD=512" "-GTD=32" "-GNL=4" "-GTROWS=640" "-GPWORDS=1"

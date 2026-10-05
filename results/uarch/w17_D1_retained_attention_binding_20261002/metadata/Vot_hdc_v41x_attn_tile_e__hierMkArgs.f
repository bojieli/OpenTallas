--cc
obj/Vot_hdc_qadd/ot_hdc_qadd.sv
-Mdir obj/Vot_hdc_v41x_attn_tile_e 
/home/ubuntu/w17work/attnsrc/ot_hdc_v41x_attn_tile.sv
/home/ubuntu/w17work/attnsrc/ot_hdc_v41x_attn.sv
/home/ubuntu/w17work/attnsrc/ot_hdc_v41x_attn_staging.sv
/home/ubuntu/w17work/attnsrc/ot_sram_1r1w_256x256_m2_r2c2.v
/home/ubuntu/w17work/attnsrc/ot_hdc_fastfp.sv
 --prefix Vot_hdc_v41x_attn_tile_e
 --mod-prefix Vot_hdc_v41x_attn_tile_e
 --top-module-encoded ot_hdc_v41x_attn_tile_e
 --lib-create ot_hdc_v41x_attn_tile_e
 --hierarchical-child 1
-GTD=32\'h20
--hierarchical-block ot_hdc_v41x_attn_tile,ot_hdc_v41x_attn_tile_e,TD,32\'h20
--hierarchical-block ot_hdc_qadd,ot_hdc_qadd
"-Wno-fatal" "-Wno-WIDTH" "-Wno-TIMESCALEMOD" "-Wno-lint" "-Wno-style" "--output-split" "20000" "--output-split-cfuncs" "2000" "--unroll-count" "1" "--unroll-limit" "131072" "-CFLAGS" "-O2" "-MAKEFLAGS" "OPT_FAST=-O2 OPT_SLOW=-O1 OPT_GLOBAL=-O2" "/home/ubuntu/w17work/attnsrc/v41_attention_hierarchy.vlt"

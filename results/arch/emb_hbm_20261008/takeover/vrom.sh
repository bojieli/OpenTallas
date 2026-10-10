#!/bin/bash
R=/srv/opentallas-scratch2/scratch/claude/emb-hbm; cd $R/src
for c in 4 32; do
 mkdir -p $R/obj_rom$c
 ( verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -O3 --top-module tb_emb_rom_baseline -Mdir $R/obj_rom$c \
   -GEA_STG=55 -GEQ_STG=59 -GCR_STG=57 -GCRD=$c rtl/qwen_sys/rtl_finish_20261007/ot_qfd_io_embedding_rom.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_su_master.sv \
   rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv rtl/test/emb_hbm/tb_emb_rom_baseline.sv > $R/obj_rom$c/build.log 2>&1 && \
   $R/obj_rom$c/Vtb_emb_rom_baseline > $R/rom$c.log 2>&1 ) &
done
wait; echo ROMDONE

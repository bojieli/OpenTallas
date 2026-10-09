#!/bin/bash
set -u
cd /srv/opentallas-scratch/codex/emb-boot-crc-r2
iverilog -g2012 -s tb_qfd_emb_boot_crc -o helper ot_qfd_emb_boot_crc.sv tb_qfd_emb_boot_crc.sv > helper_compile.log 2>&1 || exit 2
vvp helper > helper.log 2>&1 || exit 3
iverilog -g2012 -s tb_qfd_emb_boot_crc -Ptb_qfd_emb_boot_crc.MUT=1 -o mutant ot_qfd_emb_boot_crc.sv tb_qfd_emb_boot_crc.sv > mutant_compile.log 2>&1 || exit 4
vvp mutant > mutant.log 2>&1
[ "$?" = 1 ] || exit 5
for twin in 0 1;do
 iverilog -g2012 -s tb_qfd_emb_strip_crc -Ptb_qfd_emb_strip_crc.TWIN=$twin -o strip$twin ot_qfd_emb_pkg.sv ot_qfd_emb_boot_crc.sv ot_qfd_emb_strip.sv ot_qfd_emb_strip_crc.sv tb_qfd_emb_strip_crc.sv > strip${twin}_compile.log 2>&1 || exit 6
 vvp strip$twin > strip$twin.log 2>&1 || exit 7
done
iverilog -g2012 -s ot_qfd_emb_strip_bus_crc -Pot_qfd_emb_strip_bus_crc.ENABLE=1 -Pot_qfd_emb_strip_bus_crc.CRC_PIPE=1 -o bus_elab ot_qfd_emb_pkg.sv ot_qfd_emb_boot_crc.sv ot_qfd_emb_strip_crc.sv ot_qfd_emb_strip_bus_crc.sv > bus_compile.log 2>&1 || exit 8
sha256sum *.sv *.mem > source_sha256.txt
echo PASS_ALL > verdict.txt

#!/usr/bin/env bash
# STW-S81c-TOK4-BAND (10-22): behaviour campaign of the LANDED banded idx rg3 -- tb_dsdv_idx_rg3 with every reader =
# dsdv_idx_rg3_lpw (frozen ports over lp/dsdv_idx_rg3_bf_lp, LX 8 / PD 2).  Same cases / verdicts as idxrd3_campaign.sh.
# Chain check: qo == qi + 5 edges a reader (W pin flop, qoi, landing 2, S23 stage) = the tb's 2 + OH + IH with OH 3, IH 0.
#   run_rg3_band_lp.sh OUT BUILD "<-G flags incl -GOH=3 -GIH=0>" JOBS "name|+plusargs" ...
set -u
O=$1; BN=$2; G=$3; J=$4; shift 4
D=$O/$BN; mkdir -p "$D"
T=rtl/dsrom_sys/s81_dv/idx/test; I=rtl/dsrom_sys/s81_dv/idx
sed 's/dsdv_idx_rg3 #(/dsdv_idx_rg3_lpw #(/' $T/tb_dsdv_idx_rg3.sv > "$D/tb_dsdv_idx_rg3.sv"
grep -q 'dsdv_idx_rg3_lpw #(' "$D/tb_dsdv_idx_rg3.sv" || { echo "LP: tb sed failed"; exit 2; }
L="rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_rst_copy.sv rtl/common/landed_parent/ot_pl_land_split.sv"
sed -e "s#rtl/dsrom_sys/s81_dv/idx/test/tb_dsdv_idx_rg3.sv)#$I/dsdv_idx_rg3_br.sv $I/dsdv_idx_rg3_band.sv $L $I/lp/dsdv_idx_rg3_bf_lp.sv $I/dsdv_idx_rg3_lpw.sv $D/tb_dsdv_idx_rg3.sv)#" \
    $T/idxrd3_campaign.sh > "$D/campaign.sh"
grep -q dsdv_idx_rg3_lpw.sv "$D/campaign.sh" || { echo "LP: campaign sed failed"; exit 2; }
exec bash "$D/campaign.sh" "$O" "$BN" "$G" "$J" "$@"

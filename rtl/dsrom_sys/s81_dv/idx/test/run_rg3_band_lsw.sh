#!/usr/bin/env bash
# STW-S81c-TOK4-BAND (10-22): lockstep campaign -- tb_dsdv_idx_rg3 with every reader = dsdv_idx_rg3_lsw (dsdv_idx_rg3
# drives, the banded dsdv_idx_rg3_bf shadows it on the same inputs).  Wraps idxrd3_campaign.sh (same cases / verdicts);
# a case passes the lockstep when all 8 readers print TB_LSW ... OK.  Run from the repo root on a fleet host.
#   run_rg3_band_lsw.sh OUT BUILD "<-G flags incl -GIH=0 -GOH=1 -GKR=1>" JOBS "name|+plusargs" ...
set -u
O=$1; BN=$2; G=$3; J=$4; shift 4
D=$O/$BN; mkdir -p "$D"
T=rtl/dsrom_sys/s81_dv/idx/test
sed 's/dsdv_idx_rg3 #(/dsdv_idx_rg3_lsw #(/' $T/tb_dsdv_idx_rg3.sv > "$D/tb_dsdv_idx_rg3.sv"
grep -q 'dsdv_idx_rg3_lsw #(' "$D/tb_dsdv_idx_rg3.sv" || { echo "LSW: tb sed failed"; exit 2; }
# the campaign's source list, the tb replaced by the lockstep copy + the band sources
sed -e "s#rtl/dsrom_sys/s81_dv/idx/test/tb_dsdv_idx_rg3.sv)#rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg3_br.sv rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg3_band.sv rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg3_bf.sv $T/dsdv_idx_rg3_lsw.sv $D/tb_dsdv_idx_rg3.sv)#" \
    $T/idxrd3_campaign.sh > "$D/campaign.sh"
grep -q dsdv_idx_rg3_lsw.sv "$D/campaign.sh" || { echo "LSW: campaign sed failed"; exit 2; }
bash "$D/campaign.sh" "$O" "$BN" "$G" "$J" "$@"; rc=$?
bad=0
for spec in "$@"; do
  n=${spec%%|*}; f=$D/$n.log
  k=$(grep -c '^TB_LSW sid .* OK ' "$f" 2>/dev/null); m=$(grep -c 'TB_LSW MISMATCH' "$f" 2>/dev/null)
  echo "LSW_CASE $([ "$k" = 8 ] && [ "$m" = 0 ] && echo OK || echo BAD) $BN/$n: ok_readers $k mismatches $m $(grep -m1 'TB_LSW MISMATCH' "$f")"
  [ "$k" = 8 ] && [ "$m" = 0 ] || bad=1
done
[ $bad -eq 0 ] && [ $rc -eq 0 ] && { echo "LSW_CAMPAIGN PASS"; exit 0; }
echo "LSW_CAMPAIGN FAIL (campaign rc $rc)"; exit 1

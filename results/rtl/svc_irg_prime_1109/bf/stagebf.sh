#!/bin/bash
# stage the banded-flat (bf) reader bench inputs into src/ (needs the git tree).  ref_rg3.sv = rtl dsdv_idx_rg3 at
# 7960f12fb4c (used with the define off = 9b6810c755 bytes on -E); br / band / bf = this tree's rtl.
set -euo pipefail
cd "$(dirname "$0")"; G=$(git rev-parse --show-toplevel); R=$G/rtl; I=$R/dsrom_sys/s81_dv/idx
rm -rf src; mkdir -p src/rtl/lib src/rtl/hdc/v41x
cp $R/lib/ot_rst_relay.sv src/rtl/lib/
for f in ot_hdc_delay ot_hdc_prefix ot_hdc_fastfp ot_hdc_fp32_add_lat ot_hdc_fp32_add_lat_nr; do cp $R/hdc/$f.sv src/rtl/hdc/; done
for f in ot_hdc_v41x_idx_arith ot_hdc_v41x_idx_arith_lat ot_hdc_v41x_idx_hslice ot_hdc_v41x_idx_hslice_fp; do cp $R/hdc/v41x/$f.sv src/rtl/hdc/v41x/; done
cp $I/dsdv_idx_rg2.sv $I/dsdv_idx_rg3_br.sv $I/dsdv_idx_rg3_band.sv $I/dsdv_idx_rg3_bf.sv src/rtl/
git -C $G show 7960f12fb4c:rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg3.sv > src/ref_rg3.sv
ext() { awk '/^module dsdv_idx_rg2_chunk \(/{p=1} p{print} p&&/^endmodule/{exit}'; }
ext < $I/dsdv_idx_rg2.sv | sed 's/^module dsdv_idx_rg2_chunk (/module chk_ref (/' > src/chk_ref.sv
{ echo '`define OT_IDX_HSLICE_FASTPAD'; git -C $G show b9200f3611:rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg2.sv | ext |
  sed 's/^module dsdv_idx_rg2_chunk (/module chk_fp (/'; echo '`undef OT_IDX_HSLICE_FASTPAD'; } > src/chk_fp.sv
(cd src && sha256sum ref_rg3.sv chk_*.sv rtl/*.sv) > src/SHA256SUMS

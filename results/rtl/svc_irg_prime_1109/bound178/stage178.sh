#!/bin/bash
# stage the bound-b178 reader bench inputs into src/ (needs the git tree; run where the worktree is).
# ref_<m>.sv = portfix178/<m>.sv as bound (module -> rg3_ref_m); p_<m>.sv = the same file + <m>.prime.patch
# (module -> rg3_p_m); chk_ref / chk_fp as ../run.sh (orig chunk; FASTPAD chunk of b9200f3611, no guard).
set -euo pipefail
cd "$(dirname "$0")"; B=$PWD; G=$(git rev-parse --show-toplevel); R=$G/rtl
P=$G/physical/die_plan/s81/bind/source_modules/portfix178
rm -rf src; mkdir -p src/rtl/lib src/rtl/hdc/v41x
cp $R/lib/ot_rst_relay.sv src/rtl/lib/
for f in ot_hdc_delay ot_hdc_prefix ot_hdc_fastfp ot_hdc_fp32_add_lat ot_hdc_fp32_add_lat_nr; do cp $R/hdc/$f.sv src/rtl/hdc/; done
for f in ot_hdc_v41x_idx_arith ot_hdc_v41x_idx_arith_lat ot_hdc_v41x_idx_hslice ot_hdc_v41x_idx_hslice_fp; do cp $R/hdc/v41x/$f.sv src/rtl/hdc/v41x/; done
RG2=$R/dsrom_sys/s81_dv/idx/dsdv_idx_rg2.sv; cp $RG2 src/rtl/dsdv_idx_rg2.sv
ext() { awk '/^module dsdv_idx_rg2_chunk \(/{p=1} p{print} p&&/^endmodule/{exit}'; }
ext < $RG2 | sed 's/^module dsdv_idx_rg2_chunk (/module chk_ref (/' > src/chk_ref.sv
{ echo '`define OT_IDX_HSLICE_FASTPAD'; git -C $G show b9200f3611:rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg2.sv | ext |
  sed 's/^module dsdv_idx_rg2_chunk (/module chk_fp (/'; echo '`undef OT_IDX_HSLICE_FASTPAD'; } > src/chk_fp.sv
for m in dsdv_idx_rg3 dsdv_idx_rg3_nq_native; do
  sed "s/^module $m #(/module rg3_ref_m #(/" $P/$m.sv > src/ref_$m.sv
  cp $P/$m.sv src/p_$m.sv; (cd src && patch -s -p1 --no-backup-if-mismatch p_$m.sv < $B/$m.prime.patch)
  sed -i "s/^module $m #(/module rg3_p_m #(/" src/p_$m.sv
  grep -q "^module rg3_ref_m #(" src/ref_$m.sv; grep -q "^module rg3_p_m #(" src/p_$m.sv
done
sha256sum $P/dsdv_idx_rg3.sv $P/dsdv_idx_rg3_nq_native.sv src/*.sv | sed "s|$G/||" > src/SHA256SUMS

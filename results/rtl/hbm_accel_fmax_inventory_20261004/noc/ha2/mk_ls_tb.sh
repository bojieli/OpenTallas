#!/bin/bash
# Generate the lockstep testbench from the pinned rtl/hbm_accel/ha2_ar/tb_ha2_ar.sv (unmodified in the repo):
# the top instantiates tb_ha2_ep_ls (this directory) in place of tb_ha2_ep.  Usage: mk_ls_tb.sh <src_root> <out.sv>
sed -e 's/^\(\s*\)tb_ha2_ep u_ep (/\1tb_ha2_ep_ls u_ep (/' "$1/rtl/hbm_accel/ha2_ar/tb_ha2_ar.sv" > "$2"
grep -q "tb_ha2_ep_ls u_ep" "$2" || { echo "rewrite failed"; exit 1; }

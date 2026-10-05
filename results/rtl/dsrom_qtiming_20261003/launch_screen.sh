#!/bin/bash
# usage: screen.sh FRAME(C|A) RUN
set -e
F=$1; RUN=$2
J=/home/ubuntu/otjobs/dsrom_qtiming_20261003/$RUN
mkdir -p $J
cd ${WT:-/home/ubuntu/dsrom-qelem-timing-20261003}
if [ $F = C ]; then DIE="0 0 510.84 126.9"; CORE="0 0.27 510.84 126.63"; PR="136.08-374.76";
else DIE="0 0 521.64 178.47"; CORE="0 0.27 521.64 178.2"; PR="141.48-380.16"; fi
STOP=${STOP:-cts}
SRCS=""
for s in rtl/v41rom/ot_v41_rom_elem_q_qt_w10.sv rtl/v41rom/ot_v41_rom_elem_qt_w10.sv rtl/v41rom/ot_v41_rom_elem_w10.sv rtl/v41rom/ot_v41_bterm.sv rtl/v41rom/ot_v41_chain.sv rtl/v41rom/ot_v41_segtree.sv rtl/v41rom/ot_v41_bf16_lanes.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_cg.sv rtl/proto/ot_fp32_add_rne_pipe.sv physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8_bb.v rtl/v41rom/ot_v41_fadd.sv rtl/common/ot_prefix.sv rtl/v41rom/ot_v41_bterm2_w10.sv rtl/v41rom/ot_v41_chain2.sv rtl/v41rom/ot_v41_segtree2.sv rtl/v41rom/ot_v41_bf16_lanes2.sv physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_bb.v; do SRCS="$SRCS --source $s"; done
exec python3 tools/run_abi3_physical_persistent.py --persistent-workdir $J/work --launch-receipt $J/receipt.json \
 --view asap7 --top ot_v41_rom_elem_q_qt_w10 $SRCS \
 --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --io-delay-fraction 0.2 --stages pnr \
 --die-area $DIE --core-area $CORE --place-density 0.6 --macro-place-halo 2 2 \
 --pin-region "^(p|busy|fault|xs_q1|xs_e1).*=top:$PR" --pin-region "^(clk|rst|cfg|go|xs_v|xs_p|xs_b|xs_sv|xs_q0|xs_e0).*=bottom:$PR" \
 --max-transition-ns 0.32 --slew-margin-percent 40 --hold-margin-ns 0.0 \
 --step-tcl POST_MACRO_PLACE=physical/abi3/${HOOK:-dsrom_qtiming_${F}_place}.tcl --step-tcl POST_DETAIL_PLACE=physical/abi3/check_pg_before_route.tcl \
 --orfs-var PDN_TCL=/src/tools/chip_assembly/tcl/pdn_w10_elem_m7_ir.tcl --nickname-tag dsrom_qtiming_${RUN}_20261003 \
 --output $J/out --sdc-append physical/abi3/v41_w10_elem_pp_multicycle.sdc \
 --macro-view ot_rom_4096x274_m8=physical/asap7_memory_macros/ot_rom_4096x274_m8 \
 --param MTP=1 --param EARLY=1 --param NB=2 --param FAST=1 --param PP=1 --param QTIMING_FIX=1 \
 --pnr-stop-after $STOP --orfs-corner WC --clock-uncertainty-hold-ns 0.025 \
 --core-input-delay-min-ns 0.36 --core-input-delay-max-ns 0.727 --output-delay-min-ns -0.56 --output-delay-max-ns -0.193 > $J/launch.log 2>&1

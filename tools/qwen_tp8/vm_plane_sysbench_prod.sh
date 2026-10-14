#!/bin/bash
# PRODUCTION-SHAPE bit-plane VM system bench (tb_qfd_vm_bv_ports), ONE run, ON the remote host (as vm_plane_sysbench.sh):
#   SW 64, ELEMS 177,808, NRB 64, SMIN 7, SMAX 11, BMAX 8, ND 14 (the die's stride set), CRB 16, region built from
#   leaves (ot_qfd_vm_region_leaf), RV 1 RO 1.  Shape rule: XVM = BMAX + 7 (15) + RV + RO + 7 (24); bit plane
#   + XPR + 1 - RO; owners + XQR + 2.  VL = 7 + RV + RO + 5 = 14.  XRN 32768: x tuples up to BMAX beats of 1,008.
#   vm_plane_sysbench_prod.sh <name> <trees: 0|1> "<more -G args>"
n=$1; tr=$2; more=$3
D="112'h6040302018100c08060403020100"
G="-GELEMS=177808 -GNRB=64 -GSW=64 -GSMIN=7 -GSMAX=11 -GBMAX=8 -GND=14 -GDSET=$D -GCRB=16 -GXRN=32768 -GSEED=5 -GRV=1 -GRO=1 -GVL=14 -GXPR=10"
if [ "$tr" = 1 ]; then G="$G -GXVM=38 -GXTK=3 -GXMK=2 -GXLO=1 -GXQR=2"; else G="$G -GXVM=34 -GMWD=3"; fi
# a parameter given again in <more> REPLACES the default above (the PLAN runs: -GXPR=12 -GXVM=40 -GXTK=7)
for k in XPR XVM XTK XMK XQR; do
  case " $more " in *" -G$k="*) G=$(echo "$G" | sed "s/-G$k=[^ ]*//") ;; esac
done
exec "$(dirname "$0")/vm_plane_sysbench.sh" "$n" "$G $more" +define+OT_QFD_VM_TILE_MOD=ot_qfd_vm_region_leaf \
  rtl/qwen_sys/vm_die_split_20261012/ot_qfd_vm_region_quarter.sv rtl/qwen_sys/vm_die_split_20261012/ot_qfd_vm_xfifo8_t.sv \
  rtl/qwen_sys/vm_die_split_20261012/ot_qfd_vm_answer_tiles.sv rtl/qwen_sys/vm_plane_20261013/ot_qfd_vm_region_leaf.sv

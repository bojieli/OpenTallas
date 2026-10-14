#!/bin/bash
# Root launches only from a frozen admitted snapshot with a fresh label.
set -euo pipefail
: "${SRC:?frozen source snapshot with SOURCE_COMMIT is required}"
: "${OUT:?immutable route output base is required}"
label=${1:?fresh unique label is required}
test -f "$SRC/SOURCE_COMMIT"
kit=physical/s81_be_access_m7_candidate
# The route helper consumes this isolated pin directory; published views/ports stand.
mkdir -p "$SRC/physical/s81_ph_views/ports/be_access_m7_candidate/dsfd_vm_be_sl"
cp "$SRC/$kit/io_place.tcl" "$SRC/$kit/ports.json" "$SRC/physical/s81_ph_views/ports/be_access_m7_candidate/dsfd_vm_be_sl/"
export MAXL=M7 PD=0.45 PER=1.1111 HM=0.035 CLK=ck
export SDCM="$kit/margin.sdc" PDN="$kit/pdn.tcl" POSTCTS="$kit/post_cts.tcl" PREGRT="$kit/full_depth_keepout.tcl"
export SRCS="rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bgq_sys.sv rtl/dsrom_sys/mtp/dsfd_vm_wfc_ep.sv rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_rtt.sv rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv rtl/dsrom_sys/mtp/rtt/ot_dsrom_mtp_rstsync.sv rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv rtl/common/ot_ratio_cdc_fifo.sv"
# Legacy closed routing cap is preserved honestly. No M6 metadata waiver.
bash "$SRC/physical/s81_ph_views/common/route_view.sh" "$label" be_access_m7_candidate dsfd_vm_be_sl rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm.sv \
    --step-tcl PRE_GLOBAL_PLACE="physical/s81_ph_views/vm_master/besl_rhold.tcl" \
    --step-tcl POST_DETAIL_ROUTE="$kit/full_depth_keepout.tcl" \
    --orfs-var OT_RHOLD_N=2 \
    --orfs-var CTS_SNAPSHOTS=1

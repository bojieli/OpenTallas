#!/bin/bash
# DIE-HBM-89-SPB2F 11-07: assemble the q_spb2 vF kit (REDESIGN of vE, 0 PIN CYCLES, RTL/netlist unchanged) from the vE kit.
#   spb2_vf_assemble.sh VE_GEN_DIR VF_GEN_DIR TOOLS_DIR
# vE failed routed sign-off as a LARGE miss (TT -112.15/873, FF hold -247.14/8774, slew 16,056 TT, DRC 0).  Geometry
# (DIE-HBM-89 18:43): station clumps, weak 1x drivers alone on 300-343 um hops, two U-turn chains crossing.  vF changes:
#  (a) drive: repeater pitch OT_MAXWIRE_UM 450 (COORD 19:0x, owner repeater rule) at the placement repair_design
#      (PRE_RESIZE) and the GRT repair_design (grt_pre.tcl); weak INV/BUF drivers of nets >= 150 um upsized to
#      INVx6/BUFx6f before and after the placement repair and before the GRT repair (hop_drive.tcl);
#  (b) FT stations L33x2, L720x2, L722x2, L723x2 as strips across the bundle (ft_strip_sites.py), plan centres kept;
#  (d) L1278x3 stations translated +40/+50/+50/+40 um in y (plan shape and order kept) so the inner U-turn no longer
#      shares its y band with L1280x6 (vE crossing at y 1020-1170).
# Synth and floorplan are reused (stage resume start=place: same RTL, SDC, io.tcl, die, macros); the vE kit-local
# run_kit.sh child-record mount (DIE-HBM-87) is kept, the flow tag comes from OT_FLOW_TAG at launch.
set -euo pipefail
VE=$1; VF=$2; T=$3
KE=$VE/q_spb2; KF=$VF/q_spb2
[ -e "$KF" ] && { echo "refuse: $KF exists"; exit 2; }
mkdir -p "$KF"
cp -p "$VE/run_kit.sh" "$VF/run_kit.sh"
# kit sources: everything but run outputs, gate results/history and stage-resume markers
( cd "$KE" && find . -maxdepth 1 -type f \
    ! -name '*.previous.*' ! -name 'FAIL_*' ! -name '.kwrs_done*' ! -name 'run_*.log' ! -name 'signoff.log' \
    ! -name 'grt_policy*' ! -name 'postcts_gate_*' ! -name 'kit_preflight_2*' ! -name 'preflight.json' \
    ! -name 'pin_audit.json' ! -name 'hold_gate.log' ! -name 'lec_async.lock' -print0 | xargs -0 cp -p -t "$KF" )
for d in rtl macros lec; do cp -rp "$KE/$d" "$KF/$d"; done
# reused synth + floorplan (hardlinks of the vE step outputs; later steps never write them under stage resume)
R=run/results/asap7/dp_q_spb2/base; L=run/logs/asap7/dp_q_spb2/base; P=run/reports/asap7/dp_q_spb2/base
mkdir -p "$KF/$R" "$KF/$L" "$KF/$P"
for f in "$KE/$R"/1_* "$KE/$R"/2_*; do ln "$f" "$KF/$R/"; done
for f in "$KE/$L"/1_* "$KE/$L"/2_*; do [ -e "$f" ] && cp -p "$f" "$KF/$L/"; done
for f in "$KE/$P"/synth_* "$KE/$P"/2_*; do [ -e "$f" ] && cp -p "$f" "$KF/$P/"; done
cat > "$KF/resume.json" <<EOF
{"schema": "opentallas.kw_stage_resume.v1", "start": "place", "reused_steps": ["synth", "floorplan"], "why": "DIE-HBM-89-SPB2F 11-07 vF: RTL, SDC, io.tcl, die and macros unchanged from vE; placement form changed", "source": {"host": "epyc2", "kit": "$KE", "attempt": null, "attempt_dir": null, "relay": null}}
EOF
# (b)+(d) FT station sites
python3 -I "$T/ft_strip_sites.py" "$KE" "$KF/ft_bit_sites.tcl" "$KF/ft_strip_sites.json" \
  --strip L33x2,L720x2,L722x2,L723x2 \
  --shift L1278x3:1:0:40 --shift L1278x3:2:0:50 --shift L1278x3:3:0:50 --shift L1278x3:4:0:40
# (a) drive
cp -p "$T/grt_maxwire.tcl" "$T/hop_drive.tcl" "$KF/"
cat > "$KF/vf_pre_resize.tcl" <<'EOF'
# q_spb2 vF PRE_RESIZE hook: placement repair_design with the repeater pitch, weak hop drivers upsized first.
source /work/grt_maxwire.tcl
source /work/hop_drive.tcl
ot_hop_drive pre_resize
EOF
cat > "$KF/vf_post_resize.tcl" <<'EOF'
# q_spb2 vF POST_RESIZE hook: upsize weak drivers repair_design left on long nets (legalized by 3_5 detail placement).
source /work/hop_drive.tcl
ot_hop_drive post_resize
EOF
cat > "$KF/vf_grt_pre.tcl" <<'EOF'
# q_spb2 vF PRE_GLOBAL_ROUTE hook: the kit's hold_repair_pre.tcl (grt_pre.tcl sources grt_maxwire.tcl via OT_MAXWIRE_UM),
# then weak hop drivers upsized before the GRT repair_design (its detailed_placement legalizes them).
source /work/hold_repair_pre.tcl
source /work/hop_drive.tcl
ot_hop_drive pre_grt
EOF
sed -i 's#^export PRE_GLOBAL_ROUTE_TCL = /work/hold_repair_pre.tcl$#export PRE_GLOBAL_ROUTE_TCL = /work/vf_grt_pre.tcl#' "$KF/config.mk"
grep -q '^export PRE_GLOBAL_ROUTE_TCL = /work/vf_grt_pre.tcl$' "$KF/config.mk"
cat >> "$KF/config.mk" <<'EOF'
# DIE-HBM-89-SPB2F 11-07 q_spb2 vF (REDESIGN of vE; COORD 19:0x): repeater pitch 450 um at placement + GRT repair_design,
# weak hop drivers upsized (hop_drive.tcl), FT station strips + L1278x3 uncrossed (ft_bit_sites.tcl, ft_strip_sites.json).
export OT_MAXWIRE_UM = 450
export OT_HOP_DRIVE_UM = 150
export PRE_RESIZE_TCL = /work/vf_pre_resize.tcl
export POST_RESIZE_TCL = /work/vf_post_resize.tcl
EOF
echo "q_spb2 vF = vE kit + strip/shift FT sites, maxwire 450, hop_drive (DIE-HBM-89-SPB2F, $(date))" > "$KF/TYPE_VARIANT.txt"
echo ASSEMBLED "$KF"

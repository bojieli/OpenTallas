# GENERATED-COPY of tools/die_plan/grt_ff_scene.sdc (FLOW-MCMM-GRT 2026-10-27): IO virtual clock of the FF HOLD scene in
# the two-scene GRT repair (grt_scenes.sh).  Read by orfs_hold_mm.tcl ot_mm_sync in mode ff, on the global-route
# parasitics, with pin arrivals answered from scene BC.  vclk = OT_VCLK_FF (+ the hard-core FF tap overlay); a 'rebind'
# kit (vclk_ref.py, the decision signoff.py uses) then gets the measured FF pin-register mean, band-checked (fail
# closed), i.e. the frame FF hold is signed off in (S81-ECO-2 measured-frame hold).
if {![llength [info commands ot_vclk_bind]]} { source /work/vclk_corner.tcl }
if {![llength [info commands ot_vmh_scene_bind]]} { source /work/vclk_measured_hold.tcl }
ot_vmh_scene_bind

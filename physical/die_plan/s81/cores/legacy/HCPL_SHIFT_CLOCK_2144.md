HCPL shift-chain clock recipe (opt in)

The old HCPL V1 route missed FF hold by 1.40 ps at four endpoints because
short delay-register transfers crossed clock leaves. The new recipe puts each
complete zero-logic delay chain on one local clock root: 32 groups containing
608 delay-line FF plus 94 connected FF. All other FF, including reset/control,
remain explicitly inventoried. It changes no RTL, pin contract or public cycle.

The actual trial reached GRT0 with TT setup +49.324 ps / FF hold +3.240 ps at
833 ps and 60/25 ps uncertainty. It is NOT SIGNED and enables no route entry point.
See results/geom_review/codex_hcpl_shiftclk_2144_grt.json for the measured cohort.

Generate and apply from this checkout (no old runtime or closed view is imported):

    python3 physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py \
      --module ot_dsrom_su_hcpost_lane_pr --suffix shift2144 --out "$SCRATCH/kits"
    python3 physical/die_plan/s81/cores/legacy/apply_hcpl_shift_clock_2144.py \
      --kit "$SCRATCH/kits/ot_dsrom_su_hcpost_lane_pr_shift2144"

Run each heavy phase through ot-run and keep review before P&R/STA:

    bash KIT/run_kit.sh KIT place 16 8
    bash KIT/run_kit.sh KIT cts 16 8
    bash KIT/run_kit.sh KIT ff 16 8
    bash KIT/run_kit.sh KIT grt 16 8

Render and inspect placement before CTS, then review actual clock ownership
before the separate fresh FF phase. The cts phase freezes original synthesis
and placement hashes. The ff phase uses a new FF-only process and the canonical
repair_ff.tcl, then independently reloads TT and FF. The grt phase disables
in-session timing repair, retains DRV repair, and independently checks stored
ODB global-route parasitics. Do not replay read_guides before that estimate:
OpenROAD warns GRT-0008 and loses the stored route-to-pin basis.

The generator/apply step was checked on the current repo: 277 pins, one clock,
one reset, no macros; all seven emitted RTL files match the measured cohort.
No old timing view transfers. Any changed inventory or clock contract fails
closed; the 32-group / 608-line-FF guards run before CTS. Current die/flow gates
and independent geometry approval still govern any future route.

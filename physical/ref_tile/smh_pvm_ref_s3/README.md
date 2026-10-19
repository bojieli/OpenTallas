# PVM whole-macro mirror successor

Source-bound analytical geometry packet: `results/arch/hbm_pvm_safe2_1019/mirror_geometry/`. This new kit uses ot_hbm_sm_pv_merge_s3 and distinct ot_sram_1r1w_64x512_m1_r2c2_p192_mir with complete compiler-generated boundary/PG/contact/RC/Lib. The original p192 macro and failed s2 physical evidence are immutable.

Entire macro R180 at43.2/43.2 moves the real modeled clock contact to214.476/196.332,19.668um from the only legal north driver band. Mirror-compatible H153.912 restores all1585 M4contact centres to actual tracks; old H153.900 R180 has1585offtrack. Clock/data core timing and actual addedleadcap are regenerated, not reduced to assume closure. SRAMbehavior/arithmetic/calendar unchanged. Same302.4square slot, per-macro area+2.055456um², no addedexternaledge.

Actual-core row band[2.16,216,300.24,300.24], synthesisstd10343um² yields41.19%. Original gate41.3% was totalfill; it was not the standardcell-band metric. Actual cells/rows after mapping must be measured again. Canonical 24x24nm contacts need real route patches to satisfy minimum area; trackalignment alone does not prove external escape/PG/DRC.

Read design_review.json for all eight checklist findings. Model PNG is geometry only, not placed-cell evidence. Functional newmacro/nativebehavior proof runs before gate. Actual TTsetup/FFhold, relative nativeclock/parent, reach and critical PNG rootreview remain required. No REVIEW.json or submit.

# BTAB measured repair packet, not activated

Source proposal8bb9043d0a2 is separate from this old-cohort diagnostic. Original C exactfinalODB d3c9d212e994 andSPEF f9648ea03943 remain immutable. Metadata diagnostic completed under same clock binding/rebind and exact6TT/6FFlibrary hashes. Diagnostic—not adopted or SIGNED—result: TTsetup274.93,FFhold-2.59 (3endpoints), DRV82slew/3capTT and34/3FF, DRC3. Clockpair57.76/53.67,unconstrained0,PG/SDC/modesPASS,antenna0. Native FACE shared stickyfault is a sourcefailure; latephysicalclone already exists and mustbeaccounted.

Measured hold endpoints: ptw_data153→u_twpd153 -2.5896;145→145 -2.4310; u_twpd247→g_btb0.u_wd247 -1.5967. All full FF paths and actualhomes included.73point-to-point bad data nets cover82unique badpin names; driver types41BUFx3,16DFF,14INV,1BUFx16f,1BUFx2. Longest147.015um; most cross eastern SRAMs with no midspan cellsite.

Proposed data-only correction uses existing `tools/die_plan/final_ff_hold.tcl::ot_final_ff_converge` with the kit's unchanged normal margins, actualTT/BC frames and clockfreeze guard. Reuse lawful repair_design_helper for data electrical repair and repair_timing for residual hold; no FF/clock master resizing or clock movement. A routed-final adapter still needs FLOW review: the existing helper is GRT-stage-qualified and cannot simply be claimed qualified on final routed SPEF. Preserve fixed pin/outline/macros and actual source/capture FFhomes, fail on nonimprovement, then full actual re-extraction/TT/FF setup+hold+pairs/FACE/nativeLEC/DRC/PG. No extra margin scan or unchangedfullsignoff rerun.

DRC localproposal records one net3486 driver/sink and exact3markers. Candidate M5 crossing withV4 outside macro body is a geometry option; API/PG/spacing and allowed incremental routing must be reviewed before any routing. It is not a blanket fullroute restart.

Rendered and personally LOOKED repair_scope.png. Fourmacrogeometry andfrozen pins remain. Orange lines show measured endpointspans, not actual routedshapes; criticalSW holdpaths andexistingfaultfacehomeare marked. This is concrete proposed scope, no physical repair has executed.

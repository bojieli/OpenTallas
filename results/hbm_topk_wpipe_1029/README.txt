TOPK two-stage SRAM writer prototype; READY for shared-source review, default off.

WRITE_PIPE_STAGES=0 preserves current source. Opt-in2 pipelines WE/ADDR/DATA coherently by exactly2internal SRAM write edges. Carry/flits/total/selected_count/fault/emit dates unchanged. Addresses/data are unreset; reset/clear cancels pending WE only. No production instantiation enabled and no P&R approval.

Actual production ordered calendar:171ingest slots,flush+3idle,16 ordered emit groups at II8. Four frames cover2048records, cold/warm reset, consecutiveclear, high20bitindices, final-ingest-slot write. Legacy serial reference vs tree WRITE_PIPE_STAGES0 and2 eachPASS0errors/1235cycle checks; PIPE2 checks256coherent write vectors at exactly+2edges. Pipeline-only WE/ADDR/DATA mutants4/5/6 caught1888/320/96errors. Admitted intel1 unit1374448-1793263439 exit0; exact_lastslot/run*.log. No arbitrary out-of-order emit protocol equivalence claim.

Guide estimate uses existing native line_r register stage plus8304newFF upperbound; conservative area3147.88um2. Per-bit logical guides csv (8304uniquebits) are a placement intent, not mapped-cell constraints. All guide corner-pair reach <=360.72um, every new guide58.57%fill; no macrohalo/island overlap. Native stage remains unadded. Existing source reachable fill7/flits0 ->record0 indexbit0 targets bank0wd480:923.610um fromface, beyond2x405evenallowing20umanchor. Earlier786.810wd16case alone did not account for native stage; corrected here.

Analytic timing799.426ps worst vs833ps uses explicitly uncalibrated assumptions; mapped STA,clockload,macroescape/congestion still required. No measured closure claim. write_pipeline_guides.png personally reviewed; macros/islands shown. Model source C25b macro locations retained; C25c selected-line paired-W pin update changes interface only, needs actual binding before newkit.

Reproduce: bash results/hbm_topk_wpipe_1029/run.sh REPO NEW_OUT via admitted ot-run. Shared RTL requires root review. Existing serial source and old failed LEC/geometry records retained elsewhere unchanged.

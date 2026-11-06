# INGEST phase decoder banks, provisional physical event

Opt-in `OT_INGEST_PHASE_DAG_LOCAL=1`; source phase_dag_local.tcl AFTER the unchanged vD face_and_phase hooks. Uses existing load_bank.tcl API, preserves its serial namespace and all 29 prior mode banks. Dynamically walks actual mapped _069618_ source cone and requires seven unique internal st_mode[0:2],st_d[3],st_ph[0:2] state roles; primary capture frontiers are refused by the existing API. Exact final terminal names and pin/net membership fail closed.

Actual source-floorplan application: 7 banks,63 final terminals,77 copied cells (49 FF and28 combinational),210 exact master/input/D/CLK/reset/set audits,0 extra cycles. Source cone has4 combinational nodes per bank; routed vD has three added BUFs, so no routed BUF names are assumed in this hook. Original phase bank34copies/528loads and29 modebanks/160copies retained. Actual32 SRAM geometry reviewed; bank centers lie in bottom corridors, nearest macro L1 clearance8.004um. Ordinary placement/legalization decides actual cells.

Bounded actual-routed observer projection at _123610_/B proved37/37 equivalence points; direct output-inversion mutant left y unproven. This composes identical-state phase assumptions with exact FF inputs and does not claim full routed LEC. Fresh vE requires its own final routed LEC, full TT/FF/DRV/DRC and parent qualification.

Artifacts: Intel1 andIntel2 /srv/opentallas-scratch2/claude/codex-kv-ingest-phase-cone-1106/preplace/{phase_dag_probe.odb,phase_dag_banks.tsv,macros.tsv}; Intel2 sibling projection_positive.log/projection_mutant.log/projection_receipt.txt. Source application log intel2 ~/kv-peer-1/ingest_phase_source_application_intel1.otrun.log, actual unit3999463-1793982799.

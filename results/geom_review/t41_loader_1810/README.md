# T41A original-state observer loader PREP

PREP ONLY: no CTS/STA command executed. Physical runner and admission are owned by G0C/S81; ROOT reviews the concrete joint scope before any EDA. GROUP_RE stays OFF. Use corrected ORIGINAL3_place and apply established hooks exactly once. The post_hook audit DB is not the starting snapshot.

Loader: `tools/die_plan/forwarded_export_loader.py`. Dependencies: `forwarded_export_observer.py`, `pair_skew.tcl`, `signoff.py` (exact corner-library resolver and existing FF_BOUND_TCL only), `sdc_lint.py` (signoff import). All other imports are standard Python. The generated Tcl is standalone; it does not import postcts_gate.py or core_clock_band.py. This does not repair a missing dependency in the physical runner itself.

Actual prepared packet on Intel2:
`/srv/opentallas-scratch2/claude/codex-t41-export-observer-1640/loader1810/{PREP.json,tt/session.tcl,ff/session.tcl}`.

Input kit:
`/srv/opentallas-scratch2/claude/codex-s81-t41-cts-prep-1810/kit`.

Preparation invocation (Python/text only):
```
python3 forwarded_export_loader.py --kit KIT --out loader1810 --enable --odb 4_cts.odb
```
Default is OFF. The exact selected config, original SDC, compiled1_2_yosys.v and existing setRC_rcx.tcl are SHA-checked before loading. Runtime records the actual completed CTS ODB hash and actually loaded TT/FF library receipt. Use fresh distinct TT/FF output directories. Loader rejects stale observer payloads and incomplete/error/missing/limited requested observations.

After ROOT authorization and actual normal CTS completion/LOOK, the owner supplies these read-only mounts to one OpenROAD invocation per corner through ot-run (commands here are PREP, not launches):
```
docker run --rm -v KIT:/work:ro -v ACTUAL_BASE:/base:ro -v LOADER/CORNER:/observer:ro -v NEW_OUTPUT/CORNER:/out IMAGE /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /observer/session.tcl
```
The original kit determines exact TC/BC NLDM libs via the common signoff make-based library loader. `read_db /base/4_cts.odb`, original golden SDC, declared FF virtual IO202.5ps (TT250ps), existing kit per-class RC and `estimate_parasitics -placement`, propagated clocks, then all-bit observer run. The FF overlay is exactly the existing normal postcts sole-source-less-vclk reference adjustment, not a new budget. Original setup0/hold25 and seam12.5 uncertainties, source windows, input/output delays and generated exports remain intact. No pair zero_unc, clock deletion, ETM mutation, CPPR addition or changed verdict.

This is **POST_CTS_PLACEMENT_ESTIMATE_NOT_ROUTED_OR_EXTRACTED**. It is not extracted or routed timing, signoff or final link qualification. Preserve this RC basis in every summary. There are4816 actual output bits and9632bounded min/max data queries, physical forwarded-source K checks for all8 exports, and original-state native vclk STD observations. Native STD slack remains distinct from conservative uncorrelated D/K bounds. F/R count-phase caller qualification remains separate.

After the real authorized run, call `forwarded_export_observer.validate(request, output/t41_export_witness, sta.log)` outside EDA and retain the resulting summary plus PREP/runtime/library/SDC identities. Missing root/source/edge or paths remain NOT_ASSERTED; no aggregate ownership inference.

Nine focused Python/Tcl-generated controls passed (existing7observer +2loader); no EDA, synthesis, equivalence or physical replay performed by this PREP.

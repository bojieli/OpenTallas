S81 element UPF (item8 sectiond ONLY)

physical/upf/dsrom_s81_elem.upf describes PG=1/NB=2/NSUB=4/DOM_CG=0: AO domain, switched u_pg/u_elem, four existing staggered header controls, all element outputs clamped0 by AO iso_n, and existing676-bit AO configuration shadow/replay. The volatile element configuration is deliberately NOT retained. No new cells, clock gates, pipeline, area or latency have been added.

Existing R4 route read_upf PASS on pinned OpenROAD26Q3-1510-g6cb3f2b704:2domains/4switch models;339330instances unchanged. OpenROAD supplies commands are absent: import explicitly reference_only, no Tcl stubs or hidden success for supply/retention implementation. A full-UPF-tool branch declares VDD/VSS and logical VDD_ELEM; not tested by this limited reader. The real R4 grid connects all cells to VDD, so switched-grid/header-library mapping is NOT qualified. Retention is existing AO-powered storage rather than invented backup cells or switched-domain preservation.

Existing tools/rom_stage_pg_sim.py on current pinnedsource6847b30e0 PASS: base148645cycles/204rows/nonzero96/sleeps13/wakes13/restores325/aborts3; exact against current unmodified element reference; no_restore/no_iso/short_lead all detect faults and exit1. Original exact.json verdict agrees. Existing b9e873649 second-macro row-decode fix and54cdd72f9 class7-both-macros bench explain different source hashes and historical row counts; historical_source_differences.json pins both. This is existing RTL PA corruption/reference simulation, NOT a full standard UPF simulator.

Clock constraints untouched:0.833ns/SSsetup60ps/FFhold25ps. Existing R4 -228.382ps setup/-13.1459ps hold and fanout failures remain history/unqualified; no reroute/STA or signoff/adoption claim. AO-alone prior closure cannot qualify the switched element.

Validation commands, remoteEPYC2 admitted8GiB with actual headroom, one CPU each:
  docker run --rm -v JOB:/work -v PINNED_SOURCE:/src:ro --entrypoint /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad openroad/orfs:asap7lock -exit /work/read_upf.tcl
  python3 tools/rom_stage_pg_sim.py --work JOB/pa_work --out JOB/pa
No local/PVE2/3 heavy job, timeout/RAM/file caps, meso/fulltop/EM edits or restarted peer job. Original route/source/logs preserved. Optional write_upf crashed on unmapped switch serialization; Tcl local-variable diagnostic failed; both immutable logs/Tcl/exit retained. Required finalread and PA gates exit0.

Inventory row dsrom_s81/power_intent remainsPARTIAL: add physical/upf/dsrom_s81_elem.upf and thisrecord, replace noUPF with actualimport+PA status and tool/physicalmapping limitations. Confucius owns serialized build_inventory.py+README+inventory.json changes; Einstein edits none of those. Qwen/HBM intent, meso and EM remain separate owners.

OpenROAD primary API reference: https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/upf/README.md

# Repeated forwarded clock exports at pre-CTS

Actual RCK vG t16 completed PLACE, then pre-CTS sourced clock_taps.tcl and failed `OT_CLAND_EXPORT cland_fwd_fclk_out_coll_o0 exists`. PLACE had already materialized the same forwarded clocks. This is a FLOW failure before CTS construction, separate from the PIN-control cohort geometry failure.

`landing_contract.export_tcl_fwd` now reuses an existing forwarder only when its master, A/Y directions, source net, dedicated CLOCK output net, exact destination BTerm, and absence of other output loads match the requested one-buffer topology. Mismatches still fail closed. Existing location/status and the original first-creation/orphan handling remain unchanged. No pin, RTL, clock window or latency changes.

Real fixture: read-only copy of E4 `/srv/opentallas-scratch3/claude/s81-rck-5/vG/serdes__t16/gen/serdes__t16/run/results/asap7/dp_serdes__t16/base/3_place.odb`, 628251331bytes, retained E6 physical scratch2 `/srv/opentallas-scratch2/claude/codex-rck-vG-view-1209/3_place.odb`. Ordinary ot-run8GB2T, capped Docker, unit oth-ubuntu-679486-1794084860, exit0. It sources freshly emitted four-export Tcl twice:8matching reuses. Wrong source, wrong destination and wrong expected master each rejected; cell/net counts, export connectivity, master, placement/status unchanged. No DB written and no live kit modified. See real_fixture.tcl, emitted_exports.tcl and real_fixture.log.

Focused existing `test_cts0114_fwd` and `test_fwdclk_shared_tap`:18passed. Hub interpreter lacked pytest; exact modified module and its source dependencies were copied to a temporary local test closure. Initial missing closure files were supplied before the passing run.

Source fix is ready for review. No CTS restore authorized by this artifact: current RCK placed PIN0/1 valid/reset controls are far from data and on different clock roots. That structural geometry FAIL must be corrected before any continuation.

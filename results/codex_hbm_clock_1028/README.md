HBM clock structural successor, C25b source cef2eac649.

Current release clock remains FAIL: trial2b FF duty 346/3294, no freeze.
Actual inherited tree has390 cell-to-parent legs above450um, maximum1105.4um.
The leg9096 across u_hb_vms_Q__q1 has783.12um without a repeater. Its macro wall is777.6x1635.552um.
The shared legal_detour A* default600um search clips the route around this macro.
At identical endpoints, default search FAILS at5.4/2.16/1.08um grid; increasing search margin to900um at5.4um grid returns a legal8point route in0.34s.
The die-specific adaptive_detour adapter derives778.14um from the blocking macro extent and returns the same class of route. No shared helper/default changed. The route is an analytic candidate; body/legal-hop review and DME repricing are required before P&R.

Separately, signed alternating stage load/length regression explains most inherited FF duty error: RMS23.18→6.48ps. This is a diagnosis, not a closure model or gate.

Clock-only synthesis is live on intel2:/srv/opentallas-scratch2/claude/codex-hbm-clock-1028/build2.otrun.log, unit oth-ubuntu-1152639-1793256397. C25b legal DME delay, early-merge, inv2, rep180. No route submitted. Initial stage estimate retained; actual tap-wire fit must replace the provisional stage-wire tap coefficients before route.

Actual compiled paths disprove the internal DME score: corridor internal max119.7ps, same stage polynomial on exported paths1647.67TT/1424.27FF,32/31regions above150. These are planning diagnostics, notSTA. Source root cause: delay mode prices direct Manhattan lengths, then export adds unpriced legal detours; non-snake leaves interpret tap distance inum asps despite calibration. Shared physical_leg pricing fix is owned by FLOW clock_tools on codex/dme-actual-1029@5c882841e; HBM reuses it experimentally, no duplicate tool edit/adoption.

BodySiteMap adapter preserves1.62x.27 nativeCKINV footprint and currenthalos before DME; guards reject plannedsnakehops>450. Current street_body uses pins'updatedPHYtuple and remains FAIL (8longhops, nominal281.6, compiled model2563.97TT). It is retained; no route/STA.

TOPKdirect-mode regional-clock receipt topk_regional_clock.json confirms selector.selected_line launchclk_ctl and link.selected_line captureclk both T010 in the explicit compiled tree. This is region identity only, unsignedparentbudget views, noSTA/signoffclaim.

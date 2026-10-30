# A0 electrical closure: current diagnosis and internal channel rebuild

This is work in progress, not a passing physical or electrical view. No RTL,
cycles, parent pins, outline, child master or Liberty files changed.

Existing B hold guard is reproduced from its exact cts_prehold checkpoint.
Rawleaf-input 2009 violations / -129.249 ps; register-register 1890 / -72.747;
reset removal 3 / -23.970; ROM reset 1 / -0.657. Input frame +8.025 ps.
Two tied output paths are diagnostic, not a new signoff ruling.

The worst rawleaf input has launch clock538.61 ps, macro clock523.59 ps,
library hold171.73 ps and unchanged25 ps uncertainty: data585.72 ps vs required
714.97 ps. Equal stage count misbalances macro long-wire stages against shorter
register stages. Shared electrical-latency compiler support is owned by FLOW.

A separate placement root cause was found from the actual ODB: real macro
rows use4.32 um halos, but the clock generator hardcodes5.8 um. It therefore
erases a physically legal2.16 um column and sends two pipeline FFs13.6 um apart
to separate clock leaves~80 um away. Actual narrow strip fill is71.3%; adding
pair-clock leaves/drivers would exhaust it. Internal rawleaf columns are therefore
moved+2.16/+4.32 um to double the legal strip width to4.32 um. Reserve its central
2.16 um for clocks. Projected combined fill49.67%. Wholecore pins/outline stay
unchanged. All2525 affected actual NL direct data edges remain<=405 um after
exact child-pin translation,0 newly failing. NK right outline margin12.316 um.
The render was personally viewed; geometry verdict is PASS-COND for fresh
FLOORPLAN/PLACE only. CTS/route and adoption remain held.

Fresh NL prototype: intel2:/srv/opentallas-scratch2/claude/codex-qc-a0-0336/
physical/nl_widen, ot-run unit3885703/client3884597, container
codex-a0-widen-place-0336, logs widen/place.log and widen.otrun.log. It reuses the
exact unchanged synthesized RTL vehicle, then rebuilds all floorplan/place stages.
397 graph-home centers move<=0.966 um out of reserved columns. No old placement
is copied. Fresh placement legality/density/reach and electrical modeling are pending.

The connectivity-only analytic plan pairs3649 register groups in17 functional
clock domains, but still FAILS: calibrated hold model p50 -119.9 / p05 -151.3 ps.
No physical run was launched from that failing estimate. Results-local electrical
models are diagnostic. Their private compiler flag allows unequal depth only for
analysis and REFUSES installation. The all-leaf model exposed an O(N²) deferred
node-set construction in shared core_infra.compile_slice; FLOW has the diagnosis.

All run artifacts live at intel2:/srv/opentallas-scratch2/claude/codex-qc-a0-0336.
Original failed B and current jobs are preserved. No new owner question.

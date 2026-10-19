Column-station detailed-route/native final packet

Exact submitted jobs qfd_c_xstn_safe-safe1-ac5cc8826 and qfd_c_xstnw_safe-safe1-ac5cc8826. Component source ac5cc88266b6 (scoped REVIEW-only suffix), gate consumed-source cbb09ff42; geometry/snapshot/current-rule binding unchanged from xstn_child_attempt2. Both daemon jobs reached READY after collection rc0; detailed-route verdict CLOSED. This is component closure evidence only.

qfd_c_xstn_safe: TTsetup+320.74ps, FFhold+25.83ps, DRC0, SS sensitivity+185.66ps (nonbinding),699/699registersclocked; TT boundarymean/min/max{'clock': 'core_clk', 'mean': 140.3, 'min': 121.7, 'max': 158.3, 'n': 599, 'kind': 'boundary'}, FF{'clock': 'core_clk', 'mean': 118.7, 'min': 100.3, 'max': 136.2, 'n': 599, 'kind': 'boundary'}

qfd_c_xstnw_safe: TTsetup+343.92ps, FFhold+19.84ps, DRC0, SS sensitivity+256.89ps (nonbinding),699/699registersclocked; TT boundarymean/min/max{'clock': 'core_clk', 'mean': 136.2, 'min': 118.5, 'max': 151.9, 'n': 599, 'kind': 'boundary'}, FF{'clock': 'core_clk', 'mean': 115.0, 'min': 97.1, 'max': 130.7, 'n': 599, 'kind': 'boundary'}

Native routed-insertion IO re-STA uses6_final.sdc and actual routed extracted parasitics, with all699registersclocked and599classified boundary registers, no negedge/noarc/inverted samples. TT setup and FF hold are binding; the daemon legacy metric name ss_ps actually contains TT setup here (setup_corner=tt), SS sensitivity remains separate. No TT diagnostic hold is substituted.

Three admission benches each completed ok in daemon: lint, primary PASS, mutant expected FAIL5994. Both exported TT/FF/SS abstractions complete rc0. child_lint PASS with no fails/warns, PG M5 full coverage89%spread, strapM6,0blocked-above/blocked-same facepins,0pockets. Complete view/native6_finalODB/SDC/SPEF input hashes are in final_native_inputs.json; remote immutable paths retained. Views remain in daemon record/views until coordinator record/merge handling.

All six native final PNGs personally viewed: each component/layout/{floorplan,density,congestion}.png. Continuous standard-cell rows, no macros, expected full-face pins,90.72x129.6 shape; final fill3.9% remains ROOT's scoped pin-bound lowutil component approval. Congestion images show no flagged cells; final DRC0 confirms detailed routing.

Parent remains UNQUALIFIED: legal endpoint405reach, selected A0 native views, clock compensation/reserves/phase windows, absolute sample ages/reset+2 equalization, actual reset hardening and compiler composition. Existing full parent MODELv7 is functional only. No parent adoption or timing waiver follows from these two component results.

Final routed-netlist structural replay (afterholdrepair), flatten withoutoptimization using nativeTTcell portdirections:

qfd_c_xstn_safe: final6_final.v699FF, FFmax5, ALLnonclockmax32, rawresetloads{'0': 1}, no>32violations

qfd_c_xstnw_safe: final6_final.v699FF, FFmax5, ALLnonclockmax26, rawresetloads{'0': 1}, no>32violations

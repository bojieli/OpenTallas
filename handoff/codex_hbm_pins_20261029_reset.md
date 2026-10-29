# HBM pins / physical integration handback — explicit reset PARK

No new work/jobs/merges after root reset instruction. Existing signal G2 continues; no kills.

## Source / READY
Own worktree: /srv/opentallas-scratch/claude/wt/codex-hbm-pins-1028
Branch: codex/hbm-spb-native-1029, pushed HEAD aad78cce2.
Important commits: e64c6bba8 PG-safe native SPB FF geometry; 88a8d670a signal G2 builder/review; 67c59f3a0 schema-supported 28-type variant overlay tool; 006e31f84 complete40 missing-lane driver census; aad78cce2 reserved/residual capacity diagnosis.
Original pin/PHY/actual-sidecar work remains codex/hbm-pins-1028@93d467de7 (including e8b410898 bdring/QW,876f36a2d original face census,93d467de7 actual partial connectivity census).
No uncommitted source is intentionally left.

## 28 physical types — concrete overlay
Standalone tool: results/die_hbm_1027/hbm10/c25c_type_variants.py SRC OUT REPORT LATENCY.
Concrete complete overlay tree: /srv/opentallas-scratch/claude/codex-hbm-pins-1028/c25c_types_native
Current output SHA99ed0c373ba97fe4e38e200bc2fc460ae7d7d22b85ce978c90487a732e7d9a1e, based on parent source62cc57556834b6d1a399943e6a3004f56781f62c9515495dbd7727fa95627260.
Validated0errors using parent schema856104ad2. Old own/root checkout schema rejected32 NP4 keys; those were schema-version mismatch, NOT stripped descriptors.
Parent subsequently advanced c25c_native to source6658d374cb0a8c0a452f0960fb853529da4bd834266535d88b23f2b5b7ab6021 (2ac86593b), removing16 bare reserve taps. That final update has NOT been reapplied because reset arrived. Physical geometry unchanged; next owner must copy that latest source then reapply tool once. Parent snapshots untouched.
All25 FT splits are real used-width/hop-presence differences, not bit order: NE612 vs NW611/610; NW634+612 vs NE7+absent; NW20 vs NE2; NW68 vs NE66. Three SPB/SPT types have actual connection/output-bus differences. No type-check waiver, no invented spare hardware, no cycle change. Leaf masters/geometry/pins unchanged. Type-keyed sidecars/clock/budget indices cloned; core_conns.json emitted. Distinct wrapper modules require independent G3.
NE_spb0 becomes q_spb0__physical_v1; NW remains q_spb0. Native SPB and eight-tap clock opt-ins must cover BOTH.

Next exact overlay command (ONLY after work resumes):
cp -a /srv/opentallas-scratch/claude/codex-hbm-1028/c25c_native/. /srv/opentallas-scratch/claude/codex-hbm-pins-1028/c25c_types_native/
python3 /srv/opentallas-scratch/claude/wt/codex-hbm-pins-1028/results/die_hbm_1027/hbm10/c25c_type_variants.py /srv/opentallas-scratch/claude/codex-hbm-1028/c25c_native /srv/opentallas-scratch/claude/codex-hbm-pins-1028/c25c_types_native /srv/opentallas-scratch/claude/codex-hbm-bind-1028/bind_sourcefix_report.json /srv/opentallas-scratch/claude/codex-hbm-pins-1028/bind_latency_sourcefix.json

## Complete 40 missing-lane failure diagnosis
Full sourcefix latency copied locally: /srv/opentallas-scratch/claude/codex-hbm-pins-1028/bind_latency_sourcefix.json (existing bind output; no replay).
Committed unplanned_sourcefix_census.json recovers ALL40 pairs /15,319 bits; original report examples truncate at6,637 bits.
Committed residual_lane_report.json and residual_lane_summary.txt list exact driver widths, direct lane capacities, before/after reservations and saved-use residuals, per-pair maxflow/min-cut. Reproducer residual_lane_diagnose.py.
Actual sourcefix manifest has NO plan_cells; parent confirmed no new plan-cell reservations. Therefore reserved_buses is empty; before/after-reservation capacities equal.39/40 missing pairs have ZERO residual maxflow after existing allocations. Only NW_hub→root has320 unused bits, on HOST_BOOT (320cap/0used) versus2,385 missing. This is the priced boot path, not a justified spare route; no reuse/mux adopted.
Examples: NE_sm0→hub L67m268/268 + L120m9/9, request37 missing. NW↔NE L4=2816/2816 +L96=22/22. Hub→SPB0 has no directed path even before allocations (capacity0), return has13 before/0after. No safe narrow reroute was found. No lanes/source/cycles were changed by this diagnosis.

## Latest requested task — unfinished explicit hub↔SPB0 geometry EVENT ESTIMATE
Parent requested actual632/615b links first; no speculative lane or HOST_BOOT reuse. Started read-only endpoint/corridor diagnosis; NO plan edit, route, render or final legality verdict yet.
Actual native source /srv/opentallas-scratch/claude/codex-hbm-bind-1028/hbm_top_physplit.sv confirms:
- ep_S0 .tx_frame(hb_coll_NW.tx_pin_flit[1223:612]), .tx_v(tx_pin_v[1]); epcal_NW.payload[37:19] drives8 EP calendar/control ports (19b). Total632.
- EP rx_pin_flit612 +rx_pin_v1 +phy_up1 +fault1 total615. HB_COLLECTIVE concatenations put EP_S0 in link1. NE corresponding physical EP_S3 is same local geometry.
- Current actual_hub_graph maps hb_coll_NW to virtual u_hb_coll_Q, so do NOT use obsolete stub center. Current real q1 edge master u_hb_coll_Q_edge__q1 has matching link1_{tx/rx}_pin_* ports. Direct source bit indices establish link1, but compound master projection must still be confirmed for final endpoints. EP fault/calendar soft-source providers still need physical endpoint mapping.
Current parent c25c_native STILL has SPB u_lk_S0 origin[0,34.56], not shifted103.68; full PHY/PG street repair has NOT yet been composed there. It is a required explicitly labeled dependency, not a reason to mutate parent snapshot.
Physical NW corridor sequence: NW_hub ->NW_spu1 ->NW_spb2 ->NW_spb1 ->NW_spb0.
NW_hub bbox[5140.8,6065.28,13357.44,10385.28]. NW_spu1[6117.12,4510.08,7585.92,6065.28]. Three SPB column boxes x[5806.08,7551.36], consecutive y[3006.72,4510.08],[1503.36,3006.72],[0,1503.36]. Shared x overlap1434.24um.
SPB2 XC3 macro local[1321.92,1244.16] size241.92x224.64 leaves181.44um to SPB east boundary before halos/existing FT demand. No corridor/track occupancy census done yet; cannot declare it free.
Track lower bound, not route proof: M7 vertical pitch.064, utilization cap.6 gives632*.064/.6=67.413um and615*.064/.6=65.6um, combined133.013um plus epoch/guards/other existing demands. M6 horizontal bends need corresponding capacity. Partition-owned M6/M7 signals over M5 cores are allowed; FFs and clock/die-owned legs over bodies remain prohibited.
Actual q1 edge TX pins: global x9175.776, y6477.912..7143.096. EP bbox global[5987.52,1088.64,6229.44,1486.08]. Farthest TX source-to-nearest-EP-box Manhattan lower bound8603.352um implies at least22 <=405um wire segments for that source, even before detours. NOT a priced register count or chosen latency. Need per-bit actual capture pins, legal FF bays/rows and existing cut demand to finish. Do not assume two stages for a ~8.6mm path.
Next command is read-only geometry script to collect full actual link1 pin endpoints + epcal provider, reserve candidate632/615 windows across that sequence, and solve <=405um FF-home chains excluding all hard cores/full PHY/PG/current FF sites. No such script/report exists yet; continue from above facts and committed plan/census assets. Review image before any physical probe.

## MCA reset-only carriers
Prototype helper/coupons in63b5c84b2/594c4072d; FLOW adopted narrow shared helper6ca6f950d, then hidden-payload guards d0a182153 and exact approved names933cc06fe. FLOW reports16 focused controls PASS; do not enable before both guards publish. Default-off asbuilt.reset_carrier_parts=[NW_mca,NE_mca]. Rejects macro, buses, FT, source cells, plan cells, intra_dly, transport links. Existing reset_tree.rtl_lines emits real clocked reset/START logic; no zero-cost or deleted-empty stub claim.
Baseline old-plan RT diagnostic completed: NW_mca parentNW_mcb.rst_o_1, hop362.9um, entry relayed, depth16,79 taps, release+17. Exact NEW event FF names/homes/master clock/reset must be exported from parent's single GEN/reset/synthesis event and sent CLOCK. cells=1000 is not actual netlist count. No payload cycles added.

## SPB native + shared integration
Native e64 FF banks4104/part PG-safe, <=.579fill, exact RX/ST399.966um /TX395.280um reach. Initial e53 geometry explicitly rejected (2054FF inside PHY domain andfill>60%). Full PHY tuple+103.68 fixes original4 SM street overreach to0/1192; requires PG re-solve.
Actual RTL direct→four stages adds+4 RX/ST and+4TX; old unmaterialized MODEL2RX/4TX→new4 gives+2RX/0TX. Keep both baselines. II1. Minimal miter11962 edges0diff with both mutants caught; not full EP/PHY qualification.
FLOW bridge d3d7fc341 default off; variant coverage476e2ca41 enforces both types/actual replicas. Production remains disabled: actual bound q_spb0 unavailable because global MCA EMIT abort +other strict errors. SIM contract is not production.
CLOCK candidate4eaee9497 replaces20 grid soft taps with8; covers4104 nativeFF+faces/control with max1026sinks/radius139.3um. Both SPB types need delta in one interface GEN/reset/START/CA event. No physical clock driver-placement signoff.

## ONLY live owned job — collect without duplicate / kill
Signal-only SPB G2 full4104FF /3identity nets, two full M5 macro OBS, exact e64 FF sites, M2-M7 at0.5capacity; no clocks/STA/full partition claim.
intel1 unit oth-ubuntu-1172825-1793262081 (key-cardinal). OpenROAD PID1172934 at last process inventory; hub intel2 client3761599.
Remote actual run: intel1:/srv/opentallas-scratch2/claude/codex-hbm-spb-probe4-1029/
Hub log: intel2:/srv/opentallas-scratch2/claude/codex-hbm-spb-native-1029/spb_probe4.otrun.log
Last observed iteration19/50; no terminal verdict. No duplicate. Backend bounded32GB/4CPU, OpenROAD default single thread observed.
Check command:
ssh intel1 'cat /srv/opentallas-scratch2/claude/codex-hbm-spb-probe4-1029/probe.exit 2>/dev/null; tail -70 /srv/opentallas-scratch2/claude/codex-hbm-spb-probe4-1029/grt.log'
Require valid capacity, total overflow0 and clean pin_access. global_route uses allow_congestion; exit0 alone is NOT PASS. Source markerSPB_SIGNAL_PROBE_DONE, notOT_DONE. Use existing g2.parse_grt but handle explicit completion marker honestly. Artifact probe_grt.odb, congestion.rpt, scope.json. Synthetic macro pin/envelope assumptions remain IP qualification limit.
Prior failures retained and diagnosed: probe1 LEF-only blackbox lostatlink ORD0063; probe2 scalar busLib parsersegfault139; probe3 Liberty whitespaceSTA0164. Probe4 canonical bus Lib frontend fixed and physicalGRT started. None of first3 is a physical routing verdict.

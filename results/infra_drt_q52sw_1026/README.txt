INFRA-FIRST-R5 (QC die infra) 2026-10-26: routed-clock (TritonRoute + RCX) vs GRT RC on the q52sw crop
(SW quadrant of R2-i6 clock region 52, 1951 x 1642 um, 142 clock buffers, 83 clock nets incl. the 32-driver region mesh
net ck_mesh_r52, 35 M9 tap ports). Crop db = INFRA-FIRST-R4 epyc1:/srv/opentallas-scratch2/claude/infra-r4-1026/drt/q52sw.odb.
All numbers UNCHECKED (not yet recomputed by NUMBER-CHECK). Diagnostic only, not a 12.4a gate number.

R4 DRT blow-up, root cause (measured): DRT inherits the GRT gcell grid. Kit M1-M3 tracks at 0.72 um -> GRT tile 15 x 0.72 = 10.8 um,
so a DR iteration-0 worker (7x7 gcells) is 75.6 um square while M1-M3 were remade at 0.036 um for std-cell pin access ->
~6 GB per worker (R4: 16 threads OOM at 48 GB in 28 s; 4 threads 26 GB plateau, 10 % of iter 0 in 14 min).
Fix (route_r5.tcl): GRT on M1-M3 tracks at 0.144 um -> 2.16-um gcells (903 x 760), then M1-M3 remade at 0.036 for DRT.
Result: iter 0 peak 9.0 GB at 16 threads, 14 min. (0.036-um GRT tracks -> 0.54-um gcells aborted GRT-0228 edge usage.)
The 35 off-track tap pins were NOT the cause; they were snapped plan-side to the die M9 grid (40 + 80k nm, max move 24 nm):
DRT-0422 0 (was 35); coarse-GRT RC/latency change from the snap 0.008 ps max pair (cgrt vs r4grt).

DRT run: -droute_end_iter 1 (iters 0-1), 2874 DRC left: M1-M7 shorts 219/layer = pin via stacks of all 142 buffers, which lie
inside the crop's M1-M7 partition obstructions (crop artefact: islands are not carved in the crop), M8 short 289 / spacing 150,
M9 short 62. All 83 nets have wire, every pin on the main RC component (236 floating RCX nodes, 2.5 fF, dropped).
Full-iteration run killed at iter 3 (2889 DRC, not converging because of the obstruction shorts; ~10 min/iter).
Wirelength GRT 26384 um, DRT 24974 um.

Latency model (identical for every SPEF): OpenSTA propagated arrival at the 32 mesh-driver A pins (clock defined at the 2 root-net
sinks, so absolute latency is crop-relative, NOT the die 250-ps core latency); mesh = linear RC with each BUFx24 a Thevenin source
(die_clock_mesh.lib_buf fit) at its tree arrival, multi-source first moment x 0.69; stub BUFx4 NLDM at fixed 30-ps slew; stub net
Elmore x 0.69. Tap ports carry no core-pin load (not in the crop). Mesh is routed as a 94-pin Steiner net (no straps, no NDR).

Baseline = R4 kit GRT (10.8-um gcells, estimate_parasitics, setRC, M8/M9 C x 1.3) = what the die flow uses.
                         kit GRT    fine GRT(2.16um)   DRT+RCX
 sum C (83 nets) fF      3441       3208               1994   (-42 %)
 sum R kohm              191.2      157.3              243.2  (+27 %)
 per-net C ratio med     1          0.91               0.43   (min 0.02 short stubs, max 0.90)
 per-net R ratio med     1          0.72               1.84   (max 3.17)
 mesh net C fF           1374       1296               906
 TT tap latency ps       792..865   678..764           747..820   delta vs kit GRT mean -53.2 (-79.9 .. -20.2)
 TT tap spread ps        73.40      86.62              73.06      max related-pair skew change 59.70
 FF tap latency ps       658..723   550..626           634..700   delta mean -30.9 (-53.9 .. -0.4)
 FF tap spread ps        65.02      76.05              66.57      max related-pair skew change 53.58
Reading: GRT spread is close to DRT spread here, but individual pair skews move by up to ~60 ps TT / ~54 FF -> GRT-RC skew numbers
on this crop are only good to about +-60 ps per pair; GRT over-estimates C (x1.3 M8/M9 factor + gcell-centre detours) and
under-estimates R (DRT via stacks + min-width M8/M9, no NDR in the crop) -> GRT latency pessimistic by ~30-50 ps.

Files: route_r5.tcl / route_r5_i1.tcl (crop route), run.sh, arr_pins.tcl + sta_head.tcl + arrs.sh (STA arrivals), cmp_rc.py
(comparison), cmp.json (per-net C/R for all 83 nets, per-tap latency for each SPEF/corner), logs. Big data on epyc1:
/srv/opentallas-scratch2/claude/infra-r5-1026/drt/ (i1/q52sw_drt.spef, i1/q52sw_routed.odb, q52sw_drt_grt.spef, q52sw_cgrt_grt.spef).

# Held HEAD master-plan static diagnosis

Candidate analysis only, no plan edit, freeze, kit generation or P&R. Tools are
main b7232fde4; the held plan is byte-identical to c9238048c (16 types, 326 parts).
Tracked elemA/elemB actual pin tables were staged with the plan. One ot-run job,
32 GB / 2 threads, unit3356935-1793034681 on epyc1, completed exit1 (model FAIL).

Traffic model: 362 paths (328 lanes,34 internal),198326 bits,77723.708 bit-mm,
294 zero-length centroid paths.372 road segments,132 station bays,336 repeater
bays; max gap401.742um,0 reach gaps. Max bay fill49.6%; peak corridor use37.9% M4,
49.8% M5;0 blocked sections or leftover-M8/M9 roads. Reach, bay fill, corridor,
entry-pin allocation and lot fit pass **this centroid/static model**. It does not
certify indexed-bit/epoch transport or actual routes.

Clock shield, regional IR, tree balance/skew, lattice, clock repeaters,
containment, footless stubs and FT inputs are NOT RUN: no clock mesh or IR was
supplied. The infra-sites FAIL includes unknown island clock demand/porosity,
not a demonstrated physical shortage; all its completed checks pass. Clock-sites
also identifies the hd_serdes planned tap inside PHY, a real placement issue.

Clock/core failures require one structural event. Four elemA corners are319.68um
from the proposed centre and elemB278.824um, beyond200um. The model proposes a
2x2 internal H-tree/island pattern (leaf reach158.836/138.826um). Existing plan
core tap latencies415.627A/378.756B offset the250 target by165.627/128.756ps;
they do not qualify common core timing. Analytic centre-entry prediction forA
is270.2TT/216.1FF and fails the TT upper bound by0.2ps; its calibration RMS is21.1ps,
so it is planning evidence, not measured closure. No padding or early-clock fix
is proposed.

The clock-entry report has a schema limitation: master_plan.py looks only for
`<core>.ck`, while these actual core pins and existing taps are `.clk`. Its five
"no plan clock tap" labels are therefore misleading. It also uses proposed
centre entries by default, not the actual native pin locations. This does not
clear the real mismatch: direct transforms of the tracked native pins give:

| Core | Actual placed native clk | Existing plan tap | L1 mismatch um |
|---|---|---|---:|
| A0 MX |310.860,8.682|341.112,8.710|30.280|
| A1 R180 |395.612,8.682|365.400,8.710|30.240|
| A2 R0 |310.860,697.790|310.872,704.282|6.504|
| A3 MY |395.612,697.790|395.640,704.282|6.520|
| B R0 |216.042,991.980|209.574,991.992|6.480|

Native core-local clock pins areA293.580,317.630 andB0.042,257.580. A future common
clock-entry event must publish the actual port name/position together with the
new internal tree and regenerate the partition tap geometry. The held baseline
cannot be adopted by relabeling the report.

Visual review of master_plan.png: repeated core islands remain in regular
paired rows, a continuous wide central vertical channel carries the model trunk,
outer and top/bottom corridors remain open, and no red reach-gap marks appear.
This is a static model image review only; the output slices remain unfrozen.

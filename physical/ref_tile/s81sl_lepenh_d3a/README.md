# s81sl_lepenh_d3a -- dsdv_slice_lepe_nh landed parent, DIAGNOSTIC stand-in kit (DRIVE-S81-LEPENH 10-20)

Built by ../s81sl_lepenh_d2/mk_d3.py (read its docstring: d2b gate facts + d3 changes). **Not bindable, never submit** (stand-in children).
Same RTL/landed record as d2 (16e530953): native census PASS max 32 loads (d2b gate native_census.json, 75,363 roots).

## d3 changes vs d2
- real lep_nh size 475.2x561.6 (r5a), channel 129.6 -> 172.8 um, lep|lane gap 43.2; ro_e/ri_e <-> ro/ri bit-aligned (LEF checked: ro_e[0]=ro[0] y 2596.128, ri_e[1103]=ri[1103] y 3149.472)
- lep sl_f at the S channel corner, lep fault at the S lane corner; parent fault pin E y 2500-2504 (below lane0), rst_n E 2436-2440 beside ck_S
- d3a: port flops (u_lpr_root, u_lpo_fault) NOT anchored at pins (OT_OFLOP_PORT_RE matches no port) so the CTS sink boxes stay on the channel; PD 0.45

## SAFE-DESIGN checklist (parent level; items as d2 README unless noted)
1 Pins PASS (children register their pins; parent ports are 43.2-um abutment hops; reset root + 2 K fault out_regs).
2 Reach: landing channel 172.8 um, line ports bit-aligned; rst_n / fault E-face wires ~0.5-1.0 mm to the channel are quasi-static (reset / status), timed in->reg / reg->out; gate measures.
3 Fanout PASS (census max 32). 4 Depth PASS (ring write + one read stage per chunk). 5 Storage WAIVED (landing contract: D=4 fixed-latency rings).
6 Floorplan: children on 43.2 lattice; aspect 2.35 WAIVED (die-plan slice column); std-cell band = channel + free area N/S of lep.
7 Clock: regional roots ck_S / ck_K with landed crossings (rings); judge spread within region <=80 TT/FF; io_hold_margin 0.03.
8 Schedule PASS: static, +3/+3 line edges (RESCHEDULE), fault +2, reset +4 (lp record).

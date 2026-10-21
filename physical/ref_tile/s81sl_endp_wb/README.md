# s81sl_endp_wb (S81-SLICE/ENDP 10-21) -- DIAGNOSTIC landed-regions gate, stand-in children (never submit, never bind)

S81-SLICE/ENDP 10-21 s81sl_endp_wb: LANDED-REGIONS rebuild of the selected72 MU end parent lepw_mu (G8 die source; DIAGNOSTIC stand-ins, never bindable). d1a/d1b/d3a/lepenhmu d1 FAILED: one ck_S/ck_K tree over the 2.8x5.8 mm slot (CTS pin spread 275-1143 ps) + one reset root u_lpr_root (in->reg -19.6/-48.6 ns). Now 4 regions S/K/ML/P with own roots, regional reset ports (no root), fixed-depth forests with fenced prefix hops, every crossing a D4 chunk-8 ring fenced beside its face, lanes abutting the endpoint, P port group landed at the face, outputs through 3 OREG relay stages; slot 3024.0 x 6825.6, channel 345.6, lp E 3, PD 0.4.

Top `ot_s81sl_slice_lepw_mu_lrb_lp` from `tools/landed_parent/specs/mu72_lepw_mu_lrb.json` (tools/s81_slice/mk_mu72_lr.py); kit by tools/s81_slice/mk_mu72_lr_kits.py.
Landings 10, flops {"landing": 34148, "pads": 0, "reset": 1199, "out_regs": 99}, lp E 3.

## SAFE 8-point review (before gate)
1 pins: PASS -- children register their pins; every input lands on a ring writer / forest stage / child pin register; outputs leave a child register or 3 OREG relay stages
2 reach: PASS (gate measures) -- line 1104 b x2 bit-aligned across the 345.6 um channel; lanes abut the endpoint (51.84 um); face->endpoint control/host runs = ring bank wires (multicycle E=3 T) for inputs, 3 relay stages (~4 hops <= ~400 um) for outputs; reset prefix hops fenced, mean S 357.0 / K 251.4 / ML 221.1 um (P local at the face)
3 fanout: PASS (in-gate native census decides) -- chunk-8 kept-enable rings + forest leaf per chunk (<= 32 loads); in-gate native census decides
4 depth: PASS -- ring read = 4:1 slot mux + chunk decode; no parent logic beyond rings / relays
5 storage: WAIVED (landing rings D=4: contract storage, not arrays) -- WAIVED rings (landing contract D=4)
6 floorplan: PASS (die slot fixed; macros dominate area, parent std-cell fill low by construction) -- children on the 43.2 lattice; std-cell bands = channel + lane street + free area; slot 3024.0 x 6825.6; PD 0.4
7 clock: PASS (child-flop spread <=80 TT+FF per region = gate verdict) -- 4 local roots ck_S / ck_K / ck_ML / ck_P, each tree = own children's clock pins + own fenced ring halves; every crossing landed; u_sl's 9 other real roots pass straight to the slice (single-ck stand-in here)
8 reset: PASS by construction -- regional rst_n_S/K/ML/P, forest DEPTH 10 on its own clock (+10 edges at release, one die edge), reset on control/valid only

## Priced cycles (calendar, S81 MU.S81.CAL)
- every landed net (line ro/ri 1104 b each way, sl_f, MU land wr/cmd/ret, P->K mu_c, P->ML mu_rc): +4 edges (G8 source: +3 on the S<->K line and MU land; P entry is NEW: +4 on mu_c / mu_rc)
- outputs mu_rt / fault: 3 OREG relay stages (G8: fault +2, mu_rt 0) -> fault +1, mu_rt +3
- reset release: +10 edges on every region (die releases rst_n_S/K/ML/P on one edge)
- die obligations: 4 regional roots ck_S/ck_K/ck_ML/ck_P + 4 regional resets per end parent (ck_P/rst_n_P NEW at the lane face)

Stand-ins: STANDIN_NOT_A_VIEW in standin_views/ (slice c1x_k8_cap5r_lp, lep_mu_*, lane safe8_ntf); real dsdv_mu_land view.

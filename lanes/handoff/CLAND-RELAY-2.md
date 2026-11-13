# CLAND-RELAY-2 handoff (successor of GEN-CLASS-1; COORD is the coordinator)

## Scope
Reader-START relay (RSTREP-1 form, COORD-approved) proof + READY. Branch claude/cland-relay-2-1112 = GEN-CLASS-1
claude/cland-hop-maxwire-1112@9b9a767b387 rebased clean on origin/main 7073a6b4a5 -> be6b22d72e (not pushed yet).
Proof branch (local only) claude/cland-relay-2-proof = be6b22d72e + cherry-pick of HEAD-ROUTE-1 ad61fd322b (RA=0) -> d3dfd8630c.

## Worktree
epyc9 /srv/opentallas-scratch2/claude/cland-relay-2/wt (worktree of epyc9 moved/home__ubuntu__OpenTallas repo).
Currently checked out: claude/cland-relay-2-proof. Untracked links at the root (never stage): native_domains assets core_pins
lat macro_rects_hd_*.json -> kit-ops-1/head_rp18c/prep (gen needs them, as in kw45 src).

## Proof kits (plan = kit-ops-1/head_rp18c/prep/source_plan.json 53d5e794, sidecar 0ff8152f; env as the wave)
- hd_turn_b: epyc9 cland-relay-2/proof_turn_b/gen/hd_turn_b (plain gen, private_raw 0 so = wave kit). Diff vs
  HEAD-ROUTE-1 proof2_turn_b kit: only relay+RSTREP10/PLACEREP, landing_placement/ft_hop_maxwire (branch), file order.
  Route+signoff: ot-run client localhost, log ~/cr2log/turn_b_route.log.
- hd_spn_wshim_rx: epyc9 cland-relay-2/proof_wrx (wave_export.py = wave kit_rtl export, token compare recorded in
  rtl/token_diff.txt; then gen --kit-rtl). Route+signoff log ~/cr2log/wrx_route.log.
- Baseline already done by GEN-CLASS-1 (rp16, WREG+START, no M8 grant): epyc4 gen-class-1/proof/wrx_rs signoff:
  slew 0/0 TT/FF, setup +13.1, hold FF port-only NEEDS_PARENT (core 0), DRC 0, fanout WARN 4 (fo 65).

## Results so far (11-13 ~01:00)
- turn_b relay build (proof_turn_b): DRC 0, TT setup +101.95, slew TT 1587 / FF 5 (proof2 1408/108), hold FF -16.78 / 33.
  Slew nets (ana/relay_tt, ana/relay_trace): 31/35 = WREG write enables u_wen (explicit rp18 cfg write_chunk 64 ->
  128 leaf loads each, BUFx2 fo64 split), 4/35 = reader-START copies g_x[1,2,3,8] (65 loads each). Long-net/origin
  violators (424 ps) gone.  Hold: 0 land-ring endpoints; 32 u_ft_t_s0->s1 + 1 u_rrl_12->u_cland_rst_t_i, all
  inter-tap zero-logic hops (clk/clk_t4 -40 ps FF source latency vs clk_t2/t3; flat 40 ps TAP_WINDOW FALLBACK).
- RA question (ana/grt_{A,B,D}, GRT-only on proof2 5_1_grt.odb): design slew count M8+RA0 852, M7+RA1 874, M8+RA1 923;
  the 39 cland slew nets: wire C mean 15.60 / 15.59 / 15.84 fF, max load slew 340 / 349 / 347. RA=0 not the cause.
- wc16 variant: plan copy pd_wc16 (hd_turn_b landing_ring_wreg.write_chunk 16), kit proof_turn_b_wc16, log
  ~/cr2log/turn_b_wc16_route.log.
- RTL bench rsbench/ (verilator): relay+RSTREP10 ring at K-1 == as-built ring at K on every edge, same arm edge:
  PASS 203 valid cases / 26194 edges; mutant (K unchanged) 0 match.
- Corrected K lists (kd/*.txt; explicit WREG not double-counted): HEAD 51 buses/389 inst/21 types, 11 boot+1;
  KV 828/2260/34, 867 boot; QC 135/231/9, 135 boot; S81 0 (not strap form); HBM no sidecar.
- lane_asbuilt_latency (lat/): KV vN2i PASS 2404, S81 r12bA PASS 873, QC qcs28in FAIL 403 (DOUBLE_PAD 144,
  STALE_TABLE 259), HBM t39w FAIL 131 (UNPRICED_KIT_STATIONS 114 ...) = pre-existing kit-station classes, not landing.

- wc16 result: TT/FF slew 99/0, setup +104.54, hold -15.61/50 (48 ft inter-tap + 2 u_cland_t_i->u_ft_t_s0), DRC 0.
  99 pins = reader-START copies g_x[2,5,6]: 65 loads (64 u_sel pins + 1 INV) -> 64-fanout split into BUFx2.
- PUSHED hub claude/cland-relay-2-1112@77c591e314 (rebase + evidence results/cland_relay_2_1112/). Worktree now on it.

## Next
1. Wait for both routes; read signoff.json (drv slew TT/FF, hold_ff core vs port, setup).
2. RA question: compare cland-net per-layer wire vs a cheap RA-on / no-grant reference (rp17 turn_b if one exists).
3. K lists (kdelta_list.py), lane_asbuilt_latency.py one bind per die.
4. Push claude/cland-relay-2-1112 to hub, post ONE READY, stop.

## 2026-11-13 00:52 READY posted (branch c08c2078ea); lane STOPPED. Open: asks (1)-(4) in the READY.
- wshim_rx rp18 proof: DRC 0, TT +6.37, slew 102/2 (99 = reader-copy 65-load nets), hold core 0.

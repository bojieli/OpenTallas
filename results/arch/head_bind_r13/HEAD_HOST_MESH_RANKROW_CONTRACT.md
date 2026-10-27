# s81_head host / mesh / rank-row contract (spec item for HEAD.BIND), DRAFT

HEAD-CORE-R13 draft, 2026-10-27 03:13 PDT. COORD-decidable; the owner gave no input. Everything comes from RTL, specs and evidence that already exist. Nothing here invents a codec, ties a pin or truncates identity bits.

- Refs: origin/main = 262d070384. 9412fd850b and d0eb3d3d01 are NOT ancestors of main. Their best64, host276, beat_link and head_row_map files are byte-identical on main (blob compare, CHECKED). rank_merge_hsf0 differs (main 4fdfa9a1 vs d0eb3d3d01 ac4848af).
- Tags: **CHECKED** = I recomputed it from the RTL or source at that ref. **UNCHECKED** = copied from a log or lane line.

## 0. Beat protocol all three links use (rtl/dsrom_sys/s81_head/ot_s81hd_beat_link.sv@main)
- Port = P+1+BW wires, `{bi[BW-1:0], vb, pay[P-1:0]}`, with BW = max(1, clog2 N).
- Fixed phase, no credit. Rate is at most 1 word every N cycles. A rate, order or pad violation is a sticky fault.
- Latency: RX valid at t+N+1+S edges (S = relay stations). CHECKED from the header and the RTL.
- So each extra beat costs exactly +1 edge, and the one-beat form is t+2+S.

## (a) Host frame: 553-b HSF0 record on the 276-wire host lane
**Arithmetic (CHECKED):**

| Option | Formula | Wires | Rate | Edges |
|---|---|---|---|---|
| N=2 | P = ceil(553/2) = 277, BW = 1 | 277+1+1 = **279** | 553/2 = 276.5 b/cyc = 331.9 Gb/s @833 ps | t+3+S |
| N=3 | P = 273 (explicit), BW = 2 | 273+1+2 = **276** | 553/3 = 184.3 b/cyc = 221.3 Gb/s | t+4+S |

- N=2 does not fit 276: 2 x (276-2) = 548 < 553.
- N=3 capacity is 3 x 273 = 819 bits, so 266 pad bits in beat 2 must be 0 (RX checks them).
- Net cost of N=3: **+1 edge vs N=2**, +2 vs one-beat.

**Existing RTL that implements N=3 (all on main):**
- `ot_s81hd_host276_tx/_rx` (rtl/dsrom_sys/s81_head/ot_s81hd_host276.sv@9412fd850b = main 0124…/aadfa14c; W553 N3 P273).
- `ot_s81hd_ctl_core.sv` (u_hr, u_ht) on the ctl side.
- `ot_s81hd_host_ep_core.sv` (u_ctl_rx, u_ctl_tx) on the host side (bceaec7caf ⊂ main).
- `h_tx` = {job_active, host276}, so 277 wires. `h_rx` = 276 wires. This is in the candidate plan results/arch/head_rtl3_1026/candidate.json (CHECKED).

**Evidence (UNCHECKED):**
- Lockstep 1024 frames plus 1024 high-bit mutants (results/arch/s81_head_source_1025/transport_1026/gate.json). It records the sampled delta as 3 edges / +2 vs one beat, by its own sampling convention. tools/s81_head/head_host_model.json says 4 edges without relays, which agrees with the formula.
- Real 2-core HBC→HOST276→CTL coupon: 7 CSR writes + 512-b HFWD, payload mutant caught (PATH-S81 / HEAD-RTL 20:50).

**Demand (CHECKED from head_control_model.json + ctl_core):**
- ctl→host carries RESULT (type 9) and STATUS (type 8) through one-entry holds. That is about 2 frames, or 6 lane cycles, per position, against an 8269-cycle SK11 replay per position.
- host→ctl carries CSRW (once per job) and HFWD.
- XB/x loads do NOT use the host lane: they come from the stage ring, lepk 80 x 1024 b.
- The 221 Gb/s N=3 rate is therefore not binding.

**Recommend N=3 at 276 wires (h_tx 277 incl. job_active), i.e. keep what main implements.**
- It needs no widening of the spine/host FT stations (36 per ADAPTER.md, UNCHECKED). The 279/280-wire option would re-kit hd_spn, hd_spn_end, hd_host and hd_ctl (ADAPTER.md COORD? 1).
- Its cost is +1 edge on a non-critical, once-per-token path.
- ADAPTER.md@main recommended (a) widen-to-279 on 10-25, before N3 RTL existed and before the rate demand was measured. This supersedes that recommendation.

## (b) Mesh: HSF0 BEST97 on mesh64
**Record (CHECKED, ot_s81hd_best64.sv@main):**
- BEST = header[15:0] + identity record[96:16]. 96-16+1 = **81 identity bits**, 97 live bits in total.
- Canonical form has frame[552]=1, type frame[3:0]=1 and payload[551:97]=0. TX raises a format fault otherwise. RX rebuilds `{1, 455'0, body}`.
- user10/position21 inside the 81 bits is UNCHECKED here. It comes from source README@main ("81 live bits including user10 and position21").

**Arithmetic (CHECKED):**

| Option | Formula | Wires | Edges | Verdict |
|---|---|---|---|---|
| mesh64 | W=97, N=2, P=62: capacity 2 x 62 = 124 ≥ 97 (27 pad) | 62+1+1 = **64**, = plan bus 64 | t+3+S, +1 vs one-beat | **chosen** |
| one-beat | P=97, BW=1 | 99 | t+2+S | needs widening |
| mesh66 (ADAPTER.md@main row "W 64 N 1") | 64 data + vb + bi | 66 | — | **rejected**, see below |

- mesh66 assumed a 50-b "local best + tag" summary. Per source README@main, that summary silently drops identity bits.

**RX direction (CHECKED, ot_s81hd_mesh_ep_core.sv@main):**
- The endpoint returns 110-b words {ep_fault12, copy, BEST97} (12+1+97 = 110) with N=2, P=62, again 64 wires.
- Copies A and B are both delivered, so one peer record pair takes 4 cycles.
- There is a burst FIFO with BQ=7 (HEAD-RTL-4, COORD 22:59). Its depth is to be frozen from mesh_bq_bound.py at the worst-case production replay stall (UNCHECKED).

**"515th channel-board bit": resolved, not a die bit (CHECKED in ot_s81hd_mesh_lane, mesh_ep_core.sv@main).**
- `lrx = {rx[512], rx[513], rx[511:0], rxen}`.
- rxen is a locally registered receive-valid. `chb` is a parameter strap (host_ep_core CH_B, lep0N CH_B).
- The 514-b coll bus = {st[1]=live, st[0]=fault, rx512}, which matches ot_s81hd_serdes_link (CHECKED). It needs no widening.
- Equivalence with the layer-die wrapper is UNCHECKED (source README@main line 31).

**H4 276 vs 278: moot.**
- The candidate deletes tl/ca/cb, because `ot_s81hd_lep0N_noidx_core` selects IDX_EN=0 (lep0N_core.sv@main:75-83, CHECKED). Under IDX_EN=0, tl is unread and ca/cb are structurally absent.
- The deletion goes into the next single HEAD PLAN-DELTA (COORD 22:21).

**Recommend mesh64 2-beat BEST97 (implemented: ctl_core u_tx/u_rx, mesh_ep_core), no mesh66, H4 removed.**

## (c) Rank-row map
**Source (CHECKED):** tools/s81_head/head_row_map.py@9412fd850b = main. It walks the actual directed 565-b chains (tiles + turn_a/turn_b) of 6 spines x {W,E} x 22 tiles.
- That is **264 slots/die**.
- 129280/128 = **1010 bundles**. ceil/floor of 1010/4 gives **253/253/252/252** active per rank, so **11/11/12/12** dark (TEN=0).

**Bases (CHECKED):**
- c_rbase = 0 / 32384 / 64768 / 97024, from prefix sums x 128. The last rank ends at 97024 + 252·128 = 129280, so the map is exact with no overlap.
- Controller convention (CHECKED, ot_s81hd_ctl_hsf0_static.sv@main:283): global row = local row17 + c_rbase.
- c_rbase is 17 b, loaded by host CSRW (ce_rb, ctl_hsf0_static.sv:464; "CSR 4 rbase" per HEAD-RTL-2 note, UNCHECKED). Its max of 97024 < 2^17, and the max local row 252·128+127 = 32383 fits 17 b.

**Evidence (UNCHECKED):** gate.json rows: coverage 1010/129280, 0 dup / 0 missing, broken-chain mutant caught.

**GAP (CHECKED):** the map is NOT realized in any bound RTL.
- The generated wrapper results/arch/head_rtl5_1026/cand/gen/ot_s81hd_tile_p.sv:226 hard-codes `ot_s81hd_strap #(.ROW0(0),.TEN(1))`.
- s81_head_top.sv passes no ROW0 parameter, so 0 occurrences.
- A bind today would therefore give all 264 tiles rows 0..127 with TEN=1.

**Needed:**
- Per-instance ROW0/TEN as declared ID straps, which OWNER 10-25 (B) allows: "18 same-footprint TIEHI/TIELO cells" per gen_plan.py@main:296.
- Per-rank weight ROM images at weight_row0.
- A per-die c_rbase CSR value in the host programme.

## (d) hd_serdes 514-b coll_o0 → 512-b u_phy.rx, and the raw PMA 544 binding
**Exists (CHECKED):**
- The plan (gen_plan.py@main:349-354 and candidate.json) binds `coll_o0[514]` to the leaf `u_phy.rx` of `ot_pdie_serdes`, whose rx is 512 b and st is a separate 2 b.
- The generated candidate wrapper (cand/gen/ot_s81hd_serdes.sv:606-610) instantiates `ot_pdie_serdes u_phy(.rx(coll_o0_d[513:0]), .tx(coll_i0_q))` and nothing else.
  - **clk, rst, st, pma_tx, pma_tck, pma_rx and pma_rck are unconnected.**
  - coll_o0_d[513:512] is undriven, which is the live/fault bits every endpoint reads.
- The strict HEAD_DIE_PORTBIND PASS does not see this: die_port_bind checks only the 326 partition instances at the die top, not leaf pins inside the wrappers.
- `ot_s81hd_serdes_link` (rtl/dsrom_sys/s81_head/ot_s81hd_serdes_link.sv@main 40b869fba) packs `coll_o0[513:0]={st,rx}` with 0 added cycles and exposes the pma_* ports. tools/s81_head/serdes_link_eq.py exists. It is not in any type's sources.
- ot_pdie_serdes@main:
  - `pma_tx[543:0]`/`pma_tck`(=clk) out and `pma_rx[543:0]`/`pma_rck` in.
  - pma_rck is a recovered-clock domain with its own reset synchronizer, crossing to clk via ot_s81_rate_match.
  - rst is active low.
  - For 12 hd_serdes, that is (545+545) x 12 = **13,080 behavioural pad bits** and **12 extra pma_rck clock inputs** (CHECKED).
- die_io.json@main has 12 `phy_macro` reservations with "signals 26" each (6 lanes x 4 + 2 refclk; basis UNCHECKED).
- The die top has only clk/rst_n/start (CHECKED).

**Remains (owner lane, RTL/tool work, not decided here):**
1. Switch the hd_serdes contents to ot_s81hd_serdes_link with bind ck=clk, rst_n=rst_n (plan delta).
2. Give gen.py rtl an explicit partition/die IO pin class for pma_*. Today it accepts only clk/reset/bus/net leaf binds, so the pads cannot be expressed without inventing flops or ties.
3. Decide the PMA boundary form: (i) 544-b behavioural word pads at the die top, or (ii) ot_pdie_serdes treated as a hard PHY macro whose pma_* pins are its die_io phy_macro terminals and are therefore not die-top RTL ports.
4. Constrain pma_rck as a per-SerDes clock (SDC/CDC), with the rate matcher as the only crossing.

## (e) What the strict as-built bind needs beyond (a)-(d)
**Providers (CHECKED):**

| Plan | Providers | Result |
|---|---|---|
| main canonical die_plan.json (13 sources) | ctl/host/mesh = self-instantiating wrappers, so STUB; lep0N = `dsdv_slice_lepw_mu.LP` (not a module) | module_missing 4, FAIL (results/arch/head_rtl5_1026 canon) |
| candidate (64 sources + 18 supplement) | ctl = ot_s81hd_ctl_core, host = ot_s81hd_host_ep_core, mesh = ot_s81hd_mesh_ep_core, lep0N = ot_s81hd_lep0N_noidx_core, all REAL RTL on main | HEAD_DIE_PORTBIND PASS: 326 inst, 100 files, 0 open, tied or undriven |

- The candidate is NOT adopted. COORD 22:21 put it into the next single HEAD PLAN-DELTA together with the infra-first re-plan. D-INFRA-FIRST-HEAD is still PENDING (HEAD-KITS-1 01:43).

**Recipe:**
- Main has no s81_head as-built recipe: no physical/die_plan/s81_head/bind/, and the plan has no `asbuilt` key (CHECKED).
- The S81 precedent is the repo-relative physical/die_plan/s81/bind/asbuilt_b178_coll.json:
  - base `../../../..`;
  - netlist physical/die_plan/s81/bind/inputs/die_b178.v;
  - 387 files, 0 absolute (CHECKED);
  - map_file inputs/map_b178.json;
  - straps.
- It runs as `bind.py elab|bind --strict <plan> --asbuilt <manifest>` (results/token_pass/tokds_1026/s81_877_strict/run_gate.sh) and is gated by tools/die_plan/manifest_paths.py, listed in test_manifest_paths.py OPERATIONAL.
- The old asbuilt_s81_r8.json still has 391/391 absolute files. It must not be the model.
- The manifest proposal is in head_bind_manifest_proposal.txt.

**Also owed before a whole-head bind is meaningful (from head_control_model.json/head_host_model.json@main, UNCHECKED):**
- Compiled production HBC BOOT_HEADER/BOOT_COMMIT dates and START/ISS_OFF/ISS_PER/MRG_DL. Their defaults are all-ones (not admitted), and only TEST-profile dates exist.
- CLOCK_RESET_ID.
- A real Markov/DHRES/ROWS producer for MTP. AR is complete without it.
- The hd_serdes fix in (d) and the ROW0/TEN realization in (c).
- A leaf-internal wrapper connectivity check. Without it, (d) passes silently.

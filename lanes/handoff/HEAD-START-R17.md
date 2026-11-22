# HEAD-START-R17 handoff (2026-11-21 18:5x PST)

Goal: the HEAD transport bench PASSes functionally on p6 (every lane at plan latency, plus mutants), then one combined HEAD apply.
e1a (hd_lep0N shelf + hd_serdes clock rows, plan 00b2abf6e7a6) is owned by FABLE-FIX-HEAD-LEP0N-R3. e1b = p6 START delta, rebased onto e1a.

## Inputs (frozen copies; nothing reads the live tree)
- p6 plan 58f896b3fcbe, sidecar facc71b93198: epyc10 /srv/opentallas-scratch2/claude/head-start-r16/prep_p6b; bind = head-start-r16/bind2/bind.json.
- provider_p6r = provider_p6 + 9 START reset relays (relay_over.py, max half-hop 286.2 um, span 72 + 4 <= settle 88), at head-start-r16/provider_p6r.
- Completed top + stages of p6/provider_p6r: epyc10 head-start-r17/completed_tr11, also copied to epyc7 head-start-r17/w7.
- ring_declared.json committed main add52afbbbfa physical/die_plan/s81_head/ring_declared.json. Declared common latency, types {}; the original is unrecoverable.

## Findings
- The bench never passed on any plan. Before main db6962d5134 it was vacuous.
- Ideal-clock bench (tr7/8/10, 78 failing) cannot model count-aligned HEAD:
  - 19 rings fall below the read window at d=0;
  - the per-part START origins are within +-1 of n_nominal, and these deltas explain the 19 tile-chain +-1 failures.
- tr9 was invalid: the stubs used the global tb cycle counter.
- Phased bench (`gen --phases`, tr11 onward, including Codex tr12-tr24) was INVALID too. Verilator 5.050 rounds fractional delays to whole time units (1 ns = T/2): epyc7 head-start-r17/dlytest shows #(0.4) -> 0 and #(6.6) -> 7.
  - Codex's 53 K candidates (tr21/tr22) are artefacts: do not adopt them.
- Fix in lane clone epyc10 head-start-r17/repo (NOT pushed yet), tools/s81_head/head_transport_depth.py + test:
  - `phases` subcommand (tree phases from the bind START-edge d; 427/427 crossings inside [d_lo, d_hi]);
  - `gen --phases`: tb under `timescale 1ps/1ps`, integer-ps delays;
  - stubs count their own clock edges;
  - a shared region clock port (clk_region_host = host_nstrip/e/w, 39 ps spread) takes the mean phase when the spread is <= 60 ps.
- Running: tr25 on epyc7 (`N=/srv/opentallas-scratch2/claude/head-start-r17`, tr25.sh, log intel2 ~/head-start-r17/tr25.otrun.log).

## Next
1. Read tr25. On PASS: mutants (MUTANT=st_bypass|st_double|k_plus1|bit_swap|oracle TAG=tr25_<m> bash tr25.sh); each must FAIL. Then push the tool (ot-push-main) and post.
2. On FAIL: run origin_cmp-style per-part origin vs n_nominal, with local index = floor(cyc - phase/T). Then do ring gap analysis.
3. Then rebase p6 onto e1a (00b2abf6e7a6) once R3 applies it. Re-site the lep0N START reset ports against the new wrapper exports, rerun the bench, then apply e1b.

## Handed hd_host_e items (from FLOW-OBS-GCELL-R2)
- v2 proof (epyc8 flow-obs-gcell-1121/host_e2/hd_host_e) ENDED NOT SIGNED: DRC 25, all M7 at the u_epc top edge y 60.672 (the he_epc class); TT -83.81 (19 endpoints); internal FF hold -39.50.
- he_epc M7 check: OPUS-FIX-HEAD-SERDES-R4's kit epyc7 opus-fix-head-serdes-r4/host_e_access1415_retry/gen_access/hd_host_e carries the he_epc lef_override and preflight PASS, but is not built. My private-spec was refused: epyc7 DRAINING; gen hosts are epyc10 (40 GB free) and intel2. BLOCKED on gen-host disk.

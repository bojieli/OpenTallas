# DIE-STA lane (claude/die-sta-1024, wt localhost:~/wt/die-sta)

## RESUMED 12:15 PDT (after 08:50-12:04 limit)
- Adopted: Codex-collected N512 flat capacity (73,363,456 inst, 172.82 GB, 5816.7 s, SPEF 4368 s; receipt main
  58436d2c6c results/die_sta/codex_replica512_capacity_1024.json). No live DIE-STA jobs. CP1 new proof pair is root's
  codex-cp1/reach405 (r0 DRT live, r1 not signed) -> G4 ilm-vs-flat on it when r0 routes (do not duplicate).
- MERGED main e70305aec7: die_sta.py + tests + README + results/die_sta (was missing on main -> DIE-CI sta NOT RUN).
- Next: die STA on the trial dies (s81, s81_head, qk, hbm) at TT/FF via their sta/ stand-ins.

## PARKED 18:55 PDT
- Branch claude/die-sta-1024@97fd4371ec (pushed). main has up to 96ce86b63e; branch adds: no half-period arrival wrap,
  empty-pin fix, tests 9/9, results/die_sta/trial (v1). NOT yet merged (merge after v2 results).
- Live jobs (intel2 = tolerant-swine, ot-run, die_sta.py pids): hbm_B2l:1389069 qwen_kvsys:1389720 s81:1389748 s81_head:1390005 qwen_compute:1390007 hbm_B2l:1390279 qwen_kvsys:1390349 s81:1390356 qwen_compute:1390361 s81_head:1390362 hbm_B2l:1390576 hbm_B2l:1390577 hbm_B2l:1390594 qwen_kvsys:1390617 qwen_kvsys:1390618 qwen_kvsys:1390635 s81:1390653 s81:1390654 s81:1390671 qwen_compute:1390680 qwen_compute:1390681 qwen_compute:1390702 s81_head:1390721 s81_head:1390722 s81_head:1390739 
  dirs intel2:/srv/opentallas-scratch2/claude/die-sta/trial/<die>/sta/run_ttff_v2 (logs run_ttff_v2.log;
  ot-run logs ~/coord/part-cap-logs/die-sta-run2-*.log). ~1-2 h (hbm slowest). Cancel: ot-run --cancel <dir>.
- Results: CP1 G4 reach405 ilm == flat 0.000 ps, seam PASS (TT +432.5 / FF hold +87.8 / spread 56.8). Trial dies v1:
  TT setup OK on all 5, FF hold FAIL on all 5 (table below). Capacity: full die 970 GB (no) / 540 GB --reduce (yes).
- Failures: none of the tool; trial dies FAIL FF seam hold (H-tree tap skew).
- Next: when v2 done -> `python3 /tmp/trial_sum.py` on intel2 (copy in ~/wt/die-sta? no: script at intel2:/tmp/trial_sum.py),
  copy run_ttff_v2/die_sta.json to results/die_sta/trial/<die>/v2_die_sta.json, update README.txt, commit, merge.
- OWNER?: hbm_B2l NW_sm2 tap +440 ps and qwen_kvsys hub taps (216 ps spread) need spine rebalancing before any seam
  can close hold; per-partition hold fixing cannot absorb -417/-173 ps.

## 18:50 PDT (resumed after session limit)
- OWNER DECISION ack: gate = TT setup / FF hold at 60/25 ps uncertainty (+ pin-flop spread <= 80 per AGENTS.md L32);
  everything else (SS, TT hold, FF setup, extra margins) INFO only. die_sta.py verdict already does exactly this.
- Trial-die seam STA v1 (current main plans, budget stand-ins, trial H-tree spine), seam slacks valid:
  | die | groups/bits | TT setup | FF hold (neg bits) | verdict |
  | s81 | 2151/1.06M | +654.4 | -52.5 (661k) | FAIL |
  | s81_head | 425/212k | +626.3 | -82.1 (124k) | FAIL |
  | qwen_compute | 2934/1.32M | +661.6 | -46.4 (1.0M) | FAIL |
  | qwen_kvsys | 3939/620k | +501.9 | -173.4 (437k) | FAIL |
  | hbm_B2l | 918/610k | +411.2 | -417.0 (369k) | FAIL |
  Setup is never the problem (stand-in seams are flop-to-flop, >400 ps slack). Hold fails on every die because
  stand-in seams have ~zero data delay (QN -> wire -> D) against H-tree tap skew of 50-440 ps: the capture tap is
  later than launch. Worst: hbm_B2l NW_sm2 single tap +440 ps (FF) vs neighbours ~25-90 ps; qwen_kvsys hub_* taps
  (spread 216 ps > 80 inside hub_Wi/Wo/Eo). Real partitions will add hold buffers inside each seam flop's input
  cone, but -417/-173 ps is beyond per-partition hold fixing (~1 buffer = 10-15 ps): the H-tree tap skew must come
  down (spine balancing / tap re-insertion) - OWNER? / TRIAL-HBM + TRIAL-QK: hbm NW_sm2 tap, kvsys hub taps.
- BUG found + fixed: clock arrivals in launch/capture/FFSPREAD were wrapped by period/2 (hid the 440 ps tap; slacks
  unaffected). v2 rerun of all 5 (correct spreads) running intel2 run_ttff_v2. Also fixed: empty pin connects
  in rewritten tops ('{}'); 'ports' spine == gclk 0.000 ps on routed CP1 reach405 pair.

## 14:20 PDT
- MERGED main 96ce86b63e (CP1 G4 + die-scale fixes + capacity SUMMARY).
- CP1 G4 (root reach405 pair, kits NOT SIGNED internally): ilm == flat 0.000 ps, 2 seam groups / 1533 bits, TT/FF/SS,
  ideal + CP2 branch spine. Seams: TT setup +432.5, FF hold +87.8, spread TT 56.8 / FF 46.2 -> seam PASS.
  Evidence results/die_sta/cp1_reach405.
- Trial s81_head (current plan a00cc383, budget stand-ins, trial H-tree spine): FAIL: TT setup +626 OK, FF hold -82.1 ps
  (123,852 neg seam bits; worst mesh0S->sst4/rx_i, launch 22.8 vs capture 101.6 ps clock), spread 105 ps (tW4b8,
  tW4o8, tE4b8, +1 > 80). => H-tree tap skew alone breaks seam hold; matches TRIAL-S81 OCV finding (shared seam leaf
  fallback = OWNER? item there).
- s81 / qwen_compute / qwen_kvsys / hbm_B2l running (TT ~50 min/corner; hbm ~2 h/corner).

## 13:50 PDT
- Trial dies on CURRENT main plans (die_trial.py kit + clock TT/FF, my dirs; stand-ins = one face flop per pin bit,
  spine = trial H-tree arrival per tap): intel2:/srv/opentallas-scratch2/claude/die-sta/trial/{s81,s81_head,
  qwen_compute,qwen_kvsys,hbm_B2l}/sta/run_ttff (ot-run, 48 GB/8 thr each), logs ~/coord/part-cap-logs/die-sta-run-*.log.
  die_sta fixes on the way (committed): per-bit seam slack (path enumeration too slow at 1M bits; == to 0.001 ps on
  KV), spine as ONE clock + per-tap port source latency (generated clock per tap: 3.8k-8.2k clocks stalled).
- CP1 G4 validation now possible: root's codex-cp1/reach405 pair both routed (NOT SIGNED): ilm + flat TT/FF/SS (+ branch
  spine) running localhost:/srv/opentallas-scratch/claude/die-sta/cp1_reach405 (ot-run 24 GB).
- Capacity SUMMARY committed (results/die_sta/capacity/SUMMARY.json): full die ~970 GB full parasitics (NOT feasible
  on 1 TB), ~540 GB with --reduce (feasible, ~19 h/corner, SPEF reader bound).

## Current step (08:25 PDT)
die_sta.py verdict switched to TT setup / FF hold / spread<=80 (7ba6155209).
die_sta.py v1 committed + pushed (ilm / flat / etm modes, compare, replica). Flat capacity replicas running on intel2.
Waiting for CP1-R10 routed kits (r10a epyc3:~/ot-scratch/cp1-r10/kits at GRT; r10b ~/ot-scratch/cp1-r10b/kits) to
validate ilm vs flat on the CP1 pair.

## Blocked
- CP1 validation (ilm vs flat on the CP1 pair): r10a r0 kit cancelled 07:42 (CP1-R10), r10b r0 kit container ended 08:16
  in DRT 80% (17185 viol) with no exit line (killed?); only r1 routed (r10a + r10b). Script ready:
  epyc3:~/ot-scratch/die-sta/cp1_die_sta.sh (ilm+flat TT/FF/SS + compare) -> run when r10b r0 has 6_final.*.

## Results
- OpenSTA be771a0 HAS write_timing_model, but MakeTimingModel fixes min_max_=max: clk->out arcs carry the MAX arrival
  only -> ETM hold at a seam is optimistic. Measured on the KV pair e5e6 (routed kv3_io_cor_v1 | kv3_io_ft_v1,
  intel2:~/ot-scratch/die-sta/kv): ETM vs flat seam slack off by -82 ps setup (pessimistic) / +73 ps hold (optimistic).
  => abstract = ILM (interface logic model) extracted from the routed netlist + filtered SPEF (die_sta.py ilm).
- ILM vs flat, KV pair, SS/FF/TT, 4 seam groups x setup/hold: max |delta| 0.000 ps (AGREE). ILM 2x faster.
- KV pair e5e6 at signoff (owner 08:10: TT setup / FF hold / spread<=80): TT setup +93.681 ps, FF hold +230.957 ps,
  face-flop spread TT 24.75 / FF 20.05 ps -> PASS (die_sta.py, flat == ilm). SS setup -100.8 is info only (not a gate).
- Flat capacity (replica of kv3_io_cor_v1, 143k inst, 60 MB SPEF, 16 thr, intel2): N=8 1.15M inst 2.81 GB 79 s
  (SPEF read 55 s of it). N=32/128 running (intel2 ~/ot-scratch/die-sta/rep, nohup pid 258599).

- 2nd validation: chain of 3 routed kv3_io_cor_v1 (50 seam groups, 6106 seam bits, synthetic adjacency): ilm == flat
  0.000 ps over all 100 seam checks + spread at TT/FF (ilm 58 s / 0.56 GB vs flat 82 s / 0.93 GB).
- Flat capacity (replica of kv3_io_cor_v1: 40.4k logic cells + 102.9k tapcells, 43k nets, 60 MB SPEF; 16 thr):
  N=8 1.15M inst 2.81 GB 79 s; N=32 4.59M 10.89 GB 313 s; N=128 18.3M 43.3 GB 1276 s (linear);
  N=32 no SPEF 5.68 GB, no SPEF+no tapcells 2.97 GB; N=32 read_spef -reduce 7.15 GB (parasitics 5.2 -> 1.5 GB), 502 s.
  N=512 (73M inst) running on intel1 /srv/opentallas-scratch2/die-sta/rep512 (ot-run, 260 GB).

## Runs
- intel2:~/ot-scratch/die-sta/{kv,rep}; bin = copy of die_sta.py.

## msg from TRIAL-HBM (2026-10-24 07:55 PDT)
- HBM B2r2 has no routed partitions (G3 none), so die_sta.py ilm/flat/etm have no inputs there. TRIAL-HBM times the die fabric in budget mode instead: every lane hop as flop->flop (boundary flops at plan pins, ft stations at plan sites) with die GRT parasitics, TT setup / FF hold, 60/25 ps, H-tree tap latencies applied per partition (tools/die_trial/fabric.py on claude/trial-hbm-1024). If you want a 'budget' mode in die_sta.py, the case dir is reusable; tell me in lanes/TRIAL-HBM.md.

## CODEX notes
- 2026-10-24 09:01 PDT: CODEX root collecting; N512 (73M instances) intel1:/srv/opentallas-scratch2/die-sta/rep512 live, log has link110752ms and SPEF4368197ms. CP1 validation waits valid new r10c/r10d both kits, not invalid cancelled r10b.

CODEX 10:45 PDT: N512 COLLECTED, completed09:05 (was stale markedrunning). 73,363,456instances, exit0,172.82GBpeak,5816.7s; link110.752s/SPEF4368.197s/WNS5612.451s. LegacySS/833.333ps run is CAPACITYPASS only, release timingNOT EVALUATED (max-361.39psSSinformational). Physical TAPCELL blackbox warning documented. Receipt own codex/kit-guard-1024 results/die_sta/codex_replica512_capacity_1024.json. FreshCP1 current833/TTFF proofpair runslocalhost codex-cp1/reach405; no actual CP1flat-vsETM claim yet.

## FROM TRIAL-QK 2026-10-24 12:26
- die_sta.py (main) ILM io_E5|io_E6 with die H-tree tap offsets as --spine-branch: TT +20.8 / FF +232.0 ps, ffspread 46.1/47.8 (results/die_trial_1024/qwen_kvsys/ilm_kv_p7_e5e6). Measured die tree ~240-300 ps/mm (TT) vs spine.py 60 ps/mm default: insertion KV 5.4 ns TT, QC 8.2 ns TT. Any OCV/derate on non-common clock path dominates seams (5 %: KV 544 ps, QC 852 ps).

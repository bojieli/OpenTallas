# DIE-STA lane (claude/die-sta-1024, wt localhost:~/wt/die-sta)

## RESUMED 12:15 PDT (after 08:50-12:04 limit)
- Adopted: Codex-collected N512 flat capacity (73,363,456 inst, 172.82 GB, 5816.7 s, SPEF 4368 s; receipt main
  58436d2c6c results/die_sta/codex_replica512_capacity_1024.json). No live DIE-STA jobs. CP1 new proof pair is root's
  codex-cp1/reach405 (r0 DRT live, r1 not signed) -> G4 ilm-vs-flat on it when r0 routes (do not duplicate).
- MERGED main e70305aec7: die_sta.py + tests + README + results/die_sta (was missing on main -> DIE-CI sta NOT RUN).
- Next: die STA on the trial dies (s81, s81_head, qk, hbm) at TT/FF via their sta/ stand-ins.

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

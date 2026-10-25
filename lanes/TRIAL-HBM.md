# TRIAL-HBM lane (2026-10-24)
branch claude/trial-hbm-1024 (main + claude/hbm-arch-1024 @3277b5e78b), worktree localhost:~/wt/trial-hbm
## current step
RESUMED 12:10 PDT, adopted: codex/trial-hbm-1024 @0404dd4648 (ff), live B2l_fabric_buf12_legal_r4 (epyc3 codex-hbm, GRT), legacy fab_rep_m8 (epyc2, diagnostic); killed my redundant fab_rep_avg (epyc3). B2r2 trial record committed 90a62b98ee; IR sub-run finishing; next: collect B2l r4 GRT/STA, apply tap latencies.
## results
(none yet)
## runs
## OWNER?
## 07:58 PDT
- sub-agents: H-tree clock build (tools/die_trial/htree_clock.py -> results/.../clock/), die top + PDN + IR (-> top/, ir/).
- me: tools/die_trial/fabric.py = flat die fabric case: 1.36M flops (410k boundary flops at plan pins + 951k ft stations at plan sites), ~1.2M hop nets, partitions abstract (cores block M4..top pin layer, IO PHY keep-outs M4-M9, die PG + H-tree NDR on M8/M9, M4-M7 own-logic adjust 0.5), GRT M4-M9 9.6-um gcells, then STA SS/FF (+repair_design).
- smoke window case running localhost /srv/opentallas-scratch/claude/trial-hbm/fab_win (docker 8 cpu 64 GB).
- NOTE plan vs brief: B2r2 = 2 mirrored quad tiles, ONE HBM3E PHY_N (not 4 clusters/4 stacks); asked HBM-ARCH which number the "0.55 cut" claim is.
## 08:00 PDT
- smoke window (130k nets): GRT 0 overflow 46 s; STA scene syntax fixed (OpenSTA scenes). Early finding: FF hold on 2-um abutted bf->bf hops = -2.2 ps at ZERO skew (DFFx1, 25 ps hold unc) -> every abutted seam needs hold fix even before skew.
- FULL die fabric run launched: epyc2:/srv/opentallas-scratch/claude/trial-hbm/fab_full (ot-run --mem 320 --threads 32, local ot-run pid 1051726). 1,360,342 flops / 1,155,477 hop nets. Per-bit hops: max 957 um, 14,397 > 850 um, 506 > 900 um (all L19_2 / L19m_2 into b103: per-bit spread beyond the G0 window-centre hop 849.6).

## CODEX notes
- 2026-10-24 08:54 PDT CODEX results: full fabric GRT overflow 0, TT setup -1045.06ps, FF hold -2.07ps (1277), 2,850,943 slew violations. FAIL: no closure. repair_design abort DPL-0012 = no rows in prototype DEF. Median hop 671.2um; 896100 hops >500um -> unbuffered RC dominates, not congestion; add physical repeaters and legal rows in successor, preserving this failure.

- 2026-10-24 10:20 PDT CODEX: Collected fullfabric TTsetup-1045.06ps, FFhold-2.07ps1277viol and2.85Mslewviol,0GRT overflow. adj097 fullGRT now exit0 after1h51m (epyc2 fab_adj097), noSTAyet. Legal-row repair fab_rep_m8 remains live,391kbuf31%lastseen. Do not kill. Own trial1585dcd183 enforces833ps TT/FF andpreserveslegalrows; B2r2 probes diagnosticonly, no planadoption.

- 2026-10-24 11:00 PDT CODEX: 3fd63666dc native40path data-wire probe: bareTT-51.29ps vsBUFx12<=200um TT+358.72/FF+74.46;0cycles. fabric.py optionalexplicitrepeaters correctDEF Y/A/noCLKsinks. Fullmacro-free site successor next. RealhubcoreG2r2 legalizingintel2 192GB;64GBOOMpreserved. Oldfabrepair epyc2~632kbuf43% continues; legacySS-influenced neverclosure. LegacyDIE-CI q_sfuc/q_su1 OOMsuperseded, notrerun.

## 12:35 PDT results (90a62b98ee, results/die_trial_1024/hbm_b2/README.md)
- GRT: 0 overflow M4-M9 at M4-M7 derate 0.5/0.75/0.9/0.97 (WL 676-688 m, 24-27 GB, 3 min-112 min). Hot M8/M9 windows over 0.6 budget (central hc-ring/root x12.5 y6.25, spt PHY corridors, hub W face).
- Clock: insertion 4.0-5.8 ns, seam skew 38-55 ps no OCV, 407-594 ps 5% OCV FAIL.
- STA budget mode: unbuffered TT -1045; window repair SS -95.7 / TT +83.8 (+87% area); Codex BUF12@200um TT +358.7/FF +74.5; FF seam hold -2.07 ps at zero skew.
- visual review written (README + results/geom_review/hbm_b2r2_trial_die__hbm_arch_B2__7f541aa7dee4.json); findings sent to HBM-ARCH lane file.
## 2026-10-24 14:20 PDT
- MERGED main edb8ae059a. IR windows: hub 12.7 / PHY+corridor 29.6 PASS, SM 47.0 (31.7 int), SerDes 146-203 mV FAIL; top 88/88 placed, PG PASS; gen.py %g origin rounding bug (23 macros refused) -> tools/die_plan owner.
- running: epyc3 trial-hbm/ir/full_s4m (coarse full-die PSM, IR sub-run), epyc3 codex-hbm/B2l_fabric_buf12_legal_r4 (GRT iter 1 since 11:54), epyc2 fab_rep_m8 (legacy diagnostic).
- next: collect full_s4m -> ir/README; collect B2l r4 GRT + TT/FF STA, then STA with clock/tap_latency.json.
## 2026-10-24 14:23 PDT
- MERGED main 5897a76d2f (IR README final for this pass). Still running, to collect: epyc3 container thbm_ir_full_s4m_3787090 (/srv/opentallas-scratch/claude/trial-hbm/ir/full_s4m, coarse full-die PSM; commands to record/render in ir/README.md), epyc3 codex-hbm/B2l_fabric_buf12_legal_r4 (GRT), epyc2 fab_rep_m8 (legacy diagnostic, may be killed when done).
- FOR tools/die_plan owner: gen_phys.die_flow_tcl/macro_place_tcl print origins with %g -> origins >= 10 mm rounded, place_macro refuses 23/88; place_macro um->dbu truncation fails 3 more (use integer dbu setLocation).

## PARK 2026-10-24 18:56 PDT -- sub-agent "die top (1) + IR (4b)" state
- Branch: none committed by me (brief: no git in ~/wt/trial-hbm; the lane owner commits). Uncommitted files in ~/wt/trial-hbm:
  tools/die_trial/{hbm_b2_top.py,hbm_b2_power.py,hbm_b2_ir.py,hbm_b2_render.py,ir_run.sh},
  results/die_trial_1024/hbm_b2/top/{README.md,pg_stats.json,die_io.json,real_views.json,trial_flow_summary.log},
  results/die_trial_1024/hbm_b2/ir/{README.md,power_map.json,cases/*.json,*.png}. -> lane owner: commit + push these.
- Live jobs: NONE (all finished/stopped; no thbm_* containers on epyc2/epyc3/intel1/intel2).
- Results: top: 88/88 exact placement (odb), 0 overlaps; gen_phys %g origins refuse 23 (tool bug); check_power_grid VDD/VSS PASS;
  M7-M8 vias 6.197M/6.182M; GRT FAIL overflow 394 (taps under PHY_N + UCIe keep-outs); DRT NOT RUN.
  Power est 642.7 W (SM 395 W; SerDes 12.1 W/mm2). IR exact windows rail sum vs 35 mV: hub 12.7 PASS, PHY+corridor 29.6 PASS,
  SM 47.0 FAIL (interior 31.7), NW_io SerDes 146 FAIL, spb0 SerDes 203 FAIL. Full die exact NOT COMPLETED (pdngen >4h);
  coarse x4 done (880 mV) but invalid as absolute (5-8x over exact windows; relative map only).
- Big outputs: intel1:/srv/opentallas-scratch/claude/trial-hbm/top/kit/die (die_top.odb/def), intel2:.../ir/w_*, epyc3:.../ir/full_s4m, full_exact.
- Next step: exact full-die IR with the grid written as DEF special nets (no pdngen macro grids); plan fixes for F3/F4 (PHY outline, taps out of keep-outs, SerDes at edge); SerDes own supply/dense PG.

## CODEX notes 2026-10-24 21:12 PDT (parked on Claude reset)
- Collected legacy fab_rep_m8 epyc2 EXIT0: TT+398.87ps, FF-2.52ps (204865 min violations), 1,842,032 buffers, 5h39m18.1GB; diagnostic only, NOT SIGNED, FF seam fix remains open.
- B2l_fabric_buf12_legal_r4 epyc3 still running hbm-fabric-buf12-3701110, GRT extraiter2/30 asof19:52, preserved. No duplicate run.
- Own codex/hbm-trial2-1024 checkout; draft specialnets helper at /srv/opentallas-scratch/claude/codex-hbm-trial2/specialnets.py, py_compile only, NOT RUN; writes DEF PG to avoid full-die pdngen bottleneck. Requires small-window syntax/PDNSim comparison and rendered review before any new run. No fleet jobs launched by this takeover. Full details CODEX-LOG handoff.
- 2026-10-25 01:03 PDT CLOCK -> TRIAL-HBM: B2l trial die STA with the v2 die clock (run_ttff_clk): TT +670.7 / FF -42.0 (was -417.0), spread 61/67; v6 spine (pair 34 ps) die STA running intel2 die-sta/trial/hbm_B2l/sta/run_ttff_v6. B2l's tree cannot reach the 20-ps target: 32 plan taps on PHY/SerDes keepouts, PHY_N/clk pin 1 mm inside the macro (corner-inverted, 247 ps at TT vs FF). B2m (HBM-ARCH plan) gets gate PASS 66.7/67.7 ps intra, 30.5/24.1 seam; tap fixes posted in HBM-ARCH.md. claude/clock-1024@161826bb16 results/die_clock_1024

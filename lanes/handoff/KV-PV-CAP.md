# KV-PV-CAP handoff (Opus 5.5, COORD split 11-23 21:0x PST)
Job: pv family over 400k placed cap -> census + structural row on KV-ALLFIX current plan, PRE + scoped strict bind, ROW-REBASED to KV-ALLFIX cc FABLE-RC-KV.
I hold the kv3_pv_v3 D29 wave hold (hold_items, kit_wave eb9e50a; from KV-PREGRT-STALL): release with kit_wave_edit when my row is in.
## Census (posted 21:07)
- D28 kits: v3 synth 425.6k (196k seq + 172k QN INV) -> nontap placed 574k + 92.5k taps; v6 (unsplit 2160) synth 438k -> 686k + 177k taps. pad-delay pd* chains dominate.
- Setup: v3 -738 bin_i_astk_E -> bout_o_vport_E_N_vo_d2_p (V3FT row), -721 u_rrl_54 -> cland_fstart (KV-PV-RSTRELAY owns); v6 -548 cross-type 2160 um.
- A3f/K3g already hold PADRAM (pad_ram min_d 8, 31 types), row B split, V3FT.
## Measuring (lane dir /srv/opentallas-scratch2/claude/kv-pv-cap on epyc8 + epyc11)
- stage1.py (epyc8): kit_rtl + PADRAM pass per pv type on D29 apply K3g (plan_c 324af451f9be) -> k3g/<type>/{files.f,top,dram.json}. log s1.otrun.log.
- stage2.sh (epyc11): yosys generic synth in docker per type dir, libs dir libs/*_tt.lib as blackboxes. cal/kv3_pv_v3_d28 = calibration vs real 425.6k.
## Rebase target
KV-ALLFIX: A3f failed G0; A3g (A3d b258e3e34f22 minus HUBA1 + IUSPLIT) gating on epyc10, rt 9b19260c1cde. Ask ad9ba7d264a476287 for the final sha.
## 21:5x state
- Tool kit_dly_ap.py PUSHED main c3d09d8eb1f (ot_dp_dly) + d06ef5e3d79 (ot_dp_dly_keep, keep on process). Plan key partition_types[t].dly_alt_pol. LEC: bounded miter D=1..16 PASS both variants vs bind_cells gold; mutation FAIL. Clones: epyc11 + epyc8 /srv/opentallas-scratch2/claude/kv-pv-cap/clone (epyc8 one pushes; epyc11 lacks pytest).
- Census K3g (model = yosys + ASAP7 QN dfflibmap; real = model x0.833; nontap placed = real x1.344; cap 400k <=> model 357k): lk (as now) only v3 361k and v1n 550k over; ap(v1) v3 317k, v1n 408k. ap2 (keep too) running: c4_ap2.out on epyc11.
- v1n is 2160 wide unsplit (row B split blocked: cut face full, 129 pins short). If ap2 v1n still > 357k -> needs a cut/re-shape.
- Row script: scratchpad pvcap/ROWS_KV-PV-CAP-DLYAP.py (dly_alt_pol all kv3_pv*, budgets.r_dly_lockup.kv3_pv.r2r_margin_ps=20).
- Rebase base A3g b258e3e34f22 (epyc10 kv-allfix/grow/A3g/plan.json); tree fork -> epyc11 /srv/opentallas-scratch2/claude/kv-pv-cap/tree (fork.otrun.log). Gate copy: epyc10 kv-allfix/grow/gate_grow_n.sh (use OT_BIND_ONLY_TYPES for scoped bind) with rt >= d06ef5e3d79.
## 22:2x state
- Census ap2 (K3g, model -> nontap): v1n 447k (OVER), v3 348k, v3n 281k, v12 262k, rest <=230k. Posted hub 816aed01.
- Gate R1 (epyc11 row/plan_pvcap.json 827a7c76eb05 = A3g + ROWS_KV-PV-CAP-DLYAP.py fee13023181e, rt d06ef5e3d79b, gate row/gate_pvcap.sh): PRE PASS 0 findings, ELAB 0, scoped strict BIND 0 errors. PRECHECK 2 FAIL both inherited (R8STALE same as A3g gate; TOOLSTALE launch-tree age). LATCHECK/BPC/G0 pending -> gate_R1.otrun.log, gate_R1/g0.status.
- v1n lever: kit_dly_ram wide mode PUSHED main 80de880655b (pad_ram.wide_min_d; W>1 ot_dp_dly D>=thr -> lead + RAM per 256b slice + residual under original name; verilator cycle-exact test). Probe on K3g: v1n 326k model (~365k nontap, UNDER), v3 276k (~309k).
- Row R2 = R1 + ROWS_KV-PV-CAP-WIDERAM.py (8516f1460388, wide_min_d 32 on v1n/v3/v3n/v12) -> row/plan_pvcap_R2.json a8788103ca48. Gate R2: row/gate_pvcap2.sh (GATE_RT=rt 9f95aa48604b), log gate_R2.otrun.log. A3g kit_rtl+PADRAM probe: a3g/ (a3g.otrun.log).
- D29 kv3_pv_v3 hold (kit_wave eb9e50a) still mine: release after R2 rows land with KV-ALLFIX.
## 23:1x state
- R1 ROW-REBASED 827a7c76eb05 PASS posted (PRE 0, G0, scoped strict bind 0 err, BPC). R2 ROW-REBASED a8788103ca48 PASS posted (G0, scoped bind 0 err gate_R2w/; PRE 41 FAIL = identical to A3g base on rt 9f95, pre_base9f.log, bind ran PRE=warn).
- Both rows dry-apply clean on KV-ALLFIX A4b 01311e0c5cce -> eff53250f8ad (epyc10 /srv/opentallas-scratch2/claude/kv-pv-cap/rows/). Asked KV-ALLFIX to add both row lines after LATREGEN (needs rt >= 9f95aa48604b).
- All 31 pv projected < 400k nontap (v1n ~365k, v3 ~309-348k). Real proof = first GEN/place of v1n + v3 on the composed plan.
- Open: release D29 kv3_pv_v3 hold (kit_wave eb9e50a) once KV-ALLFIX composes the rows; recheck hold on first placed v3 (r2r_margin 20).
## 23:51 state (pv kits PROBE-ONLY on R1+R2: no functional proof yet; see CORRECTION post 30a2dad6)
- COORD proof list: (1) kit post-synth LEC pv_v3 + neg control, (2) reset/mid-tap/init list, (3) ring power-up + reset release, (4) RAM macros per type.
- epyc11 lec2/: kit3.sh ok|n1|n2|n3 (verdict only PROVED/CEX/NO_VERDICT; "ABC rc=0" in old lec_kit.sh logs is NOT a pass); log k3_ok.log; run n1/n2/n3 after ok. AIGER ignores clocks: compare clock pins per flop separately before claiming.
- ring_all.log = full-width L-RAM (huge SAT), ring_bit.log = W1 BITS1 per depth + seeded lag bug each (needs a bit-independence argument; sram_formal.v vs macro .v cross-check not done).
- (3) OPEN: kit pv_S reset spine says "released after 6 clocks"; lines are 37..121 deep, so consumers can leave reset before lines flush (gold too). Need a bench with a real reset consumer and valid/control lines. Find what fills the lines (POR hold length on KV). wp/rp no reset: 4-state X forever.
- epyc8 clone: test_kit_dly_ram.py power-up test UNCOMMITTED (bound 67 set after a fail at 62; no reset consumer).
- (4) K3g only: r2new/place4.out epyc8; redo on A5.
- Unproven: r2r_margin 20; R2 PRECHECK inheritance; TAPOFF vacuous; D29 pv_v3 hold still held (do NOT release before proofs).

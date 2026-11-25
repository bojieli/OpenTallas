# S81-KVLEAF-T2-ARCH handoff (Fable; root cause + one structural fix for S81 ot_s81sl kv_leaf t2)
Brief + rules: localhost scratchpad rules.txt (session c228d9e1). Lane dir: intel2 /srv/opentallas-scratch2/claude/s81-kvleaf-t2-arch (wt = lane clone, branch s81-kvleaf-t2-hardkv; synth1 = hier synth; eq1 = HARD_RQ 0/1/2 structural compare).
## Findings (11-23 04:2x, posted hub 3af9daa6)
- t2 = ordinary leaf + D512 KV bank (ot_s81sl_kv_bank CNIK=1 HARD_RQ=0) + compressor pool. Arithmetic, not a flop store; storage is already 183 SRAM macros.
- Cause: plan row t2 has no hard_cores and the die slice top ot_s81sl_slice_sukv_raw512_w3 passes KV_HARD_RQ 0, so 64 norm engines + 16 quant + taps + trees + writers + 8 pool lanes are flattened into one soft run. The bank was designed and CLOSED (10-12/13, 833 ps) as small masters: physical/ref_tile/s81su_{kvt,kve,kvp,kvr,kvq,qnh}_ref with LEF/lib views.
- Area claim 9.1 mm2 is wrong (0.979 um2/cell includes t5 hard macros); measured 0.11-0.13 um2/cell. Masters footprint 2.28 mm2 in a 5.31 mm2 slot. No die growth, no 28-piece cut.
- Unique to t2 (t1/t3/t4/t5 have no bank; 23 hard cores each).
## Fix = hierarchy (option d)
- RTL draft in wt (NOT pushed yet): HARD_RQ >= 2 in ot_s81sl_kv_bank picks masters for kvt/kve/kvp/qnh/cn_write/ik_write/ik_reduce (new file rtl/dsrom_sys/s81_suhc/hier/dsfd_su_t_kvcn.sv: dsfd_su_t_kvtc/kvec/kvpc/cnw/ikw/ikr), pool HARD=1 -> dsfd_sl_t_cpl x8, slice top sukv_raw512_w3 sets KV_HARD_RQ(2). Soft instance names unchanged for HARD_RQ 0 kve and pool lanes.
## Jobs
- synth1 (ot-run intel2, docker s81kvt2arch_synth1): hier yosys of kv_leaf -> per-master mapped cells + soft residue. Output synth1/stat_mapped.txt.
- eq1 (docker s81kvt2arch_eq1): flatten stat for HARD_RQ 0/1/2 must be equal (wrappers are renames).
## Next
1. Read synth1/eq1; post measured composition + row/RTL plan with owner + ETA to COORD, FIX-LEDGER, FABLE-RC-S81.
2. Run tools/s81_dv/rtlgap_sukv_1021/hard_rq.py form with HARD_RQ=2 (Verilator, ot-run) if fixtures found; then push via ot-push-main with tests.

## 11-24 08:xx PST fresh lane S81-KVLEAF-T2-ARCH (post-limit; supersedes R2 for the B job)
Clone: E2 /srv/opentallas-scratch2/claude/s81-kvleaf-t2-arch/wt_1124 (branch s81-kvt2-lepk-gate-1124, pushed).
- (1) eq3 died 06:01 (EQUIV_INDUCT: no SAT model for black-box ikr). eq4 (E2 blk97c, cutpoint -blackbox after equiv_struct; 47 black boxes shared once): base case diverges on 18,159 points where XMRG gate side is constant (u_xc/u_xn lines, cd/nd/cm/ca/na/cv/nv, ...). eq7 intel1 blk97c (equiv_make -blacklist eq7_blacklist.txt, 254 internal names) running; log eq7.log, rc7.txt.
- (2) Estimator: intel1 s81-kvleaf-t2-arch/rde (rde_dump.py openroad -python, rde.py RUDY+cover model, cutcount.py exact cut counts, cut_census.py). v8 placed probe: cut H 0.91 @x1966, V 0.94 @y572 (incl ft 6,823 bits); spine band 5-17x; 80% crossings kvi/kvx relay hops. Master LEFs 15-39k shape OBS = 3.4M GRT blockages.
- Fix: seats t2b_seats_d3fit_ch2x43_1124.json 98c505a87106 (E9 lane dir) = d3fit b40f43dd1dad + 43.2 channels at y760.32 and y1209.6 (chan_insert.py), 2211.84 tall, schedules XD/KST/XST unchanged, inter-relay <=401.8, last kvi->engine 391.0, store 469.6 (= base). cover_obs.py = cover-OBS abstracts. probe_v10 (E9 mk_probe10.py) = place+CTS+GRT(30 it, allow_congestion) on these.
- Die: refloor/spec_t2B_ch86.json on D3 49332d346d48 (E2 refloor/), s_3N_L0 +86.4 tall + 22 parts above +86.4 (top margin 103.68 -> 17.28). price_t2B_ch86.json running.
- (4) LEPK gate: annotate_soft_dest KeyError 'id'; fix 245ed6cdf98 on main (with 0f1a09d6d5cc). Mixed LEPK/UNIT held.
- Cancelled: probe_v9 waiter (never started). probe_v8 (intel1, stuck GRT on shape OBS) still running.
## 11-24 ~09:30 PST update
- eq proof: eq10 intel1 blk97c (equiv_make -blacklist eq10_blacklist.txt; equiv_struct -fwonly <each black-box type>; cutpoint -blackbox; equiv_induct -seq 16; 2 h bound). eq4-eq9 lessons: (a) no SAT model -> cutpoint after struct; (b) XMRG-removed CN state name-matched to constants -> blacklist; (c) plain equiv_struct BACKWARD-merged the 16 cnw / cn_norm_write black boxes ACROSS blocks (i_block strap 1 vs 0) = unsound, base case diverged -> -fwonly per type. eq10 struct counts = per-form counts (every black box paired once), no constant-sided equivs; induction running. Result: rc10.txt, eq10_status.txt, eq10_tgt_total.txt.
- Die price: E2 refloor/ spec_t2B_ch{86,86b,86c,d,e}.json; e (+43.2, x06 rows -43.2 tall, gunit/bk_sel fixed) blocks only 3 NO-ROOM seams (xring s_5N_C|s_4N_C, s_2N_C|s_1N_C, x_W4_in__1); posted to T2-REFLOOR.
- probe_v10 intel1 (cover-OBS + ch2x43 seats 98c505a87106) unit oth-ubuntu-2432180-1795567341: read GRT overflow + congestion.rpt when done, rerun rde on its 3_place.odb (run_dump.sh / run_rde.sh / cutcount.py in rde/), render, then decide route checkpoint.
- hub write-up results/geom_review/s81_t2b_rde_1124.md (f0b61ca520cf).
## 11-24 ~19:30 PST update
- eq10: NO VERDICT, 2 h bound in equiv_induct -seq 16 (284549 equiv points, 55822 proven, 228727 open before induct). Relaunched intel1 blk97c, 6 h bound each: eq11 (equiv_simple -seq 2, tee eq11_after_simple.txt, equiv_induct -seq 1; unit oth-ubuntu-3998364-1795575732) and eq12 (equiv_induct -seq 4; oth-ubuntu-3998562-1795575732). Results in rc11/rc12.txt, eq1x_status.txt, eq1x_tgt_total.txt.
- probe_v10 placement estimate (rde/v10_*; run_dump2.sh takes ODB=3_3_place_gp.odb): cut-lines 0.77 H / 0.74 V (v8: 0.91/0.94); total 0.42/0.32; 13.7% H bins >1 (max 8.5) on the kv_store SRAM farm (144 ot_sram_1r1w2c_32x64 at 43.2 x 30.24 pitch, x345-1371 y898-1084: 11.2 um H streets) and the stripe to its right. GPL routability failed to reach target. Hub render results/geom_review/t2b_rde_v10_place.png. probe_v10 now in CTS; GRT next -> read overflow, rule route checkpoint.

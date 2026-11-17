# S81-CORES-R3 handoff (Opus, succeeded S81-CORES-R)

## State 2026-11-17 07:5x PST
### (1) dsdv_bksel_q eco3 RTL merge (S81-DIE-R3 NEEDS-LANE (a))
- The eco3 source (epyc2 fable-fix-bksel/fx6/hei_fable/eco3/i1/rtl) is byte-identical to the main legacy profile
  physical/die_plan/s81/cores/legacy/profiles/bkr1c8_hlat_1113/rtl: dsdv_bksel_c 651f2895, and hq_tile/parts/slice/hist_bank/
  native_sel_lib also differ from main's canonical (hq3) lineage.
- Branch claude/s81-bksel-rfh-merge-1117 @650801d2456. Gate GREEN (static, main 1338a50c811). Changes:
  dsdv_bksel_c.sv: dsdv_bksel_q gets RFH/HLAT and the face flops, plus the station DM 4+DMX. The control gets QRX, so XDX = 1+ceil((RC+RS+QRX)/2).
  dsdv_bk_sel.sv: OT_BKQ_ECO3 sets the quarters to literal OLL 2 RFH 2 HLAT 1 and the control to QRX 1. OT_BKQ_QRX_MUT is the mutant. The default (hq3) is unchanged.
  ot_s81ph_hq_tile.sv (canonical): FACE/HLAT params, modelled by edges only. Defaults are unchanged.
- Bench rtl/.../bk/test/run_bksel_rfh_qrx.sh, epyc2 r1, wt/bench_out/r1: base PASS, eco3 PASS 6/6, qrxmut FAIL (606/274 errors).
  So the +1 is REAL and the control must take QRX 1 (fixed waits +2 edges: WAIT +2, HOLD/HC0/HF0/CLRW +4).
  p2mut and facemut are cycle-benign (they PASS), so they are info rows, not gates.
- The merged dsdv_bksel_q under eco3 defines vs 651f2895 differs only in [0:0] port widths and DM(4+0).
- LEC: merged RTL (eco3 kit config) vs SIGNED eco3 6_final.v is running. Unit oth-ubuntu-811138-1794928950 on epyc2,
  dir /srv/opentallas-scratch3/claude/s81-cores-r3/lec_merged, out lec_final/lec.json, log intel2 ~/s81-cores-r3/lec_final.log.
  The previous LEC took about 4.8 h. If it is EQUIVALENT, there is no quarter re-sign. If it is NOT EQUIVALENT, re-sign the quarter from the merged RTL.
- OPEN BLOCKER (control): eco3 quarters need the control dsdv_bksel_c re-built with QRX 1. Signed control view bksel_c3_1104
  (odb 11f32154) was built with -G OLL=2 SELOH=1 RNF=1 LQH=1 (ss29 lecrun gold.ys). LQH is not in any repo RTL, and its kit
  (epyc2 ss29/resign/kit_bksel_c, intel1 die-s81-56/eco/run/bksel_c3/i1) is gone; only the DB is left in AGIdock s81/dsdv_bksel_c.
  The die also instantiates the control with defaults (OLL 0 SELOH 0 RNF 0), and its HCPARAM-ALL entry is allowlisted, so it is unchecked.
  The control needs its source recovered (from the archived 6_final.v / LEC gold) plus QRX 1 and a re-sign before eco3 can be bound.
- LATCHECK: the +1 lane edge and the +2 wait edges are internal to bk_sel__t2 (no type bus changes), so LATCHECK lanes do not move.
  The cost is selector search latency (+1 lane, +2 wait edges a pass). It is priced at the next C4 bind by S81-DIE-R3.
### (2) dsdv_gunit_l1f_bf: signed + ARCHIVED-BOTH (AGIdock s81/dsdv_gunit_l1f_bf, INDEX row present); bf-view branches 1c5843ae7e2 and
  a20426a4c12 are merged. The count misses it only because the kit-wave plan is still 819037bbe371 (bf 432x172.8); D5e/C4r3 plans carry
  432x216 + signed_1116 pins (2689/2689 match). It counts when the wave moves to D5e/C4. No fix needed.

## Next
1. Read the LEC verdict and post it. On EQUIVALENT, MERGE the branch.
2. Control: open a lane (or do it here) to recover the dsdv_bksel_c LQH source and re-sign with QRX 1. Until then C4 keeps hq3.
3. Clean up after merge: the wt, bench_out and lec_merged on epyc2 /srv/opentallas-scratch3/claude/s81-cores-r3 (ot-delete), and bf-wt (no changes).

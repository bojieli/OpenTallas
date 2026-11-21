# FAM-QC-HCST handoff (started 2026-11-20 23:3x PST)
Family: QC sle_hc*/slw_hc*, sle_st*/slw_st*, sle_su*/slw_su*. FABLE-FIX-QC-SLE keeps sle_ctl/sle_sc/slw_sc + GRT class.
## Census 23:45
- 6 "STALE unowned" hc types = old pv names (pv1c2f9baa, pve230954c, pv77c16c8a, pv0d63d22b, pv39aac7a1, pv6c2c33ed), absent from kit_wave only_items; V1 live names are the N_PAD split reps (pvcaa93304 pve289215f pv97423966 pvcf529cc9 pvcca9ff41 pvfd488b8f), all running. Not orphans; drop on V2 rename.
- Fixes already on main (helper of QC-PLAN-R8): 77440fa43c land_slots share_trunk; 2bdea13bb1 ft_spread keeps exact internal station banks. Both in rt f453583d5830 / 124d829f45f5.
- Wave attempts on fixed tools: slw_hc3 pvcca9ff41 a3 (rep), slw_hc3 pvfd488b8f a4 (place), slw_st_a_v2__clf4365a62 a3 (gen).
- Watcher: intel2 /tmp/hcst_watch.sh (exits on first AP_RC).
## Next
- Rep to sign-off; then hand fix rows to QC-PLAN-R8 for V2; relaunch siblings (slw_hc3 other pv variants if any).
- slw_st_a_v2__cl9f076a5c + slw_su_c__cl19bb38ef "placed, route held": check route-hold reason.

## 2026-11-21 02:29 PST Codex notes
- Applied feedthrough candidate: `epyc9:/srv/opentallas-scratch2/claude/qc-plan-r8/v2b/hcst_ft/ledger.json` reports 36 spread slots on 19 current HC/ST types, no added stations and every computed per-bit hop ≤300 µm. They ride b10.
- 24 slots deferred. The 1,574-bit `b_hw_ctl_hc3` banks fan from opposing unequal windows and push central hops to 324 µm. The two-stage `x_fw_ctl_p2` slots land at 323 µm. Other misses are three each of `cws3` and `x_su_l0_ctl`. Physical window/column placement must improve before adding larger banks.


## 2026-11-21 02:37 PST Codex notes
- The follow-up exact planner recovered 12 of the 24 deferred slots at the same station count. All nine 1,574-bit `b_hw_ctl_hc3` banks pass when each bit takes its own jog (roughly 267–277 µm per hop), and three `cws3` slots reach 290.8 µm. Exact per-type delta files and measurements are in `v2b/hcst_ft_followup` on epyc9. Keep them out of active b10 pending a subsequent bounded rebind and image review.
- The other 12 have a mathematical endpoint-distance lower bound above 300 µm per existing hop. Nine `x_fw_ctl_p2` need at least three hops and three `x_su_l0_ctl` at least four unless their pin windows move. Reprice those explicit cycles or change windows with both ends aligned.


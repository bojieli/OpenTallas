# KV-AHUB-RH1 handoff (Opus 5.5). Goal: re-harden qkd_ahub (hc_qkd_ahub 604.8x440.64, no growth) to FULL SIGN-OFF with strap_ofs_ap[31:0]/strap_ofs_fr[7:0] strap inputs.
Gates: DRC 0, TT >= -42, FF hold >= 0, bind+LATCHECK, LEC. Deliver: signed view + hub_C hard_cores row + strap-tie parent row -> KV-PLAN-R6 (D28 cut 11-22 12:00 PST, else late row/D29).
Peers: FAM-KV-HUBC-SYSC-R2 (hub_C/sys_c ops), KV-PLAN-R6 (plan rows).
Clone: epyc8 /srv/opentallas-scratch2/claude/kv-ahub-rh1/wt (main 0092847a58). Tmp: epyc8 .../kv-ahub-rh1/tmp.
## Plan
1. bo RTL: rename ofs_ap/ofs_fr -> strap_ofs_*; ahub_clock7 bo substitution set.
2. bench: closed-hub equivalence old table (old core) + new table (new core).
3. core.json/pins +40 strap pins; kit gen (wave env); P&R variants epyc8/epyc9.
4. swap_ahub_boundary reads tied strap value; tests; ot-push-main.
## Log
- 11-21 22:3x started.

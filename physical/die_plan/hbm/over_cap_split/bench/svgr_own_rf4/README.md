# ot_svgr_own RF4: registered skid pop (DIE-HBM-92-OPEN/OWNRF, 2026-11-08)

RF4 (`OT_SVGR_OWN_RF4`, on top of RF1+RF2+RF3) breaks the setup chain of ot_svgr_own vB/vG4:
skid state / hbm_fault -> response_ok -> 8-lane arbiter -> response_accepted -> skid pop -> 285-bit enable.
The skid now pops on `acc_q[pc]`, the already-registered response_accepted. While a pop is pending, the
eligible entry is the tail (`sk_e_v = pend ? n==2 : n!=0`, `dec_fire = kr_v && (n!=2 || pend)`), so every
output is cycle-identical to RF3, and the 285-bit head/tail enables start at a flop.

Lock-step proof (build.sh; REF = the pre-RF4 ot_svgr_split.sv at 685b58b8, NEW = this branch):

| run | result |
|---|---|
| RF4 seeds 1-4 x 20k cycles | mismatch -1, ~300 descriptors, ~19.5k tail grants each, 0 faults |
| RF4 seeds 11-18 x 200k cycles | mismatch -1 on all 8 (2881-3010 descriptors, 197-201k tail grants each), 0 faults |
| MUT17 (no tail select) | caught (cycle 56 on seed 1) |
| MUT18 (no push while a pop is pending) | caught (cycle 63 on seed 1) |

Physical form: own_vRF4S (epyc6 /srv/opentallas-scratch2/claude/die-hbm-92-open/own_vRF4S).

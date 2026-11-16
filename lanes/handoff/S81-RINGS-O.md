# S81-RINGS-O handoff (Opus successor of FABLE-FIX-S81-RINGS), 2026-11-16

## Done
- Branch claude/s81-ring-ff-1116 @526fc2be53d (supersedes 55ffcde5ada): MERGED to main (r282). Contents: FABLE-PD-S81-0117 levers 1-4 (S81 compose default --band-ring ff + --band-reserve ring_ff, compose RING-FF-GUARD ring_ff_min_bits 256, kit_preflight ring_ff ERROR on S81). It also has `_frozen_band()`: frozen clock.band_fixed_um bands keep their rects and take the compose BAND_RING when they have no ring_place key. That was the svc ff drop: all 82 svc bands F2s lost were frozen bands, deep-copied without the key.
  Gate GREEN 35/35 on epyc2. Log: intel2 ~/fable-fix-s81-rings/gate_526fc2b.log.
- Compose test, epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-rings/cmpF/physical/die_plan/s81/:
  - cmpF1 (55ffcde) FAILED the guard on 52 wide svc frozen bands, so the guard works.
  - cmpF3 (526fc2b, B6gG3b_pre, chain_ca_f args, no ring flag): RC 0, 0 placement failures, ff on 988/988 ring bands (svc 106/106).
  - Median band area vs B6gG3b: 0.49 / 0.53 / 0.53 / 0.55 for <200 / 200-511 / 512-999 / >=1000 bits.
  - Median max pin hop: 71 / 95 / 126 / 211 um, against 120 / 136 / 163 / 387 before.
  - (cmpF2 failed only on a harness symlink; tools are now a real copy.)
- A_t65 kit (epyc9 fable-fix-s81-rings/A_t65; B6gE rects + ff/ffr; E/W face; lever-2 form): post-CTS GRT overflow 162 at iteration 5, 3 at 10, FINAL 0, in 15:27 min. The lane kit without ff read 354,826 at iteration 5.
- F2s key delta: epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-rings/ring_ff_stamp.py PLAN SIDECAR PLAN_OUT SIDECAR_OUT [type_re]. Run on ev/B6gF2s.json, it stamps 82 bands in 10 svc types (52 of them wide), with 0 left. Output: stamp/B6gF2s_svcff.json, sha1 4c163bdc1625. Not adopted: DIE-S81-92 owns the plan.

## Open
- A_t65 route goal is still running on epyc9 (post-GRT repair at 13:35 UTC). Log: intel2 ~/fable-fix-s81-rings/route_A_t65.log; kit log A_t65/gen/ot_s81sl_leaf__t65/run_route.log. Next owner: read the DRT result and post it.
- DIE-S81-92 / S81-CA-BAND: lift the svc exemption in chain_f2s.sh RINGFF accept, and apply ring_ff_stamp.py (or re-compose on main) to the current F2s plan.
- t68 ft5_i band (x 207..332) still sits beside its pin window (x 336..461) in cmpF3. On N/S faces the +ff pin-slot places the flops on the pins anyway (PD-0117 section 3), so this is advisory only.

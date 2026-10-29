# HBM-CORES-KITS-7: GQ q1 -> ring_ag q1 transport estimate (2026-10-29, estimate only, no build)

Problem (Codex packet codex_hbm_cores_20261029_reset, CHECKED from its json): the 512 raw q1 GQ->ring `ra_lp_data` pairs
are 1222.75..1614.96 um direct, all > 405. In RTL the link is direct (no logic, no register). The q0 copy has no native producer.

Inputs: Codex candidate plan `/srv/opentallas-scratch/claude/hbm-gq-stage-1029/plan/die_plan.json` (sha256 3adb874db5918b64...),
plus Codex `gq_ring_pair_estimate.json` and `gq_q1_direct_endpoints.json` from the same `packet/` folder.
Replay: `gq_ring_transport_estimate.py PLAN PAIR ENDS REPO out.json` and `render_slot.py PLAN out.png`.

Option R, paired-lot relocation (0 cycles, no RTL change):
- Slot: move `u_hb_coll_Q_ring_ag__q1` to (4527.36, 2626.56), hub-local, orientation MX unchanged, into the 272-um gap
  between the GQ east face and `xq_Q_p1_bfq1`.
- NW hub: the slot is hard-free with 4.32 um clearance (CHECKED here). The actual-pin maximum is 293.04 um (Codex).
  Ten planned station centres must be re-sited, two of them die-bus stations (L103_o, L37_o).
- NE hub: the same slot hits only `u_ctl_Q_p15` (178x178, CHECKED). Codex's hard-free NE slot (4544.64, 2540.16) reaches
  396.72 um, only 8 um margin, and needs 54 station centres and 6 bus stations re-sited.
- Every other ring_ag q1 leg gets shorter (plan points, 405-um hops): GQ 4->1, gq_land 5-6->2-3, cij 9->7, body 5-8->5.
- View: gq_ring_slot.png (viewed).

Option P, explicit pipeline event:
- Size: 3 coherent register stages (405-um reach) or 4 (360-um plan hop rule) on all ~495 GQ<->ring bits,
  about 1.5-2k FF plus station clock taps.
- RTL and calendar: the ring calendar shifts +N cycles a ring record. If q0 is ever realized (~2.9 mm), the shared
  calendar needs N = 7-8.
- Price (S2 schedule, accepted_cost.hbm_schedule, +N fixed cycles on all 642 COLL.* records of ds_ar):
  N=3 -0.248 %, N=4 -0.330 %, N=8 -0.660 %, i.e. 1906 -> 1901.2 / 1899.7 / 1893.4 tok/s; qwen_ar <= 0.05 % (CHECKED tool run).
- The plan already lists 18 regs on each GQ<->ring conn. Whether planU3f priced them is UNCHECKED.

Recommendation: option R in both hubs (NE: re-site u_ctl_Q_p15 or accept the 8-um-margin slot). Keep P as the fallback.

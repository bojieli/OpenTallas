# DIE-HBM-13 (2026-10-29 05:15-05:47 PDT)

Base plan: Codex street plan `4d53747f` = codex/hbm-plan-1029 exact-count ring (f9c82446b) + PHY tuple 103.68 (886f74f7d).
Derived plan `c25c_d13` sha256 `1d0b75d17db0...` = `c25c_d13_delta.py STREET OUT` (reproduced byte-identical; runtime copy
localhost:/srv/opentallas-scratch/claude/die-hbm-13/c25c_d13, other plan files are links to the street dir).

## Plan delta (G0 PASS 0 err / 761 warn; G0C 16 err, was 17 on street) - main 2b90210bd tools/die_plan/check.py
1. NE u_ctl_Q_p15 (ring-move re-site) origin off the 8.64 lattice (G0C hard_cores). Moved (+4.32,-4.32) to (4328.64,3075.84);
   tap, 28 station endpoints, die tap moved with it. track_offset cannot hold 4.32 (BASE_LATTICE 2.16).
2. COORD 05:35 ruling: ring_ag `qid[*]` -> `strap_qid[*]` in the ring pin file; qid conns body<->ring_ag dropped (parent tie, bind
   strap regex `.qid`); phantom cij inj_d*/inj_idx* and hcollgl pa_* -> ring_ag targets dropped. 40 station legs / 679 plan regs
   removed (ring_strap_phantom_report.json). The sw2 wrapper RTL port rename must land in the same event (ring kit lane).
Remaining G0C: 14 core_faces (q_hub_nw 63 / q_hub_ne 84 ports, spb sd_tx) + 2 SPB legacy internal-station hops >405.

## NE L4_i (+1 cycle)
TOK coupon (TOK-HBM-7 notes, ring 856efb504): NE inbound +1 = one cycle per batch (tail 674->675). The upper bound is 1/675 = 0.148 %.
Priced per COLL record like fallback P, it is 0.083 % (P N=3 = 0.248 %). Both are below P -> accept +1 on the two NE pr_cw_i/pr_ccw_i chains
(already 12 in f9c82446b). UNCHECKED arithmetic.

## gq_land pair move (option R): estimate only
Ring ag_* -> hcollgl pa_* is RTL-direct, and the plan has 9-11 stations on it. No body-legal slot within 405 um of all ag pins exists
while the current stations stay fixed (gl_slot_report.json). With the stations re-sited, there are 293 slots (gl_slot_report_nostation.json).
The best slot is hcollgl__q1 -> (4492.8,2246.4) in both hubs, directly south of ring_ag__q1. All 3 other partners get closer (worst -177/-168 um).
The move displaces 24 (NW) / 72 (NE) station points, which need the exact-count solver re-run. The pin-level check is UNCHECKED (centre Manhattan).

## SPB PHY/EP: OWNER 05:3x modeled M6/M7 escape
`m67_escape.py`: 1024 PHY N-face pins -> M7 .032x.192 edge-depth stubs at the digital face line y=635.04. The 512+512 EP E/W pins
-> M6 .032x.192. Each pin is snapped to a unique track (max shift 0.024 um). Full M1-M5 OBS, sizes, 4104 FF sites, nets and status M5 pins
are unchanged. pin_access diagnostic: `Complete pin access`, exit 0 (spb_m67_access.log; was DRT-0073 ep/sd_rx[448], phy/rx[0]).
Full G2 (GRT 50 it + pin_access) is LIVE: intel1 docker d13-spb-m67-g2, /srv/opentallas-scratch2/claude/die-hbm-13/m67_g2
(grt.log, probe.exit, congestion.rpt). The baseline took ~3 h. PASS needs overflow 0 + pin_access clean.

## Plan c25c_d14 (sha256 84d4117c2454...): option-R gq_land pair move, built on d13
`gl_pairmove.py d13 d14 tools/die_plan ring_fixed_count.py` then `gl_direct.py d14/die_plan.json`.
- u_hcollgl_Q__q1 moved to (4492.8,2246.4) in both hubs (NW from 4043.52,2756.16; NE from 4043.52,2064.96), just south of ring_ag__q1.
  Its tap and station endpoints move with it. The die tap moves through the partition orient (NE MY).
- Every touched chain is re-sited with the SAME register count by the codex exact-count Manhattan solver: NW 40 chains, NE 76 chains, 0 added, 0 failed.
- Ring ag_* -> gl pa_* q1 is now 226.5-272.0 um direct (<=405) and the RTL is direct, so the plan carries 0 regs there
  (removed NW 43 / NE 37 phantom station FFs). 0 cycles; the RTL is unchanged. This is endpoint-centre Manhattan, UNCHECKED at pin level.
- G0 PASS 0 err/761 warn; G0C 16 err (same set as d13). Station FFs inside any core body+4.32 halo do not rise (NW 2107->2103, NE 2142->2139).
  But about 2100 PRE-EXISTING plan station FFs per hub sit inside hard-core body+halo. That is inherited, not from this delta.
- Image gl_pairmove.png personally viewed (before/after both hubs).

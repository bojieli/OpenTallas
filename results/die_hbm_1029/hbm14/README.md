# DIE-HBM-14 (2026-10-29 06:00-06:30 PDT)

## (4) Station FFs inside hard-core body + 4.32 halo: root cause + generator fix -> plan c25c_d15
- Measure (plan c25c_d14 84d4117c, open body+halo rect, st_in_body.py): q_hub_nw 2782 / q_hub_ne 2749 plan station registers
  inside a core body+halo (1331 / 1434 strictly inside the body). DIE-HBM-13 quoted 2107/2142 with a different counter. Under
  hub_repack.Raster legality (halo edge blocked) the tool counts 2991 / 2955; all types: 11 more types affected (q_b102 1067,
  q_b101_nw 832, q_b103 583, root 124, q_b113 87, q_su01 63, ...).
- ROOT CAUSE (st_cause.py, image resite.png VIEWED): the station generators (hub_repack.place_regs, hbm_r9_delta.realise) only
  place registers on free lattice points. LATER events moved or grew cores and never re-sited the chains they covered:
  HBM-STREETS-3 C19 re-outlines, DIE-HBM C20 C17g growth re-pack, C20f +106 um height, HBM-MU-QUAD-5/6, OUTL growths. 90% of
  the bad registers sit under a THIRD core (NW 2495 / NE 2571), not the chain's own endpoints. In the image, the red bands are
  the old edges of the grown u_hb_vms_Q__q0/q1 and u_xl_Q_ctl bodies.
- FIX (generator, opt-in delta, no new check): tools/die_plan/station_resite.py re-solves every chain that has a register in a
  body+halo (or a hop > 405) with the SAME register count. It uses the exact-count Manhattan reachability solver (codex
  ring_fixed_count.route, numpy-only port). It tries +1..+3 only when the same count is impossible, and reports every added
  cycle. Run it after any event that moves or grows a core; on a legal plan it is a no-op (test_station_resite.py 3/3 PASS).
- Result c25c_d15 (sha256 0110f4fd7ebc..., = station_resite.py c25c_d14 c25c_d15 --jobs 48, intel2 61 s):
  - regs in body+halo: all types -> 0 (Raster legality).
  - The render shows 3 points per hub exactly on the 4.32 halo line. They are legal; the renderer flags them from float
    equality with no track_offset.
  - 0 failed.
  - +1 cycle on 6 chains, which needs TOK pricing:
    - NW: u_vmb_Q4.rr1 -> u_hb_dbk_Q 2 -> 3 (258 b).
    - NE: u_vmb_Q7.{eg,pr,status,xq2_done,xq_done} -> u_hb_vms_Q 5 -> 6 (139/134/10/1/1 b).
    - These chains were legal only by sitting inside the grown vms/dbk bodies.
  - G0 PASS 0 err / 739 warn. G0C 16 -> 14 err: the 2 SPB legacy u_lk_S0.tx|u_ep_S0 hop > 405 errors (HBM-012) are gone. The 14
    core_faces errors (HBM-011) are the same set, with NE count 91 -> 92 and one NW listed port reordered (partner direction is
    taken from the moved register positions).
  - CHECKED: tool output + the main check.py d3b422a9c re-run of both d14 and d15 (g0_*.tail.txt).
  - UNCHECKED: per-chain pin-level hops (endpoint centres).

## (3) 12.18 census (complete; census.tsv, census_summary.md, closure_rows.tsv -> CLOSURE-LIST HBM-017..024)
- "49 types + 210 cores" is plan hbm_arch/B2n (10-25), which tools/autopilot/ownership.py DIES still names for hbm. It counts
  49 types and 226 core designs (210 modules), 54 of them RETIRED, leaving 172 live.
- The current plan c25c_d14 has 81 types and 80 core designs (78 modules), with 1197 placed replicas.
- 0 of the 80 current core designs equal a B2n design (all have new pin tables). 32 modules have no OWNERS row.
- 0/80 signed off.
- Owners with no live agent: HBM-PLAN / HBM-CORES / CORE-VIEWS. 147 of the 161 current items have no live owner.
- Counts were recomputed with main ownership.plan_items (CHECKED).

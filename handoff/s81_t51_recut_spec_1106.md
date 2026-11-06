# S81 slice_station__t51 native split: registered-face re-cut spec (DIE-S81-69, 2026-11-06)

COORD 10:0x approved (A): registered seam and outer faces in the private GEN, no raw face_guard bypass.
t51 physical stays parked until the regenerated W/E netlists exist.

## Why the current split fails
- Kits: epyc5 /srv/opentallas-scratch3/claude/die-s81-69/pg/kits/s81p_slice_station__t51_ot_s81_station_t51_native_{w,e}_ds69p
  (same GEN inputs as Codex native_a, plus my exact FF pose). The RAW face_guard (1_2_yosys.v) result is face_guard_raw.json:

  | child | bits | ok | shared | merged | unregistered |
  |---|---|---|---|---|---|
  | W | 11024 | 9780 | 1242 | 0 | 2 |
  | E | 11102 | 9711 | 827 | 554 | 10 |

- Examples:
  - `shared`, input side: W input p02183 drives 17 gates. A combinational cone sits behind the port, so there is no dedicated capture FF.
  - `shared`, output side: the launch FF Q also has local loads.
  - `merged`: one flop, for example u_ft_ft4_o_3 q[i], drives two ports (p00836 and p10841).
  - `unregistered`: the u_cland_collect_* reset AND gates drive ports directly.
- Root cause: the split is a mapped gate netlist cut with 0 added cycles. Crossings are not FF->FF wires. The 402.84-um budget proof covers geometry, but not the registered-face rule.

## Target form (zero added cycles; preferred)
1. **Cut on registers.** Every W<->E seam net and every outer face net must be a direct launch-FF Q -> capture-FF D wire.
   - Move each combinational cone wholly into one child: either the launch side or the capture side. Then the face net is FF Q at one end and FF D at the other.
   - The GEN cut chooser runs on the mapped graph (the same one used for graph conservation): cut edges = FF->FF edges only.
2. **Dedicated face flops.** Where a launch FF's Q also feeds local logic, replicate the FF:
   - same D, clock and reset;
   - the copy drives the port only, the original keeps the local loads;
   - add keep/dont_touch so Yosys opt_merge cannot fold them again (the face_guard `merged` class).
   - The input side is the same rule: the port drives exactly one capture FF D.
3. **merged ft flops.** One FF per port bit. Keep the per-port copies (keep attribute) for u_ft_ft4_o_3 and any other ft bank.
4. **Reset collect ANDs** (u_cland_collect_rst_*). Either declare them as reset-spine pins (face_guard reset_spine / skip set, as other kits do for collect outputs) or register them through ot_dp_rrelay.
5. **Accounting.** Recompute FF count with replicas. Each child must stay <= 150k functional cells and util <= 0.45 (owner conservative form). Re-run graph conservation (identity + replicas), LEC vs source, and the 402.84-um pair audit.
6. **Fallback.** If a crossing cone cannot be made FF->FF without exceeding a child cap, add one seam register stage on those nets only.
   - This adds a cycle. It needs the schedule owner's sign-off (pin cycles), the TOK delta, and an EQ-with-latency proof.
   - List these nets explicitly. Never add them silently.

## Acceptance before any place
- RAW and post-synth face_guard PASS on both children, with face_guard_raw.json showing 0 fails.
- GEN hash + freeze, then regenerate the kits with gen_core_kit_legacy.py native_ff_pose. That is my c8e0d595929 (approved, ROOT-MERGE-43). The pose files must include the replica FFs, with sha256 in recipes.
- Then GOAL=place on epyc5 (same command as ~/ds69-logs/t51_*_place.otrun.log), followed by placed-DB review. The owner PASS-COND conditions from 09:46 still apply:
  - seam-bin pin-access check;
  - honest M7 clock/PG OBS;
  - measured root arrivals at the 89 entries;
  - no route before review.

## Inputs
- Codex split WT: intel2 /srv/opentallas-scratch2/claude/wt/codex-s81-station-split-1106 (flow-bt5856395f8).
- Mapped controls: intel1 /srv/opentallas-scratch2/claude/codex-s81-split-1106/mapped_controls.
- GEN inputs: intel2 /srv/opentallas-scratch2/claude/codex-s81-privategen-1106 (my copy: epyc5 /srv/opentallas-scratch3/claude/die-s81-69/pg).

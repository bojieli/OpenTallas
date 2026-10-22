# S81-CAL241 (10-21): the exact multi-user static calendar on the qualified 241-stage map

This calendar replaces the 81-stage one. The 44-user calendar at claude/s81-link5-cal-1021 @c028c373c was built on the old 81-stage map, so its user count is not the release count.

Grade: **MODEL**. It is exact calendar arithmetic. The checker brute-forces every window of every user, modulo the period, on 510 resources, and passes. A run at N+1 users must fault and does; an injected shift collision must fault and does. The stage windows are built from composed node cycles, which carry the composer's grades (69.7 % measured AR). MU.TOK measures the calendar on RTL.

## Inputs

- **Map:** `results/arch/s81_map72_1021/r2_241/stage_map_f72r224gpq_241.json`, as bound at 483869b91 (sha 3b9962aa7afd). It holds 241 stages / 964 layer dies, merge --cover all_pass 241/241 (capacity receipt ccff664a5). The map is unchanged, so no new capacity run is needed.
- **Tool:** `tools/s81_dv/dv_mu_calendar_phys.py`, the MUCAL140 / 140B / SWEET lineage (21b9cecc0). It is extended with `--release241` and `--attn`. All new terms are off by default, and the mucal140 records still reproduce (`--check` SAME).
- **Composition:** `--compose romopt --alap`, the same base as the 139-stage receipt MODEL (1,011.8 / 2,991.2).
- **Release terms** (`REL241`, recorded in `composition.release241` of every record):
  - **Direct cabling.** Each 453-cycle switched leg is replaced by its class's `D_cycles_max` from `results/arch/release_rack_1021/hop_latency.json` @4b528ad2b: tp_mesh 251, stage_hop 266, head_hop 257.
    - This is applied per DAG node: TP4 collectives times their crossings (257 AR crossings, -51,914 cycles), and the composed stage hops (-22,253). The composer T is then re-solved on the same DAG.
    - The stage-hop law becomes HOP = 1,008 - 187 = 821.
  - **S81-LINK5 circuits.** Each die has 5 lane pairs: the TP4 mesh plus a dedicated stage-hop circuit. Every message from stage s to s+1 rides that one circuit and is serialised in send order: x, partial, combined, DENSE2 A->B. That makes 440 messages on 240 circuits a token.
  - **Land 0 + TX send hold.** NB is 80 and the closed land view has NS = 1, so a window cuts through only into a stage copy that already belongs to that user.
    - The first beat lands HOP - x_flat + RX_JIT = 821 - 376 + 2 = **447 cycles** before the receiver starts. Every receiving stage copy is held from that landing.
    - The sender holds its TX so that no message lands earlier than that (this covers the ALAP slots).
  - **DENSE2.** The A stage computes a_proj rows [0,224): the norm prefix plus half the a_proj. It sends x plus its partial (H_MSG + 8 cycles of serialisation) to B. B runs A_l + D_l - a_proj/2 + 8.
  - **Host option (b)** (owner 07:10). Jobs start from the local calendar on every stage die. The stage circuits carry no host or KS frame. The host plane is the head die's: HOST_TOK = 134 cycles a token a user.
  - **4.4 L2 index latency (G7, readers by the PHY):** +40 cycles on every attn.idx.score job (8 layers, +320 AR).
  - **Engram at RETURN_AGE 640.** eng.hbm_read takes 640 cycles. The Engram engine resource opens one new window per 576 cycles (II) a position, or 6 x 576 per MTP step, on R007 (L1 B) and R085 (L14 B).
  - **Attention variant.** attn.scores / attn.pv node cycles are G16 289/596 (composer), G8 449/756 and G4 769/1,076 (S81-SVCFIT). The die72 release candidate carries the co-located G4 `svc_full` slot (1728 x 3758.4).

## Result

| attention | AR users x tok/s/user = agg | AR period | MTP users x tok/s/user = agg | MTP step |
|---|---|---|---|---|
| G16 | **50 x 982.8 = 49,140** | 1,221,000 | **10 x 3,006.2 = 30,062** | 1,660,168 |
| G8 | 50 x 972.6 = 48,630 | 1,233,800 | 10 x 2,991.8 = 29,918 | 1,668,168 |
| G4 (die72 release slot) | **50 x 952.8 = 47,642** | 1,259,400 | **10 x 2,963.4 = 29,634** | 1,684,168 |

**Binding resource:** the copy-B (duplicated) DENSE2-B index stages, not a hop.
- **AR:** at 51 users the odd user count cannot be 2-coloured on R013 (L2 B). At 52, R121 (L20 B) cannot be coloured either, because its copy windows are 47.6k (G16) / 48.5k (G4) cycles, more than 2 x the 52-user slot.
- **AR, non-replicated stages:** the largest window is R007 (L1 B + Engram), 22,517 cycles (G16) / 23,477 (G4). On its own it would allow 54 users.
- **MTP:** at 11 users R013 (L2 B) cannot be coloured. R085 (L14 B) fails at 12.
- **Hops:** the busiest stage-hop circuit carries 1,304 cycles a user per period (7,824 a MTP step). That alone would allow about 936 AR users, so no hop binds.
- **Land 0:** every receiving copy is held 447 cycles from first-beat landing. This is inside the copy-B slack at 50 / 10 users, so the TX send hold costs 0 users.

**MTP >= 3,000:** only **G16** reaches 3,006.2.
- G8 gives 2,991.8 (-0.3 %).
- G4 gives 2,963.4. That is above the owner's earlier-accepted ~2,947, but below 3,000.
- The release die72 slot is G4. G16 needs the 2851.2 x 3801.6 contingency service slot.

**Compared with the TOK-RATE MODEL** (a0b6c71f1: G16 AR 1,002.4 / MTP 2,974.4, G4 966.9 / 2,931.1, with 44 users carried over from the 81-stage calendar):
- The exact calendar gives about 2 % less AR per user.
- That comes from the forward-x chain on 241 stages: +40.0k cycles chain - legacy, made of the partial-chain adds, DENSE2 A->B, and Engram 640.
- Users rise from 44 to 50.
- MTP per user is higher: 3,006 / 2,963. The physical wave term replaces the composer wave, and the direct legs are applied per node.

## Files

- `calendar_rel241_{G16,G8,G4}_{ar,mtp}.json`: slots, copies, stage windows (t / occ / step / eng_off), checker, `binding_next_user`, `binding_link`, `composition.release241`.
- `run_cal241.sh`: the exact command (CHECK=1 = `--check`). These records ran on the fleet: ot-run unpinned, unit oth-ubuntu-544377-1792595426 on ot-gold2. A local `--check` reproduces them SAME.

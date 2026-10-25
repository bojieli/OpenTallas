# S81 head die: link adapter / beat contract (S81-HEAD/ADAPT, 2026-10-25)

This contract implements COORD ruling (3) of 2026-10-25 03:45 (lanes/COORD-REVIEW-QUEUE.md):
- each 553-b lane record crosses a 276-class lane as registered beats plus a valid;
- each HBC 1104-b ring word crosses as 4 beats;
- latency is fixed;
- a rate or beat-order violation raises a sticky fault;
- the H4 tl/ca/cb lanes are added to the head plan.

No codec is invented. Fields that the compiled schedule does not fix are marked **COORD?**.

## Beat format (one RTL pair for every head link)

The RTL is `rtl/dsrom_sys/s81_head/ot_s81hd_beat_link.sv`, with modules `ot_s81hd_beat_tx` and `ot_s81hd_beat_rx`. It has three parameters:
- `W`: data bits per word. The valid is a separate wire.
- `N`: beats per word.
- `P = ceil(W/N)`: payload bits per beat.

**Port.** The port has `P + 1 + BW` wires, with `BW = max(1, clog2 N)`. The field order is `{bi[BW-1:0], vb, pay[P-1:0]}`.

**Beats.** Beat k (k = 0..N-1) leaves in cycle t0+k with `vb=1`, `bi=k` and `pay = {0,d}[k*P +: P]`. Beat 0 always comes first. The `N*P - W` pad bits of beat N-1 are 0.

**Timing.** The phase is fixed. There is no handshake and no credit.
- **Rate:** at most one word every N cycles in each direction.
- **Sender:** the compiled schedule's sender issues a word only in its slot.

**Fixed latency.** Let S be the stations of the plan lane. The plan lane cycles are 2 + S: the TX pin flop, then S stations, then the RX pin flop. A word presented to the TX in cycle t is valid at the RX output in cycle t + N + 1 + S, which equals t + (plan lane cycles) + N − 1.

**Pins.** The TX output register is the partition's out pin flop. The RX input register is its in pin flop. Every partition pin is registered.

**Sticky faults.** They are never arbitrated and are cleared only by reset.

| Side | Fault condition |
|---|---|
| TX | A valid word arrives while beats are still owed. That word is dropped. |
| RX | `bi != 0` outside a word. |
| RX | `bi` is not the expected next index (beat order). |
| RX | `vb = 0` inside a word (dropped beat). |
| RX | A pad bit of beat N-1 is non-zero. |

**Reset (decision 2 / 13, control only).** Reset clears:
- the owed count and next index;
- the `vb`/`bi` pin-register bits;
- the expected index and the mid-word flag;
- the faults.

The payload and data registers have no reset. The block is released by the die reset wavefront, like every other block.

**Reuse.** This pair generalises the approved S81/SVCG fold lane, `dsdv_svc_f2b_tx/_rx` (`claude/s81-svcg-1024r@9be238f21b`). The rules are the same: fixed phase, sticky TX rate fault, RX order and pad faults, control-only reset, and pin flops as stations. The svcg pair could not be reused directly:
- it is fixed at N=2;
- it carries v inside word[0], whereas head lane records have a separate valid next to 553 data bits.

So the pair takes N as a parameter and has an explicit `vb`/`bi`.

## Per-link contract (plan `physical/die_plan/s81_head`, latency table `lat/s81_head_latency.json`)

| Link (plan lanes) | Word W | N | P | Port wires | Plan bus | Lane cycles | Word latency | Rate | Calendar slot |
|---|---|---|---|---|---|---|---|---|---|
| TP4 mesh core lanes `m0S_tx/rx`, `m7S_tx/rx`, `m7N_tx/rx` (ctl ↔ hd_mesh) | 64 (SPEC: 50-b local best + tag) | 1 | 64 | 64 + vb + bi = 66 | 64 | 49/51, 46/47, 6/7 | = lane cycles | 1/cycle | one word per position (rank all-gather; calendar `calendar_rel241_G4_*` head window 10,357 cyc; tp_mesh hop D 251) |
| Host core lane `host_tx/rx` (ctl ↔ hd_host), 553-b lane record (`ot_s81ph_coll_lane_safe4` lo_d/li_d [552:0] + lo_v/li_v) | 553 | 2 | 277 | 279 | **276 (see COORD? 1)** | 38 / 38 | 39 | ≤ 1 record / 2 cyc (276.5 b/cyc ≈ 331 Gb/s = the model host lane `tools/s81_head_die_model.py links.host`) | **COORD? 2** |
| Host core lane, HBC 1104-b ring word (`dsdv_hostb_stage_hbc` from_prev/next_ro/return_ro [1103:0]) | 1104 | 4 | 276 | 279 | 276 (see COORD? 1) | 38 / 38 | 41 | ≤ 1 word / 4 cyc | **COORD? 2** (boot dates = `BOOT_HEADER_EDGE` / `BOOT_COMMIT_EDGE`, compiled params, unset in the tree) |
| ctl ↔ lep0N `kd` / `ku` (lepk 1104, abutted k5 \| k6) | 1104 | 1 | 1104 | 1106 | 1104 | 2 / 2 | 2 | 1/cycle | the layer die's s_0N_C ↔ s_0N_LP ring dates (unchanged) |
| H4 index rank tree `h4_tl` (ctl→lep0N tl_i), `h4_ca`, `h4_cb` (lep0N ca_o/cb_o→ctl) **NEW** | 276 | 1 | 276 | 278 | 276 | 2 / 2 / 2 | 2 | 1/cycle (one IDX frame beat a cycle, as on the layer die `claude/s81-h4-1024r`) | the lep IDX static slot (type 5 frame, lane 2 → pair A, lane 3 → pair B; RX B → ca, A → cb) |

On the N=1 rows:
- The `bi` wire is constant 0 and is checked by the RX.
- The `vb` wire is the word valid. The plan bus counts only data bits. For example, the H4 lanes are 276-b on both dies, as on the layer die.

## Verification

All benches ran on Verilator 5.050 (the daemon's pinned version) through `ot-run` on epyc1.
- Runner: `tools/s81_head/beat_link_bench.sh`.
- Logs: `epyc1:/srv/opentallas-scratch2/claude/s81-head-adapt/b5`.

**Lockstep.** The bench `rtl/dsrom_sys/s81_head/test/tb_s81hd_beat_link.sv` chains TX → S plain stations → RX. It sends 1,200 words per run:
- the first words are all-0 and all-1, the rest random;
- spacing is back-to-back at the allowed rate plus random gaps.

Every word must arrive bit-exact at exactly t + N + 1 + S, with no fault.

| Case | W/N/S | Seeds | Result |
|---|---|---|---|
| r553 (lane record) | 553/2/2 | 1,2,3 | PASS 1200/1200 each; TX rate fault on a double word (word dropped, RX clean); RX injection faults 1111 (bi≠0 outside, dropped beat, order 0-0, pad bit) |
| h1104 (HBC) | 1104/4/2 | 1,2,3 | PASS 1200/1200; TX rate fault; RX injection 111 (no pad bits: 4×276 = 1104) |
| m64 (mesh) | 64/1/1 | 1,2,3 | PASS 1200/1200 |
| t276 (H4) | 276/1/1 | 1,2,3 | PASS 1200/1200 |

**Mutants.** Every mutant run must print FAIL. All 18 runs did (6 mutants × 3 seeds).

| Mutant | Meaning | 553 | 1104 |
|---|---|---|---|
| MUT 1 | beats 0/1 swapped | caught (RX order fault, words lost) | caught |
| MUT 2 | beat 1 dropped | caught (dropped-beat fault, 0 words) | caught |
| MUT 3 | TX rate check removed + rate violation | caught (RX order fault) | caught |

## Plan delta (H4 tl/ca/cb on the head die)

Source: `physical/die_plan/s81_head/gen_plan.py` only. The plan was regenerated with the tools: gen_plan.py, then `gen.py latency --inplace`, then check.py.

**Buses added**
- hd_lep0N: `tl_i` (in 276), `ca_o` (out 276), `cb_o` (out 276). They sit on the E face, above `lepf/unit/ctrl`.
- hd_ctl: `tl_o`, `ca_i`, `cb_i`. Their geometry is derived through the abutted seam.

**Lanes added:** `h4_tl`, `h4_ca`, `h4_cb`, 2 cycles each (0 stations), params `LAT_HD_H4_{TL,CA,CB}`.

**Effect on the rest of the plan:**
- 0 existing lanes change cycles.
- 326 partitions and 16 types are unchanged.
- ports 425 → 428, lanes 325 → 328.

**Checks:** G0 PASS with 0 errors and 6 warnings, all pre-existing. G0C (`--completeness`) PASS with 0 errors and 16/16 types clean.

On the head die the ctl is the IDX partner, where bk_sel is the partner on the layer die. The ctl RTL is absent on main (status `rework`), and its content must source tl and sink ca/cb. See COORD? 3.

## COORD? / OWNER? (not fixed by the compiled schedule; not invented here)

1. **Host lane width.** A 553-b record does not fit two 276-b beats: 2 × 276 = 552. Exact bits need P = 277, so the port is 279 wires. A 1104-b HBC word in 4 beats also uses a 279-wire port (276 + vb + 2 bi). The plan's host lane is 276 wires through 36 spine/host ft stations. The choices are:
   - (a) widen `host_tx/rx` plus the spine `hu/hd` ft slots to 279. This adds 3 wires per direction and 0 cycles, but it re-kits hd_spn/hd_spn_end/hd_host/hd_ctl, and hd_spn place is in flight.
   - (b) keep 276 and send a 553-b record as 3 beats (P = 185, 188 wires). This costs 1 record per 3 cycles, about 221 Gb/s, below the 331 Gb/s model.

   Recommend (a). The RTL takes either as a parameter.
2. **Host-lane calendar.** It is not set by the calendar of record. `calendar_rel241_G4_{ar,mtp}.json` has no head-die host or HBC slot dates, and `dsdv_hostb_stage_hbc` `BOOT_HEADER_EDGE` / `BOOT_COMMIT_EDGE` are unset. Two decisions are owed:
   - which compiled slots carry lane records and which carry HBC words on the shared host lane;
   - whether the two kinds share the lane by slot date or by separate lanes.

   A kind field would be a codec, so none is added.
3. **H4 on the head die.** Whether the head ctl originates the IDX tree beats (tl) and consumes ca/cb, or forwards them, is set by the head stage's place in the rank tree (TOK-DS). The plan lanes and pins exist, so nothing is tied or left open.

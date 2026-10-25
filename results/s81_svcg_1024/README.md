# S81/SVCG: 2-beat score-gather fold lane in the svc RTL (OWNER DECISION 12 re-plan)

Branch `claude/s81-svcg-1024r`, based on the DEC12 plan `claude/s81-dec12-1024r@d206dfb226`.
Run dir: `epyc1:/srv/opentallas-scratch2/claude/s81-svcg`. All heavy runs went through `ot-run` on epyc1 (tender-ray).

## What changed

The svc fold rung (svc_2k <-> svc_2k+1, faces N / S) carries the score-gather word on its own 2-beat lane
`attnh__svc_A__svc_B`. The other sub-buses stay on the attn lane.

| Item | Format |
|---|---|
| Word (2,133 b) | `{go_d[2131:0], go_v}`, with `go_v = word[0]` |
| Port (1,068 b a face) | `{beat, payload[1066:0]}` |
| Beat 0 | `payload = word[1066:0]` |
| Beat 1 (next cycle) | `payload[1065:0] = word[2132:1067]`, `payload[1066] = 0` |
| Rate | at most 1 word every 2 cycles in each direction |
| Handshake | none: fixed phase, no credits |
| Faults (sticky) | TX: a word while beat 1 is still owed. RX: beat 1 without a beat 0, a beat 0 when beat 1 is owed, or the beat-1 pad bit set |
| Reset | control state only (owed, expect, the beat and v bits of the pin registers, fault). Data registers have no reset |

This matches the plan's FOLD 2-BEAT CONTRACT (lanes/S81.md 00:19) bit for bit. The 11 directed fold hops of the gather
tree are exactly the plan's 11 attnh lanes: 0→1, 2→3, 3→2, 4→5, 5→4, 6→7, 7→6, 9→8, 10→11, 14→15, 15→14.

### RTL

- **`rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_sx.sv`**
  - New params `FH_GO` / `FH_GI` (4 b each, default 0) and new ports `gh_o` / `gh_i` (4 × 1,068 b).
  - New modules `dsdv_svc_f2b_tx` (serializer) and `dsdv_svc_f2b_rx` (deserializer).
  - The TX output register is the face pin flop. It replaces the last OUT relay station (B) of that face.
  - The RX pin register replaces the first IN station (C).
  - A fold word therefore reaches the half rows one cycle later than over a full-width face. This is the plan's
    word latency of 3 instead of 2.
  - On a fold face, `go_*` is driven to 0 and `gi_*` is not read.
  - With `FH = 0` the module is unchanged, apart from `gh_o = 0`.
- **`dsdv_svc_rs.sv`**
  - `dsdv_svc_rs_c` gets `F2B` and `FH` params, gh ports, and the F2B role and P.V-slot tables.
  - New sticky fault: `sx_fh(sid) != FH`, ORed into the core fault.
  - New die master `dsdv_svc_rs_f2b`.
  - **`pv_so/dsdv_svc_rs_pvso_entry.sv`**: new master `dsdv_svc_rs_pvso_entry_f2b`.
  - The legacy masters keep their ports. Current v4.8 kits and binds are unaffected.
- **`dsdv_svc_rs_fv_f2b.sv`** (generated): 15 F2B port variants, `dsdv_svc_rs[_pvso_entry]_fv_<FM>_f2b<FH>`. A fold face
  exposes `gh_o_<f>` / `gh_i_<f>` (1,068 b) in place of `go_v/go_d_<f>` / `gi_v/gi_d_<f>`.
- **Other `dsdv_svc_sx` instances** get `.gh_i(0), .gh_o()`: entry_f, f, lp, entry_lp and the group72 versions.

### Schedule (static gather tree)

Adding one cycle to a fold hop moves the gather-tree alignment, so the F2B build gets its own tables. The legacy
tables are untouched.

- `tools/s81_dv/svc_rs/svc_rs_embed.py --fold-extra 1` writes `dsdv_svc_sx_f2b.svh` (`sx_fh`, `sx_role_off_f2b`) and
  `results/arch/s81_dv_1016/svc_rs/embed_f2b.json`.
- `tools/s81_dv/svc_rs/svc_rs_tree.py --fold-extra 1` writes `dsdv_svc_rs_roles_f2b.svh` and `tree_f2b.json`.
- `tools/s81_dv/svc_rs/svc_rs_faces.py` writes `dsdv_svc_rs_fv_f2b.sv` and `faces_f2b.json`.
- The `sx_role` words (SIGNED hard core `dsdv_svc_sx_hrow` r15) are **unchanged**. Only the leaf start offsets move.

| | base | F2B | delta |
|---|---|---|---|
| gather root time T_root | 51 | 54 | **+3 cycles** |
| max leaf offset | 15 | 17 | +2 |
| rs gd per sid (0..15) | 6,16,16,16,16,16,6,16,21,21,21,21,21,21,11,11 | 8,19,18,17,18,17,6,17,23,22,23,24,23,24,13,12 | +0..+3 |
| P.V slot (pvslot_all) max | 295 | 296 | +1 (per-slice −1..+2) |

Leaf offsets by sid: F2B 7,13,12,6,7,1,0,6,17,11,12,8,17,13,12,6; base 5,10,10,5,5,0,0,5,15,10,10,5,15,10,10,5.

`sx_fh` by sid, as {GI, GO} with N = bit 0 and S = bit 2: 01,40,11,44,11,44,11,44,10,04,01,40,00,00,11,44.

## Verification

All runs used Verilator 5.050 (the daemon's pinned version) and the ORFS asap7lock yosys, launched through `ot-run`
on epyc1. Logs are under `epyc1:/srv/opentallas-scratch2/claude/s81-svcg/{u3,sx,svcik,selchain,lint,lint2,fg}`.

### Unit bench: exact golden through one fold pair

The unit bench is `rtl/dsrom_sys/s81_dv/svc_rs/test/tb_dsdv_svc_f2b.sv`, run by `tools/s81_dv/svc_rs/f2b_unit_bench.sh`.
The lane is TX → 2 plan boundary flops → RX.

| run | seeds | result |
|---|---|---|
| base | 1, 2, 3 | **PASS**: 3000/3000 words exact, bit for bit, at exactly t+L+3. Spacing is 2 cycles (back-to-back at the allowed rate) plus random gaps, with all-0 / all-1 halves. Every port beat matches the contract bits (port err 0). No fault in phase A. Phase B: a word in the cycle after a word sets the TX sticky fault (it stays 1), and the dropped word never arrives. Phase C: a lone beat 1, beat 0 twice, and the beat-1 pad bit each raise the RX sticky fault (`111`) |
| `F2B_MUT=1` (beat order swapped) | 1, 2, 3 | **FAIL as required**: rx err about 1,550 of 3,000, port err about 7,500, RX fault set |

### Exchange bench: the 16-slice score gather with the fold lanes in place

The bench is `tb_dsdv_svc_sx` via `tools/s81_dv/svc_rs/sx_bench.sh`. It checks golden sums at the root and the taps.
In F2B mode it also checks that every fold-lane word leaves the receiving RX bit-exact, 3 cycles after its TX took it,
and that beat 1 follows a valid beat 0 and never appears otherwise.

| variant | seeds | result |
|---|---|---|
| base (legacy, FH = 0) | 1, 2, 3 | PASS: 600/600 root, 9600/9600 taps |
| fmask (legacy face-masked) | 1, 2, 3 | PASS |
| **f2b** (FH = sx_fh, f2b offsets, words ≥ 2 cycles apart) | 1, 2, 3 | **PASS**: 600/600 root, 9600/9600 taps, fault 0. 11/11 fold lanes carried 6,600 words with lane err 0. t_root 54 |
| **f2bfmask** (the same on the face-masked slices, i.e. the port variants' cores) | 1, 2, 3 | **PASS** |
| f2bmut (TX beat order swapped) | 1 | **FAIL, caught**: root 285/600 (err 285), lane err 12,005, sticky faults on 12 of 16 slices |
| f2brate (old 1-cycle word spacing = rate violation) | 1 | **FAIL, caught**: root 324/600, **sticky fault** on 14 of 16 slices |
| f2bskew (one slice a cycle late) | 1 | **FAIL, caught**: 600 root errors, alignment fault |

### Existing svc gates on this branch

| gate | result |
|---|---|
| SVCIK_GATE (`run_svc_att_ik.sh`) | **PASS**: base PASS on 3 seeds; mut4, mut5 and mut1 all caught |
| SELCHAIN_GATE | **PASS**: 3 seeds; pair_err 0, rung_err 0, neg_fault 1 |

### Lint

Verilator `--lint-only` via `rs_fv_lint.sh`: **errors 0** on all 21 tops. These are `dsdv_svc_rs`,
`dsdv_svc_rs_f2b`, `dsdv_svc_rs_pvso_entry`, `dsdv_svc_rs_pvso_entry_f2b`, all 15 `*_f2b<FH>` variants and the legacy
`dsdv_svc_rs_fv_0110101001` and `dsdv_svc_rs_pvso_entry_fv_6aa60e0ee0`.

The first lint run found that the legacy entry variant was connecting gh ports that its master does not have. I fixed
the generator so the legacy entry variants are byte-identical to the base, then re-linted that variant: 0 errors.

### face_guard on the 2-beat fold pins (CP1-R10, `tools/die_plan/face_guard.py`)

The design is yosys generic synth of `dsdv_svc_sx` with each FH, in a pure-wire wrapper that exposes the `gh` faces as
the variants do. Relay stations and `dsdv_svc_sx_hrow` are black boxes, as they are macros in the kit. The checked
ports are `gh_o_<f>` / `gh_i_<f>`.

| FH {GI,GO} | bits | result |
|---|---|---|
| 11 (N in + N out) | 2,136 | **PASS** 2136/2136 |
| 44 (S in + S out) | 2,136 | **PASS** 2136/2136 |
| 01 (N out) | 1,068 | **PASS** |
| 40 (S in) | 1,068 | **PASS** |

Every gh pin bit is its own flop: no merged, shared, const, dropped, feedthrough or unregistered bits. The script is
`fg.sh`; the output is `face_guard.json`.

### Yosys cell delta (`dsdv_svc_sx`, generic cells, closed stations as black boxes)

| build | cells | std flops | relay stations (276 b closed macros) |
|---|---|---|---|
| FH 00 (full-width fold) | 381 | 0 | 144 |
| FH 01 (one TX face) | 3,578 (+3,197) | +2,136 | 136 (−8) |
| FH 40 (one RX face) | 2,515 (+2,134) | +2,136 | 136 (−8) |
| FH 11 / 44 (TX + RX) | 5,712 (+5,331) | +4,272 | 128 (−16) |

How to read the table, per fold direction:

- The TX adds 1,066 hold flops, 1,068 pin flops and 1,066 2:1 muxes.
- The RX adds 1,066 `lo` flops, 1,068 pin flops and the fault logic.
- Each face replaces one relay stage: 8 stations × 276 b = 2,208 flop bits.
- **Net register bits: −72 per direction.** Std cells: about +1,066 muxes on the TX side.
- **Pins on the fold face: 2,133 → 1,068 per direction.** The plan's face count is 9,004 → about 6,870.

The `rs_c` F2B logic adds an 8-bit compare against the constant `sx_fh(sid)` and 1 sticky flop. The role and P.V-slot
tables are a different ROM content of the same size.


## Follow-ups (die-level adoption, not on this branch)

These belong to KITS / PORTBIND:

1. The die plan's v4.8 binds still instantiate `dsdv_svc_rs` / legacy `_fv_` variants. The DEC12 die must bind the
   `*_f2b<FH>` variants (`faces_f2b.json`, by sid). It must also map `gh_o_<n|s>` / `gh_i_<n|s>` to the plan's attnh lane
   (1,068 b) and drop the `go_*` / `gi_*` bits of those faces from the attn lane.
2. The census or port-bind alias `gh` ↔ `attnh` is needed in `gen_plan_v4` / `dv_bind`. Then re-run the strict
   port-bind check.
3. **Duty.** The 2-beat lane relies on the compiled schedule spacing gather words at least 2 cycles apart. TOK-DS has
   not yet confirmed that gather duty is at most 50%. A violation is caught in silicon as a sticky fault. It is not
   arbitrated.

# Qwen3-8B TP8 split: compute die <-> KV/system die link, v1 (2026-10-14)

Owner decision 2026-10-14 06:45 PT: Qwen moves to two dies per TP rank, a compute/ROM die and a KV/system die. This file
is the link contract. The KV/system-die lead (stream log `el1014-qwen-split-kvsys.log`) owns it. The compute-die lead
(`el1014-qwen-split-compute.log`) owns the compute-side placement of its end.

Measured evidence: `link/measured.json`, `link/results.txt` (bench `rtl/test/qwen_split/tb_qwen_split_link.sv`).

## 1. What crosses

The split keeps every closed KV-side master: the sequencer `qkd_seq` (`ot_qkvd_kv_seq_merged`, HEADS 1 / Q_FP32 1), the
KV end of the link `qkd_d2d` (`ot_qkvd_kv_end`, thin cluster SPL 1 over its 18 closed tiles), and the compute end
`qfd_d2d_rom` (`ot_qkvd_rom_end`). Two new small masters translate between the sequencer's ROM-side faces and the
link classes:

- `qkd_lnk` = `ot_qkvd_split_kvlink`, on the KV/system die, abutting `qkd_d2d`;
- `qfd_lnk` = the codec in `ot_qfd_split_romlink`, on the compute die, abutting `qfd_d2d_rom`.

Faces that stay on one die:

- **KV/system die:** host (`qkd_host`) <-> sequencer `hc` / `tk`; sequencer <-> stacks / landings / controllers;
  embedding gateway <-> landings; PLL / reset.
- **Compute die:** everything ROM-side (tiles, VM, SU, tree, collective and its SerDes).

## 2. Physical layer

| Item | Value |
|---|---|
| Macro | `ot_qkvd_ucie_x64_phy`: UCIe-A x64 module, abstract in `physical/qwen_kv_die_phy`. Area 0.6047 mm², 777.6 µm shoreline per die, one module per die. |
| Raw rate | 64 + 64 lanes at 16 GT/s = 1,024 Gb/s each way |
| Load | One 548-b flit per 1.2 GHz cycle each way = 657.6 Gb/s (64 % of raw) |
| FDI-to-far-FDI latency | 3 / 5 / 9 cycles (best / typical / worst). The measured sweep covers all three. |
| CRC / retry / FEC | **Owed as real RTL** (owner 08:05 PT, no stubs: only the PHY analog may be a behavioural model). v1 assumed them inside the vendor macro. Our adapter (`ot_qkvd_d2d`) checks the sequence and fails closed. The CRC / retry layer goes between `ot_qkvd_d2d` and the PHY model at both ends, and the link cost is re-measured with it. |
| Placement | KV/system die: the macro on the N short edge at the centre column. Both long edges are HBM shoreline (2 x 12 mm PHYs each), so the link cannot go there. Compute die: on the edge that faces the KV/system die (compute lead). |
| Clock | One 1.2 GHz domain. The system-die PLL forwards the clock and reset on a bump pair beside the macro (`qkd_ckbump` -> compute `qfd_clkrx`). The dies are mesochronous. There is no CDC in our logic; the HBM CDC stays on the system die. |

Bandwidth check (per layer, native TP8):

- forward: 36 data words + about 2 CTL words;
- reverse: 32 RES words + about 2-4 SCTL words.

That is at most about 40 flits each way for a layer of about 1,050 cycles, about 4 % of the link. Embedding adds 65
EMBQ + 65 EMBD flits per token. A wider PHY would not help: the sequencer's `x3` and `ar` faces move one 512-b word a
cycle, and the measured cost is latency, not serialisation.

## 3. Classes and word formats

The flit and adapter are unchanged: `{seq 8, credit return 4 x 2 b, dv, class 3, word 528 = {tag 16, data 512}}`.

| Cls | Name | Dir | Producer -> consumer | Count | Word |
|---:|---|---|---|---|---|
| 0 | CTL | C->S | ROM sequencer `sd` (56-b levels) and SU `kvd` (posted descriptors) -> `qkd_lnk` -> sequencer | about 2 per layer + 1 per stage | `tag[15:12]` op: 1 = SD `{data[55:0] = sd}` (event word, sent on change); 2 = KVD `{data[42:0] = kvd[42:0]}` (one per descriptor) |
| 1 | Q | C->S | SU `x3` (class 001) | 32 / layer | `{10'd0, beat 6 \| 16 FP32}` (FP32 kept; RNE to BF16 only at attention ingress) |
| 2 | KVN | C->S | SU `x3` (class 010) | 4 / layer | `{13'd0, tag 3 \| 64 E4M3}`, tags 0, 1 (K) and 4, 5 (V) |
| 3 | EMBQ | C->S | SU `ea` -> `qkd_embgw` | 65 / token | `{15'd0, kind \| 488'd0, addr 24}` |
| 4 | RES | S->C | sequencer `ar` -> VM | 32 / layer | `{9'd0, g = 0, beat 6, 16 FP32}` (`ar_d[518:0]`) |
| 5 | EMBD | S->C | `qkd_embgw` `eq` -> SU (posted) | 65 / token | `{16'd0, data 512}` |
| 6 | SCTL | S->C | sequencer `ds` (187 b) + `pw` (75 b) -> ROM sequencer / ROM control tile | 2 per stage + program writes | `tag[15:12] = 3`, `data[261:0] = {pw, ds}` (event words). Pulse bits: `ds[42]` h_start, `ds[118]` pws_v, `ds[186]` dw_v, `pw[74]` pw_v. |

**Level faces as events** (`ot_qwen_split_lvl_tx` / `_rx`).

- The sender sends a word whenever the registered face changes, or when a pulse bit has fired since the last word.
- The receiver holds the latest levels. It asserts each pulse bit for exactly one cycle after that bit's word arrives.
- The per-class order is the sender's order, so `s_done` (which must fall before it rises, the done_armed rule) and
  the `stage` / `token` / `pos` latched with `h_start` arrive in sequence.
- A pulse that fires again while its previous firing is still waiting for a credit is a sticky fault, never a merge.

## 4. Credits and buffers

| Loop | Credits / buffer |
|---|---|
| SU `x3` -> `qfd_d2d_rom` | XS >= 2 x C_ST + 48. One native layer is 36 words. |
| ROM end <-> KV end, per class | Link buffers as in CONTRACT v1.1. Q 32, KVN 8, CTL 4, EMBQ 32; RES 32 (= `qfd_d2d_rom` RB_RES), EMBD 32, SCTL 4. |
| KV end -> `qkd_lnk` (abutted) | Q QD = 8, KVN 8, CTL 4, EMBQ 32. The bridge FIFOs have the same depths. |
| `qkd_lnk` -> sequencer `x3` | The sequencer's single pool XS = 40. That covers one 36-word layer, so a layer never waits for a credit. |
| Sequencer `ar` -> KV end RES | Sequencer OCR_AR = 64 = `qkd_d2d` UCX = 64. The hub has no ready, and a layer starts only with 32 RES credits in hand. |
| `qfd_d2d_rom` -> VM `ar` | OCR_AR >= 2 x C_ST + 40 |

Every face input is captured at a pin flop, and every output is launched from a flop. Relay stations carry data
forward and one credit pulse back. Each station is a register with at most 500 µm of wire in front of it.

## 5. Measured cost (native protocol; `link/measured.json`)

The bench covers one full decode step (38 stages: E, L0..L35, H) through the real RTL:

- the ROM end and its codec;
- the PHY model pair;
- the KV end, flat and as the closed thin cluster;
- the bridge;
- the unchanged sequencer at HEADS 1 / Q_FP32 1.

Exact-data checks pass on every case:

- Q -> RES carries Q bit for bit;
- the posted K / V rows;
- the four quadrant copies;
- the token handed back at H.

Three mutants fail as required:

- a flit dropped in the PHY: 1 error;
- Q beats 0 and 1 swapped: 72 errors;
- the V tag dropped in the bridge: 73 errors.

| Case (ENG 849) | Attention, first `x3` word -> last RES at the VM face | Decode step |
|---|---:|---:|
| Engine only, zero distance | 965 | 37,831 |
| Merged die, 24 on-die relay stages each way | 1,013 | 41,383 |
| **Split, C_ST 8 / K_ST 16 / PHY 5 / KV end thin cluster (design point)** | **1,052 (+87)** | **44,421 (+6,590)** |
| Split, C_ST 26 / K_ST 16 | 1,088 (+123) | 47,085 |
| Split, PHY 3 / 9 | 1,048 / 1,060 | |

How the costs combine:

- **Linear model** (fits all 18 split rows exactly): attention = 965 + 39 + 2 x (C_ST + K_ST) + 2 x (PHY - 5). The
  fixed 39 covers both directions of the codec, `qfd_d2d_rom`, two PHY traversals, `qkd_d2d` and `qkd_lnk`. With a flat
  KV end it is 31. The deltas do not depend on the attention body: ENG 200 and ENG 849 differ by exactly 649 cycles in
  every case.
- **Per layer, attention:** +87 cycles at the design point. The TP4 BF16 estimate was +455.
- **Per stage, stage stepper round trip:** about 91 cycles. The stepper (`ot_qfd_dctl`) stays inside the closed
  sequencer on the KV/system die, so `h_start` / `s_done` cross once per stage.
- **Per token:** +6,590 cycles against a zero-distance die.

Effect on the TP8 SPEC B4 central model (205,496 cycles/token, which already carried 100 cycles/layer of on-die
crossing):

- 208,486 cycles/token = **5,755.8 tok/s**;
- **-1.43 %** against the merged-die B4 central;
- **+2.68 %** against track A central, which carried the measured 455 per layer.

The immutable price, the TP4 two-die token path, already contains the 455-per-layer link. The split is under it, so
this needs no ledger row.

**Structural lever (not taken in v1).** Move the stage stepper (`ot_qfd_dctl`) next to the ROM sequencer on the compute
die. The host `hc` / `tk` faces (one per token) would then cross instead of the per-stage `ds` / `sd` faces. Measured
saving: about 38 x 91 = 3,460 cycles/token, about 1.7 %. It needs an RTL change in the closed `qkd_seq_core` leaf,
plus a re-route.

## 6. Open items (owner: this stream unless named)

0. **Release blocker (no stubs):** CRC / retry / FEC digital layer as real RTL at both link ends, plus a re-measure.

1. Link faults must reach the host status (`kst` / `tk` fault code). The merged sequencer dropped `d2df`. Sources:
   `qkd_d2d` fault, `qkd_lnk` fault, and `qfd_d2d_rom` fault (over SCTL).
2. Exact relay counts come from the dies: C_ST from the compute-die plan (compute lead) and K_ST from the
   KV/system-die plan (section 1 of `CONTRACT_KVSYS.md`).
3. `qkd_lnk` and `qfd_lnk` need ref_tile kits and routes. Each is a new small master: about 10k flops for qkd_lnk (Q and KVN FIFOs 8 x 518 b each),
   about 0.5k for the codec.
4. A production-shape throughput run with the real attention body (HEADS 1 native PV256) replaces the timing stand-in
   once the native attention is qualified.

# Qwen ROM r22ko4 die seam bench (el1011-qseam, 2026-10-12)

- **Source:** `tools/qwen_die_seam/` at 3614755c0 (`extract.py`, `gen_bench.py`, `summarize.py`, `collect.py`, `run.sh`).
- **Contract:** `results/arch/hier_contract_1011/qwen_rom.json` v5.
- **Simulator:** Verilator 5.050 on ot-epyc1tb, run under a systemd-run memory cap.
- **Run directory:** `/srv/opentallas-scratch/claude/qseam-1012/runs`.
- **Full record:** `record.json`.

## What is built
- **Seam table.** `extract.py` reads the die-chain netlist `die.v`: r22ko4 e7 case, `tools/qwen_rom_fulldie_b3r2.py --recipe r22ko4`, src 22760e79f. The file was copied off EPYC3 to `/home/ubuntu/closed_archive/qseam-1012/case_r22k/`. It holds 6,392 buses and 9,896 relays. This census equals the contract v5 `die_top_logic.relays` exactly: 139 relay masters with 0 mismatches. `gen_bench.py` asserts this match and refuses to build if it fails.
- **Seams.** Every non-clock bus is built as the registered link the die places: source out flop, then K `ot_qwen_die_station` TAP 0 relays (K from die.v), then the sink pin.
- **Station words (v5 D5).** Corridor and tap station words are 509 bits: 508 data plus a ready that is wired backwards through every relay and station. The ready reaches the VM xw/xe pins as 1.
- **Composed seams.** Element latencies are checked at the contract values:
  - vm_grp x path: K + XVM, with XVM = 25.
  - SU master: Ka + VL + Kq, with VL = 15.
  - ctlm p_am pin register: K + 1.
- **Monitors.** Every seam has a `qseam_mon`. Each transaction entering the seam must leave it identical, in order, exactly at the contract latency, with nothing left in flight.
- **Stimulus.** Transactions recorded from the Qwen L0-L2 chain (split-partition vehicle `partition_token.py`, stage L3, exact, SEAMREC on die 0):
  - 18 tile instruction issues, carrying the full 379-bit ib.
  - 1,536 tiles × 2,184 lockstep tree-output words.
  - 1,536 collective words and 1,536 collective returns.

## Results (positive runs)
| bench | class | seams PASS / built | transactions | relays |
|---|---|---|---|---|
| p2p | p2p | 128 / 128 | 395,520 | 1,208 |
| p2p | credit (n_rk) | 6 / 6 | 18,540 | 105 |
| p2p | SU master (VL 15) | 1 / 1 | 3,090 | 0 |
| p2p | ctlm p_am (+1 pin register) | 6 / 6 | 18,540 | 121 |
| credit | credit | 32 / 32 | 98,880 | 465 |
| array (deskewed) | corridor (509-bit) | 3,136 / 3,136 | 56,448 | 3,085 |
| array (deskewed) | tree (incl. 96 bwords, 2,926 pads) | 2,976 / 2,976 | 6,499,584 | 7,958 |
| array (deskewed) | vm_grp (XVM 25) | 1 / 1 | 18 | 1 |

Additional checks on these runs:
- **Credit bench:** all 15 lanes deliver every word. A lane's buffer equals its round-trip credits (coll: 127). The receiver stalls 256 of every 512 cycles, and no lane overflows or leaks a credit.
- **Array bench (deskewed):**
  - All 1,440 nodes paired 3,144,960 words with 0 mismatches.
  - All 96 roots match the golden tree reduction in order: 209,664 words.
  - 0 tile errors.

## Finding: the tree legs do not line up as placed (array as placed: FAIL)
- **Failure.** `ot_qwen_rom_tile_nk` pairs n_a and n_b under one valid (`n_va`), so a node's two legs must arrive in the same cycle. The die as placed does not deliver that:
  - The static model shows 1,252 of 1,440 nodes receiving their legs in different cycles, with skew from -12 to +2 cycles.
  - The skew comes from tap arrival differences (36..102 cycles from the corridor) plus unequal relay counts on the tree words.
- **Simulation as placed.** Every corridor seam and every tile t_out seam passes, but 768 leaf nodes never pair, so 0 words reach the 96 roots.
- **Fix used here (`--deskew`).** Add 2,926 pad relays (1.50 Mbit of flops) on the earlier leg of 1,252 tree buses. With them, the tree passes end to end.
- **Rejected alternative.** Equalising tap arrival instead would need 50,560 relays of 509 bits, and 661 nodes would still be skewed by the tree relays alone.
- **Decision needed.** The die generator (e8) should either balance the tree legs or the tile node should get a tag-matching skid. This is a die-contract decision for the Qwen die lead.

## Mutants (every one FAILS)
| seam class | mutant | failure |
|---|---|---|
| corridor | drop relay 1 of n_cor_0_10 | seam latency 1 vs 2. The skew it adds breaks 18 nodes and 3 roots. |
| tree | drop relay 1 of n_tree_0_1_0b | seam latency 2 vs 3. 3 nodes mismatch. |
| p2p | drop relay 5 of n_tt_c0 | seam latency 31 vs 32 |
| p2p | relay 3 of n_emb flips bit 7 | data mismatch at the right latency |
| credit | sender starts with CR + 1 credits | BUFFER_OVERFLOW in all 15 lanes |
| credit | drop relay 3 of n_rs_0 | seam latency 26 vs 27 |
| vm_grp | XVM 20 (the old value) | composed latency 21 vs 26 |
| SU master | VL 11 (the old value) | composed latency 11 vs 15 |
| ctlm p_am | no pin register | composed latency K vs K + 1 on all 6 |

## Limits
- **Bench-defined fields.** Valid is bit 0 of each word: die.v carries no separate valid nets.
- **Element models.** Tiles, nodes, the VM, the SU master and io_xfifo are transaction models:
  - tap pin flop
  - recorded output offsets
  - NL 3
  - XFIFO 4 edges
- **No timing evidence.** This is a functional check only: routed seam timing is covered by the die chain (`seam_check` in the contract).
- **die.v source.** die.v is the e7 netlist (contract v4 placement). The v5 widths for the station and tap words are applied in the bench, because the die generator does not carry them until e8.

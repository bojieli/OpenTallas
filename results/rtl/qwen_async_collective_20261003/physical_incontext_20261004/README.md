# Qwen async collective: in-context SS/FF and hub routing (2026-10-04)

**Verdict: the hardware as built does NOT close at 1.2 GHz. Physical adoption fails.** Under the owner rule this is recorded with its numbers and no rescue.

## The block
The top is `ot_qwen_tp_seq_async_ctx_w12`: the async TP sequencer at the W12 TP4 point (NP 48, MAW 24, FW 512, AR256, QWEN_FULLSHAPE).

- Every port faces a register, as it does in the die.
- The 48 ME-tap inputs are driven by registers that stand in for `o_we2`/`o_addr2`/`o_mask2`.

## The flow
- **Script and target:** `run_abi3_physical.py`, `synth,pnr`, at 0.833 ns.
- **Corners:** SS is the primary corner. Repair runs at both SS and FF.
- **Constraints:**
  - uncertainty: 60 ps setup, 25 ps hold
  - max-transition, max-fanout 32, slew margin 30%
  - adder map off
  - die area 130 x 130 µm
- **Hold-margin variants:** `a0h`/`a1h` add `--hold-margin-ns 0.01`, which is the W11 recipe.
- **Signoff timing:** per-corner OpenSTA on the routed ODB with RCX SPEF, using `tools/qwen_async_seq_incontext_physical.py sta`.

## Results

| | ASYNC_COLL=0 (a0h) | ASYNC_COLL=1 (a1 / a1h) |
|---|---|---|
| SS setup WNS | **+17.1 ps**, 0 failing | **-546 / -544 ps** after GRT repair (CTS: -533 ps, TNS -141 ns), 548 failing endpoints, all `seq.lw[*]` |
| FF hold WNS | **+6.2 ps** | not reached |
| Routed std-cell area | 3,199 µm² (24,552 cells) | not reached |
| Pre-layout TT area | 2,352 µm² | 5,168 µm² (+2,816 µm², including wrapper registers) |

- **a0 without the hold margin:** SS +15.7 ps, FF hold -0.73 ps on one wrapper output flop.
- **Failing path:** `seq.vw` → 24-bit `me_addr - vw` and range compare → one-hot decode → 48-port OR tree (6 levels of OR3/OR4) → `lw`.
  - About 1.3 ns of logic in one cycle: this is logic depth, not fan-out.
  - Repair stalled at the same WNS for more than 2,300 iterations.
  - It is new with the async scoreboard; the baseline sequencer closes.
- **Pre-layout fmax** (218 and 222 MHz) is set by fan-out in both settings and hid this path.
- **Committed-write gating** (`vw_me_we & me_clk_en`, the REAL_MEM die) would add one AND per port to this same path. It was not modelled.

## Hub routing (`hub_route_check.json`)
- **Inputs:** the full-die placements (`claude/qwen-rom-fulldie-20261003` @ c3a56754) and the r2 netting rule with the corridor-gate routed ratios.
- **Route:** the tap carries 48 x (1 + 24 + 16) = 1,968 wires.
  - It goes from the tree_top east face, across the 174 µm vertical link channel on M6/M8, to the sequencer slab.
  - Together with the baseline sequencer buses it is 4,075 wires: 9.6% of the netted target and 6% of raw over the 2,428 µm overlap window. It needs 644 µm of band at the 0.225 routed-pass ratio. **PASS.**
- **Wire timing:** the 174 µm hop is a 459 ps SS wire stage, so the tap needs its own register stage. That is +1 cycle per scoreboard set, at most 2 cycles a layer, and it stays exact.
- **Rejected placement:** riding the tap along the existing ME→VM write bus. That cut already carries 26,544 wires against 25,697 raw vertical tracks.
  - This is a pre-existing gap in the full-die bus model: the write bus is not modelled there.

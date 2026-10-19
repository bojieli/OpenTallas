# Native landing boundary prototype

`ot_hbm_svc_sm8_landing_boundary` is an opt-in replacement for one
`ot_hbm_svc_sm8_landing_bank_sram285`, with identical external port names.
Production parameters remain BANK 0..7, LBANKS=4, RESPONSE_DEPTH=8, IW=285.
It wraps the actual 8x285 dual-clock FIFO and 256x256 landing SRAM. Original
release masters are byte-identical. This prototype is behaviorally qualified;
it is **not gate-ready** until the remaining physical checklist is satisfied.

The analytical model was committed before RTL (2dc162539, revised reservation
model f624c0dd4 before three-slot RTL ca1c98b66), and is callable through
`uarch_model.hbm_svg_landing_boundary_model()`.

## Admission and native clocks

HBM pins use `hbm_clk`; reserve/read/stop and payload/completion/fault pins use
`stream_clk`. Each domain has its own asynchronous-assert, two-edge-release
reset landing. First HBM ready appears at the third rising edge after release,
after both reset stages have released. Hold both domains in reset together when
flushing the asynchronous FIFO, as required by the original FIFO contract.

Each 16-bit segment captures its input every HBM edge, then writes a three-slot
ring under a kept local valid register. Kept local write/read pointer copies
avoid a common pointer driving all 285 data muxes. Eighteen segment-control
copies consume global push/pop, below 32 loads at RTL. The 285-bit pin register
and three 285-bit ring entries total 1140 bits; the ring is not a flop delay
chain. Actual FIFO and landing storage remain in SRAM.

Let R be reserved words, P the one-cycle pin pending flag, A=in_v&&ready, and
D=(R>P)&&core_ready. Then R_next=R+A-D, P_next=A, and
ready_next=(R_next<3). Queue occupancy is R-P. The invariant is
0<=R<=3 and ready==(R<3) after each active edge. If ready is high, R<=2,
so accepting A cannot overflow. A simultaneous ring read/write uses distinct
addresses unless empty/full; empty never pops, and full cannot admit another
reservation without a drain. When a pin word is pending with no drain, the
ring has at most two entries, so the pending write always has capacity.
Only D drives core FIFO valid, preserving the original overflow convention.
Inputs asserted while ready is low raise sticky ingress overflow, matching
the original pulse-on-admission producer contract.

The third reservation matters: with two reservations, the two-edge ingress
pipeline sustains only 2/3 word/HBM edge. The three-slot ring sustains one word
per HBM edge after priming. No new SM backpressure or credits are introduced.

## Fixed latency table

Edges refer to the rising edge at which the original consumer samples an
input or output. The existing macro/FIFO clock-crossing latency is unchanged.

| Path | Original event | New event | Compiler price |
|---|---|---|---|
| HBM admitted response | FIFO write H0 | Pin capture H0, ring write H1, FIFO write H2 | +2 HBM edges, plus existing CDC phase rounding |
| Reserve pins | State changes S0 | Pin capture S0, state changes S1 | Issue reserve 1 stream edge earlier |
| Stop pins | Stop applies S0 | Pin capture S0, stop applies S1 | Issue both assert/release 1 stream edge earlier |
| Read pins to read_data | SRAM result after S0 | Pin capture S0, SRAM result after S1, output capture after S2 | Issue read 2 stream edges earlier |
| Completion consumer | Samples old combin completion at landing write edge S0 | Pin publishes after S0, consumer samples S1 | +1 stream edge |
| Fault consumer | Original fault sampling edge | Sampling 1 edge later | +1 stream edge |
| Overflow consumer | Original overflow sampling edge | Sampling 1 edge later | +1 HBM edge |

HBM ingress delay is two edges when unblocked, and may grow under the existing
HBM-side ready protocol. Static SM timing must allow the priced prefetch edges;
there is no performance credit until the parent schedule composes them.

## Component evidence

`run_svg_landing_boundary.sh` uses fleet Verilator 5.050, real macro models,
and the original flop-FIFO landing master as a reference. The external accepted
stream is score-boarded independently, then replayed into the reference at the
new FIFO write edge. This checks ordering and all payloads, with reference
reserve/stop/read delays matching the fixed table. It checks the reservation
invariant every edge and checks two-edge ingress on unblocked transfers.

Pinned RTL/bench revision: 72be5e25a. Evidence in
`rtl/test/hbm_accel/svg_rel/landing_boundary_evidence/`.
The production LBANKS=4 bench passes 408 payload readbacks, 12 block completions,
413 admitted packets (408 payloads, four reset-flushed packets, one duplicate),
three reset episodes including occupied ingress, and stop/full/release bursts.
Twelve independent 16-sector windows at both pins and core FIFO each take
exactly 16 HBM edges. Peak contiguous burst is 23 edges. The duplicate guard
still trips; epoch/count/ordinal checks are inherited without modification.

Mutant 1 removes the pending pin reservation from ready calculation:
`ADMISSION_FAIL` / `RESERVATION_INVARIANT_FAIL` witnesses capacity loss.
Mutant 2 breaks actual macro FIFO head prefetch: `EVENT_FAIL` witnesses mismatch
against the original master. Witnesses are committed, not waived.

## Safe-design checklist before any gate

1. **Fixed at RTL:** every data/control pin enters or leaves a native register;
   each reset lands in two stages. Reset distribution still needs mapped audit.
2. **Model PASS, physical pending:** 224.64x181.44 um proposed element envelope
   is below 405 um reach. No placed wire-reach claim is made.
3. **Fixed at boundary, not yet PASS overall:** 16-bit kept segments and 18
   global control loads. Must audit mapped kept copies and inherited core
   bank/seen/count mux controls; the original core fanout is not qualified here.
4. **Fixed at boundary, physical pending:** no combinational pin-to-pin path;
   native captures and shallow ring muxes. Inherited logic depth needs STA.
5. **PASS by construction:** 1140-bit ring/capture uses flops, all larger payload
   stores use actual SRAM. No three-stage shift-register delay line.
6. **Not yet PASS:** use the existing macro-model lattice/envelope proposal,
   then size from synthesis area at 40-60% utilization, verify full-width cell
   band, full-face <=6 pins/um, aspect <=2, and pin-face channels before gate.
7. **Fixed roots, physical pending:** separate HBM/stream roots and landed CDC;
   measure pin-flop spread <=80 ps TT/FF and hold margin >=0.03 ns in parent.
8. **Model PASS, integration pending:** no new SM flow control; all fixed edges
   are explicit above. Parent GO/reserve/read/cache-prefetch schedule must
   consume them before claiming production timing or rate.

No REVIEW.json, gate, submission, adoption, or physical closure is claimed.

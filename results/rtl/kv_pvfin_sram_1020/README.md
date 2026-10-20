# PVFIN SRAM successor (K.STA.PVFIN)

Source behavior proved at `ccf0752a2`; its production native census FAIL is preserved. R6 `21d73156e` is in proof/census. No layout or release qualification claimed.

The established uarch vehicle is the single 512-bit PVFIN beat slice in
`results/arch/qwen_kv_pvfin_1017/plan.json` (existing arithmetic model).
Sixteen LAT-7 adds and sixteen LAT-6 multiplies sustain one beat/edge for 32
beats. Both input ports carry 64 B/edge, the result port 64 B/edge; four
32x128 1R1W SRAMs hold 2,048 B of sums. Each SRAM reads and writes 16 B/edge.
The sum-buffer memory boundary therefore needs 512 write bits/edge and 512
read bits/edge. Replica count is four banks; each address/control reaches
four macro ports. No arithmetic replica or command latency is added.

The SRAM read is issued two edges before MUL_AGE+b. Three kept 512-bit
operand captures occur one edge before that same multiply slot. Writes at
either of the two prefetch edges forward the corresponding sum. The
critical earliest legal timeline is MUL_AGE=SUM_AGE+1: final capture sees
the sum directly while SRAM may still contain an older command. The
second case MUL_AGE=SUM_AGE+2 uses first-edge forwarding. MUT4 suppresses
first-edge forwarding; MUT5 suppresses final-edge forwarding.

Operand deskew uses fixed-age one-hot selections in 16 kept banks of
32 bits; there is no runtime-indexed payload read mux. Reciprocal head
selection similarly uses per-lane kept one-hot controls. Data and
normaliser copies are actual same-edge registers with independent random
power-up state. Every valid transaction defines those registers before
use. Mutable SRAM uses the existing academic fault-free assumption.

Safe-design checklist (pre-layout):
1. Pins: inherited data pin flops; control pin flop. Reset assertion/release
   uses two bounded farms, three-edge release (+2 boot edges vs legacy).
2. Reach: 259.2-square inherited slot is within 405um axial reach; actual
   macro placement and routed reach audit remain owed.
3. Fanout: RTL copies and bounded leaves implemented; mapped census owed.
4. Depth: arithmetic cuts unchanged; mapped depth measurement owed.
5. Storage: 16kb indexed sum flop bank replaced with 4 SRAMs. Fixed-age
   operand taps remain fixed pipeline registers (explicit lane brief).
6. Floorplan: 4 macros need a lattice/face-density floorplan and synthesis
   area measurement before any gate; legacy no-macro kit is not usable.
7. Clock: reset leaves <=32 by construction; native census, TT/FF spread,
   neighbour boundary and hold margin >=0.03 remain owed.
8. Schedule: all token ages unchanged; only reset-release boot grows two
   edges. Sustained production throughput proof is the 32-beat exact
   one-beat/edge output scoreboard; immutable measured receipts owed.

Do not submit or gate until the native census passes. Original module and
closed views are untouched. R9 library add/mul/reset files were imported
from claude/kv-params4-qkh-1020; live-b multiply is a separate PVFIN module
with 4 a operand row copies, 4 b operand column copies and split input
normalisers. This variable-b path requires mapped census verification.

R5 verification (V5.050, source hashes in r5_proof/m*/source.sha256):
- Main gate-style suite: 40 unstretched + 48 stretched commands, 2,816
  output beats. Every valid beat compared against the full original
  qkd_pv_fin_s; two blocks per command also against the independent golden
  finalize arithmetic. All ages/beat indices/epochs exact.
- Three additional independently randomised power-up seeds (1,29,53),
  40 commands in each stretch regime: another 7,680 output beats. Total
  328 complete commands / 10,496 valid output beats, one beat per edge.
- Each non-negative run first aborts a command after partial SRAM writes,
  then starts a fresh command after bounded reset. Periodic reset epochs
  every eleven commands prove stale SRAM payload is never read valid.
- NEG1..3 fault; causal MUT1..5 all detected. Witness logs are committed.
- R3 RA=1 regression and R4 bench-parser failure are preserved under
  preliminary/. The RA=1 fix predicts the first reciprocal slot directly
  from the incoming calendar on the command edge.
- Preliminary census is diagnostic only: it predates bounded payload
  selectors and omitted macro Liberty roles (516 role errors); its 17
  fanout violations, max 1536, were principally selector distribution.
  The production census includes SKEW=1 and the actual SRAM Liberty.

R5 mapped verdict (not overwritten): FAIL max166 /117 violations /0 role
errors. Area including SRAM is 34,863.011 um2; four macros total 4,275.089
um2, leaving ~30,588 um2 cells and ~48.6% utilisation in the inherited
259.2-square frame after macro subtraction. Violation classes: 80-bit
command capture shared enable (166); 32-bit CE and forwarding selects
(64); operand taps folded into FP input decode (40); active/control (38).
All arithmetic-library drivers are <=32 on this vehicle. R6 divides data
selectors into16-bit pieces and command captures into8-bit pieces, with
independent pin images. Gate admission remains blocked on R6 census.

The live-variable multiplier independently passed 11,997 valid outputs
per seed x3 against the original LAT6 multiplier, including subnormals,
NaN/Inf, finite overflow, arbitrary 32-bit operands and midstream reset.

Physical pre-gate correction: the original32x128 macro has199 pins on
its20.79um SHORT face, 9.57/um, and is not admissible. The p192_pvfin
successor uses the established p192 calibrated lead RC/cap/energy recipe:
51.408x39.96um, 199/39.96=4.98pins/um. Storage, behavior and cycle timing
are unchanged; TT clk-to-q274.1ps and minimum period278.6ps include the
extra lead. Four macros total8217.055um2, conservatively ~52% slot use
with the R5 cell area. Original master bytes stay unchanged. The final
R7+ mapped census and gate must bind the stretched master Liberty/LEF.

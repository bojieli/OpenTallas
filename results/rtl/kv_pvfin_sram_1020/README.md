# PVFIN SRAM successor (K.STA.PVFIN)

Source work in progress; no layout or release qualification claimed.

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

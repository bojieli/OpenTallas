# A0 native reset source continuation

This packet creates an isolated specialized native source,
`qfd_tile_nk_regroot5_reset_native`, from the preserved actual REGROOT5
synthesized ODB. Production RTL and wrapper parameter defaults are unchanged.
No gate, REVIEW, submit, native LEF selection or physical acceptance occurred.

The source is `r3/candidate.v.gz`. The exact input ODB is retained as
`r3/input.odb.gz`; `r3/manifest.json` pins its SHA256 and every changed original
input. The generator and actual native state/cell models are committed. The
original worktree and all earlier fleet jobs remain untouched.

The reset source now has two asynchronous-assert, synchronous-release face
stages on `ck_fa4`, one face-clock branch stage, and 19 destination-clock leaf
stages. Raw reset drives exactly one actual `RESETN` pin. All new FFs are actual
`DFFASRHQNx1_ASAP7_75t_R` cells; dedicated local tie cells drive each D/SETN
pair. Each leaf drives at most24 original native inputs. Independent audit
covers all22 reset FF outputs and all120 original reset-dependent endpoints:
91 native asynchronous reset pins, one hard-node reset pin, and28 synchronous
reset-logic inputs. There are17 actual reset-tree clock nets.

All38,544 original cells remain, with the original face reset state changing
from native DFFHQN to DFFASRHQN. Every other original master is preserved.
Only the original face D connection and the120 explicit reset-dependent input
connections change. All original non-reset cell equations and connections,
including D/enable/mux feedback, remain. Added state is21 FF; total added cells
are65 (21 FF,22 INV,22 local TIE). Actual total state15,651 FF; synthesized
standard area6293.13624um2 vs6283.16352um2 before reset (+9.97272um2), hard
area322971.4944um2 unchanged. These are actual native area inventories,
separate from the inherited unplaced floorplan model.

The independent state audit follows the28 synchronous reset-logic endpoints
through all combinational gates to260 actual FF D inputs. Symbolic proofs use
actual Liberty-to-Yosys native gate equations and native asynchronous pin
semantics: six metadata FFs clear QN to1 (positive state0), and254 core context
FFs retain QN exactly. Zero states are unproven. Those254 fields must not be
converted to asynchronous clear: retention is part of the existing behavior.
The full equations and individual classifications are retained.

Assertion propagates asynchronously through face, branch and leaf while ALL
clocks are stopped. Raw deassertion while stopped releases nothing. Release
requires two `ck_fa4` face sample edges, the next branch edge, and then each
local destination edge after the branch is high. With aligned clocks this is
four edges. Original synchronous metadata clears on its first resumed edge
while its leaf remains low; leaf release can occur on that edge, and subsequent
edges may consume metadata. A physical phase/resume contract remains unbound.
The actual native tree cut passes32 independent resume scenarios across17
clock nets/22052 checks. Missing leaf, missing face stage, lost async assertion,
and missing branch mutants each fail. Native functional simulation uses
Verilator5.050 and the actual Liberty functions; it is not timing simulation.

The strict full64-MAC numerical comparator is preserved under `diagnostics`:
r1 (synchronous-only tree) passes its limited clock-stop scenario; r2/r3 each
fail95 idle-payload comparisons after the stopped TX warm reset, while each
has5120 real nonzero valid outputs. The invalid payload contains retained
unreset data; changing it to zero would change existing state semantics.
The coordinator authorized a separate protocol comparison that checks all
status/valid bits continuously, checks every payload bit when either side is
valid, and reports all invalid-payload differences separately. It introduces
no hardware data mask, gate or drop. That numerical continuation is pending
when this document is first committed; see the final receipts before use.

Remaining actual all-root census: seven FF roots exceed32 (split[3:0], wsrc_r,
active_o, k_last; maximum415). There are70 nonclock drivers above32 in total:
seven FF,61 combinational/buffer roots and two tie roots. The complete native
census is retained, including all failing and passing classes. Reset is one
bounded source step, not a full safe-design PASS.

The previous REGROOT4 +65FF/zero-edge operand/round proof and REGROOT5 +513FF/
+1 data-valid return edge remain distinct. This reset change adds boot/reset
sample events, no steady-state data edges. The REGROOT5 node-edge compiler
obligation, ROM return ages, full-token price, all remaining runtime-indexed
state and delay>=3 inventory, physical reach<=405, row/PG/channel geometry,
clock pair reserves and TT/FF native timing are all still open. No data timing
exceptions, invented phase or stand-in binding is introduced.


| Safe checklist item | Source proof / remaining obligation |
|---|---|
| Pins/reset | Raw1RESETN, two face release stages and bounded actual leaves proved; physical face positions and pin access open. |
| Reach | Exact endpoint cohort list supplied; no placed reset/control segment<=405 proof yet. |
| Fanout | New reset source max24; seven original FF and70 total nonclock driver failures remain. |
| Depth | Native asynchronous and gate equations pinned; loaded reset recovery/removal and data-cone timing open. |
| Storage | New21 reset state bits are static tree controls; whole-parent runtime array/delay inventory remains open. |
| Geometry | Predecessor model retained; new FF/INV/TIE row positions, continuous band, tracks, PG and escape not implemented. |
| Clock | Existing17 tree-owner clock nets, no added entry; actual phase/native TT/FF and pair reserves unbound. |
| Schedule | Four aligned reset release events, independent resume ledger and static boot guard tested; no steady data edge added. |

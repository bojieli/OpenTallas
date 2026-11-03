# Disabled QC FDI station/calendar contract and native pulse counterexample

This advances the SerDes source-domain trace with an actual selected-RTL
counterexample and explicit compiler constraints. It does not emit a changed
binding, replace a model globally, add a public clock, alter a programme, or
qualify physical 1 GHz operation.

The source is the exact frozen `bd55` Git blob for
`rtl/rom/ot_coll_static_linkcal.sv`, recovered by the QC source owner. SHA256 is
`c0248ae00f9b425969960a88cdea9dd0423a8b6387901676ef0a6f3d33aad8dd`;
Git blob `d450165681831030d729b5e73b13ffc74b5440e8`.
`inputs/selected_face_calls.json` records the actual three calls in current
`bind_complete4`, not a historical profile. They select SAFE0/TOK_REG0, hence
native `ot_coll_lcal_tx` KC4/KW2, SAFE_RING0/LAND_CORE0. The selected PHY calendar
values are **367/343/369**, with L436 and R21/23/23, peer-R23/23/21. Their base
is 339 plus LX28/4/30; 367 is the first face's composed PHY value, not a common
base for all three faces.

The existing native CDC SRAM preserves records, but the selected calendar
directly samples its one-core-edge `slot` into the FDI KC4 shift chain. Its own
source contract says the compiled tokens and measured related-clock phase must
make this sampling valid; observed validity never reschedules a missed token.
Thus restoring FDI clocks on the 15 boundary and 95 FT groups cannot, on its
own, establish a valid whole-interface schedule.

The minimal component test compiles that original calendar only. Core timing
matches the frozen vehicle exactly: 833 ps period, first positive edge416 ps;
declared FDI is 1000 ps, first positive edge500 ps. Public clock values are
unchanged. Reset has settled well before either test slot. Both cases present
one real core-side slot to the same native body:

| Case | Core slot interval, ps | Next FDI edge relative to launch | Native result |
|---|---|---:|---|
| Core edge100 | 83716–84549 | 784 ps | One source slot, one FDI read slot: PASS |
| Core edge101 | 84549–85382 | 951 ps | One source slot, zero FDI read slots: **FAIL retained** |
| Edge100 with private zero-slot RTL mutant | Same eligible interval | Same | Positive oracle rejects the mutant |

The failure is not a statement that every compiled programme fails. It proves
that an unqualified one-edge core slot is insufficient: some source dates are
missed even under ideal clocks. The exact selected RTL is unchanged in the
first two cases. The mutant replaces only the direct calendar crossing's
`.d(slot)` with `.d(1'b0)` in a separate private source file.

Intel2 job `oth-ubuntu-1822435-1793622322` completed this bounded diagnostic under
normal `ot-run` admission at1GB/1thread. No QC hierarchy, data SRAM, PHY, or
clock-generation job was launched. The earlier testbench compile failure used
reserved identifier `edge`; it is preserved in
`run/compile_attempt1_SVkeyword_FAIL.log` and was corrected to `core_index`.
No further Intel2 run is needed; future small gates use the eligible fleet or
Intel1/EPYC2 while the large QC die admission is pending.

For this diagnostic phase, the next FDI edge after core launch n is
`delta(n) = (84 - 833*n) mod 1000 ps`. An ideal strictly interior sample requires
`0 < delta(n) < 833 ps`. The repeating phase pattern is1000 core edges/833 FDI
edges, or833000 ps. It contains832 ideal-capture residues,166 ideal misses and
two edge-coincident residues. `generated/contract.json` provides these sets and
the exact110 proposed typed station roles. This ideal map has **no qualified
setup/hold aperture or physical phase bound**; real timing can only narrow the
permitted set. It is a compiler constraint discovery artifact, not an execution
or sign-off gate.

There is also a concrete calendar component equation. Under a hypothetical
all-FDI station-clock implementation, using current bound stage counts and
avoiding double-counting the hard TX/RX registers already inside LAT223:

| Own face / peer | Peer TX / own RX stages | LAT223 + non-overlapping transport | Selected native PHY | Unjoined difference |
|---|---:|---:|---:|---:|
| 0 / 2 | 26 / 2 | 249 | 367 | 118 |
| 1 / 1 | 2 / 2 | 225 | 343 | 118 |
| 2 / 0 | 2 / 28 | 251 | 369 | 118 |

The common arithmetic difference118 is not a newly adopted delay and is not
proof of an error in the old profile. The CA/count-origin/FSTART and peer-epoch
contribution has not been joined in the proposed FDI clock domain. The disabled
model therefore records `U_j=null` in
`PHY_j =223+(TX_peer-1)+(RX_self-1)+U_j`; it does not replace the selected PHY
values with249/225/251 or borrow118 from an old event. Likewise, selected
`PEER_R-R` is a core-age difference (+2/0/−2), while the native RX calendar adds
it to a link-edge delay. Mapping that correction under833/1000 ps needs the
actual compiled slot phase; its new FDI value remains null.

The genuinely missing contract is now specific:

1. A real clock relationship and bounded data/phase aperture for existing
   `clk_serdes`, preserving mission833 ps and the declared FDI source.
2. An FDI START/reset epoch and paired-peer slot dates that satisfy the native
   sampling condition, including the two independent raw-reset release depths.
3. Typed per-bus roles through all15 bin/bout and95 FT groups, plus their CA,
   FCLK, FSTART and reset infrastructure. The native core/FDI CDC remains intact.
4. A current source programme/calendar object that consumes those domain units
   and reprices the exact transported dates. Token owner confirms821/f79 is a
   source/bind cohort only: no qualified global PW or FDI START epoch exists.

`generated/contract.json` is default-off with `emit_allowed=false`; new calendar,
programme reprice, START epoch and added START/reset FF count remain null. It is
the smallest coherent source/model proposal supported by current evidence.
Producing changed RTL before those inputs exist would silently invent the
missing phase and calendar contract. No regional root is slowed and no physical
or numerical mission qualification is claimed.

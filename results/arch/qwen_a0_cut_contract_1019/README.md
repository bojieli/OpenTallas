# A0 exact cut, retention and epoch contract

MODEL ONLY, based on `8f6101cf2` and unchanged composed native source SHA256 `422b8cdacc31dd6cc14cc912cf91a1a037f2de4e09a4875f1a1d9e0749f4f66a`. The exact semantic source is included with SHA256 `e32fd49a2924e26fe27bc7ea0321062808a1d29082db202a40bcee2d54002ea5`. No RTL was activated and no synthesis, simulation or physical job ran. The compact 3,773-cell / 576-FF assignment is retained as a necessary subset; this packet adds no claim that the whole A0 partition closes.

`model.py` reuses the complete expanded parser: 38,609 cells, 65 concatenated hard connections / 11,480 bits and all 11,567 non-PG hard terminals. It never reuses the incomplete scalar-only parser. `input_hashes.json` names every source/model input. Run `python3 results/arch/qwen_a0_cut_contract_1019/model.py` in the pinned sparse worktree to regenerate the bounded source analysis.

## Exact cuts and existing storage

The 1,154 cut nets comprise **1,145 data or decoded-control nets, five reset/control nets, three ties and one clock**. A tie feeding SETN remains a tie with an asynchronous-control consumer; it is not counted as new payload. The reset nets are `a0_reset_branch_q`, `a0_reset_leaf_00_q`, `a0_reset_leaf_00_qn`, `a0_reset_leaf_02_q` and `a0_reset_leaf_03_q`. The ties are `_21602_`, `a0_reset_leaf_00_hi` and `a0_reset_leaf_03_hi`; the clock is `ck`.

`cut_contracts.json.gz` preserves every cut, its 3,985 distinct immediate external endpoints, actual producer and first consuming storage, actual clocks, and each endpoint assignment. `existing_registered_pairs.json.gz` expands **9,684 distinct existing source/consumer dependencies over 850 existing FF**: 9,347 data/decoded-control pairs and 337 reset/control pairs. These are graph dependencies, not 9,684 new lanes or 850 new landing bits. **9,323 data pairs use logical ck → ck; 24 are actual ck_fa4 → ck data crossings.** Neither case establishes equal physical launch/capture phase. The 24 crossing ports are `u_g.go/QN → logic.go_i/D`, `tap_q[126..129] → ib_i[125..128]` and `tap_q[325..343] → ib_i[324..342]`. `cross_clock_data_ports.json.gz` names each exact source/receiver, cut net and proposed source ownership. These GO/config ports are a direct blocker on treating accepted GO as a proved boot edge. Reset relationships retain `ck_fa4` and their distinct downstream clock identities, including `ck_tx*`, regional roots and `ck_node`.

There are 7,791 FF with direct hard-pin source/consumer anchors in the complete graph. Existing regional IO ownership is assigned from those real pins and first storage boundaries. An otherwise unanchored FF follows the fewest existing FF dependencies to a real hard-pin seed. Among equal-hop candidates, the selected terminal minimizes actual pin-to-band necessary Manhattan distance; ties prefer proximity to the compact region. The proposed IO point is the terminal midpoint projected into the inherited connected band, **not a legal placed FF location**. Every alternative seed/child remains in the ledger. Anonymous shared combinational cones get one joint median band assignment from their actual storage source/consumer anchors; no shared cone is silently copied. Native sites, pin offsets, OBS detours and PG routes remain unqualified. This assigns 2,109 immediate FF endpoints and 1,875 shared-cone endpoints; the remaining endpoint is `PORT/ck`.

## Ten actual unsafe control roots

The three combinational roots admit concrete logical partitions, with their original canonical-cone terminals retained:

| Original root | Same-master copies | Moved terminal groups | Extra mapped cell area |
|---|---:|---|---:|
| `_31855_/Y`, NOR2 | 5 | at most 32 each, exact membership recorded | 0.43740 µm² |
| `_31850_/Y`, OR2 | 3 | at most 32 each, exact membership recorded | 0.26244 µm² |
| `_31808_/Y`, AND3 | 2 | at most 32 each, exact membership recorded | 0.17496 µm² |

Total: **10 logic cells / 0.87480 µm², zero new state, zero new clock pins and zero logical edges**. The compact existing-cell area plus this selected logic is 483.77898 µm² (43.2044% necessary region fill); access RC/energy, native placement and extra upstream distribution costs are not qualified. All selected terminal paths have noninverting transparent parity, so this selected partition needs zero additional polarity inverters; the generator explicitly counts inverters if a negative group is present. Each replica keeps the exact actual input nets and original Boolean master. The exhaustive named-cell Boolean tables in `finite_checks.json` establish the model's stable-value identity and distinguish an inverted-output mutant. This is a finite equation check, not a Verilator or Liberty-based simulation. This is a logical partition, not whole-native SAFE: every replica adds loads on its real reset/control inputs, propagation and hazards must meet native timing, and the complete upstream fanout/reset/tie fixed point is still required. The full selected input-load increment is +8 each on leaf00_qn and `_14821_`, and +2 each on active, pend and leaf03_q (22 input pins total); the output and actual input nets remain explicit. No removal/area credit is taken for original transparent cells.

For **each of the seven sequential roots**, `root_contracts.json.gz` records one specific nonprotected native terminal and first consumer where an arbitrary pre-edge clone value changes the captured D, even though both original and clone capture the shared original canonical D on that edge:

| Root | Native rewired terminal | First consumer family |
|---|---|---|
| split[1] | `_23930_/A2` | klim[0][8] |
| split[0] | `_23909_/A2` | klim[0][11] |
| split[2] | `_23982_/B2` | klim[0][6] |
| split[3] | `_24012_/A` | klim[0][12] |
| wsrc | `_37095_/A` | tstep_r[0] |
| active | `_31787_/A` | j[0] |
| k_last | `_32554_/B` | k[0] |

Each witness contains the complete evaluated boundary values, actual transparent inversion parity, both consumer D values and the first consumer clock. The active witness requires its actual RESETN and SETN to be inactive. These are **arbitrary-start same-edge retention counterexamples, not production reset-reachable failures**. They disprove accepting shared-D convergence alone. They do not reject all cloning, nor replace the missing real boot/valid-overwrite proof with a blanket 59-FF estimate. Protected original feedback and original reset branches are untouched.

## First meaningful use and remaining contract

For every root the ledger names actual canonical input sources, first storage controls and the relevant semantic source lines. Split/wsrc are installed by accepted GO (`!pend && !active && go`); k_last is installed from the actual `kc_is_1`. On that GO edge E0, old active suppresses x_re and e_v. Direct tags and read enables can use the new configuration at E1. Unreset terms/limits/address stages can capture arbitrary values before GO, and must retain their existing term/sum/result, IL and KV_PREP stages until overwritten. The source does not permit bypassing these stages. Active itself has a real asynchronous reset, but its clone requires the same actual assertion and qualified release/recovery. No new warm18 guard, stopped-clock assumption or equal-phase relation is introduced.

The production reset epoch, earliest accepted GO and full validity/overwrite chain are **not established by the emitted mapped netlist plus semantic equations**. Accordingly each qualified first-use edge remains NULL. Preserve all original reset, strict-idle and numerical failures. Actual source boot instrumentation/native phase evidence must close these particular ports, rather than treating an observed GO16 as a contract.

No new sequential landing has been selected: the current source endpoints have proposed ownership but no legal native sites, routed cut lengths, actual clock arrivals or epoch proof. **New landing bits, added compiler ages and full SU/MU token cost remain NULL, not zero.** A chosen four-slot publication must price its whole payload, identity/valid/epoch state, control, reset2, clock/PG pins and every added edge; coherent storage above 2 kb requires SRAM and cannot be split to evade that rule. This packet's complete selected hardware cost is only the ten combinational replicas above; it provides no sequential clone or landing activation grant.

All **121 CB16 A0 endpoints**, native phase, actual PG contacts, reset recovery/removal, parent fit and native fanout closure remain HOLD. No repeated 19-macro geometry exercise or new physical PASS is claimed. The next bounded work begins with the 24 actual ck_fa4 → ck GO/config ports, then the actual reset/accepted-GO/valid-overwrite proof for the seven named retention paths, together with a native site/clock assignment for any cut proposed for a new publication edge.

# A0 topology and first-use continuation

MODEL ONLY. This packet does not authorize RTL, a kit, a gate, a low-fill exception, or parent binding. It refines e09907596 without changing its source or numerical evidence.

The committed native source SHA256 is `422b8cdacc31dd6cc14cc912cf91a1a037f2de4e09a4875f1a1d9e0749f4f66a`. The semantic matvec source SHA256 is `e32fd49a2924e26fe27bc7ea0321062808a1d29082db202a40bcee2d54002ea5`, matching the REGROOT5 manifest. The native ODB is synthesis-only and has no qualified placement. Existing macro origins below are proposals from `4204d15a6:results/arch/qwen_a0_safe_1019/model.json`, not measured positions.

## Exact source ownership

`trace_ownership.py` traces every one of the twelve true roots' actual native terminals forward through combinational logic, stopping at each first native FF input or hard-macro input. `source_boundaries.json.gz` preserves every terminal and reached storage boundary; `source_summary.json` gives counts and exact canonical-D upstream storage sources. No anonymous mapped gate is assigned by centroid.

| Root | Actual terminal inputs | Distinct first storage boundaries | Clock |
|---|---:|---:|---|
| split[1], [0], [2], [3] | 415 / 335 / 281 / 235 | 242 each | ck |
| wsrc | 89 | 49 | ck |
| active | 82 | 263 | ck |
| k_last | 62 | 111 | ck |
| NOR2 / OR2 / AND3 | 156 / 84 / 34 | 117 / 82 / 18 | ck |
| TIELO | 1025 | 1024 FF inputs + tie_lo port | 128 on each ck_tx0..7 |
| TIEHI | 110 | 109 FF inputs + tie_hi port | ck plus existing regional reset clocks |

All seven control FF roots and three genuine logic roots reach **ck storage before any hard macro**. Therefore the source does not require their clones to be spread across all ROM/LSL/node positions. A compact issue-engine ownership region is a plausible next model; the 242 shared split destinations and intervening gates must be assigned together. This is not an approval to assume clock phase or collapse existing regional IO storage.

Every canonical split D depends on its original feedback, registered `go_i`, matching `ib_i[125..128]`, original active/pend and reset leaf00. wsrc uses `ib_i[324]`; k_last includes the actual split/K/wsrc input bits, loop state and leaf03. All complete source sets are recorded. These are actual native operands, not a grant to rebuild an equivalent-looking enable mux.

The original canonical-D combinational cones must keep original root operands. The trace identifies protected terminals: one per split and wsrc, seven active terminals, 22 k_last terminals, and five NOR2 terminals. Do not blindly redistribute these through clones: that would invalidate the shared canonical-D convergence argument. All are within 24 loads individually, but fixed-point/native upstream recount remains required. The earlier 59-extra-FF / 20.4849um² figure remains a lower bound, not a mapped physical cost.

## First-use proof and its boundary

For a canonical register q and arbitrary clone c on the **same actual capture edge**, preserve canonical `D = enable ? input : q`, with original q feedback. Then `q_next = c_next = D` for either enable value. A private DFFE instead gives `c_next = enable ? input : c`; choose enable=0,q=0,c=1 and equality fails indefinitely. No initial-state agreement is assumed.

This equality alone does not protect a retained consumer on the convergence edge: with c=1 and q=0, `retained_next=c` differs from `retained_next=q` even while both copies become equal afterwards. That counterexample remains an explicit adoption blocker unless the real consumer is reset, overwritten, or invalid until the stale value is flushed.

The actual semantic source gives a narrower conditional argument. `active`, `pend`, read enables and e_v are reset; split/wsrc/k_last are latched on an accepted GO. On GO edge E0, shared-D originals and clones capture the same new configuration. The old active=0 suppresses x_re and e_v on E0. At E1 the first active issue and tags use the newly equal configuration. Free-running address/term/KV-offset pipelines may contain older invalid values: terms/pr_a/kpad begin updating from the new fields at E1, sums/kc at E2, and derived steps/k_r at E3. The FAST_ISSUE source requires the first round/K boundary after at least IL>=3 edges; KV preparation has its own existing multi-edge delay. Those existing stages must be retained, not bypassed by copy placement.

This is conditional source reasoning, not a new numerical proof or physical boot contract. The reset candidate changes regional release, and arbitrary stopped/restarting clocks, asynchronous recovery/removal, command-input stability, actual parameter elaboration, all retained destinations, and native launch/capture phases remain unqualified. Early GO0 already fails 512 original comparisons; GO16 is a TB observation, not a contract. Do not advertise “one warmup edge suffices” or insert a new guard without source/epoch pricing. Preserve protocol13040, nonzero5120, reset248501, strict-idle95/final72 invalid payload differences and all original mutants.

## Actual abstract geometry at proposed origins

`geometry.py` applies each real native master pin/OBS rectangle to the nineteen proposed R0 origins. `transformed_pins.json.gz` records every transformed pin shape, including POWER/GROUND; each transformed OBS inventory has a reproducible digest. No macro is rotated, moved, or replaced. The selected east band x129.6..1166.4/y349.92..393.12 has zero positive-area intersection with **211308** transformed native OBS rectangles.

Worst necessary minimum Manhattan distances from a signal pin rectangle to this band are node295.716um, upper ROM305.496um, lower ROM132.696um, and LSL172.656um. These are lower bounds to the nearest point of the region, not routes. A straight line may cross a macro, OBS or PG conductor. The source of the distance, each native layer and pin rectangle is retained; no center-only substitute is used.

The 20um bbox halo is an assumed clearance from the earlier model, not a qualified routing/via keepout. Actual macro PG terminals are captured (38 POWER/GROUND master terms over nineteen instances), but no parent PDN, supply-domain binding, via stack or complete terminal connectivity is established. Parent face/boundary access remains unproven, including all121 CB16 A0 endpoints. Existing CB16 half PG_HOLD findings do not become A0 placement evidence.

The band is 1036.8um wide. If useful copies actually occupy both extremes, any shared canonical-D star needs a radius of at least518.4um, exceeding405 even before vertical distance. It cannot be repaired with transparent buffers under the logical reach contract. This is a conditional impossibility, not proof that A0 needs an extra edge: the exact source trace permits keeping the issue engine compact and using its already present registered IO boundaries. Any required new relay must publish its launch/capture epoch and added compiler age; no free same-phase relay is assumed.

## Bounded next mechanism

Before source changes, assign the union of actual ck issue-engine cones and protected canonical-D cones to one <=405-reachable compact region, then assign each existing ck_tx/ROM/node/LSL boundary cohort against its exact transformed native pin. Resolve shared combinational cones jointly. Check total mapped cell area, row/site legality, actual OBS/PG escape and full parent-face access, rather than treating the 14.1% whole-band fill as sufficient. A central compact controller plus distributed existing IO rows is a candidate, not a proved partition or approved exception to the one-band policy.

If this cannot fit without exceeding405, derive a new legal topology/outline with actual macro access, or price registered publication edges and rederive source ages. Outline/clock/retiming costs and full SU/MU token delta remain NULL. No source proposal is ready until this assignment and the native reset/first-use contract close; critical ROOT PNG/checklist review still precedes a gate. No new heavy job was launched for this packet.

Validation: both bounded read-only generators complete; source cell count and the pinned source/semantic hashes match inherited records. Existing tool/build results are reused unchanged. These transformations and graph reads do not constitute physical or numerical qualification.

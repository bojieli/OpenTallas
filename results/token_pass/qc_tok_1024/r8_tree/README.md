# QC-TOK 10-24: R8 landing pads as delay trees (Qwen compute)

Opt-in `asbuilt.land_pad_tree: true` (tools/die_plan/bind.py `pad_trees()`, commit d5ea505307). Each landing pad is
hoisted into the source (or forwarding) partition's tapped delay line. Each sink taps the depth it needs, so the
landed depths do not change. Types stay one module each because U is min-uniformised over (type, port, bit).
The default (chains) is unchanged.

| bind | chain pad flops | tree pad flops | types | verify |
|---|---|---|---|---|
| P5 bound_r8 (asbuilt_tie.json) | 870,428 | 587,936 | 80 = 80 | PASS (2,723,870 matched, 0 mismatched, lint 0) |
| P5 bound_r8 + CB16 align (asbuilt_tie_cb16[_tree].json) | 1,684,604 | 1,402,112 | 80 | tree: PASS (same counts) |
| P6-XT1 b3 recipe (asbuilt_xt1.json) | 1,034,324 | 985,040 | 69 | NOT RUN |
| main P6 table (model, tree_est.py) | 248,071 | 198,787 | - | NOT RUN |

Per-bind numbers are in binds.json.

## Result: trees alone do NOT reach < 150k

- **P5:** the residual is dominated by the tw_kind/tw_we x-lane chain (offset 17, one source per sink, so there is nothing to share).
- **P6:** the residual is replica stars: hw ctl->hc0..3 37.6k, chd 24.9k, tw 24.6k, hr 10.9k.
- **Both:** CB16 reduction-tree alignment (cb16_pads.py) costs a further ~0.8M on P5. Its legs need pads in all 48 clusters (t_0_0.n_a +18,
  t_1_2.n_b +14, t_2_2.n_b +1, 514 bits each), and trees cannot share these: every leg is a separate source.

Getting below 150k needs either the P6 plan (fewer crossings) plus schedule-side alignment, meaning the compiler
absorbs the CB16/replica skew instead of flops, or a plan that keeps the CB16 legs on equal hop counts. Both are
OWNER decisions (see lane file ~/coord/lanes/QC-TOK.md, OWNER?).

## Tree functional equivalence

xt1 near carve, tree bind vs chain bind (bound_r8): **EQUIVALENT** (equivalence.txt, tree_eq.sh). With the
tt_ctlm hoisted pad (+4 on hr/cmd/table_req, a partition outside the carve) re-applied at the tb, the nominal and
mutant logs match the chain logs line for line through cycle 6459. A carve vehicle on a tree bind has to re-add the
hoisted pads of the source partitions it excludes.

Capacity (Codex, 08:50-12:04): codex/qc-capacity-1024 @72ece79138 is an initial 56-type candidate with 433,915 pads
(not < 150k; it is a trade-off). Its both-cluster xt1 smoke is live on intel2
(.../codex-qwen/xt1_capacity_both16_v2, lead 16); QC-TOK has adopted it.

Scripts: cb16b.py (CB16 skew per node), cycles.py (leaf loop analysis), tree_est.py (tree model on a table).

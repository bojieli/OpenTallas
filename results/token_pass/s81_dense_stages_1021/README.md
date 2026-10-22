# Configured DENSE2 stage selection diagnostics

These are actual configured source compiler outputs on the frozen 72-frame
tree (die SHA `86dd02b2269e8ff96789db513ad4f93b501891c1e029436a9fe8cafa7d2f1718`).
They demonstrate operation ownership and expose missing lowering. They do not
qualify a stage, static completion age, or token.

The explicit compiler selector gives A only its a-proj subset and B the remaining
subset plus reachable downstream operations. Incoming and outgoing dependency
edges remain in each `prog/dense_stage_boundary.json`. Norm/quant and HC inputs
outside this selection are external obligations. All dates are inherited model
dates, marked `INHERITED_MODEL_ONLY`.

- A: unit `oth-ubuntu-1799453-1792604641`, one PARTIAL operation, zero command rows.
- B: unit `oth-ubuntu-1812848-1792604747`, 55 operations, 8 GAP / 47 PARTIAL,
  113 command rows and 112 templates.

Both ran on gold1 under
`/srv/opentallas-scratch/claude/codex-tok-s81-layers/dense_driver` using
`OT_XS_APROJ_TOPO=1 OT_XS_APROJ_ALIGN4=1 OT_XS_APROJ_RANK_TAGS=1
OT_XS_APROJ_CAP_PLAN=1 OT_XS_DENSE_SPLIT2=A|B`, with
`dv_layer_compile.py --layer L0 --dense-stage A|B --slice u_s_2N`.

The `source` directory preserves the actual compiler and key family sources.
Only the stage selector and XS producer map were overlaid on the frozen c772
source kit for this diagnostic. Other family lowerings still contain historical
gap descriptions. In particular, claims that no KV RTL, SO output path, or owner
fold encoder exists are stale descriptions, not current release source findings.
The newer KV candidate, real VP consumer proof, SO source contract, and three-RB
fold encoder have separate exact source receipts. They are not promoted by these
archived compiler counts.

A has no genuine first command row yet. B's downstream rows cannot substitute
for the missing a-proj GO when anchoring a full-stage six-KS timetable. Actual
source producer capture and boundary carriage remain required.

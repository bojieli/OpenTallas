# NL reset-output mux cleanup: exact zero-cycle candidate

`parent_reset_recipe.json` adds one exact RTL patch for this actual parent form
(REGROOT=3, NODE=0, TOREG=1):
`t_out_q[513:512]<=reset_q ? {tf,tv} : 2'd0;` becomes `t_out_q[513:512]<={tf,tv};`.
The inner valid and fault outputs are already asynchronously zero under that same reset_q.
This removes two redundant outer reset gates and their physically impossible direct root-reset
hops, without adding or removing any data cycle or changing the boot release offset.

`reset_output_miter.sv` covers reset_q changing on face-clock NBA, gated and running body
clock, independently phased output clock, and both assertion/deassertion. All 505 comparisons
pass and 505 wrong-data controls are caught. The full actual-parent regenerated gold vs the
unchanged existing r3 mapped gate proves all 12570 joint loaded relations and all 31742 full
comparison points, zero different/undecided. The existing seven loaded-counter hints from
parent_zero_proof are unchanged and their reset-false base is proved, not assumed.

Independent native proof artifacts: intel1
`/srv/opentallas-scratch2/claude/codex-qc-nl-lec-1029/reset_gold` and `reset_target`,
script `qc_reset_target.py`. Isolated source kit:
`/srv/opentallas-scratch2/claude/codex-qc-a0-2340/parent_reset`.
The old resetmux proof and original placement failures remain preserved.

Before physical adoption the candidate must be synthesized so those gates actually disappear.
Current FF anchors retain the full graph except these two proven redundant reset edges; the
placement-only trial does not adopt the RTL delta or count as a CTS/route PASS.

# PGSTREAM SAFE2 independent native pickup: HOLD

Exact source `23910522d70f6a2ea95014265128c9161d257df8`, kit `hbm_su_pg_stream_b_safe2_1019`; immutable run `ot-epyc8:/srv/opentallas-scratch/claude/ref_gate/hbm_su_pg_stream_b_safe2_1019-20261019-121732`.
Actual detailed placement `3_5_place_dp.odb` was copied read-only to `ot-epyc8:/srv/opentallas-scratch/claude/pgsafe-native-1019/placed.odb`; SHA and exact mapped netlist/TT Liberty paths+hashes are in `native_binding.json`. No resynthesis, gate launch, live-worktree modification, REVIEW or submit.

## Native findings

- Actual native graph: 44,552 cells: 10,007 FF, 18,019 combinational, 13,548 BUF/INV, 2,978 ties. Earlier independently mapped source was 9,496 FF/max32; it does not certify this gate graph.
- 27,238 all-driver roots including constants, input pins, reset and ordinary FF/logic; BUF/INV transparent; no root-count cap. Exactly 3 non-clock roots exceed32: serial inject `g_ij[0].sq[0]`, `g_ij[1].sq[1]`, `g_ij[3].sq[0]`, each42 actual native load pins. Ties are included; maximum42. Clock-only roots are separately recorded by observed native CLOCK load pin roles, not name exemptions; any mixed-use root remains in audit.
- 596 used input pins first reach logic: all562 `su_wq`, 34 `vmr_cmd`. 42 outputs are driven by logic rather than FF: 36 `ij_row`,4 `ij_v`,`ij_bad`,`lg_fault`. The request banks contain state but input-side hold muxes are not input capture registers; final selected inject outputs and OR fault summary are not output capture registers. Blanket pin-reg opt-out is unsupported.
- Both raw reset pins first reach exactly one FF D. Generated wrapper has ONE plain serial face FF. `rst_n` then passes two serial source cells (three total). Bridge serial face -> stageA -> terminals is three total; stream face -> F(serial) -> P(stream) -> terminal is four physical sampled stages across the two domains. This preserves the original three-serial-edge epoch in the tested phase; it is not an exact two-stage face landing.
- Maximum direct native pin-pair Manhattan span165.345um, no direct pair>405. Complete combinational-stage sum of native pin-to-pin Manhattan segments reaches625.418um,131 roots>405. This is a placement path-length concern, not a claim that one uninterrupted wire spans625um. Actual routed topology, complete-stage reach contract and corner timing remain open.
- `placement.png` is rendered from actual ODB bounding boxes, personally viewed. It shows pin-bound sparse diagonal clouds, not a tightly bounded two-region partition. Macro inventory0; 216x259.2 outline; prior floorplan pin geometry PASS3577/3577 track-accessible pins is retained separately. No full PG/DRC or native TT/FF qualification follows from the picture.

## Source calendar and reset evidence

Existing committed `results/rtl/hbm_pgstream_safe_1019/safe2/bench_r7` has three positives rr18,rr10,qid0 PASS and eight causal mutants m1,m2,m3,m6,m8,m12,m13,m14 FAIL. rr18 counts7194 checks/9228 windows; measured request setup/hold1.112/.556ns, return .556/1.112ns, inject .834/1.946ns. Bench uses Q278ps (actual stream834ps, serial1112ps): accepted inject capture adds ONE stream edge =834ps in this bench, nominal833.333ps in the gate model. It must be priced in production compiler/calendar, not erased by delaying only a checker. Reference injection is explicitly delayed one pg_clk edge.

The bench exercises two reset epochs released100ps before a coincident edge and independent bridge-reset versus leaf-fault ownership. Its reference reset is a12Q transport delay; it proves that chosen epoch/phase, not arbitrary phase/stopped-clock/pulse/recovery or actual wrapped native timing. `results.json` also retains the failed legacy kitland row (not another passing positive). No new reset waiver, age or full-token qualification.

## Current live pickup / integration dependencies

Gate client1311539 and exact ep8 run remain live in CTS mixed CDC seam enumeration; no final CTS ODB, native spread or GRT result at pickup. Local `gate_s2.json` is stale121431 undeclared-crossing failure; never treat it as121732 terminal verdict. `cts_summary.log` is empty because no final structural summary had printed.

Current main CDC helper lacks this branch's kept-hierarchy `/` -> `.` flow-name expansion (and original logical keep_hierarchy-unset edit needs exact independent review). Main commit71fc46afc wrapper role resolution is related but does not contain that expansion. Do not carry stale tools forward or assume daemon supports the frozen gate's branch helpers. Integration must be reviewed by ROOT-merges as a semantic source-bound change.

`native.json.raw.json.gz` preserves ALL actual cells, master/type, native pin directions/signal types/XY/connections, all ports and every net including clock/ties/reset/mixed roles, for independent strict replay. No clock names are omitted. Exact Liberty paths/hashes are pinned in `native_binding.json` and remain on the fleet. Stable full raw JSON and ODB also remain in the separate remote audit directory. Root strict-safe-source replay must use raw graph and exact library functions rather than trusting this scanner's FF/BUF name classifier as final qualification.

Next owner: preserve current gate; collect terminal result without duplicate builds. Structural source/model repair must cover actual native fanout and complete registered input/output boundary, price added stages, re-prove 3:4 seam calendar and reset ownership at the actual emitted wrapper. No critical route approval until these gaps and complete native electrical/clock proof close.

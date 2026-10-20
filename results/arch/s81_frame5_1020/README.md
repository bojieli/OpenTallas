FRAME5 standalone submission metadata.

Final candidates pin original source f9d44ffae; no running source kit is edited. source_identity.json binds the existing behavioral witness source b850173cf to the gate source for the entire RTL, s81_dv and landed_parent tool trees. Existing V5.050 h9/h10 plan+each PASS and unland/landread/reset negative witnesses are committed at f9d44ffae. No manual rerun is needed; listed commands remain real executable benches for the normal closure process.

The negative frame harness returns zero when it detects the mutant. The standalone stage converts only that exact success marker into exit1 required by closure expect=fail. A crash, build error or missing detection yields exit0 and cannot count as a detected mutant.

Next: collect terminal gates/PNGs, report native32/reach/linked-root and forwarded-child clock spreads to coordinator. Critical visual review is still mandatory. Final approved review and source-equivalent gate receipt must be committed before submit; update the spec source to that reviewed commit (or established submit --follow-head workflow). No REVIEW.json is created here.

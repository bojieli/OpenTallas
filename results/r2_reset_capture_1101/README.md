# Source-specific reset D-mask candidate checker

This isolated canary recognizes the nine actual native BFQG synchronous-reset input captures. It does not modify `geom_rules.py`, any shared gate, source RTL, or a physical kit. Its output explicitly says `registration_release=false` and `gating_changed=false`. All nine raw geometry FAILs remain in the physical evidence. ROOT review and a separate integration decision are required before any recognition affects R2.

The positive is the real current frozen two-file BFQG source, fresh native full 8650/8650 EQ, full KEEP1064/1064, default/requested/USED reset4, clean matching source/proof provenance, actual mapped gates and the actual reviewed native placement graph. The source/reset digests are fixed: this is not a generic metadata request to waive combinational input logic. The small fixture is a literal extracted cone and actual physical-path subgraph from that run; the full positive CLI also passed using the complete actual mapped netlist and geometry dump.

The check requires all nine literal pins to own exactly one AND2 mask and one distinct named clk_ctrl DFF. The only other mask operand is the actual qualified reset relay. It verifies the three real asynchronous reset-release FFs, same clk_ctrl, literal rst_n assertion, tied-high preset and release seed, exact reset-chain polarity, and no functional release input. It independently follows the real placement's pure BUF/INV input paths, mask-to-own-capture edges, cell truth families, clock root and reset operand origin/polarity. This protects against matching a plausible mapped name while the actual physical cone differs.

Fifteen tests include the native positive and controls for functional mask data, OR logic, a shared capture, an added functional enable, wrong capture clock, functional reset-release data, wrong reset assertion/polarity, shared input use, reset64, lost KEEP, changed source, a missing actual placement edge and an actual physical OR mask. All pass in under0.1s.

```
python3 -m unittest discover -s tools/autopilot -p test_reset_d_mask.py -v
python3 tools/autopilot/reset_d_mask.py --mapped ACTUAL_1_2_YOSYS.v --dump ACTUAL_GEOM.tsv --lec ACTUAL_LEC.json --provenance ACTUAL_PROVENANCE.json --source-dir ACTUAL_RTL --out candidate.json
```

Scope limits: only this frozen source and standard-cell truth family are supported. The checker rejects unfamiliar buffer/cell mappings and never uses a fallback. Generalizing beyond this exact native canary needs the same source/reset proof class and native negative controls. No geometry collector, registration, timing, CTS or DRT release is implied by a candidate result. No copied or fabricated source EQ receipt was created.

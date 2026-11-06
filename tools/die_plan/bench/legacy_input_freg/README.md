# Legacy input FREG component proof

The legacy ot_dp_clk_landing writer is free-running. FREG=1 adds one
unreset rising-forwarded-clock capture to the whole payload; pointers,
receiver training, local ready and local fault remain unchanged. This is
separate from count-aligned WREG/FREG and changes no K value.

The sender launches on the rising forwarded edge. The opt-in stream is
exactly one read cycle behind the pinned old implementation after training.
The bench checks 517 payload bits (including any in-band status), ten static
phase offsets, both rising and falling write forms, and repeated warm resets.
It requires over 1,400 ready comparisons per writer form per phase; a faulted
or never-ready run cannot pass. Bypass and payload-bit mutants are caught on
both write forms. The falling-capture mutant is caught on rising-write mode;
it is functionally indistinguishable at falling writer edges and is not
claimed as a negative control for that mode.

Run bash run.sh here, or stage this directory with the current two RTL files
under src/ and run through ot-run. The golden file is the pinned old source,
with only module names suffixed _gold to allow side-by-side elaboration.

Model convention: selected legacy sidecar rows explicitly say added_cycles:4.
The physical network retains its base data_cycles_per_crossing:3; the plan's
per-type clock.landing_input_freg bus list derives the extra cycle exactly once.
Manifest and requirements include that cycle. In-band sender ready/fault bits
also gain one transport cycle; the ring's own control outputs do not.
The parent must refresh affected latency/R8 rows and perform physical timing
and token qualification. This component proof is not a physical or die pass.

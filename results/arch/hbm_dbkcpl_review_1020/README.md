# DBK CPL review, 2026-10-20

REVIEW REFUSED for s1/s2. Original exact GRT ODBs are preserved and never written. Both source run paths contain the same dcd7a3c6 ODB hash. The read-only direct-net audit passes maximum245.489um, but buffer-transparent source-to-capture displacement fails11 paths above405um. The maximum713.268um is rr[2055] at W(0.042,252.204) to bank7.write_en(446.076,519.438). Data control paths bank_output_en7 and bank_read_en7 are454.692/408.184um. Reset landing to regional async reset pins also exceeds405um.

The conservative sequential audit propagates sources through all combinational inputs/outputs and cuts at DFF, SRAM, and BLOCK hard-child boundaries. This describes source-to-capture displacement, not routed wirelength or STA. Hardware bank pin controls may have combinational decode at the parent, therefore every flagged source must be classified against exact RTL before any claim. No full STA qualification is inferred.

PG raw audit reports18110 empty terminals. Unprotected ordinary18046 clear after canonical existing-rule global_connect on an in-memory diagnostic clone. The remaining64 terminals belong to32 protected cells. The original audit failure and diagnostic are separate immutable artifacts. Final6_final PG must pass separately.

Next: real per-bank face-local control/landing and reset geometry, price any added cycles into RR_RT, pre-gate native census then fresh layout gate with PG birth fix merged. Original source behavioural and mutant evidence must remain valid and source-pinned; no REVIEW.json or submit is written.

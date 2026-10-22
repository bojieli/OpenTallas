# N59 service gate replacement

The source is exactly 0e64aa8f3, including the original svc5 and svc5b kits, clock structures, parameters and existing behavioral benches. No RTL, physical geometry or latency changes are made. The eight-point source checklist remains in the original kit README and SQ-C2-N59 lane.

Both original normal gates terminated after the default 2700-second synthesis cap. The actual MAIN canonicalization log reports 4533 seconds in ot_keep_regs.tcl, primarily reset relay copy creation (nine families, maximum 32 loads per copy). Canonicalization completed after 4577 seconds and mapping after another 370 seconds, with a mapped netlist produced at 21:12 PT. This is evidence of insufficient wrapper time rather than an observed SHARE stall. The original FB canonicalizer remained active at collection. Original gate verdicts are preserved unchanged. The two replacement gates use the existing --synth-cap 0 option, with normal admission, native census, textbook execution and physical checks retained.

No physical PASS or source equivalence claim follows from the surviving output. The replacements must produce their own complete source-bound results before layout review and qualification.

# Main unsigned parameter parsing repair

Port only the unsigned `[31:0]` literal parser and evaluated signedness from5f2ce19bc. Actual SCALE=32'h3DB504F3 and high-bit values retain their declared unsigned meaning; integer parameters remain signed. Unsupported types, widths, unknowns and expressions refuse. Signed literal serialization preserves the same32bits under the declared unsigned parameter.

Current-main artifact identity/profile/qualification code is byte-identical. No diagnostic autoprofile behavior or e4 native-audit ancestors are imported. Fleet actual expansion→Yosys→binder regression19/19 PASS on baseline and candidate; three new parser/refusal-policy tests PASS. Initial missing-RTL fixture errors remain in the packet; exact baselineRTL dependencies were then supplied. No physical, GEN8 or SU/MU token qualification follows.

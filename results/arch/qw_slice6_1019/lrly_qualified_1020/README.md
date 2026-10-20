# LRLY qualification pickup

Both exact gate3 mapped netlists pass strict textbook buffer/inverter-transitive native fanout census with zero nonclock drivers above 32, including reset. SHA256 is fbe4d05ae17126e026b3820e6b0216ff8f244eb76b865f56b65a2d95571d2ffe for both variants. The report max_loads=0 denotes no offending row, not a claim that all drivers have zero loads.

Source bodies qfd_dv_s5_lrly and qfd_dv_s5_rst2 are byte-identical between current parent b484119db and claude/qw-slice6-lrly-1019. The current b7 positive lockstep passes all four modes. Actual lrly mutant fails 14 random /77 legal comparisons; its committed witness is preserved separately. No source behavior changed.

Checklist: pin inputs and outputs direct flop endpoints PASS (gate in/out levels0); reset two-stage landing PASS and strict census PASS; depth11.7ps PASS; storage PASS (pure<=2-edge relay flops, no runtime-indexed array or>=3deep delay); reach PASS worst95.7/101.6um<405; no tied functional port; main aspect2/fallbacksquare with fullfaces<=6pins/um, pin-bound fill3.5/4.8%; single compact root clock entriesN, pin-flopspread34.8/33.0 or56.3/54.4ps; GRT0. No latency changes. Native PG after route and real region-relative clock boundary remain owed.

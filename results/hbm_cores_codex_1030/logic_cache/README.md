Exact native-proof reuse for the two fresh FT kits avoids repeating unchanged
12058-point collar and18498-point query proofs on every physical resume.
Both original native proofs are EQUIVALENT and remain intact. The checker
requires complete RTL/macro/reset inventories, config+freeze, formal scripts
and AIGs, proof record, mapped netlists and proof-tool hashes to match exactly.
If anything differs, the private runner executes ordinary native LEC instead;
any nonzero proof result stops before P&R. No physical gate is cached.

The private wrapper changes only the unconditional LEC invocation and makes
unproved fallback fail closed. Original generated run_kit_hbm.sh is unchanged.
Both wrappers printed NATIVE_CACHE_EQ successfully before ordinary CTS/GRT/
TTFF/route/finish. Existing lint, face/port binding, SELRANGE, clock insertion,
FF hold, route, pin, DRC/DRV and full signoff gates remain active.

Independent reviewer: HBM parent personally viewed the fresh actual collar and
query placement images, accepted current pin-role disposition and authorized
ordinary gated flow. Query p90=7.86<=30, data/control max12.9; sole rst_n outlier
82.56 is below150 hard backstop. Both new actual GRT50 probes had zero overflow;
clock FT rectangles were measured from ODB at M5 .048x.48, reset .032x.192.
This is no SIGNED, adoption or parent G3 claim.

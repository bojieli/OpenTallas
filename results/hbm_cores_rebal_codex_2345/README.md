HBM canonical lane C24 physical profile correction

Inherited lanes_plain MLAT5/WCOPY1 CTS FAIL TT -323.21ps/3335 endpoints, FF reg2reg -64.53ps/2685 endpoints. Original fastfp_lat maps MLAT5 to lat5i (C1+C3), leaving all four CSA levels plus CPA in one stage. The actual lane kit is MLAT5/ALAT3/WCOPY1. Existing c12/f12 source profile maps MLAT5 to f12_l5 at the same five edges; LAT3 addition remains unchanged. The supplementary LAT4 adder coupon compares lat4i to f12_l4 and is not the actual ALAT3 kit.

run_canon_f12.py is an opt-in lane-local recipe override. No shared default changes. Positive smallest old/new lockstep compares multiplier LAT5 and adder LAT4 on 199919 valid observation edges (random FP32 encodings and subnormals, four warm resets): zero mismatches; output-bit mutant caught174762 times. No token cycles added. Run unit intel2 oth-ubuntu-1159275-1793256414; raw source/build under scratch2/claude/codex-hbm-rebal-2345/eq.

Visual review: results/geom_review/codex_hbm_lp_f12_2345.json. Same floorplan approved for synth/place/CTS trial only; full macro/pin/clock density review on successor precedes routing.

Exact-current add_lat source replay unit intel2 oth-ubuntu-1641499-1793257342 also PASS199919/0; mutant174762. Initial source differed only in inactive DRST0 err-constant branch; original receipts preserved in raw eq/*prior_add_source.log. Eq source hashes in eq_sources.json. Actual generated successor preflight PASS0 (preflight.json), hash6448ac18ed1dd8bc. CTS trial admitted intel2 oth-ubuntu-1441701-1793256955, launcher1358457; collector1495034 writes scratch2/claude/codex-hbm-rebal-2345/post. Still no route approval.

Correction 2026-10-29: baseline C24lp is explicitly5/3/WCOPY1. New5/4/WCOPY1 is a separate current-C25 candidate on codex/hbm-fullcanon-0010, with +1edge per add priced by TOK-HBM. Intentional SIDE3/3 is independently priced/held by the static compiler and is not a manifest bug.

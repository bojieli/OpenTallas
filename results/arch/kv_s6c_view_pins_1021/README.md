# Exact S6C physical pin contract

Parent dsg4central966018b48 PREP failed on a 995.8um K-response launch hop; original failure JSON is retained here and full failed plan pickle remains on ep5 under codex-kv-closure-0037/fail_dsg4central.json.pkl. The selected S6C master names were absent from KIT_FACE/default-face/face-order membership and consequently used peer-dependent synthetic faces.

Both actual CLOSED view LEFs were parsed, every signal bit checked against the committed kit face declarations, and all pin extents/SHA256 recorded in group_pin_proof.json. The original plan has188 actual overreach hops (worst EST942.7um). A canonical-face-only patch would conceal these defects.

The repair keeps exact master/source/view identities and reads actual per-bit LEF positions for the selected S6C groups. The planner uses the bit centroid as its route anchor and farthest-bit Manhattan distance for reach, including real LEF outline transforms under R0/MY/MX/R180. Wrong frame shapes fail. Synthetic frame KIT_FACE membership and explicit spec order cover clock/reset and PC pairing rather than their legacy-name fallthroughs. Legacy unselected recipes do not enter this path. No RTL/ports/calendar/state changed; generator pin update covers geometry only, all existing source/chain-tail assertions remain.

Admitted ep5 unit2932605-1792604534 (8GB) passes actual two-view parse, four orientations, farthest-bit distance, wrong-frame refusal and unknown-master non-alias proof. Full PREP/GEN and resulting stage/calendar ages remain pending; this is not a reach/GRT/STA/clock closure receipt. Reticle transforms remain a separate explicit obligation.

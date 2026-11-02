# fMX13 actual placement review

Personally LOOKED both current center/balanced auto_geom PNGs and parsed their canonical JSONs. Verdict: PASS-COND for ordinary CTS/GRT diagnostic continuation only. This is not DRT, release, timing or clock approval; no new job was launched by this reviewer.

Both actual placements have R2R384.97µm/zero captures over405, zero relay collapse, zero unregistered pins, zero blocked H/V crossings or combinational loops, pin-registration p908.12µm and max146.47/146.57µm. All43752 clock sinks are rooted. Fill18.32%, empty49.35/49.33%. Images retain the same narrow W boundary strip and broad central/south cell clusters, without a new visual blockage or macro/channel problem (no hard macros).

Preserve canonical AUTOFAIL: column demand0.636 at x0,y302.5 exceeds0.6; GRT is not run, not zero. The ordinary >=50-iteration normal GRT and actual post-CTS clock inspection must decide whether the retained projected column cut is physically routable. Pre-CTS single-root clock reach370.22µm is informational here and establishes no normal CTS qualification. Source equivalence is separately owned by PC and reported closed by actual A/B plus negative control; this review does not repeat or certify that proof.

Exact evidence: `epyc2:/srv/opentallas-scratch2/claude/codex-kv-pc-cores-1101/geomFmx13_{center,balanced}/auto_geom.{json,png}`. Copied read-only for this independent review; actual ODB/source/flow left untouched.

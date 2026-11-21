# QC CB fp3 floorplan review
- Image: `epyc9:/srv/opentallas-scratch2/claude/fable-fix-qc-cb/proof/fp3/fp3_pre_route.png`. Looked at the generated plan pins, macro boxes, station lines and clock taps.
- Four macro groups mirror in two columns. The roughly 145 µm central corridor, 69 µm cross-channel and 80 µm outer channels leave passages around the banks. The repeated wide rows are staged along those passages. Edge signal pins cluster near the corners and the inner tile faces. Scattered clock entries follow those channels. The generated top PDN joins M1/M2 rails to orthogonal M5/M6 and M7 stripes. Physical connectivity remains a floorplan check.
- Verdict: PASS to diagnostic placement. Compare FIRM/core-hook insertion, density and the worst post-place setup cone. The CB V2 tile insertion contract and reset capture need the bound V2 proof.


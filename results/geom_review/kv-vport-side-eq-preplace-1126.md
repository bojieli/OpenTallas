# KV VPORT side-equalization preplacement review

I viewed all ten receiver type floorplans under epyc12 /srv/opentallas-scratch2/claude/KV-HGI-WGATE/gate10/vport_equal_render_1126. Each R6 image is byte-identical to the corresponding HGI Return38 image. The eight cl4ea58a5c and cl7f648944 variants share the same bank and macro layout within their respective families. The cl23f6a148 variant has more planned taps near the center. The pc_v3 preview has stronger concentration in the center and upper crossings.

The floorplans preserve the hard-core aisles. Existing long nominal paths and dense east landing bands remain visible. The placement trials must measure each actual request pad bank and its receiver clock load, including the widened cl23f6a148 count strap.

Verdict. Continue place-only for all 20 scopes. Hold route and adoption until exact placed pad capacity, setup and hold, and preserved mission ages are demonstrated.

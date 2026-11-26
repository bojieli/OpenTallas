# KV Hub-Wi R6 attempt 1 detailed placement

**BAD. Keep the exact kit route-held.**

I opened the actual Intel2 3_place auto geometry, layout and density images.

- Overlay: intel2:/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t9-r6-publish-1125/items/kv3_hub_Wi/geom/auto_geom.png
- Layout: intel2:/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t9-r6-publish-1125/items/kv3_hub_Wi/gen/kv3_hub_Wi/run/layout_review/place/layout.png
- Density: intel2:/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t9-r6-publish-1125/items/kv3_hub_Wi/gen/kv3_hub_Wi/run/layout_review/place/density.png

The north row of ingest, order and CDC macros forms a wall with narrow channels. Below it, the peer and TX macros concentrate standard cells into the throat that meets the prompt and RX cluster. The southeast and northeast face feeds gather very tightly. Fill is 7.79%, empty area is 61.94%, vertical channel demand reaches 7.694, and the west vertical column reaches 8.986.

The stock exact dump reports 12,453 register captures above 405 µm, up to 2509.92 µm on the raw FSTART to ft27 branch, 598 collapsed relays, and a 5,287-sink kit tap in the central cluster. The two longest named FSTART pin-register reaches are 364.13 and 331.7 µm. These are concrete C-STREET, C-LEG405 and C-TAP-LOAD findings from the R6 placement.

KV-ALLFIX is already developing the separate X743 split and reset-tap reseat. Break the wall and central throat, then check the FSTART branch and tap loads on that exact successor. Route remains held through actual detailed-placement review.

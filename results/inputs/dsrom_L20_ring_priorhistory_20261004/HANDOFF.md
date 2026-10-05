Epicurus L20 prior-history RING input handoff
===========================================

Actual prepared path: /tmp/opentallas-L20-RING-priorhistory-20261004-r1/r{0..3}/ikring_s{0..3}.hex
Exact source/count/address/SHA manifest: /tmp/opentallas-L20-RING-priorhistory-20261004-r1/manifest.json (byte-identical copy committed here).

Uses unchanged tools/w11_idx_ring_place.py on the existing relative68B raw codes/scales. Input root /home/ubuntu/w17work/die/ctx1048576_s20260930_L20/r{0..3}/ikhbm_region.hex. Existing seed20260930 synthetic-history provenance is retained explicitly; no checkpoint-trained-history qualification inferred. No host quantization, golden scores/selected IDs/activations/current-key injection, component benchmark/build/replay, or producer regeneration.

Selected geometry: RING1 RSB64 RTAIL32 WB32 GA24; C65568 UBLK1090. Native scan count262144 perrank selects65536-key stack quarters. Prior counts r0/r1/r2=262144 each, r3=262143; total1048575. Using n262143 for rank3 would choose65528-key quarters and would NOT match this requested fullscan/source writer ownership. Input current key rank3/local262143 absent, native writer must publish it before fullscan.

cfg logicalbase0x1000000 is the source index logical word base, not an offset to add to these physical sector addresses. User0/region0 => KB0. Other users/regions need an explicit source binding, never silent rebasing. Sector units are256bit; actual channelPC/column routing remains Sagan's selected native-provider responsibility.

Native excluded current key: global1048575, rank3local262143, stack3, slot65439. Codes139070/139071, scale137203 field7. The scale sector may contain other seven PRIOR keys; don't erase the sector to omit current. The input's absence ensures its field is not supplied; native masked writer supplies current raw codes/scales. No current writer visibility/ACK is fabricated.

Sagan is the provider/lease/actualpublication owner; Epicurus solely remaps retained prior bits. Goodall remains releasedrawQE callback owner. Coordination queue includes exact ready paths/counts/hash. Images stay outsideGit; lightweight manifest/source pins are committed. Don't rerun mapping to validate the component; consume these immutable inputs in the already-owned connected source hierarchy. Keep original images untouched.

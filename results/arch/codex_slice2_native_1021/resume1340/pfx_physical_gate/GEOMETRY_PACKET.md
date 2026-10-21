Critical geometry packet: exact station prefix successors, source 369c54773295db39a0e75f3000ae6a9796155215.

Both admitted gates returned WARN with 0 FAIL and 1 logic-depth warning. I inspected all four actual gate PNGs. No REVIEW has been written and no submission has been made. ROOT personally reviews these exact images/hashes before the exclusive publisher prepares any qualified submission.

| Actual evidence | MAIN pfxa | FALLBACK pfxb |
|---|---:|---:|
| Outline (um) |151.2 ×151.2|162 ×162|
| Mapped native fanout / violations / role errors |32 /0 /0|32 /0 /0|
| Actual signal/clock pins checked / errors |560 /0|560 /0|
| TT/FF pin-flop clock spread (ps) |64.6 /61.9|73.4 /70.8|
| All-register TT/FF spread, retained (ps) |88.4 /84.6|94.1 /89.0|
| Root sinks |12,002|12,002|
| Trial GRT overflow / max layer use |0 /M2 31.59%|0 /M2 26.61%|
| Reset landing max / sink count |2 /1|2 /1|
| Synthesized total fill |50.5%|43.8%|
| TT placement-RC diagnostic WNS (ps) |−94.4|−89.7|

The 80 ps gate applies to the measured pin-flop boundary spread. The all-register ranges above are retained as separate evidence. Neither candidate is CLOSED: the reported TT placement-RC setup deficits and ~879 ps logic-depth warning remain explicit; actual routed TT setup/FF hold/DRC are not measured by this packet. The fallback has lower synthesized fill and visibly more empty space at the southeast perimeter.

Visual inspection: five real32x64 SRAMs form two columns/three rows with the upper-right site left for logic. Exact horizontal channels are20.304um and vertical channels21.6um. Macros are away from pin faces. Standard-cell rows/PG stripes continue across the block. MAIN density is broadly green, with local warmer bins and no red saturated strip. FALLBACK is broadly green but has additional blue perimeter/SE area. The clock enters W near the region centre; cfg/rs_s are W, rs_n/NB are N, scale/results are S, and NB/fault outputs are E. Actual560-pin geometry checks report0 missing/outside/inaccessible pins.

Source/frame proof: balanced33-leaf AND association only, exact four-state identity and byte-restoration certificate; all1,356 sequential instance lines and original XOR/synchronous-reset network retained. Executed full multiplier startup/reset equivalence:160cycles,4 unknown-start cycles,142 known-output cycles,883 scalar multiplier Qs and raw y/err matched. The selected realKC8/J3 case produced all48 FP32 results and drained; original lateCFG failed at cycle3300 in the same binary. FixedJB8 causal variant failed to retire the same actual24 words/stream. PIN_IN1/BT_LAT1/ADD7/SKEW14/SCALE6/MUT0 remain explicit. No extra edge or programme-age claim.

Proof records: prefix_reset_4d9/receipt.json; prefix_tail_363/receipt.json; fixedjb8_40fcc/receipt.json; prefix_child_native/receipt.json in the sibling resume1340 directories; mechanism certificate results/arch/q_station_prefix_1021/FOUR_STATE_CERTIFICATE.json.

The larger parent is independently native FAIL (MAIN13 roots/max1053; FB23/max1053). Its current red component remains soft: direct hard binding fails exact pin reach. These facts do not change the source-bound standalone child evidence and do not authorize parent layout or a view alias.

qfd_dv_s8_station_tail1_pfxa
- Gate: /home/ubuntu/wt/codex-q-s8-prefix-collect-1021/physical/ref_tile/qfd_dv_s8_station_tail1_pfxa/gate_result.json
- Floorplan PNG: /home/ubuntu/wt/codex-q-s8-prefix-collect-1021/physical/ref_tile/qfd_dv_s8_station_tail1_pfxa/gate_layout/floorplan.png
- Density PNG: /home/ubuntu/wt/codex-q-s8-prefix-collect-1021/physical/ref_tile/qfd_dv_s8_station_tail1_pfxa/gate_layout/density.png
- Frozen floorplan SHA256: f54229b4327c13f352381c48ee8838e75cdafbd018eaac5b58506e60d4963572
- Spec SHA256: 2fbb3ed8bcacbea745b40f0d4ec0d220d5c4455b7c34c2cc037ad270a1b22128
- Manifest SHA256: fd36e4c2b8187b2c4c71ccd14986974b5148875055e67aea0ba05f2339c65dc3
- Source archive SHA256: 4259ad745b8befd925b7a09af026aca3a696aa44d6666760c8482f3332be8c49
- Gate-result SHA256: d20498e250af692f97fcf94920660ea619c6475fc3377bd523c475eb8d0edaa4
- PNG SHA256: {"density.png": "03958bafc4c5bf9faf926fb682a230c443c53c120b4ed3dda57eeb750781f351", "floorplan.png": "f5944576d4376c0e462bb414279fb4c3b9467cee3c08caf5e089d764fc31a64b"}

qfd_dv_s8_station_tail1_pfxb
- Gate: /home/ubuntu/wt/codex-q-s8-prefix-collect-1021/physical/ref_tile/qfd_dv_s8_station_tail1_pfxb/gate_result.json
- Floorplan PNG: /home/ubuntu/wt/codex-q-s8-prefix-collect-1021/physical/ref_tile/qfd_dv_s8_station_tail1_pfxb/gate_layout/floorplan.png
- Density PNG: /home/ubuntu/wt/codex-q-s8-prefix-collect-1021/physical/ref_tile/qfd_dv_s8_station_tail1_pfxb/gate_layout/density.png
- Frozen floorplan SHA256: 71e36815a183190d94bcdc6a83c2020599ff295164911da5619144b5fe7432b0
- Spec SHA256: 786b1d8402a133b50ba3e3d841e37de60eed5ba9108768cdf9587ff2b5c9a6b9
- Manifest SHA256: e5ac14ac61e8713be52cc6a43c7ce1abfa44ca87eee17c6fc0c9e76c46b1166e
- Source archive SHA256: 2dac6458b1e0d5d9aa978c0b1f7a19e426c2e603c6182321b6fd7848d93eb480
- Gate-result SHA256: 90cd1300a3f2c8e92b86233babe4d5a34928529c23a762c2fa0157086614871e
- PNG SHA256: {"density.png": "a04877fdb01e9267ac20188f6befd2df75369fbbfcf5e86b1affe8a5b389af45", "floorplan.png": "11841e51e8b09774708139edb327bb8bf1509ea87e8e07baeeb963bb0f4b1c47"}

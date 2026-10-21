# Compute RoPE producer source completion

Off-default `OT_QWEN_ROPE=1` sets matching `ROPE=1` parameters on sys_face, embedding provider and native59. Default ports and default sequences remain unchanged. No physical view is adopted by this packet.

Shared external format agreed with KV die lead and sole paired-image owner: payload bit512 marks RoPE, bits523:513 remain zero, existing word index529:524 is0..7, token547:530 and the row-header epoch retain their real producer context. Each512-bit word holds8 pairs, each64-bit lane `{sin_hi32,cos_lo32}`. Table position row is `151936+pos//8`, word `(pos%8)*8+k`.

The system face maps tagged items to the existing provider scale/index pins: scale1,index0 remains the BF16 header; scale1,index1..8 stores RoPE, with E-calendar expected arguments65..72. Normal code remains scale0,index0..63. The provider checks actual token/epoch/slot and complete8-word occupancy, storing RoPE in a second existing64x512 SRAM primitive, using8 rows. Price the FULL additional SRAM primitive and resulting parent outline.

Native59 retains its existing read/address/return bus. RoPE code-read addresses occupy the unused tail: `9723904 + token*8 + beat` (`151936*64` is the base). This preserves actual requested token identity and the existing atomic code address/enable bundle; no assumption about code-vs-scale bus latency is introduced. After the existing65-edge EMB read, it reads8 RoPE words, using the same return pipeline, then emits group1 beats0..7. This is8 additional issue edges; actual landing/calendar times must include the existing provider/return lane ages.

The sole extended pair-image/HBM producer owner is ROOT kv_floorplan. Current canonical EW595_R16 does NOT contain the8 extra words and remains diagnostic for this feature. A73-item shared image, exact codec cadence, current E-calendar/programme and reclosed sys_face/provider/native59 views are mandatory before adoption. ARF/RP slice sources are QW-LAYERGAP6ff5be90f; their physical views remain a separate obligation. No new validation campaign was launched under the owner's no-more-checks instruction.

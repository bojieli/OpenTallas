# S81 SVC J8 split alternatives

**PASS-COND for private geometry and structural allocation.** The image shows all seven candidate placements and the proposed cuts. It was inspected against the macro rows, landing bands and per-bit feedthrough site reports. The seven selected layouts pass the actual cut allocator, including the two vertical fallbacks for t1 and PV t1.

| Part | Cut in type frame | Exterior windows | New lanes at +2 cycles | Existing lanes at +1 cycle |
| --- | --- | --- | ---: | ---: |
| svc_1 | x 578.88 µm | ft8_o −0.212 µm | 13 | 1 |
| svc_3 | y 1010.88 µm | Intact | 8 | 0 |
| svc_5 | x 354.24 µm | attn_o3 −3.811 µm | 16 | 0 |
| svc_7 | x 354.24 µm | attn_o1 −3.811 µm | 14 | 2 |
| svc_11 | x 466.56 µm | attn_o3 −0.743 µm | 15 | 0 |
| svc_13 | x 371.52 µm | Intact | 11 | 0 |
| svc_15 | x 622.08 µm | ft7_o −0.020 µm, attn_o1 −1.248 µm, attn_i1 −2.520 µm | 15 | 3 |

The paired generators match every one of the 9,282 payload and epoch pins across the seven moved windows. Exact per-bit feedthrough repairs retain each existing stage count. Maximum repaired local hops are 404.749 µm for t1, 404.747 µm for t3, 404.749 µm for t5 and 404.749 µm for t6. The exact structural latency receipts use individual split events and include clock landing metadata and count straps.

The combined pre-cut plan and sidecar are in epyc2 `/srv/opentallas-scratch2/claude/opus-fix-s81-svc-r8-north/j8/seven_combined_private`. Full tap and reset generation, source binding and fresh placed-kit reviews remain required for release. The separate hi4 Access proof has its own review.

The combined structural plan also clears the exact post-cut feedthrough scan. Four existing SVC-to-Slice ports initially had 268 over-length outlet bits once the receiver-side leg was included. Moving only those 268 final SVC cells keeps the stage counts and brings all 228 scanned ports and 32 internal chains within reach. The combined maxima are 404.881 µm across ports and 404.749 µm internally. The corrected plan and report are epyc2 `j8/seven_structural_pre_tap/plan_pre_tap_outlets_legal.json` and `seven_post_cut_hops_legal.json`.

[Seven split layouts](s81-svc-j8-alternatives.png)

[Exact paired exterior windows](s81-svc-j8-exterior-windows.json)

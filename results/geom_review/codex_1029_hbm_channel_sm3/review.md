# Independent HBM NW_sm3 channel clock review

Verdict PASS-COND for ONE clock-only coupon GRT TT/FF on candidate33e7d04ea, channel_sm3_v2. No die adoption, freeze or timing claim.

Personally viewed geometry.png: merge roots sit on the two horizontal cross streets, with buffered vertical legs along array streets and short entry stubs. The previous in-array merge heights and dominant U-detour balancing are absent. Read body_review/summary:392cell bodies,390cell edges+34tap edges, max319.766um,0missing homes/row/body/macro-PG overlap; native homes frozen. Model TTwindow9.81/FF13.49ps remains unqualified timing. Wire59.386mm, snake2.227mm=3.75%, below sparse residual guideline. Prior construction failure retained.

Conditions: import exact frozen homes and real hard/PG obstacles into the coupon; recheck actual pin-to-pin geometry after import; use the same NDR/PG for TT+FF routed-RC measurement. The coupon excludes full-die load/PG/other crossings and cannot qualify those gates.

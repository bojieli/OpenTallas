The actual 72-frame source inventory can hold each DENSE2 half's 224 outputs
in one phase on 56 existing frames, four rows per active frame. Sixteen frames
are idle. Even frame counts per slice make every producer boundary eight
values wide, so the existing 256-bit RD primitive can copy whole native pairs.
The previous all-frame distribution used three/four rows and left unmergeable
partial native row boundaries. The legacy 28-rows-per-slice distribution also
omits rows on the smaller actual slices.

The opt-in source map uses:

```
OT_XS_APROJ_TOPO=1 OT_XS_APROJ_ALIGN4=1 OT_XS_APROJ_RANK_TAGS=1
OT_XS_DENSE_SPLIT2=A   # upstream stage; B for downstream
```

Generate the inventory and fixture-scoreboard witness on the fleet:

```
python3 tools/s81_dv/layer_prog/aproj_native_pair_map.py \
  --tree TREE --fixtures FIXTURES/L0 --out aproj_native_pair_map.json
python3 tools/s81_dv/layer_prog/kv_transport_plan.py \
  --compiler-root ROOT --tree TREE --ownership aproj_native_pair_map.json \
  --transport-profile transport_source_profile.json --out kv_transport_plan_final.json
```

The witness binds the actual die hash, selected lowering source, fixture hash,
global output indices, native capture rows and expected BF16-expanded values.
Those values are scoreboard data only. No golden result drives an on-chip
producer. Both 224-row halves have complete, unique ownership with no added
arithmetic or phase. This is an ownership model, not a CAP RTL pass.

The rank-0 KV plan has 16 native pairs, 29 actual route legs and 58 concrete
control payloads. It uses typed V only at actual landed partner bridges,
horizontal RD on the corresponding tier, and the real XRT local-copy bit for
s3N. One pair is globally in flight; intermediate storage is rows 480..481.
Component edge contracts are pinned to the existing XRT transport source.

Calendar qualification is deliberately false. Absolute issue dates and native
SRAM commit dates remain unset until actual frame GO/FIN/CAP completion and
full primitive compositions are bound. The other three ranks' 128-value
carriage remains a separate explicit obligation. Normal slices require the
real `OT_S81SL_KV_TRANSPORT` source assembly; no prior physical view is aliased.

The separate service correction puts actual token position in the WIN_LOAD
header when explicit source-owner mode is enabled. The legacy header remains
unchanged. The actual ATT producer can consequently stamp its accepted
position, and the P.V scoreboard checks the same position in bits 119..99.

Fleet receipts: actual-map unit `1677160-1792602848` returned zero; first
concrete-plan unit `1692529-1792603139` returned zero; source-profile plan unit
`1700183-1792603281` returned zero. These are source/model records only.

# V4.1 full-shape HBM region preflight

`tools/v41_fullshape_region_preflight.py` reads the current die, tile, packed window, pooled index, RoPE guard, PHY, technology and budget sources. Its source hashes and 200K/1M arithmetic are in `results/arch/v41_fullshape_region_preflight.json`. It is a static **necessary** capacity check, not an implemented full-shape layout or token gate.

For an executable gate, run `python3 tools/v41_fullshape_region_preflight.py --require-ready`. It exits with status 2 while physical region placement or the selected CKV path remains unresolved. The focused test checks this blocked verdict.

## Present instantiation and ownership

The only RTL/test instantiation of `ot_chip_v41x_die` uses reduced defaults. The die's full-shape branch selects a 30-bit K-sector port and a real 17-sector packed FP8 window ring on `WIN_STACK=0`. It does **not** set the tile's opt-in `IDX_SHARDED`; the tile default is zero, so the current full-shape branch still writes every index key to all four stacks. Its default `IKH_SLICE=2^18` sectors cannot hold even one 1M user's replicated keys (557,056 sectors per stack). The full-shape selected CKV mux client is tied to zero and `kv_ok` is held low. A complete 640-row window-plus-selected-CKV operation cannot pass through this die yet.

The die accepts `rope_reserved_end` and two RoPE bases from outside. The guard checks that both tables follow that caller-provided end, but the only internal floor it proves is keys, plus the window region on `WIN_STACK`. No connected CKV layout proves its end. The QE weight port uses a separate dense W memory on one stack; the guard does not charge that allocation to the same physical stack as keys, window, CKV and RoPE. ROM weights remain a separate on-die word-addressed region.

## Capacity bound if the compact layout is adopted

The table assumes **future** sharded 68-B index keys (16 keys per stack group), perfectly striped 288-B FP4 CKV, the implemented 128-row packed window on stack 0 (128 × 17 sectors per user), and both deployed 1M RoPE tables (2 × 1,048,576 × 2 sectors per stack). It uses 22.5 GB per stack with the existing 0.9 reserve. CKV placement and cross-region checks are not yet implemented; these are optimistic upper bounds. Sector rounding is included for the index keys.

| Context | Model ROM users | Optimistic bound with window and two RoPE tables | Result |
|---|---:|---:|---|
| 200K | 4,516 | 4,449 | model count exceeds the physical bound |
| 1M | 866 | 859 | model count exceeds the physical bound |

The 1M sharded key slice needs 139,264 sectors per user per stack, whereas the default die reserves 262,144. A compile-time 1M slice also reserves that space for each 200K user. Achieving both model occupancy points on one chip requires a runtime compact stride or region allocator; changing only the writer's `SHARDED` bit does not provide it. Multi-user index-key write/read offsets and the full-shape controller's user IDs require a separate exact isolation gate.

The full-shape `K_MEM` default is still `2^19` sectors per stack, much smaller than the 1M state region or the two RoPE tables. A real build must configure physical stack capacity, region bases, user strides and weights before a region pass can be claimed. The model's saturation and HBM comparator numbers remain conditional on those layout and exactness gates.

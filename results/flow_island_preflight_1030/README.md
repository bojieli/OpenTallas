# Typed pushdown island admission

Static read-only comparison on intel1 selector `roles_fresh/kits/*roles5_td` and `*roles6_td` using this kit_contract source. No EDA, files or jobs in either kit were changed.

The existing `island_macro_clear` check previously returned NA because neither kit has island_ft.json. Both have nine typed master_slice.pushdown islands installed as 18 compiled clock/reset cells. The checker now coalesces these explicit reservations, rather than treating ordinary core_tree cell placement bounds as islands.

With the unchanged MACRO_PLACE_HALO=4.32, rejected roles5 produces eight exact macro/island overlap errors (two edge islands each on SRAMs #1/#4/#7/#10); corrected roles6 has zero errors. Both apply the static check to twelve SRAMs and nine unique reservations. The previous failure is retained by the owner.

Focused controls: existing island_ft static overlap/RTLMP guard behavior; new typed static overlap; duplicate compiled clock/reset rectangles coalesced; missing compiled reservation rejected; nonfinite reservation fails closed; generic full-core tree-cell bounds remain NA. Three focused tests pass.

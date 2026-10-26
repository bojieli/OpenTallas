# Compiler slice source selection from the real as-built manifest

`OT_S81_SELECTED_ASBUILT_MANIFEST=physical/die_plan/s81/bind/asbuilt_b178_coll.json` opts into the binder's actual file/preference precedence. It records every selected module path/hash, including physical preferred copies. Default source resolution is unchanged. A missing or ambiguous master, changed define set, path outside the repository, or incomplete root fails without falling back to default RTL.

Actual canonical die_b178.v: 16/16 slice source chains resolve, including four preferred physical files. Four focused source-selection tests plus seven existing source/runtime guards PASS. The no-preference duplicate, wrong-defines, missing-source, and overriding-child controls all fail.

The bind manifest blackboxes xg and omits two implementation children needed by the compiler at u_s_3S/u_s_3N: ot_s81sl_xs and ot_s81sl_rstop. Their explicit paths are supplied via `OT_S81_SELECTED_CHILD_FILES=rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv,rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv`. Extra children cannot override a manifest-selected module. This is an explicit implementation-source extension; no search or inferred fallback. Their hashes are in the selected chains.

This record establishes source selection only. The layer compiler still needs the bound geometry/ages and actual HOST/control runtime proof; no whole token claim.

# QC U/V wave fix 2026-10-29 22:49

Actual sle_sc_v2 and sle_sc_v1__cl115da35f mapped synth netlists fail PORT_BIND with exactly12extra pins: three 4-bit strap_r8pad_core_red_{addr,data,we} ports. kit_rtl.json bound_only_pins and bind_parent_id_straps.json already declare and tie them under OWNER10-28 R8 count straps. Physical plan count_straps omitted them, and its schema accepted only ca_*.

Shared schema delta accepts the existing ca_* OR r8pad_* families; arbitrary strap_* remains rejected. Generated JSON schema synchronized. Four schema/physical-port tests pass. add_r8_strap_sites.py validates exact actual bound-only input declarations, widths, kind and per-instance tied values against binder manifest; appends missing declarations and M5 sites while preserving every existing strap site. This is physical bookkeeping for already-built hardware, zero RTL/cycle/value change. Existing SRAM/ROM/clock reserved area and pin-spacing exclusions stay. r8_plan_delta.json appends28M5pins on3types (two sc12bits each + sle_fw_v1__clf58b4dfb4bits). Parent die plan owner must integrate this in next plan event; script can consume updated plan/manifest and metadata.

Actual unchanged mapped nets now pass exact port gate after generated pin inventory: sle_sc_v2 19022/19022 and sle_sc_v1__cl115da35f 19551/19551, each missing0/extra0; old inventory each extra12. Both reports retained actual_port_bind.json. This is NOT a placed/routed/signed claim. Main-tools pre-floor LEC jobs remain live and are progressing through hyp0/1/2; they are not restarted.

Other collected failures:
- slw_sc_v2 FACE shared1/feedthrough11/unregistered1 = same ringSTART class: cland_rstart_in->AND2, fstart shared231loads plus11copies. Inherited hold list uses bound-module qfd_qc_slw_sc__slw_sc_v2, whereas launcher uses plan-type slw_sc_v2; normalization needed in successor. Parent ringSTART lane owns source repair.
- tt_ctlm synth_odb ORD-2013 is an additional undeclared-macro type beyond original18 (parent macro lane informed).
- coll_ucie floorplan IFP-0002: PHY777.6x777.6 does not fit core width768.96 inside outline777.6. Minimum unrotated outline width786.24 plus declared halo; requires plan slot/placement event, no forced macro overlap.

Source inventory/readback intel2:/srv/opentallas-scratch2/claude/qc-kits-u (read only); actual failed source artifacts preserved. No inherited launcher/process/worktree mutated. RingSTART/macro source are parent-owned. This branch changes schema support and carries a die-local plan-overlay script only.

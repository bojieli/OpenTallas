# KV SD clock fix, option (b): region DME on sys_SW / sys_SE (DIE-KV-47-SD, 2026-10-30)

Clock-config-only fix for the sd47 re-site. The plan is unchanged. The only difference from
../clk_kv_e26a_w243_sd47.yaml is in `region.only`, which gains `sys_SW` and `sys_SE`
(form dme, dme_mode delay): see ../clk_kv_e26a_w243_sd47b.yaml.

## Why

In sd47, SD regions were built as region H-tree nodes and then legalized by balance_legalize.
That slid merge nodes b8158/b8143 to the W/E rim (y=26524.8): a 940-um detour of +13/14 stages.
The SD taps came out +540 ps late at TT and +480 ps late at FF, and measured CA FAILed
(SW->W2 at TT: lo -195.9).

With the two SD regions on legal-site DME (attach_region_dme, no re-slide):
- The tree has 0 illegal sites, 0 cells on the PHY body, 15270 cells and 6003 repeaters.
- SD taps are 61-98 ps earlier at TT and 53-87 ps earlier at FF than w243.
- Non-SD taps are unchanged (delta 0.0).
- Tap-only GRT spread is identical to w243 (TT 69.8 / FF 56.6 ps, 0/128 regions over 150).

## CA bind: START path remap

The KV CA bind inputs (bind_ca_wc.json from die-kv-41-1029/start_wc, and nativeB_full.json from
codex-kv-1030) live on intel1 scratch, not in this repo. Both key START stages by clock-tree path.
The SD subtree paths change with the tree, so the bind must be remapped before the CA emit.

path_remap.json maps each old path to the sd47b path of the SAME node cell (50 paths). K/PAD values
are unchanged. To apply it:

    python3 apply_path_remap.py path_remap.json bind_ca_wc.json   bind_ca_wc_sd47b.json    # 70 replacements
    python3 apply_path_remap.py path_remap.json nativeB_full.json nativeB_full_sd47b.json # 64 replacements

Both outputs were checked to be byte-identical to the inputs of the measured CA proof below.
The remap is valid only for the sd47b tree (clk_kv_e26a_w243_sd47b.yaml on the sd47 plan).
If the tree is rebuilt with any other change, regenerate the map by node cell.

## Receipts

The measured CA uses the record recipe: START-loaded GRT -> both-edge readout -> components proof ->
die_sta_related with the codex-kv-1030 e0_sta args.
- ca_worst.txt: the COUNT-ALIGN TT/FF lines for ctl (record, reproduced exactly), sd47 (FAIL) and
  sd47b (PASS: TT lo/hi 110.4/111.7, FF 100.0/228.1, 0 ports <100, start-skew fail 0/1687).
- sd_rows_sd47.json / sd_rows_sd47b.json: the SD crossings. Under sd47b, L2045/46 SE->E6 is
  TT 472.1/1610.1 and FF 550.8/1573.3; L2048/49 SW->W2 is TT 459.8/1641.2 and FF 542.2/1602.1.
- grt_spread_sd47.json / grt_spread_sd47b.json: the tap-only clock GRT spread, slew and duty per corner.

Run data is on intel1 /srv/opentallas-scratch2/claude/die-kv-47-sd (clk/sd47b, grt, cab).
ot-run units: sd47b replay oth-ubuntu-4078491-1793403717, sd47b CA oth-ubuntu-29083-1793404294.

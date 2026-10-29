# HEAD HK4 strip event: raw G0C PASS

Final RAW event: plan_spine_raw.json.gz, spine_regions.json and region_plan/regions_map.json. G0C0 errors/19 types/351 parts;23 warnings (sparse missing macro views/connectivity declarations). Reset wavefront max hop378um, unreachable0, max release91 boot cycles. Own tool results, UNCHECKED by independent NUMBER-CHECK. No P&R/STA submitted.

Seven original FT frames crop while preserving all external data pins, including hd_st_m1442.88x129.60 versus1442.88x1226.88. N3 splits into independent transit1442.88x475.20 and turn1304.64x604.80. Each spine becomes central587.52x2073.60 plus four ribbons using W/E masters699.84/95.04x682.56. The ribbons extend to the row edge so existing reset output candidate sites reach the first west tiles. All old data windows stay unchanged. Combined partition outline area drops by about16mm2; die outline stays unchanged.

Existing horizontal station registers move into the ribbons: xw4,xe4,bw8,be6 total wrapper stages remain unchanged; x_o/b_i remain7. Actual generated N3 miter PASS400cycles/four full-width paths and u1 one-stage mutant CAUGHT379. Actual real-SPO/SPR spn and end miters PASS1000 cycles each; west-shim mutants CAUGHT907/898. Vehicle is one-clock/local-reset mechanism proof; production CA/START is next.

327 regions versus326 before: independent N3 split gets one extra region; all24 added spine ribbons explicitly remain in their original six spine regions. Physical external crossing count remains427 and211,813 bits. New N3 entries need an explicit feed from the prior N3 clock neighborhood. Region planning's three-cycle/default-ring estimates are provisional: actual CA counts are not yet re-bound.

G0 failures diagnosed/fixed: stale latency rows regenerated after stripping old CA metadata; lane links spliced into existing functional lanes; east edge snapped to8.64 grid; shim clock layerM9; stale common clock header250 aligned to450 matching all16 pre-existing planned type targets (COORD approved, actual view clocks unchanged); ribbon S extension restores reset reach. Earlier failed reports are preserved in g0c_split*/. No gate weakened.

Reviewed png/hd_st_m.png,png/die_hk4.png,png/n3_split.png,png/spine_split.png. No rectangle overlap or external endpoint pin-table change (234 changed endpoints/51,248 scalar pins). CA/START compose, new clock provider/taps, ring banks, PG and complete reach review must precede P&R/STA. No SIGNED/freeze/token claim for this event.

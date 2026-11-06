# Opt-in KV prompt C: retain pin/face registers; reserve room for north rx hold pads.
# dbBlockage.maxDensity is a percentage [0,100], so 50 means local density <=50%.
uplevel #0 {
 set pb [ord::get_db_block]
 set pu [[ord::get_db_tech] getDbUnitsPerMicron]
 set pblk [odb::dbBlockage_create $pb [expr {round(15*$pu)}] [expr {round(195*$pu)}] [expr {round(95*$pu)}] [expr {round(229*$pu)}]]
 $pblk setMaxDensity 50.0
 odb::dbStringProperty_create $pblk codex_prompt_rx_spread north_gpl_only
 puts "PROMPT_RX_SPREAD north 15 195 95 229 max_density_pct [$pblk getMaxDensity]; pins and face cells retained"
}

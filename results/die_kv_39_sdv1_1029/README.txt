DIE-KV-39-SD-V1 (KV-022 variant V1, 2026-10-29 19:45 PDT). NOT ADOPTED until the FF hold gate passes.
Continues Codex codex/kv-1847-1029@635a21369 (19 explicit SD clock taps from 6589 actual main-clk sinks, E root
(1883.52,520), cland_tstart_in at E (1898.656,520)). Codex reset prep failed (35/103 relays on the PHY) because it
started from the bare event28b plan (contents.serdes without lef/origin/outline) with 12 interior local reset sites.
Fix: apply ONLY Codex's clock-entry change to the DIE-KV-36 sd36A plans (intel1 die-kv-36-1029/sd/planA), whose
contents.serdes = actual kit PHY abstract ot_qfd_serdes_112g_x6_phy_w522 origin (17.28,54) 1848.96x972 R0 (= the kits'
macro_place.tcl) and whose reset.local_taps_um = 10 rim sites (DIE-KV-36, all off the macro). Coverage check on
Codex's actual varD placement (geom.tsv): all 14004 DFFs within 181.2 um of one of the 19 taps (rim S 9110 / E 4890 /
W 4; none under the macro) -> no interior consumer site is needed. Two W-rim taps (clk_t14, clk_t17) moved x 17.28 -> 8.64
(Codex sited them on the macro edge, inside the 8.64-um tap clear). Results [CHECKED]:
 reset_tree.for_type (main tools): SD and SD_v1 depth 5, 97 relays (44 tree + 53 pad), max hop 378.0 <= 405, 29 consumer
 taps (19 clock + 10 local), 0 relays on the PHY, verify PASS; render viewed (reset_tree_kv3_sys_SD.png).
 collector (mk_sd36.py rule A): local depth 6, path max hop 372.6, 0 on macro; i_host_link_rst_n source -> rst_n_t0 (104 um).
 strict bind (bindroot tools, recipe sd36A form): errors 0 unbound 0 undriven 0 multiply_bound 0.
 gen.py phys + kit_preflight: SD / SD_v1 PASS issues 0.
SD_v1 uses the SD tap table (provisional, as in Codex prep; its own sink inventory not yet exported).
Build: intel1 /srv/opentallas-scratch2/claude/die-kv-39-1029/sdv1/kits/{kv3_sys_SD,kv3_sys_SD_v1} via run39.sh
(place -> append DIE-KV-38 declared FDI CDC to 3_place.sdc, same form as the C/A baseline -> CTS + FF hold gate -> route).
Units oth-ubuntu-277830-1793328231 (SD), oth-ubuntu-278559-1793328232 (SD_v1); logs kits/<T>/run_place.log, run_route.log,
hold_gate.log; ot-run log intel2:/tmp/dkv39_sdv1_<T>.otrun.log.
Baseline to beat: C/A SD -251.49/-286.68, SD_v1 -372.34/-379.06 ps; pass > -100.

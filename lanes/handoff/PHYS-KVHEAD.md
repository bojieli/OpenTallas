# PHYS-KVHEAD handoff 2026-11-13 18:09 PST
Launched (all ot-run, logs intel2 ~/tmp/):
- hd_lep0N street relayout (prep fixed by remap.py = reset_start_raw_exports remap by xy to depth-6 relays): epyc7 unit oth-ubuntu-3770468-1794622103, kit /srv/opentallas-scratch2/claude/phys-kvhead/kits/g_hd_lep0N, pkh_lep0N_route.log
- KV kv3_io_cor_v1 epyc8 unit oth-ubuntu-3094843-1794622101; kv3_io_cor unit oth-ubuntu-3103376-1794622153; kv3_hroot unit oth-ubuntu-3103401-1794622154. Kits epyc8 /srv/opentallas-scratch2/claude/phys-kvhead/kv/<type>/gen (plan_c copy with clock.pregrt_ff_hold true). Logs pkh_<type>_route.log.
Check on finish: pregrt_ff_hold.log class line (R-CLOCK-2), GRT overflow (lep0N was 30213), hold after GRT, DRC-0, TT setup >= -42.
Not done: SD_v1 (KV-101 owns SD32 GRT). Plan-event ask to KV-101: pregrt_ff_hold true on io_cor, io_cor_v1, hroot. HEAD-98: lep0N plan with moved SRAMs/reset taps needs remap.py logic at the next prep (rst_start_raw_2 relay moved 12 um from its pin).

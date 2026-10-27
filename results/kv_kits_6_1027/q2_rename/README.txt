D-KV-ECTLK-Q2-SI283 (COORD 10-27 07:38: plan pin rename, no RTL / xy / cycle change). Script by KV-CORES-PV3 (07:51, uncommitted when the lane died); re-checked + committed by KV-KITS-6 2026-10-27 10:37 PDT.
hm_r26 568fc66e -> hm_r26q2 1d257518: qkd_ectlk_q2 pins si[283..536] -> si_283[283..536] (RTL port input [536:283] si_283) in the NEW file
cores/qkd_ectlk_q2_pins_r26q2.json (c50fef25); the 8 kv3_hg* hard_cores entries of module qkd_ectlk_q2 repoint to it; everything else byte-identical.
Port check (portcheck.txt): r25 file 256 pins not in RTL / 254 RTL bits unpinned; r26q2 file 0 RTL bits unpinned, only ft_ck_i_0/ft_ck_o_0 (12.2a1 island ft ports, added by the kit generator).
G0 + G0C on main 60b5ddf52 tools, base and delta: PASS 0 errors, 1851 warnings each; finding sets identical after the name map.
Plan dir: intel2:/srv/opentallas-scratch2/claude/kv-kits-6-1027/pd (= clock-kv-r26-1027/pd + the two files).
Not the same as Codex codex/kv-cores-0809@1149fea184, which rewrote cores/qkd_ectlk_q2_pins_r25.json IN PLACE (ffdeb518) under the unchanged plan sha 568fc66e; pin content is identical except the "source" string.

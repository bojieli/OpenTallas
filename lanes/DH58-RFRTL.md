# DH58-RFRTL (helper of DIE-HEAD-58): RTL side of HEAD RE-FORM batch l48rf (CLOSURE-LIST HEAD-046)
Branch claude/dh58-rfrtl-1103 (off main 08542fa9d7d), wt intel2 /srv/opentallas-scratch2/claude/dh58/rfrtl, data intel2 /srv/opentallas-scratch2/claude/dh58/rfrtl_data, epyc2 /home/ubuntu/scratch-root/claude/dh58-rfrtl.
OWNER 07:0x: 150k / util / +10% quick-place are AIMS (advisory), only sign-off blocks. hd_st_m SIGNED -> unchanged.

## 2026-11-03 06:55 PST CENSUS v1: real ORFS synth std cells per HEAD type (signed hard cores + SRAM macros are macros, not counted)
Source: newest kit synth per type (run/logs/.../1_synth.json + mem.json, kit_wave/dh55 kits, l48x/l48z/cland vintages), census_i2.{json,tsv} [CHECKED].
Memories > SYNTH_MEMORY_MAX_BITS (4096): 0 in every measured kit (mem.json $mem_v2 rows, all kits synth with the 4096 default).
| type | std cells | std area um2 | macro area um2 | macros | >150k |
| hd_host (unsplit) | 204,630 | 31,297 | 124,005 | 72x sram 256x64 + 38x 32x64 | YES -> HSPLIT |
|   hd_host_w (HSPLIT genP) | 102,350 | 15,869 | | | no |
|   hd_host_e (HSPLIT genP) | 85,797 | 13,527 | | | no |
| hd_mesh | 191,052 | 29,507 | 124,005 | 72x 256x64 + 38x 32x64 | YES (plan said 140k) |
| hd_lep0N | 176,571 | 26,247 | 1,670,090 | 4 lep_pair + 45 sram | YES (plan said 365k) |
| hd_spn | 94,043 | 14,072 | 0 | | no |
| hd_tile (glue) | 64,684 | 10,351 | 490,075 | 4 elemA_cv + elemB_cv | no |
| hd_st_n4 | 64,069 | 8,940 | | | no |
| hd_spn_end | 60,758 | 8,986 | | | no |
| hd_st_k5 38,078 / hd_st_turn 37,674 / hd_ctl_n 36,745 / hd_st_n3_turn 34,099 / hd_st_str 32,080 / hd_st_n3_transit 31,950 / hd_host_n 18,450 / hd_spn_wshim_rx 16,402 / hd_turn_a 16,307 / hd_turn_b 15,144 / hd_spn_eshim_rx 14,018 / hd_st_m 5,064 / hd_spn_wshim_tx 3,473 / hd_mesh_e 2,721 / hd_ctl_e 2,715 / hd_spn_eshim_tx 1,207 | all < 150k |
| hd_ctl | PENDING: no kit ever synthesized; ORFS synth probe of ot_s81hd_ctl_core (plan sources, 4 sram64x512 macros) queued epyc2 |
| hd_serdes | PENDING: probe of ot_s81hd_serdes_link (kp4_dchn signed core blackboxed, 2 sram macros) queued epyc2 |

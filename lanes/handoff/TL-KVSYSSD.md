# TL-KVSYSSD (qwen_kvsys kv3_sys_SD_v1) 2026-11-14 04:50 PST
Finding: no live flow failure on kv3_sys_SD_v1. It is SIGNED (R-MINIMAL) and counted.
- a1d28b0aa34a SIGNED 11-13 23:03 (DRC 0, TT >=0 at 833 ps); late ECO i1 (eco_20261113_222034) then AUTO-RESIGN flow-20261113-ai-kv 23:24: TT +17.56, FF hold +4.44 (0 violators), LEC EQUIVALENT.
- signoff: epyc2:/srv/opentallas-scratch3/claude/auto-resign/qwen_kvsys/kv3_sys_SD_v1__flow-20261113-ai-kv__053d02ec/signoff/signoff.json
- kit_wave_state has NO kv102sem_ftgrid row for SD_v1 (not relaunched; SD_v1 plan entry unchanged by kvN2/sem events). The failures seen under kv102sem_ftgrid are hgi_v6/hgi_v8 CLAND (ft17_o), not SD_v1. The kv3_sys_SD (no _v1) rows are a separate type (WAIT-FORM / ENQUEUED, attempt kv102sem_ftgrid a3).
- No build launched; nothing to fix. Optional polish only: east-collar tap balance (hold >= +10 die gate).

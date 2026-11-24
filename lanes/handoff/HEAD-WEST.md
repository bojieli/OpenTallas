# HEAD-WEST handoff (split from HEAD-R18, 11-23 19:2x PST)
Job: pick HEAD West form at GRT; nst4 kit if (b) wins; else next structural form. Every chain: --remap-base = parent plan (LANDREMAP fail-closed).
- Kits (intel2 ~/fable-fix-head-lep0n-1122/r18g_exact_continue/west-*; kit dirs epyc7 .../head_rp21z20NF15f_r17b/private/HEAD-R18/):
  - (a) wband prep_r18g_wband 014661a6ea33: hd_lep0N_w_1123175932 (unit head-r18-west-wband-grt)
  - (b) wch4b prep_r18g_wch4b f570eb1144eb: hd_lep0N_w_1123175934 (unit head-r18-west-wch4b-grt)
- Waiter: head-r18-kit-waiter5 (waiter3/head_waiter.sh) posts raw reads as HEAD-R18 + WEST WINNER + launches west-wch4b-nst4/run.sh if (b) first at 0.
- 19:2x: wband tap-pre GRT 0 overflow (12 extra its); wch4b still iterating.
- Local watcher: scratchpad west_watch.sh (background).

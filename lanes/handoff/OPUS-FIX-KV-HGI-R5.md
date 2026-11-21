# OPUS-FIX-KV-HGI-R5 handoff (Opus; KV hg/hgi family owner; successor of OPUS-FIX-KV-HGI-R4). CURRENT 2026-11-21 07:5x PST

Work dir: epyc7 /srv/opentallas-scratch2/claude/opus-fix-kv-hgi-r4 (W). Client logs/waiters: intel2 ~/tmp/opusfixkvhgir5/ (wait_*.out).
COORD rulings 07:1x: kt depth stays 2; no ectl (320,900) station unless a PLACED hop > 405 in the hgi_v1 kit (measure q->hst2_g/hst3_g).

## Plans
- plan_r5d26.json (cd8a718931c0) = R4 plan_r4d26 (D26 a9f605cb1acf + hgi x-street kt rows v2 + hgi_v8 clk_t81/t82) with the schema-unknown
  'note' stripped from the 2 added_taps (first G0/bind refused: SCHEMA-UNKNOWN-KEY). In tree26/launch26.
- plan_r5d26hg.json (f45864b2605a) = plan_r5d26 + hg x 8 types rows from kst_xstreet_v3.py (soft core halo: hard 2.16 um, 12 um margin as cost):
  0 skipped (was 62 die-edge/narrow-gap skips), 0 kst sites inside cores (was 136), max hop centre 362.9 / bit 383.4 on all 8 hg types
  (hg_v1 head0 e4 was 1806 um routed / 601.9 hop in v2, now 717 / <= 363). Report W/ana/kst_v3_hg_report.json. In tree26hg/launch26hg.

## Units
- G0 + strict bind/LATCHECK on launch26: intel2 clients 1836779 (G0 -> W/g0gate26b) / 1836780 (bind -> W/bindgate26b). Elab PASS.
- chain_hg (prep tree26hg + G0 + bind on launch26hg): client 1959795.
- R4 handed units: b8/b8d oth-ubuntu-1682127/1682133-1795238641 (OT_TAP_CORE_DIRECT decision on the final 5_1_grt.odb readback),
  ft26 (Codex) oth-ubuntu-3222492-1795259200, relayfit client 42768.

## Next
- bind26b green -> private-spec qwen_kvsys kv3_hgi_v1__cl141fc26e --tree W/launch26 --bind-out W/tree26/.../bind_of_record --host epyc7
  --src-manifest off (rt/current a9ed808a98d5 has these flags), run-item, run to route; measure placed ectl hops; sign-off gates.
- Rows to KV-PLAN-R5 once bound: hgi kst rows + hgi_v8 taps (plan_r5d26), hg kst rows (plan_r5d26hg), core-tap key after b8/b8d.

## UPDATE 09:3x PST
- G0 PASS 0 errors on launch26 (cd8a718931c0) and launch26hg (f45864b2605a). Strict bind launch26: 14 EMIT reset-relay errors = KV-PLAN-R5 07:47
  D27d hidden set (pc/pv untouched types too) + BIND_SRC_OUTSIDE (symlink skeleton; add --allow-src-root if rerun). No new error from my rows.
  bindgate26hg (chain client 1959795) still running -> expect the same.
- Rows handed: epyc7 W/ana/hgi_r5_rows.json (8d11aee89567, 40 rows / 19 types) posted PLAN-ROWS 09:2x to KV-PLAN-R5.
- OT_LAND_RESERVE=1 for kv3_hg x8: kit_wave_edit 55256552eef2. Wave relaunches then FAIL src_manifest: D26 tree kvd23_hubc_views rebuilt in place
  08:07 by FAM-KV-HUBC-SYSC -> every D26 wave relaunch fails SRC_MANIFEST (posted 09:0x to COORD/KV-PLAN-R5; theirs to fix).
- Private kits (run-item on intel2, logs ~/tmp/opusfixkvhgir5/v1kit_runitem.log, v8kit_runitem.log; waiters wait_v1kit/wait_v8kit.out):
  hgi_v1 spec private_specs/OPUS-FIX-KV-HGI-R5/qwen_kvsys_kv3_hgi_v1__cl141fc26e_1121092028 pid 3802294, work epyc7 W/v1kit;
  hgi_v8 spec .../qwen_kvsys_kv3_hgi_v8_1121092637 pid 3917205, work W/v8kit (plan W/ana/plan_r5d26v8.json, fs_ft11_o stage fix).
  Both use the wave D26 bind (station counts unchanged -> RTL unchanged) and src_manifest off.
- To do in the kits: after place, measure hgi_v1 i_ectl_Q_N_tN placed hops (q -> hst2_g/hst3_g); add a station only if > 405.
  e0 self kt row (G0 routed 439, Manhattan 223) pre-existing on all heads: check placed. GRT: read final 5_1_grt.odb only.
- Generator: W/kst_xstreet_v3.py (soft halo; added_taps 'note' no longer written - schema refuses it).

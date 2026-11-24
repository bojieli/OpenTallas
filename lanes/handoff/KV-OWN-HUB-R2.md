# KV-OWN-HUB-R2 handoff (Opus 5.5, from 11-24 09:35 PST; predecessor KV-OWN-HUB died on the limit ~04:55, it left no handoff)
Job: A5t6 row for kv3_hub_Eo east macro channel (VIS-REOWN 09:31 E-side smear). Base A5t3 cbee82715bca (epyc9 kv-allfix/grow/A5t3/plan.json). Post ROW-REBASED to KV-ALLFIX.
## Cause (A5t3 probe kit epyc11 KV-D29/private/KV-ALLFIX/kv3_hub_Eo_1124042156 geom/geom.tsv, box x950-1250 y450-1400)
- 36,002/40,500 flops u_d75_seq_g_fan_2_u_fan_aq (ot_dp_dly W540 D75 age pad fan_2 -> astk_ES ctl aq) + 6,487/8,100 u_d15 (fan_3 -> astk_EN). Unseated pad line = diagonal smear.
- Separate (NOT in row): xs->fan q 4x128b NEED-STATION 840-998 um est 1040-1237 ps (placed_scan.tsv); needs priced +1 station (LAT); fan kq->kc REACH 526 um.
## Row
- epyc9 /srv/opentallas-scratch2/claude/kv-own-hub-r2/ROWS_KV-OWN-HUB-R2-ECH.py sha 236ff2e333c4: hub_Eo.pad_ram {min_d 8, wide_min_d 16, keepout_um [[1000,245,1278.72,1430]]}. kit_dly_ram dry on A5t3 bound RTL: lead 8 + 3 SRAM D66 + resid 1, sites (882.6,100.7) (904.2,48.9) (774.6,135.3). Cycle-exact.
## Gate job
- epyc11 ot-run PID 475022 (E9 waiter cancelled on load cap, never started) job_ech.sh -> out epyc11 kv-own-hub-r2/ech: row plan 3f53aba1376d (diff = hub_Eo pad_ram+note only), PRE base+row, elab, strict bind --types kv3_hub_Eo, PRE --elab-dir GENDRY. log job_ech.otrun.log. Plan copy in epyc11 grow/tree plan_of_record/plan_kvownhub_A5t3ech.json.
## Row 2 (COORD 09:5x: stations on xs->fan, own lane, LATCHECK+R8, plans only in OWN folder -- never write grow/tree again)
- epyc11 kv-own-hub-r2/ROWS_KV-OWN-HUB-R2-SEQLP.py 11d9dfe72d5c: clock.core_link_pipe qkd_seq_fan_s {q:1,aqm:1}, types += kv3_hub_Eo. Plan on A5t3 = 526110b93a98.
- Gate job_lp.sh: ot-tree-fork grow/tree -> kv-own-hub-r2/tree (own), plan there, launch_lp_70d2e, out kv-own-hub-r2/lp. ot-run PID 617482 unit oth-ubuntu-618360-1795543023.
- Told KV-ALLFIX (0e1e840b) about grow/tree plan_kvownhub_A5t3ech.json: keep or ot-delete after my row1 job ends.

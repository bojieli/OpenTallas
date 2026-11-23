# RELEC-1122 handoff (Opus, started 11-22 22:5x PST by COORD)
Goal: routed LEC EQUIVALENT evidence for the 168 AT-RISK rows of lanes/COUNT-LEC-AUDIT.tsv (hub 0369b02b). Output lanes/RELEC-1122.tsv
(die, item, record, netlist sha, routed LEC result, evidence). Never write COUNT-REVOKED. Post NOT-EQUIVALENT + NO-NETLIST lists every 2 h + end.
Order: HEAD(6) > S81(18) > KV(52) > QC(92). Report to COORD (<250 words) after HEAD+S81 and at the end.

## Method
- Record -> origin kit: signed-store record (~/coord/signed-store/records/<id[:2]>/<id>.json.gz): origin, files[] (6_final.v path+sha), netlist_sha.
- Archive (AGIdock /archive/opentallas-signed-1106/<host>/<path>) holds 6_final.v but NO RTL/config.mk/lec.py.
- Routed LEC = autopilot signoff_chain form: env OT_LEC_SUPERSET_VEC=1 python3 -I KIT/lec.py KIT --netlist <6_final.v> --out KIT/lec_routed_relec1122 [--mem --jobs]
  via ot-run --dir KIT --hosts <origin>. Launcher: <host>:/srv/opentallas-scratch2/claude/RELEC-1122/tmp/rlec.sh TAG KIT NET HOST MEM JOBS
  logs: <host>:/srv/opentallas-scratch2/claude/RELEC-1122/logs/{runs.log,TAG.log}
- Work files (rtx localhost scratchpad relec/): meta.tsv (row->record->origin), out_<host>.jsonl (probe), sib.jsonl, hits_<host>.txt (sha search of 6_final.v across hosts).

## State
- 22:5x probe: of 153 rows with a store record, only ~55 have a live kit+netlist on the origin host; 15 rows have no record ("(none)").
- Already EQUIVALENT routed on same file (audit missed): qc sle_st_b_v1__pv0e7b1dcc, slw_st_b_v2__pva66d0f22__pv3d7bec84, sle_st_b_v1__pvc5a85fd4__pv38472fb8.
- KEEP FAIL routed (=NOT-EQUIVALENT class): qc slw_hc3__clccfc3e6b__pvcca9ff41 (epyc9 lec_routed_autopilot_1795360240568320193).
- HEAD: hd_spn routed LEC launched epyc7 23:1x. hd_host_w/hd_ctl/hd_mesh/hd_host_e/hd_serdes origin kits deleted; searching other hosts by sha.
- 23:5x KEY: 106 store records carry kit rtl/+config.mk+lec.py in AGIdock archive. Reconstructed 49 dead kits from AGIdock
  (fetch.py, only from rtx localhost: ssh -i ~/.ssh/agidock_ot ubuntu@155.103.253.53) into <host>:/srv/opentallas-scratch2/claude/RELEC-1122/ak/<tag>/kit
  on epyc8/9/2/10 (sha of 6_final.v verified = record), LEC batch b4 running. HEAD hd_ctl + hd_mesh included.
- Batches: b1 (51 live kits, 6 hosts), b2 (14 live candidates for "(none)" rows), b3 (S81 core views dsfd_su_t_rxsb + dsdv_eng_rr_h1 rebuilt from main views on epyc9 rk/), b4 (archive kits).
- Collect: bash collect.sh on each host (scratchpad relec/collect.sh) -> TAG|lec.json|verdict|...
- Known NOT-EQUIVALENT (existing): s81 ot_hdc_v41x_attn_tr_x (epyc7 s81-svcrs-4/prov/resign/trx0_120p96x259p2_ni/lec/lec.json, 502 differs); qc slw_hc3__clccfc3e6b__pvcca9ff41 KEEP FAIL.
- No RTL anywhere (expected UNPROVEN-NO-RTL): HEAD hd_host_w, hd_host_e, hd_serdes (archive has netlist only); S81 legacy core views dsfd_node_LL*, dsdv_gunit_l5f/l4r, dsdv_svc_sx_hrow (no netlist in view -> NO-NETLIST).

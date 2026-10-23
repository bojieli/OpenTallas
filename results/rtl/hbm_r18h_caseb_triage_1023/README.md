# r18h case_b die smoke triage (TOKd-HBM2, 2026-10-23)
Vehicle: r18h S7 GEN (case_b, pre-forest, NO l12 in contract: hcollgi_SW VM_RT absent=0, su_SW0 READ/WRITE_RETURN 10/7),
slice /srv/opentallas-scratch/claude/hbmc-token2/dn_r18h_case_b_hw (gold2, deleted after this record), replays emitted with an r18f l12.json.
- ds_l0: FAIL from cyc 169 (rec2 COLL ring outputs). Probe (tokd2_probe: zero-valued full-mask checks on the 4 SW ring outputs every
  edge 150-330): own flits leave at 217,218,220,... with the expected header order (src0 ttl3 tag 0,1,2,...) = +48 edges, data 0;
  forwarded flits misplaced. Shifting rec2 by +48 (tokd2_sh48) does not pass (244/287 fails).
- qw_l0_r0: FAIL rec6 SU->VM checks from cyc 3217 (unpriced SU return latency).
Causes (relay_depths.txt): launch lane 54 stages vs desc 16; VM round trip 38..90 edges unequal per bank vs VM_RT 0;
ring lanes 5..36 stages vs the 2-edge ring hop. Launch/VM are priced by S8b l12; ring hop + launch skew are an open question to CHAIN.
Class: replay/contract latency mismatch by construction on a pre-l12 vehicle; not an RTL data defect.

# QC-CORES-1 item 6: re-verify the 4 SIGNED QC hard cores (2026-10-27 03:15 PDT)

Read-only check of the records the release cache (~/.local/state/fleet-viz/release_tree_plan_cache.json, plans.qwen_compute.signed_cores,
all SIGNED-LEGACY) and ~/coord/autopilot/OWNERS.tsv use. Per core: routed 6_final mtime vs signoff.json mtime, signoff numbers,
and a fresh routed-netlist LEC with main tools/die_plan/lec.py @262d07038 (diagnostic docker probes, 16 GB cap, outputs
intel{1,2}:/srv/opentallas-scratch2/claude/qccores1-1027/lec/<name>/out/lec.json; none of the 3 legacy records carried a routed LEC).

Findings (all CHECKED from the files):
- No stale sign-off log: every signoff.json is 2-13 min newer than its 6_final.* and points at that odb.
- crh / prog_s8b / rp1_f62: routed LEC EQUIVALENT 3697 / 7221 / 4323 points.
- rst3: routed LEC KEEP FAIL (16 declared kept select-replica flops g_xsl[0].g_sel[*] merged; all 7346 compare points proved).
  -> not a valid SIGNED view until rebuilt with the keep-on-cell fix (ot_keep_regs.tcl) or the replicas are declared non-kept.
- 12.3 band (INFO): rst3 and rp1-F4G in band; crh 292.5/240.6 (declares 42.5 ps early tap), prog_s8b 476/367, rp1_f62 309/252 out of band.
- The release cache still counts rp1 via the 10-25 f62 view; the 10-26 F4G view (in band, LEC 3703 EQ) is the one to point to.
- prog_s8b / rp1_f62 FF hold pass only on the vclk pin-flop-mean IO reference (raw kit SDC hold -105.26 / -46.17), as signoff.py policy.

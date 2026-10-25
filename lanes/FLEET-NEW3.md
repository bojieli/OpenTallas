# FLEET-NEW3 (branch claude/fleet-new3-1024, worktree ~/wt/fleet-new3)
Merged to main 8a5d1f3dab (branch tip 00a85d87a6), pushed. Lane DONE except OWNER? below.

Status: ot-run LIVE on localhost (~/.local/bin/ot-run) for epyc2, epyc3, intel1, intel2, localhost.
- Helpers installed on all 5 hosts via tools/fleet/install_fleet_host.sh (ot-heavy*, die protection, vl-jcap, earlyoom,
  linger, cron reconcile */2, scratch /srv/opentallas-scratch/claude + ~/ot-scratch link). localhost role coord
  (/etc/ot-heavy.conf MIN_AVAIL_FRAC=0.15). ot-sizes-sync cron on localhost */10.
- ot-run --selftest: PASS 5/5 hosts; choose selftest PASS 28; tiny job per host PASS; unpinned placement -> epyc2.
- Tool parity identical on 5/5: verilator 5.050, yosys 0.68 (38e001a6f), sta 3.1.0 (be771a0), orfs sha256:16470cea...
- Tests: test_ot_run_* all OK (spill fixed: tar prefix /usr/bin/tar:). Pre-existing FAIL on main too:
  test_ot_heavy_admit (reconcile selftest v17 HARD_INVARIANT=0 case), test_ot_heavy_v174_replay (1 failure).

OWNER?
- Old-fleet scratch filesystems found on unpartitioned nvme0n1 (signature wiped, backup superblocks intact):
  intel1 3.5T (ex ot-gold1), intel2 3.5T (ex ot-gold2), epyc2 894G (ex ot-epyc9, claude/ I/O errors).
  Mounted READ-ONLY at /mnt/old-nvme0 (not fstab). NOT formatted. Recover 10-23 outputs, then reformat as scratch?

## CODEX notes 2026-10-25 02:40 PDT
Current live5-host fleet PASS; epyc1 restored after /run/user incident without user@ restart, all5 admit. Legacy old-nvme OWNER? above is CLOSED/OVERTAKEN by owner wipe07:03 (BRIEFING decision10); no recovery or formatting task remains. Native launcher localhost selftest PASS.

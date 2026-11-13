# KIT-OPS-2 handoff (kit-wave ops lane; COORD is the coordinator) -- 2026-11-12 22:38 PST

## Task (COORD): epyc4 back into every die's kit-wave hosts/place_prefer (gen_hosts if staged), epyc7 into s81 hosts/place_prefer.
## Why epyc4 was out
- 11-11 21:2x KW-FIX-45 epyc4off: root 98% / scratch2 ~57 GB -> out of hosts + *_base + _kw17_ok, COORD to say when to restore.
- 11-12 06:2x KW-FIX-46 stash_epyc4_kw46_srcloss: DISK-1111 swap self-loop destroyed epyc4 kw45 src trees; FLEET-2 restored 5 (kv 2041/40e2, head m8w1/h94, qc s28) into scratch2/claude/kw45-real, linked from scratch3/claude/kw45. hbm p18 trees "stay off epyc4" (COORD then).
- Now (11-12 22:3x): root md0 513 GB free (85%), scratch2 nvme 217 GB (94%). None of the CURRENT die srcs were on epyc4 except qc s28.
## Layout on epyc4 (proved by readlink -f + stat dev:ino)
- /srv/opentallas-scratch2/claude/kw45 -> /srv/opentallas-scratch3/claude/kw45 (md0, dev 2304 ino 142868500). New trees go to the REAL path scratch3/claude/kw45/<tree> (md0).
- kw45-real/src_hbm_main_9fc09952cd_q0g_p18 is a 5.6 GB partial (21798 files, not linked, not FLEET-2's); rd1 empty. LEFT UNTOUCHED.
## Staging (running, started 22:38)
- epyc8 /tmp/kitops2_copy_units.sh (KIT-OPS-1 copy_units: real parents, no --delete, --ignore-existing) lists /tmp/kitops2_{small,big_src_*}.txt -> logs /tmp/kitops2_*.out (pids 806356-806360).
- epyc7 /tmp/kitops2_lfcs.txt (s81-leaf-floor-2/bsrc_main2_lfcs = the 97 bind-named files, as on epyc7/9/intel1/epyc2) pid 2991539.
- Next: manifest2 (per-file sha256) on epyc4 vs epyc8 (lfcs vs epyc7), then config edit, tick check, RESULT.

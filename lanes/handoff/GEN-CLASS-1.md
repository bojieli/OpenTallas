# GEN-CLASS-1 lane handoff (refreshed 2026-11-12 ~09:2x PST)

## 1 Scope
Generator / legalize / preflight CLASS fixes (successor of CLAND-CLASS-1 + STREET-RULE-1). Done + APPROVED: CLAND-SLEW-1,
LAND-OVERRIDE-STALE, legalize role match + FIXED-FACE flag. COORD 07:0x items: (1) SIDECAR-COVERAGE and (2) PLAN-SRC-MACRO READY on claude/preflight-sidecar-macro-1112@ad7c108277; (3) wshim_tx violators CLASSIFIED = FT-HOP-M2-WIRE (posted CLASS, offered to take the fix).

## 2 Worktree
intel2:/srv/opentallas-scratch2/claude/wt/gen-class-1 (git object store = hub mirror, remote "hub").
Current branch claude/preflight-sidecar-macro-1112@ad7c108277 (pushed), working tree clean.
Pushed branches (all on hub): claude/land-override-stale-1112@cef99b3203, claude/cland-slew-1112b@33e70e1695
(ignore claude/cland-slew-1112@3375e6375c, truncated message), claude/street-fixedface-1112@a07f957bc5 (on top of
street-rule-1112@3cca0a68ed). Scratch: intel2 /srv/opentallas-scratch2/claude/gen-class-1/ (plans/, msg*.txt, patches).
Tests run with /srv/opentallas-scratch2/claude/rm-ai-1031/venv/bin/python -m pytest -p no:warnings
--basetemp=/srv/opentallas-scratch2/claude/gen-class-1/pt (no xdist).

## 3 Running jobs
None on the fleet. (Only a read-only find for S00 logs from localhost; no need to re-run.)

## 4 Watchers
None.

## 5 Results not yet posted
None. Affected list for CLAND-SLEW-1: ~/coord/lanes/gen-class-1/cland-slew-1-affected.tsv (HEAD 23, S81 227, QC 114,
KV 54, HBM 0); COORD: no blanket re-sign, unsigned types pick it up at next kit.

## 6 Next steps
a. Wait for COORD on FT-HOP-M2 (wshim_tx: 120/125 slew pins = fanout-1 ~200-um M2-only wires from repair BUFx3 to
   ft-link station inputs; analysis script epyc8 /srv/opentallas-scratch2/claude/gen-class-1-slewcls.py <kit>).
   If assigned: in gen_phys / ft_bit_sites.tcl give ft-link station hop nets a layer floor (M4+) or a repeater per
   <= ~110 um, test, bench on the hb4k wshim_tx kit via ot-run (epyc9), post READY.
b. Watch the queue for review comments on the 4 READY branches; fix and re-post.
## 7 Open READY/ASK
land-override, cland-slew-1112b, street-fixedface APPROVED (ROOT-MERGE-60). preflight-sidecar-macro-1112@ad7c108277 READY, awaiting COORD. FT-HOP-M2 assignment ask to COORD.

## 8 Gotchas
- ssh heredocs mangle quotes: scp python patch scripts / message files and run them; commit with git commit -F file.
- Never git in /home/ubuntu/OpenTallas on intel2/localhost. ~/coord only via coord-commit.sh.
- ot-run: no colons in paths, intel2 cannot ot-run to itself (use epyc8/epyc9); docker verilator needs HOME=/w CCACHE_DISABLE=1.
- epyc4 kw45 src trees are self-symlinks (ELOOP): avoid epyc4.
- 3 tests fail on main too: band_reserve band_spread_steps, landing_pin_sites qc52, gen_phys_bump_ports refuse_mismatch.

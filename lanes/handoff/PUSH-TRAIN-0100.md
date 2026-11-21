# PUSH-TRAIN-0100 handoff
- Chosen: xdist (-n min(16,ncpu/2), --dist loadfile) + existing rebase-retry capped at 3 affected-only re-tests (simpler than a merge train).
- Gate change in clone /srv/opentallas-scratch2/claude/push-train-0100 (intel2): tools/fleet/ot-push-main, test_ot_push_main.py (13+ tests pass).
- Baseline (intel2 ot-status, 24h, 70 real pushes): 35.7% not landed (rc4 16, rc3 6, rc2 3); median 5.5 s, p90 843 s.
- Measuring kit_wave.py probe: old serial vs new xdist in /tmp/ptr0100-{base,after}.log on localhost.
- Next: commit gate + push via current gate, post results.

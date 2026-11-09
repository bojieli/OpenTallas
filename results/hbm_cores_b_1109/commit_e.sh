set -e
cd /srv/opentallas-scratch2/claude/kw36/wt_e
git add tools/autopilot/kit_wave.py tools/autopilot/test_kit_wave_composed_src.py
git commit -q -m "KW-FIX-36 (e): resolve composed queue_src to one provable commit for the queue row

A kit built from a composed source pins queue_src 'a@s1+b@s2', which the
queue refuses as 'src must be branch@sha' (hbm q_spb1, q_su01, q_su11 pv1,
vsN2, sfu_programme_store_r10, kv3_io_cor).  enqueue_src resolves it to a
real commit only when provable: die option queue_src_exact, or the spec
src_sha when every part is its ancestor or changes only tools/autopilot/.
Otherwise a FLOW failure names the missing part.  retry_enqueue resends the
rows the grammar refused, once, through the normal enqueue path.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q origin claude/kw-fix-36-queue-src-1108 2>&1 | tail -1
git log -1 --format=%H

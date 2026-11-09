set -e
cd /srv/opentallas-scratch2/claude/kw36/wt_g
git add tools/autopilot/kit_wave.py tools/autopilot/test_kit_wave_genhosts.py
git commit -q -m "KW-FIX-36: gen disk fallback when no gen host clears the preference

gen_disk_min_gb is a preference: with every host under it a die's new rows
would hold though a host can still take a kit.  Pick the host with the most
free disk on the die's lane that clears the real floor (root_floor_gb for a
lane on a root fs, ot-run's 50 GB scratch floor otherwise) plus the gen need,
at most gen_fallback_per_tick (2) per host per tick.  No behaviour change
while any host has room; option gen_disk_fallback false turns it off.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q origin claude/kw-fix-36-gen-floor-1108 2>&1 | tail -1
git rev-parse HEAD

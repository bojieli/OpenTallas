cd /srv/opentallas-scratch2/claude/kw36/wt
git show --stat --format='%h %s' 9ba1e6f86e2 | cut -c1-120 | tail -8
grep -n "def retry_enqueue" -A32 tools/autopilot/kit_wave.py | cut -c1-200
grep -n "AP.REPO\|REPO =" tools/autopilot/kit_wave.py tools/autopilot/autopilot.py | head -6 | cut -c1-160
for s in /srv/opentallas-scratch2/claude/kw35/src_cad9p /srv/opentallas-scratch2/claude/kw35/src_cad9z /srv/opentallas-scratch2/claude/kw35/src_cad9y /srv/opentallas-scratch2/claude/kw35/src_e2rd; do echo "$s: $(ls -a $s 2>/dev/null | grep -E '^\.(stage|src|keep|commit)|SOURCE|STAGE' | tr '\n' ' ')"; cat $s/SOURCE_COMMIT 2>/dev/null | head -2; done
cd ~/coord; git status -sb 2>&1 | head -6 | cut -c1-140; git log -1 --format='%h %cd %s' | cut -c1-100

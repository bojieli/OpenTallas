date
df -BG / /srv/opentallas-scratch2 2>/dev/null
echo; ls -la ~/coord/autopilot/ | head -60
R=/srv/opentallas-scratch2/claude/kw35/repo
echo; ls -la $R/.git/objects/pack | grep -E 'tmp_|total' ; du -sh $R/.git/objects/pack; cat $R/.git/objects/info/alternates
pgrep -af 'index-pack|fetch.*promisor|rev-list --objects.*stdin|git.*fetch' | cut -c1-200 | head -20
echo; ls -la /srv/opentallas-scratch2/claude/ | grep -E 'kw3[5-9]|kw4[0-9]'

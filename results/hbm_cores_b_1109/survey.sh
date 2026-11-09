cd /
echo "== ot-run wrapper"; cat ~/.local/bin/ot-run
echo "== real ot-run candidates"; ls -la ~/.local/bin/ | grep -E 'ot-run|ot-sizes|ot-reserve'
for f in $(grep -oE '/[^ "]*ot-run[^ "]*' ~/.local/bin/ot-run | sort -u); do [ -f "$f" ] && { echo "-- $f"; grep -nE '^HOSTS *=|epyc6|NO_AVX512 *=' "$f" | head -20; }; done
echo "== hub ssh aliases epyc6 stanza"; awk '/^Host epyc6/{p=1;print;next} /^Host /{p=0} p' ~/.ssh/config | grep -v -i password
echo "== epyc6 disk layout"; ssh -n -o ControlPath=none -o ConnectTimeout=10 epyc6 'ls -ld /srv/opentallas-scratch /srv/opentallas-scratch2 /srv/opentallas-scratch3; grep -E "opentallas|docker|containerd" /etc/fstab; findmnt -no SOURCE,TARGET /srv/opentallas-scratch2 /srv/opentallas-scratch3; docker images --format "{{.Repository}}:{{.Tag}} {{.ID}}" | head; crontab -l | grep -v "^#" | cut -c1-140; systemctl --user list-timers --all 2>/dev/null | grep -iE "ot-|autoclean" | cut -c1-140; sudo -n systemctl list-timers --all | grep -iE "ot-|autoclean" | cut -c1-140'
echo "== worker->hub use"; grep -rln 'hub:' ~/.local/bin 2>/dev/null | head; 

R=/srv/opentallas-scratch3/claude/rm48
for T in $R/repo $R/base; do
 for p in $(pgrep -u ubuntu -x xargs); do [ "$(readlink /proc/$p/cwd 2>/dev/null)" = "$T" ] && { echo kill-xargs $p; kill $p; }; done
done
sleep 1
for T in $R/repo $R/base; do
 for p in $(pgrep -u ubuntu -x python3) $(pgrep -u ubuntu -x timeout) $(pgrep -u ubuntu -x bash); do [ "$p" = "$$" ] && continue; [ "$(readlink /proc/$p/cwd 2>/dev/null)" = "$T" ] && { kill $p && echo killed $p $(tr "\0" " " </proc/$p/cmdline 2>/dev/null | cut -c1-60); }; done
done
sleep 3
n=0; for T in $R/repo $R/base; do for p in $(pgrep -u ubuntu); do [ "$(readlink /proc/$p/cwd 2>/dev/null)" = "$T" ] && n=$((n+1)); done; done; echo remaining-in-trees $n

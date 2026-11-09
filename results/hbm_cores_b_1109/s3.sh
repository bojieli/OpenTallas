cd /
for h in localhost epyc2 intel1 epyc4 epyc5 epyc6; do
  if [ $h = localhost ]; then C="bash -c"; else C="ssh -n -o ControlPath=none -o ConnectTimeout=10 $h"; fi
  echo "$h $($C 'md5sum /usr/local/bin/ot-heavy /usr/local/bin/ot-heavy-reconcile /usr/local/lib/ot-heavy/ot-heavy-exit /usr/local/lib/ot-heavy/bin/docker 2>&1 | cut -c1-8 | tr "\n" " "; stat -c %y /usr/local/bin/ot-heavy-reconcile | cut -c1-16; cat /etc/ot-heavy.conf | grep -v "^#" | tr "\n" " "')"
done
echo "== intel2 .git shape"; ls -la ~/OpenTallas | head -3; ls ~/OpenTallas/.git/objects/info/ 2>/dev/null; grep -n 'worktree\|\[remote' ~/OpenTallas/.git/config | head; du -sh ~/OpenTallas/.git/objects ~/OpenTallas/.git/worktrees 2>/dev/null; df -h ~ | tail -1

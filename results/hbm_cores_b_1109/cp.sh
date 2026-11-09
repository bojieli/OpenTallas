cd /srv/opentallas-scratch3/claude/rm48/repo || exit 1
rm -f tools/die_plan/vclk_measured_band.json
timeout 300 git fetch -q origin +refs/heads/main:refs/remotes/origin/main refs/heads/claude/die-hbm-93-mclk-1108 refs/heads/claude/hbm-spb-io-1108 || { echo FETCHFAIL; exit 2; }
[ "$(git rev-parse --short=11 origin/main)" = ed5be48cd49 ] || { echo MAINMOVED $(git rev-parse --short=11 origin/main); exit 3; }
git checkout -q --no-track -B rm54-cp origin/main
for s in adc4b6a6fa44 5e4f9ff6c4f ed94e832957; do
  git cherry-pick -x $s >/dev/null 2>&1 || { echo CONFLICT $s; git status --short | head; git cherry-pick --abort; exit 4; }
  git log -1 --format=%B | git interpret-trailers --if-exists addIfDifferent --trailer "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" | git commit -q --amend -F -
  echo "cp $s -> $(git rev-parse --short=11 HEAD) $(git log -1 --format=%s | cut -c1-70)"
done
git diff --stat origin/main HEAD | cat | cut -c1-90
timeout 200 git push -q origin HEAD:refs/heads/claude/root-merge-54-cp-1108; echo pushrc $?; git rev-parse HEAD

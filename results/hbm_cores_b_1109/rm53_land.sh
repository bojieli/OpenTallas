# rm53_land.sh TIP BASE : ff hub main to TIP under merge.lock, push origin main; no force
# Same as rm52_land.sh except: untracked ARCHIVED.json markers (AUTOCLEAN-7) do not count as dirty.
TIP=$1; BASE=$2; H=/home/ubuntu/OpenTallas
flock -w 120 ~/coord/merge.lock bash -c "
set -e; cd $H
[ \"\$(git rev-parse HEAD)\" = \"$BASE\" ] || { echo HUB-MOVED \$(git rev-parse HEAD); exit 3; }
[ \"\$(git branch --show-current)\" = main ] || { echo NOT-ON-MAIN; exit 3; }
D=\$(git status --porcelain | grep -v '^?? .*/ARCHIVED\.json\$' || true); [ -z \"\$D\" ] || { echo HUB-DIRTY; echo \"\$D\" | head; exit 3; }
OM=\$(git ls-remote origin refs/heads/main | cut -f1); [ \"\$OM\" = \"$BASE\" ] || { echo ORIGIN-MOVED \$OM; exit 3; }
git merge-base --is-ancestor $BASE $TIP || { echo BASE-NOT-ANCESTOR; exit 3; }
if git merge-base --is-ancestor e305445bcb0 $TIP 2>/dev/null; then echo NEVERTAKE; exit 5; fi
git merge -q --ff-only $TIP
timeout 200 git push -q origin main
echo hub \$(git rev-parse HEAD) origin \$(git ls-remote origin refs/heads/main | cut -f1) dirty \$(git status --porcelain | grep -v '^?? .*/ARCHIVED\.json\$' | wc -l)
"

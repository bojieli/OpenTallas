set -e
R=/srv/opentallas-scratch2/claude/kw35/repo
W=/srv/opentallas-scratch2/claude/kw36
mkdir -p $W
cd $R
git fetch -q origin 2>/dev/null || true
if [ ! -d $W/wt ]; then
  git worktree add -q --no-checkout -b claude/kw-fix-36-eco-census-1108 $W/wt origin/main
  git -C $W/wt sparse-checkout init --cone
  git -C $W/wt sparse-checkout set tools physical/common_flow
  git -C $W/wt checkout -q claude/kw-fix-36-eco-census-1108
fi
git -C $W/wt status -sb | head -2
git -C $W/wt log -1 --format='%h %s' | cut -c1-90
du -sh --exclude=.git $W/wt | cut -f1

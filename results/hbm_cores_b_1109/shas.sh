cd /srv/opentallas-scratch2/claude/kw36/wt
git fetch -q origin 2>/dev/null
for s in 9d0db1edc35f64a860d40366854e2418a864bf06 acc55d2b13033f3283522e26280ddc6275b0b8a6 cad9c038fb079605bd4c23f97a84e946d2ab6494 5178ea7aa2797689caf8c40e546e0c89fb7808e1; do
  t=$(git cat-file -t $s 2>&1 | head -1)
  echo "$s type=$t branches=$(git branch -r --contains $s 2>/dev/null | head -3 | tr -d ' ' | tr '\n' ',')"
  if [ "$t" = commit ]; then
    for a in cad9c038fb 9ba1e6f86e2 5178ea7aa2 e210d04c83; do
      git merge-base --is-ancestor $a $s 2>/dev/null && echo "   contains $a" 
    done
    git log -1 --format='   %cd %s' --date=format:'%m-%d %H:%M' $s | cut -c1-120
  fi
done
git cat-file -t e210d04c83 2>&1 | head -1
git log -1 --format='%h %s' origin/main | cut -c1-90

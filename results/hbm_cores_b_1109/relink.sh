APPLY=$1; L=/srv/opentallas-scratch2/claude/kw37/intel1_rowlinks.tsv
mkdir -p "$(dirname $L)"
cwds=$(ls -l /proc/*/cwd 2>/dev/null | sed 's/.* -> //' | sort -u)
ok=0; bad=0
while read -r d; do
  t=${d/\/srv\/opentallas-scratch3\//\/srv\/opentallas-scratch2\/}
  why=""
  [ -L "$d" ] && why="already link"
  [ -z "$why" ] && [ ! -d "$d" ] && why="missing"
  [ -z "$why" ] && [ -e "$t" ] && why="target exists"
  if [ -z "$why" ]; then n=$(find "$d" -mindepth 1 -type f | wc -l); [ "$n" = 0 ] || why="files $n"; fi
  if [ -z "$why" ]; then x=$(find "$d" -mindepth 1 -type d ! -path "$d/logs" | wc -l); [ "$x" = 0 ] || why="subdirs $x"; fi
  [ -z "$why" ] && echo "$cwds" | grep -qF "$d" && why="process cwd"
  if [ -n "$why" ]; then bad=$((bad+1)); echo "SKIP $why $d"; continue; fi
  ok=$((ok+1))
  if [ "$APPLY" = 1 ]; then mkdir -p "$t/logs"; rmdir "$d/logs" 2>/dev/null; rmdir "$d" && ln -s "$t" "$d" && printf '%s\t%s\t%s\n' "$(date '+%F %T')" "$d" "$t" >> $L; fi
done
echo "ok $ok skip $bad apply $APPLY"; df -BG --output=avail /srv/opentallas-scratch2 | tail -1

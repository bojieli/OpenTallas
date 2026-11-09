desc(){ echo $1; for c in $(ps -o pid= --ppid $1); do desc $c; done; }
roots=$(pgrep -f 'rm48_test.sh /srv/opentallas-scratch3/claude/rm48/(repo|base) /srv/opentallas-scratch3/claude/rm54/k_[tb] ')
echo "roots: $roots"
all=""; for r in $roots; do all="$all $(desc $r)"; done
echo "count: $(echo $all | wc -w)"
[ -n "$all" ] && kill -TERM $all 2>/dev/null
sleep 3; left=$(pgrep -f 'rm54/k_[tb]' | wc -l); echo left $left

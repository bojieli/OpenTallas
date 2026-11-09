for i in $(seq 1 40); do
 a=$(ssh -n -o ControlPath=none epyc6 'cd /srv/opentallas-scratch3/claude/die-hbm-94/pdnq011; grep -lE "PROBE" left.log right.log 2>/dev/null | wc -l')
 b=$(ssh -n -o ControlPath=none intel1 'grep -c RC /srv/opentallas-scratch3/claude/die-hbm-94/hostcp/out_fix.txt 2>/dev/null')
 [ "$a" = "2" ] && [ "$b" = "1" ] && { echo DONE; exit 0; }
 sleep 30
done
echo TIMEOUT a=$a b=$b

O=/srv/opentallas-scratch3/claude/rm54; X=$1
cd $O; for x in ${X}_t ${X}_b; do grep -h -E '^(FAILED|ERROR) ' $x/*.log | sed -E 's/ - .*//' | sort -u > f_$x.txt; echo "$x files $(($(wc -l < $x/results.txt)-1)) fails $(wc -l < f_$x.txt) $(awk '{for(i=1;i<=NF;i++) if($i ~ /^passed/) s+=$(i-1)} END{print "passed",s}' $x/results.txt)"; grep -E '^[^ ]+ (124|137) ' $x/results.txt | cut -c1-90; done
echo TIP-ONLY; comm -23 f_${X}_t.txt f_${X}_b.txt | cut -c1-200; echo BASE-ONLY; comm -13 f_${X}_t.txt f_${X}_b.txt | cut -c1-200
awk '$2!=0{print $1}' ${X}_b/results.txt | sort > nz_${X}_b; awk '$2!=0{print $1}' ${X}_t/results.txt | sort > nz_${X}_t; echo TIP-ONLY-RC; comm -13 nz_${X}_b nz_${X}_t

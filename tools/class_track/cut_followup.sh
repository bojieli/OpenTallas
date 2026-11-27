#!/bin/bash
# 21:23 follow-up of the 21:00 cut: confirm the cut wrote CLASS-TREND rows and posted; post CUT-MISSING otherwise; list the CARRIED classes that need hand adjudication.
export PATH=$HOME/.local/bin:/usr/local/bin:$PATH
C=$HOME/coord; LABEL="$1"
n=$(grep -c "^$LABEL" $C/lanes/CLASS-TREND.tsv)
cd $C
if [ "$n" -lt 20 ]; then
  bash bin/post.sh CLASS-TRACK "CUT-MISSING [CLASS-TRACK -> COORD] the $LABEL cut wrote $n CLASS-TREND rows (expected > 60): see ~/coord/../ journalctl --user -u class-track-cut2100 on intel2. Counts in CLASSES.tsv are still the 09:00 values."
else
  carried=$(grep "^$LABEL" lanes/CLASS-TREND.tsv | awk -F'\t' '$9=="CARRIED"{print $2":"$3}' | tr '\n' ' ')
  bash bin/post.sh CLASS-TRACK "STATE [CLASS-TRACK -> COORD] $LABEL follow-up 21:23: cut wrote $n rows. CARRIED (not re-measured, need lane adjudication or a lane-sha count): $(echo $carried | cut -c1-1500)"
fi

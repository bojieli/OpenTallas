#!/bin/bash
B=/srv/opentallas-scratch2/scratch/claude/dsrom-su-softmax-r5
cd $B/src_safe
W=$B/work
P="--lph 16 --lm 9 --la 5 --elm 9 --ela 5 --add6 2 --exp6 1 --expns 2 --denk 1 --margin 1 --safe ${SAFE:-1} --tag $1"
/srv/opentallas-scratch/admit.sh 16 -- python3 -u tools/dsrom_su_softmax.py build --work $W --jobs 16 $P > $W/build_$1.log 2>&1 || { echo "EXIT build" >> $W/run_$1.log; exit 2; }
python3 -u tools/dsrom_su_softmax.py run --work $W $P > $W/run_$1.log 2>&1
echo "EXIT $?" >> $W/run_$1.log

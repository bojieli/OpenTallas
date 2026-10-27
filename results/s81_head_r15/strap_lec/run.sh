#!/bin/bash
D=/srv/opentallas-scratch2/claude/hb4_lec_chunks
cd $D
ls -d c[0-9]* mut_strap | xargs -P 6 -I{} bash -c "docker run --rm -m 6g --name hb4c-{} -v $D:$D -w $D openroad/orfs:latest yosys -q -l $D/{}/yosys.log -s $D/{}/lec.ys > $D/{}/rc.out 2>&1; echo \$? > $D/{}/rc"
echo ALLDONE $(date) > $D/ALLDONE

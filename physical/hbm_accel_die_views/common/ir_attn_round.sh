#!/bin/bash
# ir_attn_round.sh <src> <round dir> [windows]: method-c IR windows with the hfd_attn_tile PDN exception
# (tools/hbm_die_views.py ir-attn) for every r16g IR window that overlaps an attention tile; 4 at a time.
# IMG as die_round.sh; IRX: extra ir-attn args (--quad-pg).  Record: python3 tools/hbm_accel_die_fp.py record --work <round dir> --out <json>.
set -u
SRC=$1; RD=$2
mkdir -p $RD; sed "s|openroad/orfs:asap7lock|${IMG:-openroad/orfs:asap7lock}|" $SRC/tools/hbm_accel_die_run_case.sh > $RD/run_case.sh; chmod +x $RD/run_case.sh; cp $SRC/SOURCE_COMMIT $RD/
cd $SRC
WINS=${3:-$(python3 -c "
import sys;sys.path.insert(0,'tools');import hbm_die_views as V
m,pw,M,r=V.model();t=[i for i in m['insts'] if i.master=='hfd_attn_tile']
print(' '.join(w for w,(a,b,c,d) in V.H.ir_windows(m).items() if any(i.x<c and i.x+i.w>a and i.y<d and i.y+i.h>b for i in t)))")}
for w in $WINS; do python3 tools/hbm_die_views.py ir-attn ${IRX:-} --window $w --work $RD/c_$w > $RD/c_$w.gen.log 2>&1; done
cd $RD
echo $WINS | tr ' ' '\n' | xargs -P 4 -I{} /srv/opentallas-scratch/admit.sh 6 -- ./run_case.sh c_{} run.tcl run.log 4 16
echo ALLDONE > ALLDONE

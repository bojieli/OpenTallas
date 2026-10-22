#!/bin/bash
# HBM-SUFIX coll fork: census --measured, info_banklat_all only, successor 98 + bridge 1 (= rel98 row)
cd /srv/opentallas-scratch/claude/toksim-hbm/src || exit 9
n=$1
PYTHONPATH=tools python3 -c "
import sys
from hgi_sim import toksim_hbm_census_1019 as C
C.ONLY='info_banklat_all'
sys.argv=['x','--out','/srv/opentallas-scratch/claude/toksim-hbm/sufix_coll/$n.json','--measured','/srv/opentallas-scratch/claude/toksim-hbm/sufix_coll/m_$n.json','--bw','98','--bridge','1']
C.main()" > /srv/opentallas-scratch/claude/toksim-hbm/sufix_coll/$n.log 2>&1
echo rc=$? > /srv/opentallas-scratch/claude/toksim-hbm/sufix_coll/$n.rc

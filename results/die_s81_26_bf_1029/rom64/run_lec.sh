#!/bin/bash
# DIE-S81-26 ROM _gb reset64 LEC rerun: kit = ce10-lec/rom_gb/kit + 33 hints (w_cgt[0] loaded-valid guard w_run; g_mac[1] u_l1 q0_wf bit1==bit2 merged aliases). lec.py = die-s81-25/lec.py (main f483150e0)
cd /srv/opentallas-scratch2/claude/die-s81-26/rom64
echo "start $(date -Is)" > run.status
mkdir -p lec_x64
docker run --rm --name ds81-26-rom64 --memory=64g --memory-swap=64g -v /srv/opentallas-scratch2/claude/die-s81-26/rom64/kit:/work:ro -v /srv/opentallas-scratch2/claude/die-s81-26/rom64/lec_x64:/lecout -v /srv/opentallas-scratch2/claude/die-s81-25/lec.py:/lec.py:ro -e HUID=$(id -u) -e HGID=$(id -g) -e OT_LEC_REFINE_S=3600 -e OT_LEC_RESET_CYCLES=64 openroad/orfs:asap7lock bash -lc "python3 -I /lec.py /work --out /lecout --conflicts 1000 --jobs 4 > /lecout/run.log 2>&1; rc=\$?; chown -R \$HUID:\$HGID /lecout; exit \$rc"
echo "lec rc $? $(date -Is)" >> run.status

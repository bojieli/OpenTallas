# usage: rb.sh PLAN OUT MANIFEST
cd /srv/opentallas-scratch2/claude/hbm-bind-4/tip; export PYTHONDONTWRITEBYTECODE=1
O=$2; P=$1; mkdir -p $O
prlimit --as=$((200*1024*1024*1024)) python3 -I tools/die_plan/bind.py bind $P --asbuilt physical/die_plan/hbm/bind/d44v/$3 --out $O --strict --all-gaps > $O.bind.log 2>&1; echo RC $? $(date) > $O.rc

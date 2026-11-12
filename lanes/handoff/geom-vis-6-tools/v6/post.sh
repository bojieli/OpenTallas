#!/bin/bash
# post.sh geom.md queue.md "msg"
G=$1; Q=$2; M=$3
(cat $G; echo "@@Q@@"; cat $Q) | timeout 180 ssh -o ControlPath=none intel2 'cat > /tmp/gv6_all.md && cd ~/coord && sed -n "1,/^@@Q@@$/p" /tmp/gv6_all.md | grep -v "^@@Q@@$" >> lanes/GEOM-REVIEW.md && { sed -n "/^@@Q@@$/,\$p" /tmp/gv6_all.md | grep -v "^@@Q@@$" >> lanes/COORD-REVIEW-QUEUE.md; true; } && bash ~/coord/bin/coord-commit.sh "'"$M"'" lanes/GEOM-REVIEW.md lanes/COORD-REVIEW-QUEUE.md 2>&1|tail -2; git fetch -q origin coord/state; echo origin_vis2=$(git show origin/coord/state:lanes/GEOM-REVIEW.md | grep -c "GEOM-VIS-6 viewed") origin_q=$(git show origin/coord/state:lanes/COORD-REVIEW-QUEUE.md | grep -c "GEOM-VIS-6 ->"); rm -f /tmp/gv6_all.md'

set -eu
# on intel2: private HBM-only count with plan overlay d44v_gqi
W=/srv/opentallas-scratch2/claude/hbm-hard-9; R=$W/repo; C=$W/cnt; P=$W/cnt_tool; mkdir -p $P
git -C $R branch -f main claude/hbm-hard-9-1108
rm -rf $C
git clone -q --shared --no-checkout $R $C
git -C $C fetch -q origin 'refs/heads/main:refs/remotes/origin/main'
cp ~/coord/tools/release_tree_plan.py $P/rtp.py
cd $P
python3 -I - <<PY
import re
s=open('rtp.py').read()
s=s.replace("REPO = pathlib.Path('/home/ubuntu/OpenTallas')","REPO = pathlib.Path('$C')")
s=s.replace("CACHE = pathlib.Path.home() / '.local/state/fleet-viz/release_tree_plan_cache.json'","CACHE = pathlib.Path('$P/cache.json')")
s=s.replace("_HBM_POR + 'd44v_epm/die_plan.json.gz'","_HBM_POR + 'd44v_gqi/die_plan.json.gz'")
s=s.replace("('d35a', 'd35b', 'd35c', 'd44v', 'd44v_epm'))","('d35a', 'd35b', 'd35c', 'd44v', 'd44v_epm', 'd44v_gqi'))")
open('rtp.py','w').write(s)
PY
grep -n "d44v_gqi\|^REPO\|^CACHE" rtp.py | cut -c1-160
nohup python3 -I rtp.py --force --print > run.out 2> run.err &
echo started

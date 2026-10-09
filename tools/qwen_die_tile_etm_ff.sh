#!/bin/bash
# Qwen ROM die: replace the ASSUMED qfd_tile / qfd_tile_e constant views with the ETM of a CLOSED ROM-pipe TT route,
# then rerun the die FF hold STA (GRT parasitics, r21 overflow-0 checkpoint, the dietop_r21/sta_v3_ff recipe).
# Why: the die FF hold WNS -5.64 ps sits entirely on the assumed tile views (qwen-dietop.log 22:06 PT); every
# characterised view holds.  Detached waiter, runs on the closure-loop controller (job JSONs are local):
#   setsid nohup bash tools/qwen_die_tile_etm_ff.sh > $LOGDIR/tile_etm_ff.out 2>&1 < /dev/null &
# Steps once a qfd_tile candidate is CLOSED (qfd_tile_e is bound too if one of its candidates is CLOSED by then):
#   1. on the job host: export_view.py (main's tools/w18) on the routed ORFS dir, corners ss,tt,ff, from a tree
#      holding only the sign-off SDC + macros (the docker mount is the tree);
#   2. copy the ETM libs to EPYC3 dietop_r21/tile_etm_<job>/;
#   3. EPYC3: sta_tile_ff = sta_v3_ff libs with the tile cells removed from qfd_elements_ff.lib + the ETM libs read
#      after them; dietop_run.sh grt_ff.tcl; qwen_die_sta_classes.py -> classes.json.
set -u
JOBS=${JOBS:-$HOME/.local/state/closure_loop/jobs}
DIE_HOST=${DIE_HOST:-ot-epyc3}
DIE=${DIE:-/srv/opentallas-scratch/claude/qwen-die-r20/dietop_r21}
TOOLS=$(cd "$(dirname "$0")" && pwd)
POLL=${POLL:-600}
TILE=${TILE:-"qfd_tile_rp1-c834fcfebmm-tt qfd_tile_rp2-c834fcfebmm-tt qfd_tile_rp2s330-f6e3d8cad-tt qfd_tile_rp1-3d5ad2a4ftt qfd_tile_rp2n-3d5ad2a4ftt"}
TILE_E=${TILE_E:-"qfd_tile_e_rp1-c834fcfebmm-tt qfd_tile_e_rp2-c834fcfebmm-tt qfd_tile_e_rp2s330-f6e3d8cad-tt qfd_tile_e_rp1-3d5ad2a4ftt qfd_tile_e_rp2n-3d5ad2a4ftt"}
say() { echo "$(date -Is) $*"; }
field() { python3 -c "import json,sys;j=json.load(open('$JOBS/$1.json'));print(eval(sys.argv[1]))" "$2"; }
closed() { for n in $1; do [ -f $JOBS/$n.json ] && [ "$(field $n "j['status']")" = CLOSED ] && { echo $n; return 0; }; done; return 1; }

say "waiting for a CLOSED qfd_tile ROM-pipe TT route among: $TILE"
until T=$(closed "$TILE"); do sleep $POLL; done
TE=$(closed "$TILE_E" || true)
say "CLOSED: qfd_tile <- $T; qfd_tile_e <- ${TE:-none (stays assumed)}"

export_one() {   # job -> echoes the ETM dir on $DIE_HOST
  local n=$1 H R L B SDC MAC
  H=$(field $n "j['host']"); R=$(field $n "j['run']"); L=$(field $n "j['name']" | tr -c 'A-Za-z0-9_\n' _)
  B=$(field $n "j['spec']['block']"); SDC=$(field $n "' '.join(j['spec']['verdict'].get('post_sdc',[]))")
  MAC=$(field $n "' '.join(j['spec']['verdict'].get('macros',[]))")
  local W=$R/etm_gapsflow
  ssh $H "mkdir -p $W/tree/tools/w18 $W/out" >&2
  scp -q $TOOLS/w18/export_view.py $TOOLS/w18/corner_sta.py $H:$W/tree/tools/w18/ >&2
  ssh $H "set -e; cd $R/src; for p in $SDC $MAC; do mkdir -p $W/tree/\$(dirname \$p); cp -r \$p $W/tree/\$(dirname \$p)/; done
    O=\$(ls -d $R/routes/$L/work/orfs | head -1)
    cd $W/tree && python3 tools/w18/export_view.py --orfs-dir \$O --name $B --post-sdc $(echo $SDC | cut -d' ' -f1) \
      $(for m in $MAC; do echo -n " --macro $m"; done) --corners ss,tt,ff --out $W/out > $W/export.out 2>&1
    grep -c OT_EXPORT_DONE $W/out/export_*.log" >&2 || { say "EXPORT FAILED $n ($H:$W)" >&2; return 1; }
  local D=$DIE/tile_etm_$L
  ssh $DIE_HOST "mkdir -p $D" >&2
  scp -q -3 $H:$W/out/${B}_ss.lib $H:$W/out/${B}_tt.lib $H:$W/out/${B}_ff.lib $H:$W/out/export.json $DIE_HOST:$D/ >&2 || return 1
  echo "$B $D"
}

BIND=$(export_one $T) || exit 1
[ -n "${TE:-}" ] && { BE=$(export_one $TE) && BIND="$BIND
$BE" || say "qfd_tile_e export failed: stays assumed"; }
say "ETMs: $(echo $BIND | tr '\n' ' ')"

S=$DIE/sta_tile_ff
ssh $DIE_HOST "set -e; cd $DIE; mkdir -p $S/libs; cp sta_v3_ff/libs/* $S/libs/; ln -f sta_v3_ff/ckpt_grt.odb sta_v3_ff/route.guide $S/
  cp sta_v3_ff/grt_ff.tcl $S/
  echo '$BIND' | while read b d; do [ -n \"\$b\" ] || continue
    cp \$d/\${b}_ff.lib $S/libs/etm_\${b}_ff.lib
    python3 - $S/libs/qfd_elements_ff.lib \$b <<'PY'
import re, sys
p, b = sys.argv[1], sys.argv[2]
t = open(p).read()
t2 = re.sub(r'\n  cell \(' + re.escape(b) + r'\) \{.*?\n  \}(?=\n)', '', t, flags=re.S)
assert t2 != t, b
open(p, 'w').write(t2)
PY
    sed -i \"s#^read_liberty /work/libs/ot_hbm3e_phy_ff.lib#&\nread_liberty /work/libs/etm_\${b}_ff.lib#\" $S/grt_ff.tcl
    python3 - $S/libs/views.json \$b \$d <<'PY'
import json, sys
p, b, d = sys.argv[1:]
v = json.load(open(p))
v['assumed_constants'] = [m for m in v['assumed_constants'] if m != b]
v.setdefault('etm_bound', {})[b] = f'routed CLOSED TT route ETM (write_timing_model FF, {d})'
json.dump(v, open(p, 'w'), indent=1)
PY
  done
  grep -n etm_ $S/grt_ff.tcl
  ./dietop_run.sh $S grt_ff.tcl 8 250
  python3 qwen_die_sta_classes.py $S/grt_ff_ends.rpt die.v $S/libs/views.json --out $S/classes.json > /dev/null || true
  grep -E 'tns|wns|worst' $S/grt_ff.log | tail -4"
say "die FF STA done: $DIE_HOST:$S (grt_ff.log, classes.json)"

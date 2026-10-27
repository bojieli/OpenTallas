#!/bin/bash
# TOK-DS-9 (10-27, COORD ruling TOK-DS-8): regenerate the S81 layer-compile vehicle (dv_layer_compile --die-src tree) from
# the CURRENT main die top instead of the stale tree_fc31 die.v (cap30 gen-main 64d4be88 + frame-chain reset 35ba1ef7).
# The fc31 die.v does not strict-bind to current RTL (8 mismatches, tokds8_1027/cut_rebuild/blocker.json) because main
# moved the die top on through the S81 PORTFIX/IDXNET/face-bind rewrites (eng cfg_* -> CTL boot op, sticky faults ->
# ot_s81_frs rings, svc_rs face variants, TP lep end slices, cfg/hb/so status ports dropped).  main holds the result as
# physical/die_plan/s81/bind/inputs/die_b178.v (module dv_die, dv_bind format); the rewrite scripts themselves are not on
# main.  The vehicle is therefore built from that file, never by editing RTL or by patching the old die.v:
#   1. structural identity vs the cap30 p4l plan/land the compiler reads: every landing ld_<link> (master + K strap) and
#      every relay station st_<link>_<k> of die_b178.v must equal the fc31 vehicle (same plan origin), else exit 3
#   2. mk_tree.py --die-v die_b178.v --plan p4l/plan.json --land land_plan.json -> <out>/tree_b178
#   3. (caller) strict tools/die_port_bind.py of that die.v over the 877 manifest = prep_cuts_current.sh <wt> <out>/tree_b178
# Usage: mk_vehicle_current.sh <worktree> <fc31 tree (plan/land source)> <out>
set -u
W=$(realpath $1); T0=$(realpath $2); O=$(realpath -m $3)
D=$W/physical/die_plan/s81/bind/inputs/die_b178.v
B0=$T0/results/arch/s81_dv_1016
mkdir -p $O
cd $W
git rev-parse HEAD > $O/source_sha.txt
python3 - "$D" "$B0/bind9/die.v.gz" > $O/identity.json <<"PY" || { echo "IDENTITY FAIL"; exit 3; }
import gzip, json, re, sys
LD = re.compile(r"^\s*(dsfd_dvland\w*)\s+ld_(\w+)\s*\(.*\.k\(([^)]*)\)")
ST = re.compile(r"^\s*(dsfd_dvrlyh?\w*)\s+st_(\w+)\s*\(")
def scan(text):
    ld, st = {}, set()
    for line in text.splitlines():
        m = LD.match(line)
        if m:
            ld[m.group(2)] = [m.group(1), m.group(3)]
        m = ST.match(line)
        if m:
            st.add((m.group(1), m.group(2)))
    return ld, st
new = scan(open(sys.argv[1]).read())
old = scan(gzip.decompress(open(sys.argv[2], "rb").read()).decode())
r = dict(landings=len(new[0]), landings_old=len(old[0]),
         landing_diff=sorted(set(map(str, new[0].items())) ^ set(map(str, old[0].items())))[:20],
         stations=len(new[1]), stations_old=len(old[1]), station_diff=sorted(map(str, new[1] ^ old[1]))[:20])
r["pass"] = not r["landing_diff"] and not r["station_diff"] and r["landings"] > 0
print(json.dumps(r, indent=1))
sys.exit(0 if r["pass"] else 3)
PY
python3 tools/s81_dv/tokfunc/mk_tree.py --die-v $D --plan $B0/p4l/plan.json --land $B0/landing/p4l/land_plan.json \
  --out $O/tree_b178 --tag b178 || exit 4
echo VEHICLE_DONE $O/tree_b178

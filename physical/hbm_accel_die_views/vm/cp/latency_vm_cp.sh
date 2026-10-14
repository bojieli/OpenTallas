#!/bin/bash
# latency_vm_cp.sh <out dir> [verilator]: per-operation cycle cost of the channel-plan VM (hfd_vm_cp) against the
# monolithic hfd_vm, end to end at the die pins (tb_vm_cp.sv MODE 1, VM_DBG prints the start time of every op of both
# environments; the two run the SAME operation list, so the difference of the op-to-op spans is the added latency).
O=${1:?}; VL=${2:-verilator}; mkdir -p $O; V=physical/hbm_accel_die_views; T=$V/vm/tiles; C=$V/vm/cp
SR1=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
BASE="$V/common/ot_hfd_oreg1.sv rtl/common/ot_fwd_link_stage.sv $SR1 $V/vm/rtl/ot_hbm_die_vm_multicast_root.sv $V/vm/rtl/hfd_vm.sv $T/ot_hfd_vm_slice.sv $T/ot_hfd_vm_root_x.sv"
[ -f $T/ot_hfd_vm_root_p.sv ] && BASE="$BASE $T/ot_hfd_vm_root_p.sv"   # absent before FACE3 (old root baseline)
TILES=$(ls $C/rtl/vm_cp_*.sv | tr '\n' ' ')
$VL -I$C -I$T --binary --timing -j 16 --unroll-count 8192 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-initial unique --top-module tb_vm_tiles -DMODE=1 -DSEED=3 -DVM_DBG=1 -Mdir $O/lat.obj -o sim $BASE $TILES $C/hfd_vm_cp.sv $C/tb_vm_cp.sv > $O/lat.build 2>&1 || { echo LAT_BUILD_FAILED; exit 2; }
(cd $O && ./lat.obj/sim > lat.log 2>&1); grep VM_TILES $O/lat.log
python3 - $O/lat.log <<'PY'
import re, sys
ev = {}
for l in open(sys.argv[1]):
    m = re.match(r'(\S+) (OP|WR|RD) k=(\d+).*?(?:t=(\d+))?$', l.strip())
    if not m: continue
    env = m.group(1).split('.')[-1] if '.' in m.group(1) else m.group(1)
    d = ev.setdefault(env, {}).setdefault(int(m.group(3)), {})
    if m.group(2) == 'OP': d['t'] = int(m.group(4))
    else: d.setdefault('kind', m.group(2))
envs = sorted(ev)
assert len(envs) == 2, envs
a, b = (ev[e] for e in envs)
res = {'WR': [], 'RD': []}
ks = sorted(set(a) & set(b))
for k in ks[:-1]:
    if k + 1 in a and k + 1 in b and 'kind' in a[k]:
        res[a[k]['kind']].append(((a[k + 1]['t'] - a[k]['t']) // 1000, (b[k + 1]['t'] - b[k]['t']) // 1000))
for kind, v in res.items():
    if v:
        d = [y - x for x, y in v]
        print(f"VM_CP_LATENCY {kind}: ops {len(v)} monolithic span {min(x for x, _ in v)}..{max(x for x, _ in v)} cycles, "
              f"channel plan {min(y for _, y in v)}..{max(y for _, y in v)}, added {min(d)}..{max(d)} (mean {sum(d) / len(d):.2f})")
PY

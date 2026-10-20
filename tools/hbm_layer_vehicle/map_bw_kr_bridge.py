#!/usr/bin/env python3
"""Standalone ASAP7 TT mapping/census; no physical qualification."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
baseline = '--baseline' in sys.argv[2:]
sources = ['rtl/hbm_accel/loader/service_native/ot_hbm_svc_kr_ready_bridge.sv',
           'rtl/hbm_accel/loader/service_native/ot_hbm_svc_ring_bw_safe.sv']
if baseline:
    sources[0] = 'rtl/test/hbm_accel/bw_ring_control/ref_ot_hbm_svc_kr_ready_bridge_80d.sv'
lib = '/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/'
libs = [lib+n for n in ['asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz',
    'asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz',
    'asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz',
    'asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib',
    'asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz']]
ys = ['read_verilog -sv '+' '.join('/src/'+s for s in sources)]
if not baseline:
    ys += ['chparam -set REGIONAL_VALID 1 ot_hbm_svc_kr_ready_bridge']
ys += ['hierarchy -top ot_hbm_svc_kr_ready_bridge',
      'tcl /src/physical/common_flow/ot_keep_regs.tcl',
      'synth -flatten -top ot_hbm_svc_kr_ready_bridge -noabc',
      'dffunmap', 'dfflibmap -liberty '+libs[3],
      'abc '+' '.join('-liberty '+s for s in libs)+' -D 1024',
      'clean', 'write_verilog -noattr /work/mapped.v', 'stat']
(out/'map.ys').write_text('\n'.join(ys)+'\n')
cmd = ['docker', 'run', '--rm', '-v', str(root)+':/src:ro', '-v', str(out)+':/work',
       'openroad/orfs:latest', 'bash', '-lc',
       'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1\nyosys -s /work/map.ys']
with (out/'map.log').open('w') as f:
    subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, check=True)
sys.path.insert(0, str(root/'tools'))
import textbook_lint as T
netlist = out/'mapped.v'
g, _ = T.flatten(T.parse_verilog(netlist.read_text()), 'ot_hbm_svc_kr_ready_bridge')
a = T.build(g, None)
clks, _ = T.clock_nets(g, a)
rows = []
for x, (ci, pin) in a['driver'].items():
    if x <= 3 or x in clks or (ci >= 0 and a['kind'][ci] in ('buf', 'tie')):
        continue
    total, ff, _ = T.bufinv_fanout(g, a, x, clks)
    rows.append(dict(label=T.net_label(g, a, x), loads=total, ff_loads=ff,
                     reset=T.is_reset_net(T.net_label(g, a, x), g.net_name[x], T.THRESHOLDS, port=ci<0)))
rows.sort(key=lambda r: -r['loads'])
bad = [r for r in rows if r['loads'] > 32 and not r['reset']]
receipt = dict(schema='opentallas.bw_kr_bridge_map.v1', verdict='PASS' if not bad else 'FAIL', baseline=baseline,
               source_sha256={s: hashlib.sha256((root/s).read_bytes()).hexdigest() for s in sources+['physical/common_flow/ot_keep_regs.tcl']},
               netlist_sha256=hashlib.sha256(netlist.read_bytes()).hexdigest(),
               ff_count=sum(k == 'ff' for k in a['kind']),
               nonreset_gt32=bad, reset_gt32=[r for r in rows if r['loads']>32 and r['reset']],
               max_nonreset_loads=max([r['loads'] for r in rows if not r['reset']] or [0]),
               scope='Standalone mapped fanout only; reset landing, clock, geometry and TT/FF timing remain open.', roots=rows)
(out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps({k: v for k, v in receipt.items() if k != 'roots'}))
raise SystemExit(bool(bad))

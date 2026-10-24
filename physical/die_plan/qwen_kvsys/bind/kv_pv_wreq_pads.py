#!/usr/bin/env python3
"""KV-TOK 10-24: the PV W request-lane pads on a bound KV top (KV-P7 boot item: kv41 lacks them).

Rule (KV-P6/KV-P7 boot compile, kv_boot_v36.py prep -> vport_dq_pads.json): a V port whose DQ = RL - (4 + W + RT) exceeds
the qkd_pv16_vport_b bound 15 gets (DQ - 15) register stages on its W request lane pvw_<p>__u_ctl.req_t/req_valid ->
vport pr_t/pr_valid (15 b); RL (the longest port) is unchanged, and the boot image already programs DQ = 15 on those ports.
The pad is the bind's own INNER-delay cell ot_dp_dly (reset-less, as every bound intra-partition transport stage), placed
in the V port's partition between the landed lane register (i_pvw__u_ctl_req_*_q slice) and the port pins.

Why a post-bind edit and not bind.py land_r8_extra: the as-built netlist the KV recipe binds against
(binder2-1023/kv_bound/die_bound.v) was lost with the 10-23 hosts; the edit adds only delay stages on one leaf-input
connection per port (no connectivity change), exactly what an INNER re-depth of the bind emits.

    kv_pv_wreq_pads.py SRC_RTL_DIR VPORT_DQ_PADS.json OUT_RTL_DIR      (OUT gets copies of the changed partition files)
"""
import json, re, shutil, sys
from pathlib import Path

src, padf, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
pads = {k: v for k, v in json.load(open(padf))['pad_stages'].items() if v > 0}
out.mkdir(parents=True, exist_ok=True)
done, flops, rec = {}, 0, []
for f in sorted(src.glob('kv3_*.sv')):
    t = f.read_text()
    changed = False
    for vp, d in sorted(pads.items()):
        m = re.search(rf'// as-built {vp}\n(\s*)qkd_pv16_vport_b\s*#\((?:[^()]|\([^()]*\))*\)\s*(\w+)\s*\((.*?)\n\s*\);', t, re.S)
        if not m:
            continue
        ind, inst, body = m.group(1), m.group(2), m.group(3)
        mt = re.search(r'\.pr_t\(([^()]*)\)', body); mv = re.search(r'\.pr_valid\(([^()]*)\)', body)
        assert mt and mv, (f, vp)
        w = f'wq_{inst}_pr'
        cell = (f'{ind}// KV-TOK 10-24 PV W request-lane pad: {vp} DQ unpadded {d + 15} -> 15, {d} stages x 15 b\n'
                f'{ind}wire [14:0] {w};\n'
                f'{ind}ot_dp_dly #(.W(15), .D({d})) u_wq_{inst} (.clk(clk), .d({{{mv.group(1)}, {mt.group(1)}}}), .q({w}));\n')
        body2 = body.replace(mt.group(0), f'.pr_t({w}[13:0])').replace(mv.group(0), f'.pr_valid({w}[14])')
        new = cell[len(ind):] + ind + m.group(0).replace(body, body2)   # the match starts after the comment's indent
        t = t[:m.start()] + new + t[m.end():]
        done[vp] = (f.name, inst, d); flops += 15 * d; changed = True
        rec.append(dict(vport=vp, file=f.name, inst=inst, stages=d, pr_t=mt.group(1), pr_valid=mv.group(1)))
    if changed:
        (out / f.name).write_text(t)
miss = sorted(set(pads) - set(done))
json.dump(dict(rule='pad (DQ - 15) stages on the vport W request lane (pr_valid, pr_t) = ot_dp_dly W 15', source=str(padf),
               pads=rec, pad_flops=flops, missing=miss), open(out / 'wreq_pads.json', 'w'), indent=1)
print(f'padded {len(done)} ports, {flops} flops, files {sorted({v[0] for v in done.values()})}, missing {miss}')
sys.exit(1 if miss else 0)

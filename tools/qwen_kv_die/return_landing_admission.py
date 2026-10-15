#!/usr/bin/env python3
"""Compile ring-lifetime bounds from frozen, source-pinned reservation fixtures.

This is a capacity analysis, not a PHY or RTL qualification. CORE edge indices
match tb_static_return_full128 (4749ff96e). Landing input capture/write and
rowctl/request-hop/PC capture/check each add three edges, so they cancel in the
bounds. A get must follow its put; a simultaneous overwrite/get is legal.
"""
import argparse
import hashlib
import io
import json
import subprocess
import tarfile

ROOT = 'results/rtl/qwen_static_kv_1015/full128_return/true_host_dual_clock/fixtures'
CORE_FS = 833334
HBM_FS = 1024000


def core_slots(lines, phase):
    reserved = [i for i, line in enumerate(lines.splitlines()) if line.split()[0] == '1']
    if len(reserved) != 512:
        raise ValueError(f'expected 512 KV reservations, got {len(reserved)}')
    # t0 HBM posedge is 16.5 periods. Predictor delay32, publication1,
    # two CORE synchronizer edges. ceil gives expected_put pin edge index.
    first = phase * 1000 + CORE_FS // 2
    return [((33 + 2 * (t + 33)) * HBM_FS // 2 + 2 * CORE_FS - first + CORE_FS - 1) // CORE_FS
            for t in reserved]


def bounds(slots, kind):
    start = 0 if kind == 'K' else 256
    offsets = list(range(256)) if kind == 'K' else [256 * (i // 16) + 8 * (i % 16) for i in range(256)]
    # CDC ring actual output is one edge after expected_put. Landing SRAM
    # write is another two edges; source request SRAM check is three edges.
    low = max(slots[start + i] + 1 - offsets[i] for i in range(256))
    high = min((slots[start + i + 128] - offsets[i] for i in range(256)
                if start + i + 128 < len(slots)), default=None)
    return low, high


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--revision', default='c1b3073f4')
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    archive = subprocess.check_output(['git', 'archive', args.revision, ROOT])
    fixtures = {}
    hashes = {}
    with tarfile.open(fileobj=io.BytesIO(archive)) as tf:
        for item in tf:
            if not item.isfile() or not item.name.endswith('.mem'):
                continue
            raw = tf.extractfile(item).read()
            fixtures[item.name] = raw.decode()
            hashes[item.name] = hashlib.sha256(raw).hexdigest()
    rows = []
    for phase in (137, 637):
        for stack in range(4):
            for group in range(8):
                channels = [core_slots(fixtures[f'{ROOT}/p{phase}/pc{pc:02d}_stack{stack}.mem'], phase)
                            for pc in (group + 8 * q for q in range(4))]
                for kind in ('K', 'V'):
                    bb = [bounds(slots, kind) for slots in channels]
                    lo = max(b[0] for b in bb)
                    hi = min(b[1] for b in bb if b[1] is not None)
                    rows.append(dict(phase_ps=phase, stack=stack, group=group, kind=kind,
                                     first_request_min_core=lo, first_request_max_core=hi,
                                     feasible=lo <= hi, slack_core_edges=hi - lo))
    out = dict(scope='ANALYTICAL_CAPACITY_ONLY; frozen full128 component fixtures, not production schedule',
               fixture_revision=args.revision, fixture_sha256=hashes,
               calendar_source='4749ff96e', quarter_pc_mapping='logical PC = group + 8*quarter; physical slots permute GROUP_ORDER', landing_source='qkd_static_kv_landing_physical_grp: seven edges',
               assumptions=['source-bound nominal common leaf phase; physical insertion unqualified',
                            'K group II1; V group 16 requests spaced8, next burst256',
                            'no scheduling from actual return valid or readiness'],
               groups=rows, infeasible_groups=sum(not r['feasible'] for r in rows))
    with open(args.output, 'w') as f:
        json.dump(out, f, indent=2)
        f.write('\n')
    print(json.dumps(dict(groups=len(rows), infeasible_groups=out['infeasible_groups'],
                          K_slack=min(r['slack_core_edges'] for r in rows if r['kind']=='K'),
                          V_slack=min(r['slack_core_edges'] for r in rows if r['kind']=='V'))))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""hbm-forks (2026-10-09): the hbm-sim CONFORMANCE vectors (results/arch/hgi_sim_20261009/conformance, HGI-1 1.0
owner-approved encoding) on the RTL sequencer ot_hgi_seq.

1. Header / descriptor layout: every record of every vector that carries records (`records_hex`) is decoded with the
   sequencer contract's field tables (tools/hgi_seq_vectors.py = hbm_generic_iface D_UOP_FIELDS / D_MDESC_FIELDS) and
   compared field for field with the vector's own `records` (unit, op, param, imm_a, imm_b, wait, pred, slot, tmpl,
   every descriptor field).
2. Sequencer run: each vector's image is executed by the reference model (die 0's rank, VM from dies[0].vm_in,
   the vector's cfg and doorbell); its completion status must equal the vector's `expect.status` whenever the status is
   decided by the CP (0 / 3 from the record stream); vectors whose expected status comes from a UNIT (1: a unit fault,
   or a unit's own operand-decode refusal) are run for their dispatch trace only and listed.
3. Bench files (tag _conf) for rtl/hbm_accel/generic/tb/tb_hgi_seq.sv +define+SEQ_CONF: the RTL dispatch trace and
   completion must equal the reference on every vector.
  python3 tools/hgi_seq_conformance.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hgi_seq_vectors as SV  # noqa: E402

CONF = ROOT / 'results/arch/hgi_sim_20261009/conformance'
T = ROOT / 'rtl/hbm_accel/generic/tb'
UNIT_DOMAIN = {'coll_row_gather_unwritten_faults': 'COLL unit fault (status 1)',
               'topk_nan_fails_closed': 'IDX unit fails closed (status 1)',
               'qdq_fp4_e4m3_block32_undefined': 'FUSED QDQ block-size decode (unit operand refusal; Codex QDQ decoder)',
               'idxd_out_of_range_faults': 'HBM region check: the simulator faults an access outside every placed HBM '
                                           'region (Hbm.find); the CP holds no region table (it checks the 40-bit range '
                                           'only) -> SPEC GAP reported: who bounds an indexed id (a per-descriptor '
                                           'limit, or the svc / unit address check)'}
SPACE = {v: k for k, v in SV.SPACE.items()}
FMTN = {v: k for k, v in SV.FMT.items()}


def check_fields(words, recs):
    """decode the image with the sequencer's tables; compare with the vector's records; returns mismatches"""
    bad, i = [], 0
    for r in recs:
        h = words[i]
        f = {k: SV.field(h, SV.UOP, k) for k in ('unit', 'op', 'param', 'imm_a', 'imm_b', 'wait', 'pred', 'slot', 'tmpl', 'opnd')}
        u = SV.UNITS[f['unit']]
        exp = dict(unit=r['unit'], op=r['op'], param=r['param'], imm_a=r['imm_a'] & 0xFFFFFFFF, imm_b=r['imm_b'] & 0xFFFFFFFF,
                   wait=r['wait'], pred=r['pred'], slot=r['slot'], tmpl=int(bool(r['tmpl'])))
        got = dict(unit=u, op=SV.OPS[u][f['op']] if u in SV.OPS and f['op'] < len(SV.OPS[u]) else f['op'],
                   param=f['param'], imm_a=f['imm_a'], imm_b=f['imm_b'], wait=f['wait'],
                   pred=['ALWAYS', 'POS0', 'NOT_POS0', 'LAST_ITER'][f['pred']], slot=f['slot'], tmpl=f['tmpl'])
        for k in exp:
            if exp[k] != got[k]:
                bad.append(f"rec {i}: {k} {got[k]} != {exp[k]}")
        k = i + 1 + 2 * f['tmpl']
        for j, nm in enumerate(SV.OPND):
            present = bool(f['opnd'] >> j & 1)
            if present != (nm in r['desc']):
                bad.append(f"rec {i}: operand {nm} presence {present}")
            if not present:
                continue
            d = words[k] | (words[k + 1] << 128)
            k += 2
            e = r['desc'][nm]
            for fld in ('base', 'n', 'm', 'stride', 'istride', 'lstride', 'dyn_sel', 'dyn_mul', 'n_sel', 'l1stride',
                        'ibcast', 'indexed'):
                v = SV.field(d, SV.MD, fld)
                ev = e[fld] & ((1 << SV.MD[fld][1]) - 1)
                if v != ev:
                    bad.append(f"rec {i} {nm}.{fld} {v} != {ev}")
            if SPACE[SV.field(d, SV.MD, 'space')] != e['space'] or \
                    FMTN[SV.field(d, SV.MD, 'fmt')].replace('FP8E4M3', 'FP8').replace('FP4E2M1', 'FP4') != \
                    e['fmt'].replace('FP8E4M3', 'FP8').replace('FP4E2M1', 'FP4'):
                bad.append(f"rec {i} {nm} space/fmt")
        i = k
    return bad


def main():
    words, cases, exp_lines, vmi, rows = [], [], [], [], []
    for f in sorted(CONF.glob('cf-*.json')):
        v = json.loads(f.read_text())
        if 'records_hex' not in v:
            rows.append(dict(id=v.get('id', f.stem), row=v.get('row'), sequencer='config-path vector (CF-0: tb_hgi_cmdproc)'))
            continue
        img = []
        for rh in v['record_hex']:
            x = int(rh, 16).to_bytes(len(rh) // 2, 'big')[::-1] if False else bytes.fromhex(rh)
            for q in range(0, len(x), 16):
                img.append(int.from_bytes(x[q:q + 16], 'little'))
        bad = check_fields(img, v['records'])
        entry = len(words)
        words += img
        die = v['dies'][0]
        vm = {}
        for base, hexs in die['vm_in']:
            b = bytes.fromhex(hexs)
            for q in range(0, len(b), 4):
                vm[base + q // 4] = int.from_bytes(b[q:q + 4], 'little')
        cfg = v['cfg']
        ref = SV.Ref(words, entry, v['doorbell']['token'], v['doorbell']['pos'], die.get('rank', 0), cfg['cp_vocab'],
                     cfg['cp_ctx_max'], vm)
        tr, cpl = ref.run()
        want = v['expect'].get('status')
        dom = UNIT_DOMAIN.get(v['id'])
        ok = (cpl[1] == want) if dom is None else True
        rows.append(dict(id=v['id'], row=v['row'], records=len(v['records']), fields_ok=not bad, field_mismatches=bad[:4],
                         ref_status=cpl[1], expect_status=want, status_ok=ok, unit_domain=dom, dispatches=len(tr),
                         fault=getattr(ref, 'fault', None)))
        first = len(exp_lines) // 11
        for d in tr:
            mw = d['unit'] | d['L'] << 4 | d['L1'] << 20 | (d['pos1'] & SV.M21) << 36 | (d['pslot1'] & SV.M21) << 57
            exp_lines += [mw, d['hdr'], d['sut']] + d['eff'] + [sum((n & SV.M21) << (21 * j) for j, n in enumerate(d['n']))]
        ci = len(cases)
        cases.append((entry, v['doorbell']['token'], v['doorbell']['pos'], die.get('rank', 0), cfg['cp_vocab'],
                      cfg['cp_ctx_max'], len(tr), cpl[0], cpl[1], 0xFFFF, first, 0))
        vmi += [(ci, a, x) for a, x in sorted(vm.items())]
    mds = []
    for c in cases:
        mds += SV.G.d_pack(dict(magic=SV.G.MAGIC, ver_minor=SV.G.D_VERSION[1], ver_major=SV.G.D_VERSION[0],
                                n_words=SV.G.NWORDS, cp_vocab=c[4], cp_ctx_max=c[5],
                                coll_group_size=96 if c[4] == 129280 else 4, entry_ar=c[0], image_base=0x10, image_pages=1))
    (T / 'hgi_seq_md_conf.mem').write_text('\n'.join(f'{x:08X}' for x in mds) + '\n')
    (T / 'hgi_seq_image_conf.mem').write_text('\n'.join(f'{w:032X}' for w in words) + '\n')
    (T / 'hgi_seq_expect_conf.mem').write_text('\n'.join(f'{x:064X}' for x in exp_lines) + '\n')
    (T / 'hgi_seq_cfg_conf.mem').write_text('\n'.join(' '.join(f'{x:08X}' for x in c) for c in cases) + '\n')
    (T / 'hgi_seq_vmi_conf.mem').write_text('\n'.join(f'{c:08X}{a:08X}{x:08X}' for c, a, x in vmi) + '\n')
    (T / 'hgi_seq_sizes_conf.svh').write_text('// GENERATED by tools/hgi_seq_conformance.py\n' + '\n'.join(
        f'localparam integer {k} = {v};' for k, v in dict(CONF_NW=len(words), CONF_NCASE=len(cases),
                                                        CONF_NEXP=max(11, len(exp_lines)), CONF_NVMI=max(1, len(vmi))).items()) + '\n')
    rec = dict(schema='opentallas.hbm_forks.hgi_seq_conformance.v1', vectors=str(CONF.relative_to(ROOT)),
               total=len(rows), with_records=len(cases),
               fields_ok=sum(1 for r in rows if r.get('fields_ok')), status_ok=sum(1 for r in rows if r.get('status_ok')),
               rows=rows)
    (T / 'hgi_seq_conformance.json').write_text(json.dumps(rec, indent=1) + '\n')
    bad = [r for r in rows if 'fields_ok' in r and (not r['fields_ok'] or not r['status_ok'])]
    print(f"{len(rows)} vectors, {len(cases)} with records; fields OK {rec['fields_ok']}, status OK {rec['status_ok']}; "
          f"{len(exp_lines) // 11} dispatches; problems {len(bad)}")
    for r in bad:
        print(' ', r)
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())

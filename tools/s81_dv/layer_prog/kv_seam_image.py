#!/usr/bin/env python3
"""Compiled SUKV programme images for the t2 A|B seam bench (tb_s81sl_kv_prog_timed), new dates and old-dates mutants.

The jobs are scheduled by kv_program_builder.build and encoded by lower_kv.lower (the production code), for the
CP -> GK/CN -> GK/IK -> GK/KV chain of the L14 SUKV fixture.  Nothing in the bench waits for done: every command, input
row commit and output read happens on its compiled date.  TEST_ONLY inputs: ctl path (9 edges), input producer ready
dates.  They are the compiler dates of a component programme, not a token calendar.

  kv_seam_image.py --seam 2 2 --vp-sr 0 --out DIR          image.txt + program.json per variant in DIR/<variant>/
Variants: new; old (every kind at the uncut dates); old_<KIND> (that kind alone).
image.txt lines:  L edge file lo hi | C edge c_d_hex | W edge job kind | E edge job | R edge job kind
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from layer_prog import kv_program_builder as B
from layer_prog import lower_kv as K
from layer_prog.kv_bank_contract import ADAPTER_DONE, kv_timing

DL, PATH = 4, 9
NAMES = dict(CP='attn.cmp.pool', CN='attn.cmp.row_qdq', IK='attn.cmp.k_rope_qdq', KV='attn.kv_rope_qdq')
FILES = dict(CN='img_gk3.mem', IK='img_gk0.mem', KV='img_kvg.mem')           # gain images
DATA = dict(CP='img_main.mem', CN='img_main.mem', IK='img_ik.mem', KV='img_kv.mem')
KEEP = 10 ** 6                                                                # lease ends are not under test


class Die:
    die_sha = 'TEST_ONLY_ROUTE'

    def slices(self):
        return {'u_s_3N': dict(sid=7)}


def row(lo, hi, ready, producer, src, fmt='fp32', **kw):
    return dict(lo=lo, hi=hi, ready_edge=ready, release_edge=KEEP, producer=producer, source_receipt='TEST_ONLY', format=fmt,
                file=src, **kw)


def compile_chain(timing, root, vp_sr):
    """Group by group: the inputs of a group commit one edge after the previous group's outputs were read."""
    sched = dict(ops=[dict(id=f'L14.{n}', op=n, start=10 * i) for i, n in enumerate(NAMES.values())])
    owner = {k: f'L14.{n}' for k, n in NAMES.items()}
    profile = dict(capture_offset=PATH + DL + 6 + vp_sr, leaf_downrelay=DL, adapter_done=timing['done'],
                   **{k: timing[k] for k in ('seam_in', 'seam_out', 'vp_sr', 'first_native_write', 'last_read_completion_bound',
                                             'native_write_commit_after_done', 'native_read_ready_after_done')})
    B.derive_profile = lambda *a: profile
    common = dict(status='PASS', producer_kind='TEST_ONLY_SYNTHETIC_SOURCE', clock_epoch_identity='TEST_ONLY',
                  edge_convention='native_command_epoch_relative_sampled_edges', native_command_epoch_seq_edge=0)
    binding = dict(clock_epoch_identity='TEST_ONLY', native_command_epoch_seq_edge=0, die_v_sha256=Die.die_sha,
                   parameters=dict(KV_SEAM_IN=timing['seam_in'], KV_SEAM_OUT=timing['seam_out']))
    ledger = dict(die_v_sha256=Die.die_sha, clock_epoch_identity='TEST_ONLY', context=0, producers={},
                  receipt_root=str(root), edge_convention=common['edge_convention'], native_command_epoch_seq_edge=0,
                  job_ids={o: i for i, o in enumerate(owner.values())})

    def produce(key, rows, **kw):
        rec = dict(common, rows=rows, writes=[], **kw)
        path = root / (key.replace('::', '__') + '.json')
        path.write_text(json.dumps(rec))
        ledger['producers'][key] = dict(rec, receipt_path=path.name, receipt_sha256=B.sha(path))

    ready, program = 200, None
    for kind, own in owner.items():
        gain_ready = data_ready = ready
        if kind == 'CP':
            produce(own + '::input_rows', [row(0, 511, ready, 'TEST_ONLY', DATA[kind])])
        else:
            if kind == 'CN':                                                  # gain + parameters early; operands = CP outputs
                gain_ready = data_ready = 200
                ops = [row(692, 819, ready, 'TEST_ONLY_POOL', None, producer_job=owner['CP'] + '::CP')]
            elif kind == 'IK':
                ops = [row(692, 787, ready + 1, 'TEST_ONLY', DATA[kind], 'fp32_zero_prefix384'),
                       row(788, 819, ready + 1, 'TEST_ONLY', DATA[kind])]
            else:
                ops = [row(692, 819, ready + 1, 'TEST_ONLY', DATA[kind])]
            if kind != 'CN':
                gain_ready = data_ready = ready + 1
            produce(own + '::input_rows', ops)
            produce(own + '::parameters', [row(672, 691, data_ready, 'TEST_ONLY', DATA[kind])])
            produce(own + '::gain_upload_rows', [row(528, 531, gain_ready, 'TEST_ONLY', FILES[kind]),
                                                 row(896, 1023, gain_ready, 'TEST_ONLY', FILES[kind])],
                    gain_bank_release_edge=KEEP)
        program = B.build(Die(), sched, binding, ledger, None, 'TEST_ONLY')
        ready = program['jobs'][-1]['output_ready_edge']
    assert not program['missing']
    return program, sched


def image(program, sched, vp_sr):
    class C:
        ENG = dict(VN=0)
        VP_SR = vp_sr

        @staticmethod
        def ctl_path(die, sl):
            return dict(edges=PATH)
    K._dvc = lambda: C
    commands = {}
    for op in sched['ops']:
        r = K.lower(Die(), op, dict(sched=sched, kv_program=program))
        owned = [j for j in program['jobs'] if j['owner'] == op['id']]
        assert r['native_programme'] and len(r['rows']) == len(owned)
        for j, x in zip(owned, r['rows']):
            commands[j['id']] = (x['issue'] + j['capture_offset'], r['templates'][x['template_index']][1] >> 26)
    ev = []
    for n, j in enumerate(program['jobs']):
        for x in j['residency']:
            if x.get('file'):
                ev.append((x['ready_edge'], f"L {x['ready_edge']} {x['file']} {x['lo']} {x['hi']}"))
        edge, body = commands[j['id']]
        ev.append((edge, f'C {edge} {body:040x}'))
        ev.append((j['residency'][0]['last_read_edge'], f"E {j['residency'][0]['last_read_edge']} {n}"))
        if j['kind'] != 'GK':
            ev.append((j['first_output_write_edge'], f"W {j['first_output_write_edge']} {n} {j['kind']}"))
            ev.append((j['output_ready_edge'], f"R {j['output_ready_edge']} {n} {j['kind']}"))
    return '\n'.join(x[1] for x in sorted(ev, key=lambda x: x[0])) + '\n'


def variants(seam, vp_sr):
    new, old = kv_timing(*seam, vp_sr=vp_sr), kv_timing(0, 0, vp_sr=vp_sr)
    yield 'new', new
    yield 'old', old
    for kind in ADAPTER_DONE:
        mixed = {k: v for k, v in new.items()}
        for field in ('done', 'first_native_write'):
            mixed[field] = {k: (old if k == kind else new)[field][k] for k in new[field]}
        yield 'old_' + kind, mixed


def emit(seam, vp_sr, out):
    real = B.derive_profile
    try:
        for name, timing in variants(seam, vp_sr):
            d = out / name
            d.mkdir(parents=True, exist_ok=True)
            keep, K.program_timing = K.program_timing, lambda p, t=timing: t   # validate against the variant's own dates
            try:
                program, sched = compile_chain(timing, d, vp_sr)
                (d / 'image.txt').write_text(image(program, sched, vp_sr))
            finally:
                K.program_timing = keep
            if name == 'new':
                K.validate(program, sched)                                     # production validation, real timing table
            (d / 'program.json').write_text(json.dumps(program, indent=1) + '\n')
    finally:
        B.derive_profile = real


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seam', nargs=2, type=int, default=[2, 2])
    p.add_argument('--vp-sr', type=int, default=0)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    emit(tuple(a.seam), a.vp_sr, a.out)
    print('kv_seam_image:', ', '.join(sorted(x.name for x in a.out.iterdir() if x.is_dir())))

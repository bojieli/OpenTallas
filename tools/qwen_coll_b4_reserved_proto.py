#!/usr/bin/env python3
"""Standalone B4 core: exact-cache shared-port schedules and priced legacy MU study.
Not an issuer, regional-landing, finite-body, phase or physical qualification.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import qwen_coll_tp8_static_bench as B
from qwen_coll_tp8_static_links_bench import mu_prog
from qwen_static_schedule import mu_calendar as M


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache-record', type=Path, required=True)
    ap.add_argument('--cache-exe', type=Path, required=True)
    ap.add_argument('--snapshot-manifest', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    prior = json.loads(a.cache_record.read_text())
    expected = dict(latu=65, lats=390, xu=0, xs=0, die_name_master=True, pr_b4=True, mutant=None)
    assert all(prior.get(k) == v for k, v in expected.items()), 'CACHE_PARAMETERS'
    assert sha(a.cache_exe) == prior['executable_sha256'], 'CACHE_EXECUTABLE'
    assert all(sha(B.ROOT / p) == h for p, h in prior['source_sha256'].items()), 'CACHE_RTL'
    manifest = json.loads(a.snapshot_manifest.read_text())
    assert sha(B.ROOT / 'tools/qwen_coll_tp8_static_bench.py') == manifest['tools/qwen_coll_tp8_static_bench.py'], 'CACHE_DRIVER'
    guard = dict(parameters=expected, source_sha256=prior['source_sha256'], executable_sha256=sha(a.cache_exe),
                 driver_sha256=sha(B.ROOT / 'tools/qwen_coll_tp8_static_bench.py'))
    records = []

    def run(name, modes, words, prog, seed=1000, reference=None):
        vec = a.out / ('vec_' + name)
        B.vectors(vec, words, prog, seed)
        if reference:
            source_vec, ids, source_words = reference
            for fn, multiplier in [('part.hex', B.ND), ('sum.hex', 1)]:
                lines = (source_vec / fn).read_text().splitlines(keepends=True)
                offsets = [0]
                for w in source_words:
                    offsets.append(offsets[-1] + multiplier * w)
                (vec / fn).write_text(''.join(''.join(lines[offsets[i]:offsets[i+1]]) for i in ids))
        r = subprocess.run([str(a.cache_exe.resolve()), f'+VEC={vec.resolve()}', f'+NMSG={len(prog)}'],
                           capture_output=True, text=True)
        (a.out / (name + '.log')).write_text(r.stdout + r.stderr)
        m = B.RES.search(r.stdout)
        g = m.groups() if m else None
        ok = r.returncode == 0 and g and any(x.strip() == 'PASS' for x in r.stdout.splitlines())
        ok = bool(ok and int(g[0]) == 0 and int(g[1]) == 0 and int(g[2]) == 0 and set(g[3]) == {'0'})
        span = max(p['last_out'] for p in prog) - prog[0]['first_slot'] + 1
        row = dict(name=name, passed=ok, program=prog, modes=modes, words=words, span=span,
                   result=dict(zip(['mismatches','extra','out_err','fault','fault_code','words_out','first','last'], g)) if g else None,
                   stimuli_sha256={f: sha(vec/f) for f in ['part.hex','sum.hex','cmd.hex']})
        records.append(row)
        print(f'B4_RESERVED {name} {"PASS" if ok else "FAIL"} messages={len(prog)} span={span} result={row["result"]}', flush=True)
        if not ok:
            (a.out / 'partial_record.json').write_text(json.dumps(dict(cache_guard=guard, cases=records), indent=2)+'\n')
            raise SystemExit(1)
        return vec

    for i, (name, nmsg, n, mk, kind, extra) in enumerate(B.PRODUCTION_CASES):
        modes = [0,0,1] if mk == 'rrg1' else [int(mk == 'g')] * nmsg
        words = [n] * nmsg
        prog = B.schedule(modes, words, 65, 390, shared_ucie=True)
        run('shared_' + name, modes, words, prog, 1000+i)

    # Explicit repricing of this legacy command-only model, never a sourcecert.
    # Two AR prices grow36 each, and the layer period grows72. Its old head
    # omits actual gather resources; no token rate or full+2616 claim follows.
    base_p = dict(users=4, occupancy='measured', head_chunks=8)
    base = M.compile_calendar(base_p, tokens=3, policy='priority')
    M.LAYER_WINDOWS = tuple((o,u,n+(36 if u=='coll' else 0),b) for o,u,n,b in M.LAYER_WINDOWS)
    p = dict(base_p, lu=65, ls=390, layer_period=M.SOURCED['layer_period']+72)
    cal = M.compile_calendar(p, tokens=3, policy='priority')
    fixture = M.bench_cases(cal)
    fixture['source'] = dict(grade='MODEL command-only legacy MU study; not actual finite-body/issuer/head proof',
        compiler='tools/qwen_static_schedule/mu_calendar.py', inputs=p, AR_window_added_cycles=36,
        old_single_user_study_cycles=base['single_user_token_cycles'], new_single_user_study_cycles=cal['single_user_token_cycles'],
        excluded='actual head-gather price/resources and availability/fault retirement; ROOT full-token model remains separate',
        latency_user_identical=cal['latency_user_identical'])
    assert fixture['source']['new_single_user_study_cycles']-fixture['source']['old_single_user_study_cycles']==36*72
    (a.out / 'b4_legacy_mu_cal.json').write_text(json.dumps(fixture, indent=2)+'\n')
    mc, ref = fixture['cases'][:2]
    shift = 99-min(x[0] for x in mc['cmds'])
    def program(c):
        return mu_prog([(cy+shift,mode) for cy,mode,w in c['cmds']], [w for cy,mode,w in c['cmds']],65,390,True)
    full, subset = program(mc), program(ref)
    ids = [i for i,u in enumerate(mc['users']) if u==0]
    assert len(ids)==len(subset)
    assert all(subset[i]['first_out']==full[j]['first_out'] for i,j in enumerate(ids)), 'MU_REFERENCE_CYCLES'
    words = [x[2] for x in mc['cmds']]
    mu_vec = run('b4_mu_window',[x[1] for x in mc['cmds']],words,full,2042)
    run('b4_mu_ref_user0',[x[1] for x in ref['cmds']],[x[2] for x in ref['cmds']],subset,2042,
        reference=(mu_vec,ids,words))
    (a.out / 'record.json').write_text(json.dumps(dict(schema='opentallas.coll_b4.reserved_proto.v1',
        grade='standalone core with modeled PHY; not whole-parent/issuer/phase/native timing proof',
        cache_guard=guard, shared_ucie_reservations=True, cases=records,
        reference_identity=dict(message_map=ids, same_absolute_normalized_input_output_cycles=True,
            same_numeric_stimuli=True, local_message_tags='reference tags are compact message indices; not unchanged header/body proof'),
        helper_sha256={str(p.relative_to(B.ROOT)):sha(p) for p in [Path(__file__),B.ROOT/'tools/qwen_coll_tp8_static_bench.py',B.ROOT/'tools/qwen_static_schedule/mu_calendar.py']}),indent=2)+'\n')
    print('B4_RESERVED PASS cases=6',flush=True)


if __name__ == '__main__':
    main()

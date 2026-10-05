import importlib.util
import json
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('guard', Path(__file__).resolve().parents[1] / 'tools/w17_D1_generated_native_guard.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


@pytest.fixture
def case(tmp_path):
    out, src = tmp_path / 'output', tmp_path / 'source'
    (out / 'obj').mkdir(parents=True)
    src.mkdir()
    (src / 'driver.cpp').write_text('source-bound driver')
    prefix = 'Vtb_D1_scope_core'
    (out / 'obj' / (prefix + '.h')).write_text('VL_OUT(&observed_cycle,31,0); void eval(); void final(); bool eventsPending(); uint64_t nextTimeSlot();\n' + '\n'.join('const __PVT__tb_D1_scope_core__DOT__endpoint__DOT__g_t__BRA__' + str(i) for i in range(64)))
    (out / 'obj' / (prefix + '__Dpi.h')).write_text('extern void v41rt_die_register(int rank); extern int v41rt_vm_word(int a);')
    (out / 'obj' / (prefix + '.mk')).write_text('VM_PREFIX = Vtb_D1_scope_core\n')
    (out / 'obj' / (prefix + '_classes.mk')).write_text('VM_TIMING = 1\nVM_PARALLEL_BUILDS = 1\nVM_TRACE = 0\n')
    (out / 'obj' / (prefix + '__verFiles.dat')).write_text('--timing --threads 1 --top-module tb_D1_scope_core --prefix Vtb_D1_scope_core')
    (out / 'frontend.log').write_text('terminal log')
    (out / 'start.json').write_text('{}')
    r = dict(verdict='PASS_FRONTEND_ONLY', exit_code=0, termination_reason=None,
             source_commit='source', plan_sha256='plan', GO_sha256='go',
             native_credit=False, runtime_credit=False, token_credit=False, physical_credit=False)
    c = dict(source_commit='source', plan_sha256='plan', GO_sha256='go',
             source_files={'driver.cpp': g.sha(src / 'driver.cpp')}, retained_output_cap_bytes=4096)
    return out, src, r, c


def freeze(case):
    out, src, r, c = case
    r['generated_files'] = [dict(path=str(p.relative_to(out)), bytes=p.stat().st_size, sha256=g.sha(p)) for p in sorted(out.rglob('*')) if p.is_file() and p.name not in ('start.json', 'verdict.json')]
    r['log_sha256'] = g.sha(out / 'frontend.log')
    (out / 'verdict.json').write_text(json.dumps(r))
    c['receipt_sha256'] = g.sha(out / 'verdict.json')


def test_valid_is_review_only(case):
    freeze(case)
    out, src, _, c = case
    result = g.review(out, c, src)
    assert result['interface'] == 'GENERATED_ABI_ENROLLED'
    assert result['native_execution_authorized'] is False
    assert result['compile_admission'].startswith('BLOCKED')


@pytest.mark.parametrize('field,value', [('verdict','FAIL_FRONTEND'),('exit_code',True),('exit_code',1),('termination_reason','WALL_CAP'),('source_commit','other'),('plan_sha256','other'),('GO_sha256','other'),('native_credit',True),('runtime_credit',True),('token_credit',True),('physical_credit',True)])
def test_terminal_and_binding_rejections(case, field, value):
    case[2][field] = value
    freeze(case)
    with pytest.raises(ValueError): g.review(case[0], case[3], case[1])


@pytest.mark.parametrize('name,old,new', [('.h','observed_cycle,31,0','observed_cycle,30,0'),('.h','bool eventsPending()','void eventsPending()'),('.h','BRA__63','NO_TILE_63'),('__Dpi.h','int rank','long rank'),('_classes.mk','VM_TIMING = 1','VM_TIMING = 0'),('.mk','VM_PREFIX = Vtb_D1_scope_core','VM_PREFIX = wrong'),('__verFiles.dat','--threads 1','--threads 2')])
def test_real_abi_mutants_rejected_even_enrolled(case, name, old, new):
    path = case[0] / 'obj' / ('Vtb_D1_scope_core' + name)
    path.write_text(path.read_text().replace(old,new))
    freeze(case)
    with pytest.raises(ValueError): g.review(case[0],case[3],case[1])


@pytest.mark.parametrize('mutation', ['tamper','extra','missing','source','duplicate','escape','symlink'])
def test_inventory_negative_controls(case, mutation):
    freeze(case)
    out,src,r,c = case
    p = out / 'obj/Vtb_D1_scope_core.h'
    if mutation == 'tamper': p.write_text('tampered')
    elif mutation == 'extra': (out / 'unenrolled.o').write_text('object')
    elif mutation == 'missing': p.unlink()
    elif mutation == 'source': (src / 'driver.cpp').write_text('changed')
    elif mutation == 'symlink':
        content = p.read_text(); p.unlink(); (src / 'header').write_text(content); p.symlink_to(src / 'header')
    else:
        if mutation == 'duplicate': r['generated_files'].append(r['generated_files'][0])
        else: r['generated_files'][0]['path'] = '../escape'
        (out / 'verdict.json').write_text(json.dumps(r)); c['receipt_sha256']=g.sha(out/'verdict.json')
    with pytest.raises(ValueError): g.review(out,c,src)

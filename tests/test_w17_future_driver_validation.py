"""Compile/run only the standalone helper and FakeDie; no full driver compile."""
import importlib.util
import json
from pathlib import Path
import resource
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('prepare_future',ROOT/'tools/prepare_w17_future_driver_validation.py')
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)
HEADER=ROOT/'tools/runtime/w17_future_driver_validation.hpp'
HARNESS=ROOT/'tests/cpp/w17_future_driver_validation_fake.cpp'


def limits():
    resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
    resource.setrlimit(resource.RLIMIT_CPU,(30,30))
    import os
    os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])


@pytest.fixture(scope='module')
def binary(tmp_path_factory):
    b=tmp_path_factory.mktemp('fake_driver')/'fake'
    subprocess.run(['g++','-std=c++17','-O0','-Wall','-Wextra','-Werror','-I'+str(HEADER.parent),
                    str(HARNESS),'-o',str(b)],check=True,capture_output=True,timeout=30,preexec_fn=limits)
    return b


def run(binary,*args):
    return subprocess.run([str(binary),*args],text=True,capture_output=True,timeout=5,preexec_fn=limits)


def test_fake_driver_regressions(binary):
    r=run(binary)
    assert r.returncode==0,r.stderr
    assert r.stdout.count('PASS ')==7


@pytest.mark.parametrize('kind,value',[
 ('cycles','-1'),('cycles','+1'),('cycles','1x'),('cycles','1.0'),('cycles',''),('cycles',' 1'),
 ('cycles','0'),('cycles','9223372036854775808'),('cycles','18446744073709551616'),
 ('int','2147483648'),('int','-1'),('int','0'),('latency','-1'),('latency','2147483648'),
 ('bool','2'),('bool','true'),('bool','-0')])
def test_strict_invalid_parameters(binary,kind,value):
    assert run(binary,'parse',kind,value).returncode==2


@pytest.mark.parametrize('kind,value,expected',[
 ('cycles','1','1'),('cycles','9223372036854775807','9223372036854775807'),
 ('int','2147483647','2147483647'),('latency','0','0'),('latency','177','177'),
 ('bool','0','0'),('bool','1','1')])
def test_parameter_boundaries(binary,kind,value,expected):
    r=run(binary,'parse',kind,value)
    assert r.returncode==0 and r.stdout.strip()==expected


def test_exact_transformation_and_inverse():
    original=P.source();copy,changes=P.transform(original)
    assert (ROOT/P.COPY).read_text()==copy
    for change in reversed(changes):
        offset=change['offset'];end=offset+len(change['after'])
        assert copy[offset:end]==change['after']
        copy=copy[:offset]+change['before']+copy[end:]
    assert copy==original
    assert 'cyc + LAT_U' not in (ROOT/P.COPY).read_text()


def test_copy_not_selected_or_compiled():
    text=(ROOT/P.COPY).read_text()
    assert 'W17_FUTURE_DRIVER_VALIDATION_OPT_IN' in text
    assert 'w17_future::Monitor monitor(4,cyc,maxc,WD);' in text
    assert 'monitor.sample(cyc,samples)' in text
    assert text.index('if(validation.fault)')<text.index('if(validation.all_done)')
    assert 'bool all = validation.success;' in text
    assert 'BOUND_MISSING' in text
    assert 'RT_CONTINUE_ON_FAULT' in text
    assert 'return d->dbg_fs;' in text and '#ifdef W17_FUTURE_BIND_DBG_FS' in text


def test_original_and_record_source_pins():
    text=P.source()
    import hashlib
    assert hashlib.sha256(text.encode()).hexdigest()==P.SHA
    r=json.loads((ROOT/'results/rtl/future_driver_validation_4e383_20261001/r1/transformation.json').read_text())
    assert r['original_sha256']==P.SHA
    assert hashlib.sha256((ROOT/P.COPY).read_bytes()).hexdigest()==r['copy_sha256']


def test_changed_source_rejected_before_copy(tmp_path,monkeypatch):
    monkeypatch.setattr(P.subprocess,'check_output',lambda *a,**k:b'bad source')
    with pytest.raises(ValueError,match='pin mismatch'):P.source()
    with pytest.raises(FileExistsError):P.prepare(tmp_path)


@pytest.mark.parametrize('name,old,new,expected',[
 ('shared_pc', 'r.pc=s.pc;r.last_pc=cycle;r.seen=true;r.diagnostic_reported=false;',
  'r.pc=s.pc;r.last_pc=cycle;r.seen=true;r.diagnostic_reported=false;for(auto& q:ranks_)q.last_pc=cycle;',
  'rank starvation masked'),
 ('fault_ignored', 'r.sticky_fault|=s.fault|s.sticky_sources|static_cast<uint32_t>(s.state>>32);',
  'r.sticky_fault|=0;', 'same-edge fault AND DONE accepted'),
 ('late_completion_clears', 'if(s.done) r.done=true;',
  'if(s.done) {r.done=true;r.deadline_failed=false;}', 'late DONE reset operation deadline')])
def test_real_helper_mutants_fail_fake_harness(tmp_path,name,old,new,expected):
    text=HEADER.read_text()
    assert text.count(old)==1
    (tmp_path/HEADER.name).write_text(text.replace(old,new))
    binary=tmp_path/name
    subprocess.run(['g++','-std=c++17','-O0','-I'+str(tmp_path),str(HARNESS),'-o',str(binary)],
                   check=True,capture_output=True,timeout=30,preexec_fn=limits)
    r=run(binary)
    assert r.returncode==2 and expected in r.stderr


def test_optin_copy_has_no_unchecked_control_parsing():
    text=(ROOT/P.COPY).read_text()
    assert 'atol(' not in text and 'atoi(' not in text
    assert text.index('RT_LAT_U')<text.index('RtPool pool(threads);')
    assert text.index('RT_WATCHDOG')<text.index('RtPool pool(threads);')
    assert 'line.q.front().first,line.lat,line.q.size()' in text
    assert 'monitor(4,cyc,maxc,WD)' in text # no invented service deadline supplied

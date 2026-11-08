"""Completed external references reuse real EQ; reject changed inputs and hosts."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import lec_completed_reference as ref


@pytest.fixture(scope='module')
def real_proof(tmp_path_factory):
    # Module scope runs before conftest's function-scoped OT_LEC_RAWPREFIX_S=0; capture identities under
    # the same proof-policy environment the tests then check against (OT_LEC_* is part of the identity).
    mp = pytest.MonkeyPatch(); mp.setenv('OT_LEC_RAWPREFIX_S', '0')
    try:
        return _real_proof(tmp_path_factory)
    finally:
        mp.undo()


def _real_proof(tmp_path_factory):
    root = tmp_path_factory.mktemp('real_completed_proof')
    source = root/'producer'; source.mkdir()
    rtl = """module lec_t1(input clk, input rst_n, input v, input [7:0] d,
output reg [7:0] q, output reg valid);
always @(posedge clk) if (!rst_n) begin q <= 0; valid <= 0; end
else begin valid <= v; if (v) q <= d; end
endmodule
"""
    (source/'rtl').mkdir();(source/'rtl/lec_t1.sv').write_text(rtl)
    netdir=source/'run/results/asap7/lec_t1/base';netdir.mkdir(parents=True)
    (netdir/'1_2_yosys.v').write_text(rtl)
    (source/'config.mk').write_text('export DESIGN_NAME = lec_t1\nexport VERILOG_FILES = /work/rtl/lec_t1.sv\nexport SYNTH_HDL_FRONTEND = slang\n')
    (source/'freeze.json').write_text('{}\n')
    shutil.copy2(HERE/'lec.py', source/'lec.py')
    sid = ref.identity(source, 'source')
    (source/'lec_async.source_identity').write_text(sid+'\n')
    owner = 'fixture-proof-owner'
    (source/'lec_async.owner').write_text(owner+'\n')
    (source/'lec_async.runs').mkdir()
    (source/'lec_async.runs'/(owner+'.json')).write_text(json.dumps(dict(
        run_id=owner, source_id=sid, host=socket.gethostname(), scope='', started=time.time())))
    net = '/work/run/results/asap7/lec_t1/base/1_2_yosys.v'
    command = ['python3', '-I', '/work/lec.py', '/work', '--netlist', net, '--out', '/work/lec', '--jobs', '1', '--conflicts', '1000']
    (source/'lec_async.ready').write_text('1\n'+' '.join(command)+'\n')
    (source/'lec_async.identity').write_text(ref.identity(source)+'\n')
    result = subprocess.run(['docker', 'run', '--rm', '--memory', '4g', '--memory-swap', '4g', '--cpus', '1',
        '-v', str(source)+':/work', '--entrypoint', 'python3', 'openroad/orfs:asap7lock']+command[1:], capture_output=True, text=True)
    (root/'real_proof.log').write_text(result.stdout+result.stderr)
    assert result.returncode == 0, result.stdout+result.stderr
    receipt = json.loads((source/'lec/lec.json').read_text())
    assert receipt['verdict'] == 'EQUIVALENT' and receipt['counts']['compare_points'] > 0
    (source/'lec_async.rc').write_text('0\n'); (source/'lec_async.done').touch()
    return source


def pair(tmp_path, real_proof):
    producer = tmp_path/'producer'; shutil.copytree(real_proof, producer)
    consumer = tmp_path/'consumer'; consumer.mkdir()
    for name in ('config.mk', 'freeze.json', 'lec.py'):
        shutil.copy2(producer/name, consumer/name)
    for name in ('rtl', 'run'):
        shutil.copytree(producer/name, consumer/name)
    return producer, consumer


def test_real_completed_reference_and_native_continuation(tmp_path, real_proof):
    producer, consumer = pair(tmp_path, real_proof)
    with (consumer/'config.mk').open('a') as f:
        f.write('\nexport DIE_AREA = 0 0 300 400\n')
    (consumer/'freeze.json').write_text('{"geometry_only":true}\n')
    ref.register(producer, consumer, socket.gethostname())
    assert ref.validate(consumer)['source_qualified'] is False
    for name in ('lec_async.pid', 'lec_async.rc', 'lec_async.done', 'lec/lec.json'):
        assert not (consumer/name).exists()
    script = HERE/'lec_async.sh'
    r = subprocess.run(['bash', str(script), 'start', str(consumer), 'fixture-cts', 'unused-image', '1', '1', 'docker', 'cts'], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert not (consumer/'lec_async.pid').exists()
    r = subprocess.run(['bash', str(script), 'check-synth', str(consumer), 'fixture-cts'], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    r = subprocess.run(['bash', str(script), 'wait', str(consumer), 'fixture-cts', 'cts', '0'], capture_output=True, text=True)
    assert r.returncode == 0
    physical = json.loads((consumer/'physical_completion/fixture-cts.json').read_text())
    assert physical['proof_pending'] is False and physical['proof_pid'] == ''
    assert physical['proof_reference']['producer_kit'] == str(producer)
    r = subprocess.run(['bash', str(script), 'finish', str(consumer), '0', '5', 'fixture-cts', 'cts'], capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.strip() == '0', r.stderr
    net = consumer/'run/results/asap7/lec_t1/base/1_2_yosys.v'
    net.write_text(net.read_text()+'\n// causal changed netlist\n')
    r = subprocess.run(['bash', str(script), 'finish', str(consumer), '0', '5', 'fixture-cts', 'cts'], capture_output=True, text=True)
    assert r.stdout.strip() == '11'  # no non-owner fast-path bypass


@pytest.mark.parametrize('change', ['rtl', 'netlist', 'metadata_presence', 'policy', 'host', 'abort', 'receipt'])
def test_reference_rejects_causal_mismatch(tmp_path, real_proof, monkeypatch, change):
    producer, consumer = pair(tmp_path, real_proof)
    host = socket.gethostname()
    if change == 'rtl':
        p = next((consumer/'rtl').rglob('*.sv')); p.write_text(p.read_text()+'\n// changed source\n')
    elif change == 'netlist':
        p = consumer/'run/results/asap7/lec_t1/base/1_2_yosys.v';p.write_text(p.read_text()+'\n// changed gate\n')
    elif change == 'metadata_presence':
        (consumer/'core.json').write_text('{"boundary_role":{"rst_n":"reset"}}')
    elif change == 'policy':
        monkeypatch.setenv('OT_LEC_SUPERSET_VEC', '0' if os.environ.get('OT_LEC_SUPERSET_VEC') == '1' else '1')
    elif change == 'host':
        host = 'wrong-explicit-host'
    elif change == 'abort':
        (producer/'lec_async.aborted').write_text('ABORTED rc=137')
    elif change == 'receipt':
        r=json.loads((producer/'lec/lec.json').read_text());r['verdict']='NOT EQUIVALENT';(producer/'lec/lec.json').write_text(json.dumps(r))
    with pytest.raises(ValueError):
        ref.register(producer, consumer, host)
    assert not (consumer/ref.FILE).exists()


def test_reference_refuses_active_physical_target(tmp_path, real_proof):
    producer, consumer = pair(tmp_path, real_proof)
    runs=consumer/'lec_async.runs';runs.mkdir()
    (runs/'live-physical.json').write_text(json.dumps(dict(run_id='live-physical', scope=Path('/proc/self/cgroup').read_text())))
    with pytest.raises(ValueError, match='physical scope'):
        ref.register(producer, consumer, socket.gethostname())
    assert not (consumer/ref.FILE).exists()


def test_lost_reference_cannot_fall_back_to_local_wait(tmp_path, real_proof):
    producer, consumer = pair(tmp_path, real_proof)
    ref.register(producer, consumer, socket.gethostname())
    script=HERE/'lec_async.sh'
    r=subprocess.run(['bash',str(script),'start',str(consumer),'fixture-grt','unused','1','1','docker','grt'],capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    (consumer/ref.FILE).rename(consumer/'reference_parked.json')
    r=subprocess.run(['bash',str(script),'finish',str(consumer),'0','5','fixture-grt','grt'],capture_output=True,text=True)
    assert r.returncode==0 and r.stdout.strip()=='11'

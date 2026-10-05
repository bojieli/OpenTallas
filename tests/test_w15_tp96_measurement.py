import json
import subprocess
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w15_tp96_exact as C

ROOT=Path(__file__).resolve().parents[1]

def measurement_log():
    rows=[];log=['W15MEASURE version=1 bits=64 protocol_bits=16 period_ps=1112 overflow_guard=1']
    for op,(issue,elapsed) in enumerate([(65530,463462),(529000,5001),(534100,64013)]):
        for die in range(96):
            values=[issue,issue,issue+elapsed-10,issue+elapsed-1,issue+elapsed-1,issue+elapsed]
            rows.append((op,die,[0,1,1][op],[512,5,64][op],*[v&65535 for v in values],[512,480,6144][op],[512,480,6144][op]))
            log.append('MEAS op=%d die=%d issue=%d first_tx=%d last_tx=%d first_vm=%d last_vm=%d done=%d'%(op,die,*values))
    return '\n'.join(log),rows

def test_long_round_crosses_multiple_protocol_wraps():
    log,rows=measurement_log();m=C.measurement(log,rows)
    assert m['qualified'] and m['protocol_wrap_observed']
    assert m['cycles']=={'w19_oreduce':463462,'expert_intermediate':5001,'index_candidates':64013}
    assert m['elapsed_ps']['w19_oreduce']==463462*1112
    assert m['elapsed_ns']['w19_oreduce']==(463462*1112)/1000

def test_legacy_latency_is_unqualified_without_repairing_failed_records():
    m=C.measurement('W15DONE faults=0',[])
    assert not m['qualified'] and m['status']=='pending_unqualified'
    assert 'cycles' not in m

@pytest.mark.parametrize('change', ['narrow','missing','duplicate','backwards','protocol'])
def test_measurement_rejects_incomplete_or_inconsistent_timestamps(change):
    log,rows=measurement_log()
    if change=='narrow':log=log.replace('bits=64','bits=16')
    if change=='missing':log='\n'.join(log.splitlines()[:-1])
    if change=='duplicate':log+='\n'+log.splitlines()[-1]
    if change=='backwards':log=log.replace('done=528992','done=65529',1)
    if change=='protocol':rows[0]=(*rows[0][:4],12,*rows[0][5:])
    with pytest.raises(AssertionError):C.measurement(log,rows)

def test_existing_runner_or_binary_blocks_successor(tmp_path):
    p=tmp_path/'595164';p.mkdir();(p/'cmdline').write_bytes(b'python3\0tools/w15_tp96_exact.py\0--out\0old\0')
    with pytest.raises(RuntimeError,match='595164'):C.assert_no_live_tp96(tmp_path,own_pid=1)
    (p/'cmdline').write_bytes(b'/old/obj/Vtb_w15_tp96_exact\0+VEC=old\0')
    with pytest.raises(RuntimeError):C.assert_no_live_tp96(tmp_path,own_pid=1)
    C.assert_no_live_tp96(tmp_path,own_pid=595164)

@pytest.mark.parametrize('width,overflow,witness',[(64,0,'MEASURE_CONTROL_PASS'),(16,0,'measurement width must be 23..64'),(23,1,'measurement counter overflow')])
def test_actual_sv_counter_control(tmp_path,width,overflow,witness):
    exe=tmp_path/'control.vvp'
    subprocess.run(['iverilog','-g2012','-s','tb_w15_tp96_measure_control',f'-Ptb_w15_tp96_measure_control.WIDTH={width}','-o',str(exe),str(ROOT/'rtl/test/w15_tp96_measure_counter.sv'),str(ROOT/'rtl/test/tb_w15_tp96_measure_control.sv')],check=True,capture_output=True,text=True)
    r=subprocess.run(['vvp',str(exe),f'+OVERFLOW={overflow}'],capture_output=True,text=True,timeout=60)
    assert witness in r.stdout+r.stderr
    assert (r.returncode==0)==(width==64 and not overflow)
    assert 'measurement control timeout' not in r.stdout+r.stderr

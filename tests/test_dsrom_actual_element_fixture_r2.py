"""Source/event-schedule checks only; no HDL compiler, simulator, or build."""
import importlib.util
import json
from pathlib import Path
import re
import pytest

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'rtl/test/tb_dsrom_actual_element_gate.sv'
NEW=ROOT/'rtl/test/tb_dsrom_actual_element_gate_r2.sv'

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
PREP=module('prepare_r2','tools/prepare_dsrom_actual_element_gate_r2.py')
RUN=module('run_r2','tools/run_dsrom_actual_element_gate_r2.py')

def task(text,name):
    match=re.search(r'\btask\s+'+name+r'\b.*?;(?P<body>.*?)\bendtask\b',text,re.S)
    assert match,'missing task '+name
    return match['body']

def schedule(text):
    """Inspect source events independently of HDL: continuous updates settle on time advance.

    This guard detects stale derived-clock reads; it is not RTL clockgate equivalence.
    """
    now=0;clock=0;derived_clock=0;events=[];rises=[];falls=[]
    for m in re.finditer(r'#(\d+)|\bclk\s*=\s*([01])\b|\bcompare_all\s*\(\s*\)',task(text,'tick')):
        if m[1]:
            amount=int(m[1]);assert amount>0
            now+=amount;derived_clock=clock # gate enabled; propagation settles with time
        elif m[2]:
            clock=int(m[2]);events.append((now,'clk',clock))
            (rises if clock else falls).append(now)
        else:
            events.append((now,'compare',None))
            if derived_clock!=clock:raise AssertionError('derived-clock comparison before settling')
    assert len(rises)==len(falls)==1
    assert now==833,'tick period changed'
    assert rises==[416] and falls==[832],'phase price differs from reviewed plan'
    assert falls[0]-rises[0]==416 and now+rises[0]-falls[0]==417
    return events

def async_assertion_guard(text):
    reset=task(text,'reset_now')
    assert re.search(r'rst_n\s*=\s*0\s*;\s*#1\s*;\s*compare_all\s*\(\s*\)',reset)
    assert reset.index('compare_all()')<reset.index('if(r_pv || r_fault || r_busy)')

def test_event_schedule_rejects_r1_and_accepts_settled_r2():
    with pytest.raises(AssertionError,match='before settling'):schedule(OLD.read_text())
    assert schedule(NEW.read_text())==[(0,'compare',None),(416,'clk',1),(417,'compare',None),(832,'clk',0),(833,'compare',None)]

@pytest.mark.parametrize('mutation,error',[
    ('remove_falling_settle','before settling'),
    ('add_tick_time','period changed'),
    ('remove_rising_settle','before settling'),
])
def test_timing_guard_detects_mutations(mutation,error):
    text=NEW.read_text()
    if mutation=='remove_falling_settle':text=text.replace('#415;clk=0;#1;','#415;clk=0;')
    elif mutation=='add_tick_time':text=text.replace('#415;clk=0;#1;','#416;clk=0;#1;')
    else:text=text.replace('#416; clk=1; #1;','#416; clk=1;')
    with pytest.raises(AssertionError,match=error):schedule(text)

def test_all_differential_and_reset_predicates_preserved_exactly():
    old=OLD.read_text();new=NEW.read_text()
    for name in ('compare_all','reset_now','gap','load_phase','start_phase','stream_phase'):
        assert task(old,name)==task(new,name)
    assert old.count('compare_all()')==new.count('compare_all()')
    async_assertion_guard(new)
    with pytest.raises(AssertionError):async_assertion_guard(new.replace('rst_n=0;#1;','rst_n=0;'))
    expected=old.replace('#416;clk=0;cycles=cycles+1;compare_all();','#415;clk=0;#1;cycles=cycles+1;compare_all();')
    # Only leading explanatory comments and one timing statement differ.
    strip_comments=lambda t:re.sub(r'//[^\n]*','',t)
    assert re.sub(r'\s+',' ',strip_comments(expected)).strip()==re.sub(r'\s+',' ',strip_comments(new)).strip()

def test_pins_and_generated_package_select_only_r2(tmp_path):
    model=PREP.verify_pins()
    out=tmp_path/'fresh';record=PREP.prepare(out)
    assert not (out/'tb_dsrom_actual_element_gate.sv').exists()
    assert (out/'tb_dsrom_actual_element_gate_r2.sv').read_bytes()==NEW.read_bytes()
    assert record['files_sha256']==model['generated_files_sha256']
    for case in ('q','bfcolumn'):
        argv=model['compile_plan_proposed_only'][case]
        assert 'tb_dsrom_actual_element_gate_r2.sv' in argv
        assert 'tb_dsrom_actual_element_gate.sv' not in argv
    oldpins=json.loads((ROOT/'results/rtl/dsrom_actual_element_prepare_20261001/preparation_review.json').read_text())['preparation']['files_sha256']
    for name,pin in oldpins.items():
        if name!='tb_dsrom_actual_element_gate.sv':assert record['files_sha256'][name]==pin
    with pytest.raises(FileExistsError):PREP.prepare(out)

def test_old_go_cannot_authorize_r2(monkeypatch):
    raw=json.dumps(dict(prepared_commit='4e5b407df0750a045880b5dcb81d9d0761b36e60',GO='BOUNDED_EXISTING_SOURCE_DIFFERENTIAL_VERIFICATION_ONLY')).encode()
    monkeypatch.setattr(RUN,'git',lambda *args:raw)
    with pytest.raises(ValueError,match='new r2 parent GO'):RUN.verify('old-GO')

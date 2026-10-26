"""Regression gates for actual PG failures found during infra-first bring-up."""
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
import pytest
import die_trial as D
import infra_pg as I


def _boundary_prologue(sigtype='POWER'):
    # Execute the generated Tcl, with named objects representing auto and real bump ports.
    source=D.bumps_tcl(None,[]).split('set m9 ')[0]
    mock=r'''
namespace eval ord {}; namespace eval odb {}
set deleted {}
proc ord::get_db_block {} {return block}
proc block {method name} {if {$name eq "VDD"} {return autoVDD};if {$name eq "VSS"} {return autoVSS};if {$name eq "VDD_b0"} {return realBump};return NULL}
proc autoVSS {method} {return GROUND}
proc odb::dbBTerm_destroy {obj} {global deleted;lappend deleted $obj}
'''+f'proc autoVDD {{method}} {{return {sigtype}}}\n'
    script=mock+'set caught [catch {\n'+source+'\n} message]\nputs "CAUGHT $caught"\nputs "DELETED [lsort $deleted]"\nputs "MSG $message"\n'
    return subprocess.run(['tclsh'],input=script,text=True,capture_output=True,check=True).stdout


def test_real_bumps_survive_boundary_port_cleanup():
    result=_boundary_prologue()
    assert 'CAUGHT 0' in result
    assert 'DELETED autoVDD autoVSS' in result
    assert 'realBump' not in result


def test_boundary_cleanup_rejects_non_power_port():
    result=_boundary_prologue('SIGNAL')
    assert 'CAUGHT 1' in result
    assert 'refusing to remove non-PG boundary port VDD' in result
    assert 'DELETED \n' in result


def test_mixed_partition_phy_watts_are_not_core_watts(monkeypatch):
    p=SimpleNamespace(name='s81',W=100.,H=100.,die={},parts={'host':{'type':'mixed','origin_um':[0.,0.]}},types={'mixed':{'outline_um':[100.,100.],'module':'core'}})
    monkeypatch.setattr(D,'io_windows',lambda *args:[{'name':'serdes','iface':'serdes','part':'host','rect_um':[0.,0.,10.,10.]}])
    m=I.load_model(p,Path('.'),core_watts=53.5)
    assert m['regions'][0]['power_w']==53.5
    assert sum(m['part_w'].values())==pytest.approx(53.5+4.37)
    assert sum(d*(r[2]-r[0])*(r[3]-r[1])*1e-6 for r,d in m['loads'])==pytest.approx(53.5+4.37)
    with pytest.raises(ValueError,match='not both'):
        I.load_model(p,Path('.'),core_watts=53.5,core_w_mm2=.1)


@pytest.mark.parametrize('status,drop,budget,verdict',[('OK',52.2,35.,'FAIL'),('OK',34.,35.,'PASS'),('OK',1.,None,'NOT RUN'),('ERROR',1.,35.,'NOT RUN')])
def test_successful_solver_does_not_hide_ir_failure(tmp_path,monkeypatch,status,drop,budget,verdict):
    (tmp_path/'irwin.json').write_text(json.dumps({'ir_budget_mv':budget}))
    monkeypatch.setattr(D,'psm_report',lambda *args:{'status':status,'worst_ir_drop_mv':drop})
    assert I.report(tmp_path)['ir_verdict']==verdict

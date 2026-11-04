import json
from pathlib import Path
import subprocess
import pytest

@pytest.mark.parametrize('std,macros,fail',[(0,1,False),(400000,3,False),(400001,0,True)])
def test_actual_top_cell_cap_excludes_blocks(tmp_path,std,macros,fail):
    out=tmp_path/'count.json'
    script=Path(__file__).with_name('native_cell_cap.tcl').read_text().replace('/work/native_cell_count.json',str(out))
    mock='''namespace eval ord {proc get_db_block {} {return block}}
proc block {m} {return [concat [lrepeat STD stdinst] [lrepeat MAC macros]]}
proc stdinst {m} {return stdmaster}
proc macros {m} {return macromaster}
proc stdmaster {m} {return 0}
proc macromaster {m} {return 1}
'''.replace('STD',str(std)).replace('MAC',str(macros))
    p=tmp_path/'run.tcl';p.write_text(mock+script)
    result=subprocess.run(['tclsh',str(p)],capture_output=True,text=True)
    assert bool(result.returncode)==fail, result.stderr
    count=json.loads(out.read_text())
    assert count['stdcells']==std and count['macros']==macros
    if fail:assert 'above 400000 run cap' in result.stderr

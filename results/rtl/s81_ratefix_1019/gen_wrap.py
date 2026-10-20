#!/usr/bin/env python3
"""S81-RATEFIX: run this branch's retained_xs_program.py + xs_calendar.py against the TOK2 fullsix root tree
(argv[1] = root, argv[2] = dir holding the two branch files; remaining args go to retained_xs_program)."""
import sys,importlib.util,runpy
root,mine=sys.argv[1],sys.argv[2]
sys.argv=[mine+'/retained_xs_program.py']+sys.argv[3:]
sys.path.insert(0,root+'/tools/s81_dv/layer_prog/qf_producer')
import head_local_contract  # noqa: F401  (sets ROOT paths)
sys.path.insert(0,root+'/tools/s81_dv');sys.path.insert(0,root+'/tools/s81_dv/layer_prog')
sp=importlib.util.spec_from_file_location('xs_calendar',mine+'/xs_calendar.py');m=importlib.util.module_from_spec(sp)
sys.modules['xs_calendar']=m;sp.loader.exec_module(m)
assert hasattr(m,'compile_pipeline')
runpy.run_path(sys.argv[0],run_name='__main__')

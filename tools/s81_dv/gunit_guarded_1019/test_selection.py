#!/usr/bin/env python3
import json
from pathlib import Path
import shutil
import tempfile
if __package__:
    from .selector import select, TOP
else:
    import importlib.util
    spec = importlib.util.spec_from_file_location("guarded_1019_selector", Path(__file__).with_name("selector.py"))
    selector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(selector)
    select, TOP = selector.select, selector.TOP
def run_checks():
    R=Path(__file__).resolve().parents[3]
    M=R/'results/rtl/s81_gunit_guarded_package_1019/source_manifest.json'
    m=json.loads(M.read_text());paths=[x['path'] for x in m['sources']]
    checks=0
    def rejects(fn,label):
        nonlocal checks
        try:fn()
        except ValueError:checks+=1;return
        raise AssertionError('accepted '+label)
    assert len(select(R,TOP,{'MUT':0}))==len(paths);checks+=1
    for top in ['dsdv_gunit_l5','dsdv_gunit_tail','ot_hdc_sinkhorn_fs','ed66','f03']:
        rejects(lambda:select(R,top,{'MUT':0}),top)
    for params in [{},{'MUT':8},{'MUT':0,'Q4':0},{'MUT':0,'FANOUT_SAFE':1}]:
        rejects(lambda:select(R,TOP,params),'parameters')
    for p in [paths[:-1],list(reversed(paths)),paths+[paths[0]], [x for x in paths if not x.endswith('.v')], [x.replace('.v','_bb.v') if x.endswith('.v') else x for x in paths]]:
        rejects(lambda:select(R,TOP,{'MUT':0},p),'source mixture')
    with tempfile.TemporaryDirectory() as td:
        t=Path(td)
        for p in paths+[str(M.relative_to(R))]:
            (t/p).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(R/p,t/p)
        private=next(p for p in paths if p.endswith('/dsdv_gunit_l5.sv'))
        p=t/private;p.write_text(p.read_text().replace(TOP,'dsdv_gunit_l5'))
        rejects(lambda:select(t,TOP,{'MUT':0}),'module alias/source hash')
        shutil.copyfile(R/private,p)
        mm=json.loads((t/M.relative_to(R)).read_text())
        mm['sources'][0]['modules']=['unauthorized_alias']
        (t/M.relative_to(R)).write_text(json.dumps(mm))
        rejects(lambda:select(t,TOP,{'MUT':0}),'module ownership')
    return checks


def test_selection():
    assert run_checks() == 17


def main():
    print('GUARDED_SELECTION_PASS checks='+str(run_checks()))


if __name__ == '__main__':
    main()

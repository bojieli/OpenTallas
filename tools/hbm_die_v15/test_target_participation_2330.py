#!/usr/bin/env python3
"""Two actual programme/cmd targets, six lifecycle cases; exact oldsource must fail every case."""
import pathlib,subprocess,tempfile
R=pathlib.Path(__file__).resolve().parents[2]
files=['rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv',
       'rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv']
bench=R/'rtl/hbm_accel/host_static_20261015/tb_hbm_target_participation.sv'
with tempfile.TemporaryDirectory(prefix='hbm-target-lifecycle-') as td:
    d=pathlib.Path(td)
    def build(name,fs):
        subprocess.run(['iverilog','-g2012','-s','tb_hbm_target_participation','-o',str(d/name),str(bench)]+list(map(str,fs)),check=True)
    build('current',[R/p for p in files])
    r=subprocess.run(['vvp',str(d/'current')],capture_output=True,text=True);print(r.stdout.strip())
    assert r.returncode==0 and 'TARGET_PARTICIPATION PASS' in r.stdout
    old=[]
    for p in files:
        f=d/pathlib.Path(p).name;f.write_bytes(subprocess.check_output(['git','-C',str(R),'show','8d97a38f0:'+p]));old.append(f)
    build('before',old)
    for k in range(6):
        r=subprocess.run(['vvp',str(d/'before'),f'+CASE={k}'],capture_output=True,text=True)
        print(f'OLDSOURCE_CASE{k} rc={r.returncode}: {r.stdout.splitlines()[0] if r.stdout else r.stderr.strip()}')
        assert r.returncode!=0 and 'FATAL:' in r.stdout
print('TARGET_PARTICIPATION_GATE PASS current sixcases, oldsource rejects allsix')

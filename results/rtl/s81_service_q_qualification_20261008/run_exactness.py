#!/usr/bin/env python3
import json,pathlib,re,subprocess,tempfile
D=pathlib.Path(__file__).resolve().parent
s=json.loads((D/'source_identity.json').read_text())
def module(commit):
    txt=subprocess.check_output(['git','show',commit+':rtl/dsrom_sys/s81_ph/svc/ot_s81ph_svc_io_tiles.sv'],text=True)
    return re.search(r'module dsfd_svcio_q\b.*?endmodule',txt,re.S).group(0)
with tempfile.TemporaryDirectory() as tmp:
    p=pathlib.Path(tmp)
    (p/'original.sv').write_text(module(s['routed_source_commit']).replace('dsfd_svcio_q','dsfd_svcio_q_original'))
    (p/'current.sv').write_text(module(s['source_commit']))
    for mutant in (False,True):
        tb=(D/'tb_service_q_equivalence.sv').read_text()
        if mutant: tb=tb.replace('hist[i-4]','hist[i-3]')
        (p/'tb.sv').write_text(tb)
        subprocess.run(['iverilog','-g2012','-s','tb','-o',str(p/'sim'),str(p/'tb.sv'),str(p/'original.sv'),str(p/'current.sv')],check=True)
        r=subprocess.run(['vvp',str(p/'sim')],capture_output=True,text=True)
        if mutant:
            assert r.returncode!=0 and 'q mismatch' in r.stdout,r.stdout
            print('PASS negative control detects removed OSTG latency')
        else:
            assert r.returncode==0,r.stdout
            print(r.stdout,end='')

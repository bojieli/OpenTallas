"""Same producer/HBM fixture, real descriptor lifetimes; numeric engine separate."""
import hashlib,json,re,subprocess,tempfile
from pathlib import Path
import rtl_v41x_window_stream_gate as stream
ROOT=Path(__file__).resolve().parents[1]
SOURCES=[*stream.SOURCES,ROOT/'rtl/chip/ot_chip_v41x_window_retention.sv',ROOT/'rtl/test/tb_ds_layer_retention_compose.sv']

def run():
    cases=[]
    with tempfile.TemporaryDirectory(prefix='window-retain-') as tmp:
        exe=str(Path(tmp)/'gate.vvp')
        for enable,reset,flags in [(0,0,[]),(1,0,[]),(1,0,['+SINK_PERIOD=11']),(1,0,['+INVALIDATE']),(1,0,['+PRIME']),(1,0,['+WRITE']),(1,0,['+CONFIG']),(1,65534,[])]:
            subprocess.run(['iverilog','-g2012','-s','tb_ds_layer_retention_compose',f'-Ptb_ds_layer_retention_compose.RETAIN={enable}',f'-Ptb_ds_layer_retention_compose.GENRESET={reset}','-o',exe,*map(str,SOURCES)],check=True,capture_output=True,text=True)
            p=subprocess.run(['vvp',exe,*flags],check=True,capture_output=True,text=True,timeout=120)
            assert 'RETENTION_COMPOSE_PASS' in p.stdout
            line=next(x for x in p.stdout.splitlines() if x.startswith('EDGE_CONTRACT'))
            metrics={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line)}
            cases.append(dict(enable=enable,reset_generation=reset,flags=flags,metrics=metrics,log=p.stdout))
        # Use normal generations for changed-user/position rejection.
        subprocess.run(['iverilog','-g2012','-s','tb_ds_layer_retention_compose','-Ptb_ds_layer_retention_compose.RETAIN=1','-o',exe,*map(str,SOURCES)],check=True,capture_output=True,text=True)
        for flag in ('+OTHER_USER','+OTHER_POSITION'):
            identity=subprocess.run(['vvp',exe,flag],check=True,capture_output=True,text=True,timeout=120)
            assert 'RETENTION_IDENTITY_MISS_PASS' in identity.stdout
        bad=subprocess.run(['vvp',exe,'+CORRUPT_WRITE'],capture_output=True,text=True,timeout=120)
        assert bad.returncode and 'packed row mismatch' in bad.stdout
    assert cases[0]['metrics']['reads']==4352
    assert cases[1]['metrics']['reads']==2176
    assert all(c['metrics']['reads']==4352 for c in cases[3:])
    paths=[*SOURCES,Path(__file__),ROOT/'rtl/chip/ot_chip_v41x_die.sv']
    record=dict(status='pass',cases=cases,source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                saved_fixture_cycles=cases[0]['metrics']['total_cycles']-cases[1]['metrics']['total_cycles'],saved_sectors=2176,
                scope='Same synthetic block producer and real delayed-completion HBM, actual distinct QK/PV descriptors and lifecycle, seven VM-only elapsed slots (not executed numeric SU instructions); no numeric attention or full-layer speed claim',
                pending=['numeric QK/SU/PV integration','die-level retained option exact replay','external HBM writer coherency or exclusion'])
    (ROOT/'results/rtl/v41_window_retention_gate.json').write_text(json.dumps(record,indent=2)+'\n')
    return record
if __name__=='__main__':
    x=run();print('RETENTION_GATE_PASS cases=%d saved_fixture_cycles=%d saved_sectors=%d'%(len(x['cases']),x['saved_fixture_cycles'],x['saved_sectors']))

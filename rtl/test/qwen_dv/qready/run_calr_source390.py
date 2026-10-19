#!/usr/bin/env python3
"""Replay exact archived390 commands through current native CALR ROM port.
This is a capacity/port regression; archived body is not current production.
"""
import hashlib,json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(root/'tools/qwen_layerbench'))
from calendar_rom_image import compile_image,emit
src=root/'results/rtl/qw_calr_capacity_1019/source_layer_s1.json'
raw=src.read_bytes();doc=json.loads(raw);events=doc['events'];assert len(events)==390
last=0;entries=[]
for e in events:
    delta=e['edge_w5']-last;last=e['edge_w5'];assert 0<delta<4096
    entries.append((delta,int(e['cmd'],16)))
segments=dict(boot=[],init=[],decode=entries,head=[])
receipt,words=compile_image(segments,hashlib.sha256(raw).hexdigest())
assert receipt['entries']==392 and receipt['ranges']['decode']==dict(first=0,count=390)
# compile_image pads head to4 entries. The selected region is exactly390;
# native NENT390 below deliberately excludes the two unreachable padding words.
receipt['source_entries']=390;receipt['scope']='archived dv2f14bi ROM capacity/transport only; no numerical execution or current production admission'
work=Path(sys.argv[1]);work.mkdir(parents=True,exist_ok=True);emit(work,receipt,words)
vl=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
sources=['rtl/test/qwen_dv/qready/tb_qready_calr_source390.sv','rtl/qwen_dv/qfd_dv_calendar_rom.sv','physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v']
for mut in (0,1):
    out=work/f'obj_m{mut}'
    cmd=[str(vl),'--binary','--timing','-Wno-fatal','-j','2','--top-module','tb_qready_calr_source390',f'-GMUT={mut}','--Mdir',str(out)]+[str(root/s) for s in sources]
    with (work/f'build_m{mut}.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
    r=subprocess.run([str(out/'Vtb_qready_calr_source390'),f'+EXPECTED={work}/expected.hex',f'+OT_ROM_DIR={work}'],capture_output=True,text=True)
    (work/f'm{mut}.log').write_text(r.stdout+r.stderr)
    if mut==0:assert r.returncode==0 and 'CALR_SOURCE390_ROM_PASS checks=14896' in r.stdout,r.stdout
    else:assert r.returncode!=0 and 'CAL_DATA_MISMATCH' in r.stdout,r.stdout
print('CALR_SOURCE390_NATIVE_PASS exact390 commands all38stages4users; address mutant causal FAIL')

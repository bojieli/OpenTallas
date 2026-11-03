"""Apply the normal native GEN macro pin-grid rule to a new disabled candidate."""
import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('candidate',type=Path);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--backend',type=Path,required=True);p.add_argument('--tracks',type=Path,required=True)
    p.add_argument('--macro-lef',type=Path,required=True);a=p.parse_args()
    assert not a.out.exists();a.out.mkdir()
    sys.path.insert(0,str(a.backend.parent));spec=importlib.util.spec_from_file_location('programme_native_snap_backend',a.backend)
    backend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend)
    m=json.loads((a.candidate/'model.json').read_text());master='ot_sram_1r1w_512x256_m1_r2c2'
    before=[dict(inst=q['name'],xy_um=q['rect_um'][:2],orient='R0',macro=master)for q in m['macros']]
    placements,moves=backend.snap_macro_placement(before,a.tracks.read_text(),lambda _:a.macro_lef.read_text(),m['outline_um'])
    for q,r in zip(m['macros'],placements):
        assert q['name']==r['inst'];x,y=r['xy_um'];q['rect_um']=[x,y,x+96.552,y+69.66]
    m['normal_native_macro_pin_grid_snap']=dict(backend=str(a.backend),moves=moves)
    (a.out/'model.json').write_text(json.dumps(m,indent=2)+'\n')
    for f in ('actual_FF_rows.csv','native_pins.json','native_pins_clock_entry.json','source_clock_sink_map.json'):
        shutil.copyfile(a.candidate/f,a.out/f)
    print('NORMAL_GEN_NATIVE_MACRO_SNAP',len(moves),'moves',max(max(abs(q['dx_nm']),abs(q['dy_nm']))for q in moves),'nm; new candidate only',flush=True)


if __name__=='__main__':main()

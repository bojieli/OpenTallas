#!/usr/bin/env python3
"""Map one full 32-lease native CAM; area evidence, not timing qualification."""
import argparse
from collections import Counter
import hashlib,json,re,subprocess,tempfile
from pathlib import Path
from map_hbm_svc_dma_sram_bank_wide import blocks

ROOT=Path(__file__).resolve().parents[1]
RTL='rtl/ot_hbm_svc_dma_pc_tile_wide.sv'
TOP='ot_hbm_svc_dma_pc_tile_wide'

def run(libdir):
    libs=sorted(libdir.glob('*asap7*RVT_SS*.lib'))
    assert len(libs)==5
    cells={}
    first=libs[0].read_text()
    header=first[:re.search(r'\bcell\s*\(',first).start()]
    for p in libs:cells.update(blocks(p.read_text()))
    areas={k:float(re.search(r'\barea\s*:\s*([\d.]+)',v).group(1)) for k,v in cells.items()}
    with tempfile.TemporaryDirectory(prefix='hbm-native32-map-') as td:
        merged=Path(td)/'merged.lib';mapped=Path(td)/'mapped.json'
        merged.write_text(header+'\n'.join(cells.values())+'\n}\n')
        script=(f'read_verilog -sv {RTL}; hierarchy -check -top {TOP}; '
                f'synth -top {TOP} -flatten; dfflibmap -liberty {merged}; '
                f'abc -liberty {merged}; clean; stat -liberty {merged}; write_json {mapped}')
        proc=subprocess.run(['yosys','-Q','-T','-p',script],cwd=ROOT,capture_output=True,text=True)
        if proc.returncode:raise RuntimeError(proc.stdout[-4000:]+proc.stderr)
        count=Counter(c['type'] for c in json.loads(mapped.read_text())['modules'][TOP]['cells'].values())
    unknown={k:v for k,v in count.items() if k not in areas}
    return dict(schema=1,verdict='PASS_mapped_shape' if not unknown else 'FAIL_unmapped_cells',
                leases=32,metadata_bits=32*(1+17+4+4),mapped_cell_counts=dict(count),
                mapped_logic_area_um2_per_PC=sum(n*areas[k] for k,n in count.items() if k in areas),
                unmapped_cells=unknown,mutable_metadata_protected=False,
                adoption_gate='HOLD: protected native metadata successor and SS/FF context timing required',
                scope='one actual full-depth native lease controller; no central data-array synthesis, no physical closure claim',
                RTL_source_sha256={RTL:hashlib.sha256((ROOT/RTL).read_bytes()).hexdigest()},
                liberty_source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in libs})

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--lib-dir',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();result=run(args.lib_dir)
    with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))
    raise SystemExit(result['verdict']!='PASS_mapped_shape')

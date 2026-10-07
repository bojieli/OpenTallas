#!/usr/bin/env python3
from pathlib import Path
import subprocess,json,sys,copy
import argparse
p=argparse.ArgumentParser(description='Map the full parent leaves with real hard-macro declarations and audit retained state.');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
C=Path(__file__).resolve().parents[1];R=a.out.resolve()
if R.exists():raise ValueError('new immutable output directory required')
R.mkdir(parents=True)
from check_qwen_embedding_parent_storage import check
import shutil
Y=Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys';Y=str(Y) if Y.exists() else shutil.which('yosys')
if not Y:raise ValueError('Yosys required')
lib=C/'results/uarch/topk_station_SSFF_cell_model_20261002/inputs/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib'
results=[]
for kind in ('code','scale'):
    top=f'ot_qwen_embed_{kind}_bank_parent'
    macro='ot_rom_4096x266_m8' if kind=='code' else 'ot_rom_4096x128_m8'
    # Find the actual macro inventory from the source.
    cfg=(C/f'physical/qwen_die_masters/cfg/qfd_embed_{kind}_bank_parent.env').read_text()
    import re
    bbs=re.findall(r'physical/asap7_memory_macros/[^\s\']+_bb.v',cfg)
    sources=[C/f'physical/qwen_embedding_parent/{kind}/ingress_bb.v',C/f'rtl/physical/{top}.sv']+[C/b for b in bbs]
    script='read_verilog -sv '+' '.join(str(p) for p in sources)+'; '
    if kind=='scale':script+=f'chparam -set BANK_ID 2 {top}; '
    script+=f'synth -top {top}; dfflibmap -liberty {lib}; opt_clean; write_json {R/kind}.json; write_verilog -noexpr {R/kind}.v'
    with (R/f'{kind}_map.log').open('w') as f:subprocess.run([Y,'-Q','-T','-p',script],stdout=f,stderr=subprocess.STDOUT,check=True)
    m=json.loads((R/f'{kind}.json').read_text())['modules'][top]
    good=check(m,kind);results.append(dict(kind=kind,test='full_shape_mapping',result=good))
    for mode in ('flattened','aliased'):
        bad=copy.deepcopy(m)
        if mode=='flattened':del bad['cells']['u_ingress']
        else:bad['cells']['u_ingress']['connections']['address_n']=bad['cells']['u_ingress']['connections']['address_q']
        try:check(bad,kind)
        except ValueError as e:results.append(dict(kind=kind,test=mode,result='REJECTED',reason=str(e)))
        else:raise RuntimeError('mutant escaped '+mode)
(R/'mapped_validation.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))

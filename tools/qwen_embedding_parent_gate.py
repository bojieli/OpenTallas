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

def wire_cases(m,kind):
    rows=[]
    for mode in ('buffered','double_inverted','inverted_clock','swapped_address','logic_cone','cycle'):
        n=copy.deepcopy(m);nextbit=max(b for x in n['netnames'].values() for b in x['bits'] if isinstance(b,int))+1
        def cell(name,a,inv=False):
            nonlocal nextbit
            b=nextbit;nextbit+=1
            n['cells'][name]=dict(type=('INVx1' if inv else 'BUFx2')+'_ASAP7_75t_R',connections={'A':[a],'Y':[b]})
            return b
        co=n['cells']['u_ingress']['connections']
        for pin in ('clk','rst_n','address','valid','credit'):
            co[pin]=[cell('repair_'+pin+str(i),b) for i,b in enumerate(co[pin])]
        n['netnames']['iv_q']['bits']=[cell('repair_macro_output',co['valid_q'][0])]
        if mode=='double_inverted':co['clk']=[cell('inv2',cell('inv1',co['clk'][0],True),True)]
        elif mode=='inverted_clock':co['clk']=[cell('bad_inv',co['clk'][0],True)]
        elif mode=='swapped_address':co['address'][0],co['address'][1]=co['address'][1],co['address'][0]
        elif mode=='logic_cone':n['cells']['repair_clk0']['type']='AND2x2_ASAP7_75t_R';n['cells']['repair_clk0']['connections']['B']=['1']
        elif mode=='cycle':n['cells']['repair_clk0']['connections']['A']=co['clk']
        expected=mode in ('buffered','double_inverted')
        try:check(n,kind);accepted=True
        except (ValueError,AssertionError):accepted=False
        if accepted!=expected:raise RuntimeError('incorrect physical wire verdict '+kind+' '+mode)
        rows.append(dict(kind=kind,test=mode,accepted=accepted,expected=expected))
    return rows

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
    results.extend(wire_cases(m,kind))
(R/'mapped_validation.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))

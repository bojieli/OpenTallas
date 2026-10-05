#!/usr/bin/env python3
"""Exact76BUF source materialization/count/functional gate; no STA credit."""
import argparse,gzip,hashlib,json,re
from pathlib import Path
from qwen_rom_bank5_control_gate import ROOT,OUT,YOSYS,validate_model
from qwen_rom_hold_capture_loaded_map import block
from qwen_rom_kv_finite_window_gate import guarded_process
SOURCE='rtl/physical/ot_qwen_rom_bank5_control_distribution.sv'
BENCH='rtl/test/qwen_rom_capture/tb_qwen_rom_bank5_distribution.sv'

def run(work,result):
    if work.exists() or result.exists():raise ValueError('Refusing overwrite')
    model=validate_model();work.mkdir(parents=True)
    raw={p:(ROOT/p).read_bytes() for p in [SOURCE,BENCH,'tools/qwen_rom_bank5_distribution_gate.py']}
    for corner in ['ss','ff']:
        lib=gzip.decompress((OUT/'model_packet/inputs'/('invbuf_'+corner+'.lib.gz')).read_bytes()).decode()
        at=re.search(r'\bcell\s*\(\s*BUFx4_ASAP7_75t_R\s*\)',lib)
        cell=block(lib,at.start())
        assert re.search(r'\bfunction\s*:\s*"A"',cell)
        assert abs(float(re.search(r'\barea\s*:\s*([\d.]+)',cell)[1])-model['cost']['BUF_cell_um2'])<1e-8
        (work/('invbuf_'+corner+'.lib')).write_text(lib)
    steps=[]
    for case,text in [('positive',raw[SOURCE]),('wrong_bank_owner',raw[SOURCE].replace(b'.A(bank_read_n[bank])',b'.A(bank_read_n[0])'))]:
        path=work/(case+'.sv');path.write_bytes(text);binary=work/(case+'.vvp')
        for phase,cmd in [('build',['iverilog','-g2012','-s','tb_qwen_rom_bank5_distribution','-o',str(binary),str(path),str(ROOT/BENCH)]),('run',['vvp',str(binary)])]:
            rc,out=guarded_process(cmd,work,work/(case+'_'+phase+'.log'))
            steps.append(dict(case=case,phase=phase,returncode=rc,output=out))
            if rc:break
    source=work/'distribution.sv';source.write_bytes(raw[SOURCE])
    script=work/'elaborate.ys';script.write_text(f'''read_liberty -lib {work/'invbuf_ss.lib'}
read_verilog -sv {source}
hierarchy -check -top ot_qwen_rom_bank5_control_distribution
proc
write_json {work/'elaborated.json'}
stat
''')
    rc,out=guarded_process([YOSYS,'-s',str(script)],work,work/'elaborate.log')
    net=json.loads((work/'elaborated.json').read_text())['modules']['ot_qwen_rom_bank5_control_distribution'] if rc==0 else {}
    cells=net.get('cells',{});counts={k:sum(marker in name for name in cells) for k,marker in [('bank_strobe_output_buffers','g_strobe['),('bank_hold_select_output_buffers','g_term['),('low_address_root_leaf_buffers','g_address['),('reset_root_mid_leaf_buffers','reset')]}
    topology={}
    for name,c in cells.items():
        bit=c['connections']['Y'][0]
        input_sinks=[n for n,v in cells.items() if bit in v['connections']['A']]
        output_sinks=[(port,i) for port,v in net['ports'].items() if v['direction']=='output' for i,b in enumerate(v['bits']) if b==bit]
        topology[name]={'type':c['type'],'cell_input_sinks':input_sinks,'output_sink_count':len(output_sinks),'keep':c['attributes'].get('keep')}
    positive=next(s for s in steps if s['case']=='positive' and s['phase']=='run')
    negative=next(s for s in steps if s['case']=='wrong_bank_owner' and s['phase']=='run')
    good=rc==0 and len(cells)==76 and counts==model['fixed_candidate']['buffer_counts'] and all(c['type']=='BUFx4_ASAP7_75t_R' for c in cells.values()) and positive['returncode']==0 and negative['returncode']!=0 and 'read bank ownership' in negative['output']
    stable=all((ROOT/p).read_bytes()==data for p,data in raw.items())
    record=dict(schema='opentallas.qwen-rom-bank5-buffer-materialization.v1',status='PASS_EXACT76BUF_SOURCE_AND_OWNERSHIP' if good and stable else 'FAIL',
        model_commit='cdcbe60a34389a5671f9e303c4f5023e83b23710',buffer_counts=counts,source_sha256={p:hashlib.sha256(data).hexdigest() for p,data in raw.items()},source_stable=stable,
        cell_topology=topology,steps=steps,elaboration_returncode=rc,buffer_cell_function='Y=A, source-pinned SS/FF Liberty',
        bank5FF_literal_gate='37df27f69',all76BUF_materialized_in_component=True,connected_to_actual_tile=False,
        reset_release_producer_implemented=False,upstream_address_mapped_arrivals=False,actual_context_STA_admitted=False,
        scope='Real BUFx4 instances and finite topology; functional fourstate ownership fixture and technology-library elaboration only. No wire/skew/hold/setup or fulltile credit.',
        tile_PR=False,adoption=False)
    result.parent.mkdir(parents=True,exist_ok=True)
    with result.open('x') as f:json.dump(record,f,indent=2,sort_keys=True);f.write('\n')
    print(record['status']);return 0 if good and stable else 1

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--workdir',type=Path,required=True);ap.add_argument('--result',type=Path,required=True)
    args=ap.parse_args();raise SystemExit(run(args.workdir,args.result))

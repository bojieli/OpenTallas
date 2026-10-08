#!/usr/bin/env python3
"""Minimum exact transport and scoped production sequential/clock mapping gate."""
import argparse, gzip, hashlib, json, subprocess, tempfile, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RTL='rtl/physical/ot_qwen_die_link_fwd_full_tmr.sv'
TB='rtl/test/tb_qwen_die_link_fwd_full_tmr.sv'
TOP='ot_qwen_die_link_fwd_full_tmr'
BASE='results/uarch/topk_station_SSFF_cell_model_20261002/inputs/'
SEQ=BASE+'asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib'
INV=BASE+'asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz'
SIMPLE=BASE+'asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--library-root',type=Path,default=ROOT);p.add_argument('--yosys',required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);cases=[];maps=[]
    with tempfile.TemporaryDirectory(prefix='qwen-fwd-') as d:
        d=Path(d)
        for nl,neg in [(1,0),(2,0),(2,1),(2,2),(2,3)]:
            key=f'nl{nl}_neg{neg}'
            subprocess.run(['iverilog','-g2012','-s','tb_qwen_die_link_fwd_full_tmr',f'-Ptb_qwen_die_link_fwd_full_tmr.NL={nl}',f'-Ptb_qwen_die_link_fwd_full_tmr.NEG={neg}','-o',str(d/'bench'),str(ROOT/RTL),str(ROOT/TB)],check=True,capture_output=True)
            run=subprocess.run(['vvp',str(d/'bench')],capture_output=True,text=True)
            (a.out/(key+'.log')).write_text(run.stdout+run.stderr)
            passed=run.returncode==0 and 'PASS NL=' in run.stdout
            rejected=run.returncode!=0 and ('exact mismatch' in run.stdout or 'clock ownership mismatch' in run.stdout)
            cases.append(dict(case=key,returncode=run.returncode,expected_failure=bool(neg),qualified=rejected if neg else passed))
        inv=gzip.decompress((a.library_root/INV).read_bytes()).decode()
        simple=gzip.decompress((a.library_root/SIMPLE).read_bytes()).decode()
        # Add SIMPLE cells to permit ABC library construction (INVBUF alone
        # has only two classes and ABC rejects it). Only clock leaf is mapped.
        (d/'inv.lib').write_text(inv[:inv.rfind('}')]+simple[simple.index('cell ('):simple.rfind('}')]+ '\n}\n')
        for nl in [1,2]:
            script=f'read_verilog -sv {ROOT/RTL}; chparam -set ENABLE 1 -set NL {nl} {TOP}; synth -top {TOP}; dfflibmap -liberty {a.library_root/SEQ}; abc -liberty {d}/inv.lib ; opt_clean; read_liberty -lib {a.library_root/SEQ}; read_liberty -lib {d}/inv.lib; check -assert; write_json {d}/net.json'
            run=subprocess.run([a.yosys,'-Q','-T','-p',script],capture_output=True,text=True)
            (a.out/f'mapped_nl{nl}.log').write_text(run.stdout+run.stderr)
            if run.returncode: raise RuntimeError(run.stderr)
            modules=json.loads((d/'net.json').read_text())['modules'];top=modules[TOP]
            dirs=[c for c in top['cells'].values() if 'ot_qwen_link_fwd_direction_tmr' in c['type']]
            assert len(dirs)==2*nl
            dm=modules[dirs[0]['type']]
            ffs={n:c for n,c in dm['cells'].items() if c['type'].startswith('DFF') and c['type'].endswith('_ASAP7_75t_R')}
            drivers={b:n for n,c in ffs.items() for port in ['Q','QN'] for b in c['connections'].get(port,[])}
            inverters={c['connections']['Y'][0]:c['connections']['A'][0] for c in dm['cells'].values() if c['type']=='$_NOT_' or c['type'].startswith('INV')}
            def driver(bit):
                seen=set()
                while bit in inverters and bit not in seen: seen.add(bit);bit=inverters[bit]
                return drivers.get(bit)
            payload=[driver(b) for b in dm['ports']['d_o']['bits']]
            assert None not in payload and len(set(payload))==528
            assert len(ffs)==534
            rails=[driver(bit) for n in ['release0','release1'] for bit in dm['netnames'][n]['bits']]
            assert None not in rails and len(set(rails))==6, 'Release storage merged'
            assert all(ffs[n]['connections']['RESETN']==dm['ports']['rst_n']['bits'] for n in rails)
            control=[driver(bit) for bit in dm['netnames']['control_q']['bits']]
            assert len(set(control))==16
            assert all(ffs[n]['connections']['RESETN']==dm['netnames']['release_run']['bits'] for n in control), 'Control clear is not local synchronized majority'
            assert all(c['connections']['CLK']==dm['ports']['fclk_i']['bits'] for c in ffs.values()), 'Shared/wrong clock'

            texts=[(a.library_root/SEQ).read_text(),inv,simple]
            areas={name:float(area) for text in texts for name,area in re.findall(r'cell\s*\(([^)]+)\)\s*\{.*?area\s*:\s*([0-9.eE+-]+)',text,re.S)}
            mapped_area=sum(areas[c['type']] for c in dm['cells'].values() if c['type'] in areas)
            comb_driver={bit:(n,c) for n,c in dm['cells'].items() if n not in ffs for port,direction in c['port_directions'].items() if direction=='output' for bit in c['connections'][port]}
            cone={}
            def visit(bit):
                if bit not in comb_driver:return
                n,c=comb_driver[bit]
                if n in cone:return
                cone[n]=c
                for port,direction in c['port_directions'].items():
                    if direction=='input':
                        for b in c['connections'][port]:visit(b)
            visit(dm['netnames']['release_run']['bits'][0])
            release_cone_area=sum(areas[c['type']] for c in cone.values())
            clk=[(n,c) for n,c in dm['cells'].items() if c['type']=='ot_qwen_link_fwd_inv_tmr']
            assert len(clk)==2
            byname=dict(clk)
            assert byname['inv0']['connections']['a']==dm['ports']['fclk_i']['bits']
            assert byname['inv0']['connections']['y']==byname['inv1']['connections']['a']
            assert byname['inv1']['connections']['y']==dm['ports']['fclk_o']['bits']
            leaf=list(modules['ot_qwen_link_fwd_inv_tmr']['cells'].values())
            assert len(leaf)==1 and leaf[0]['type'].startswith('INV') and 'ASAP7' in leaf[0]['type']
            # Direction ownership and distinct output nets at the hierarchical top.
            outs=[]
            for c in dirs:
                outs+=c['connections']['d_o']
                assert c['connections']['fclk_i'][0] in top['ports']['fclk_ab_i']['bits']+top['ports']['fclk_ba_i']['bits']
            assert len(set(outs))==1056*nl
            maps.append(dict(NL=nl,total_state_FF=534*2*nl,distinct_word_FF=528*2*nl,clock_inverters=4*nl,clock_cell=leaf[0]['type'],release_FF=6*2*nl,raw_POR_FF=6*2*nl,local_majority_clear_FF=16*2*nl,release_logic_cells_per_stream=[c['type'] for c in cone.values()],release_logic_area_um2=release_cone_area*2*nl,full_mapped_area_um2=(mapped_area+2*areas[leaf[0]['type']])*2*nl,netlist_sha256=sha(d/'net.json'),qualified=True))
        mutant=(ROOT/RTL).read_text().replace('(* keep = 1, dont_touch = 1 *) always @(posedge fclk_i or negedge rst_n)', 'always @(posedge fclk_i or negedge rst_n)')
        (d/'merged_rails.sv').write_text(mutant)
        script=f'read_verilog -sv {d}/merged_rails.sv; chparam -set ENABLE 1 -set NL 2 {TOP}; synth -top {TOP}; write_json {d}/merged.json'
        run=subprocess.run([a.yosys,'-Q','-T','-p',script],capture_output=True,text=True)
        (a.out/'merged_rails.log').write_text(run.stdout+run.stderr)
        assert run.returncode==0,run.stderr
        mods=json.loads((d/'merged.json').read_text())['modules']
        cells=[c for c in mods[TOP]['cells'].values() if 'ot_qwen_link_fwd_direction_tmr' in c['type']]
        dm=mods[cells[0]['type']]
        rail_bits=[bit for n in ['release0','release1'] for bit in dm['netnames'][n]['bits']]
        assert len(set(rail_bits))<6, 'Stripped-process-attribute control did not reproduce shared storage'
        cases.append(dict(case='mapped_shared_storage_negative',expected_failure=True,qualified=True,distinct_release_bits=len(set(rail_bits)),mutant_sha256=hashlib.sha256(mutant.encode()).hexdigest()))
    result=dict(schema='opentallas.qwen_forwarded_link_tmr.component_gate.v1',pass_all=all(c['qualified'] for c in cases+maps),functional=cases,mapping=maps,
      source_sha256={x:sha(ROOT/x) for x in [RTL,TB,'tools/qwen_link_forwarded_tmr_gate.py']},library_sha256={x:sha(a.library_root/x) for x in [SEQ,INV,SIMPLE]},
      yosys_version=subprocess.check_output([a.yosys,'-V'],text=True).strip(),yosys_sha256=sha(Path(a.yosys)),
      scope='Minimum full NL2 two-hop zero-delay RTL and ASAP7 sequential plus clock-inverter mapping. All data/reset logic mapped for area; P&R, full link protection, clock insertion/hold race and root reset remain unqualified.',adoption=False)
    result['log_sha256']={x.name:sha(x) for x in sorted(a.out.glob('*.log'))}
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if not result['pass_all']:raise SystemExit(1)
if __name__=='__main__': main()

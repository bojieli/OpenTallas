#!/usr/bin/env python3
"""Minimum exact transport and scoped production sequential/clock mapping gate."""
import argparse, gzip, hashlib, json, subprocess, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RTL='rtl/physical/ot_qwen_die_link_fwd_full.sv'
TB='rtl/test/tb_qwen_die_link_fwd_full.sv'
TOP='ot_qwen_die_link_fwd_full'
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
            subprocess.run(['iverilog','-g2012','-s','tb_qwen_die_link_fwd_full',f'-Ptb_qwen_die_link_fwd_full.NL={nl}',f'-Ptb_qwen_die_link_fwd_full.NEG={neg}','-o',str(d/'bench'),str(ROOT/RTL),str(ROOT/TB)],check=True,capture_output=True)
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
            script=f'read_verilog -sv {ROOT/RTL}; chparam -set ENABLE 1 -set NL {nl} {TOP}; synth -top {TOP}; dfflibmap -liberty {a.library_root/SEQ}; abc -liberty {d}/inv.lib ot_qwen_link_fwd_inv; opt_clean; read_liberty -lib {a.library_root/SEQ}; read_liberty -lib {d}/inv.lib; check -assert; write_json {d}/net.json'
            run=subprocess.run([a.yosys,'-Q','-T','-p',script],capture_output=True,text=True)
            (a.out/f'mapped_nl{nl}.log').write_text(run.stdout+run.stderr)
            if run.returncode: raise RuntimeError(run.stderr)
            modules=json.loads((d/'net.json').read_text())['modules'];top=modules[TOP]
            dirs=[c for c in top['cells'].values() if 'ot_qwen_link_fwd_direction' in c['type']]
            assert len(dirs)==2*nl
            dm=modules[dirs[0]['type']]
            ffs={n:c for n,c in dm['cells'].items() if c['type'].startswith('DFF') and c['type'].endswith('_ASAP7_75t_R')}
            drivers={b:n for n,c in ffs.items() for port in ['Q','QN'] for b in c['connections'].get(port,[])}
            inverters={c['connections']['Y'][0]:c['connections']['A'][0] for c in dm['cells'].values() if c['type']=='$_NOT_'}
            def driver(bit):
                seen=set()
                while bit in inverters and bit not in seen: seen.add(bit);bit=inverters[bit]
                return drivers.get(bit)
            payload=[driver(b) for b in dm['ports']['d_o']['bits']]
            assert None not in payload and len(set(payload))==528
            assert len(ffs)==530
            clk=[(n,c) for n,c in dm['cells'].items() if c['type']=='ot_qwen_link_fwd_inv']
            assert len(clk)==2
            byname=dict(clk)
            assert byname['inv0']['connections']['a']==dm['ports']['fclk_i']['bits']
            assert byname['inv0']['connections']['y']==byname['inv1']['connections']['a']
            assert byname['inv1']['connections']['y']==dm['ports']['fclk_o']['bits']
            leaf=list(modules['ot_qwen_link_fwd_inv']['cells'].values())
            assert len(leaf)==1 and leaf[0]['type'].startswith('INV') and 'ASAP7' in leaf[0]['type']
            # Direction ownership and distinct output nets at the hierarchical top.
            outs=[]
            for c in dirs:
                outs+=c['connections']['d_o']
                assert c['connections']['fclk_i'][0] in top['ports']['fclk_ab_i']['bits']+top['ports']['fclk_ba_i']['bits']
            assert len(set(outs))==1056*nl
            maps.append(dict(NL=nl,total_state_FF=530*2*nl,distinct_word_FF=528*2*nl,clock_inverters=4*nl,clock_cell=leaf[0]['type'],netlist_sha256=sha(d/'net.json'),qualified=True))
    result=dict(schema='opentallas.qwen_forwarded_link.component_gate.v1',pass_all=all(c['qualified'] for c in cases+maps),functional=cases,mapping=maps,
      source_sha256={x:sha(ROOT/x) for x in [RTL,TB,'tools/qwen_link_forwarded_gate.py']},library_sha256={x:sha(a.library_root/x) for x in [SEQ,INV,SIMPLE]},
      yosys_version=subprocess.check_output([a.yosys,'-V'],text=True).strip(),yosys_sha256=sha(Path(a.yosys)),
      scope='Minimum full NL2 two-hop zero-delay RTL and ASAP7 sequential plus clock-inverter mapping. Data combinational mapping, P&R, protection, clock insertion/hold race and root reset are unqualified.',adoption=False)
    result['log_sha256']={x.name:sha(x) for x in sorted(a.out.glob('*.log'))}
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if not result['pass_all']:raise SystemExit(1)
if __name__=='__main__': main()

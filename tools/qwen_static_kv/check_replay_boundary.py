#!/usr/bin/env python3
"""Prepare/execute source-pinned real ABI one-block replay join. COMPONENT ONLY."""
import argparse,hashlib,json,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PATHS=['rtl/qwen_sys/static_kv_20261014/'+x+'.sv' for x in
 ['ot_qkd_static_emb_cdc','qkd_static_kv_write_observer','qkd_ctrl_pc_host_static',
  'ot_qkd_static_ctrl_pc_emb','ot_qkd_static_kv_timing','qkd_static_kv_return_calendar',
  'qkd_static_kv_return_slots','qkd_kv_hbm_elastic_front','qkd_kv_calendar_replay']]
PATHS+=['rtl/qwen_sys/kv_die_20261009/ot_qkvd_kcmd_tap.sv',
 'rtl/qwen_sys/emb_hbm_20261008/synth/ot_qfd_emb_pcport.sv',
 'rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_cdc.sv',
 'rtl/qwen_sys/q5_20261009/synth/ot_qfd_kv_landing_ecc.sv',
 'rtl/qwen_sys/host_20261013/qkd_host_static_pc.sv','rtl/lib/ot_async_fifo.sv',
 'rtl/lib/ot_reset_sync.sv','rtl/test/qwen_static_kv/tb_qkd_kv_replay_boundary.sv']

def prepare(out):
    out.mkdir(parents=True,exist_ok=False)
    for p in PATHS:
        dest=out/'source'/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/p,dest)
    (out/'source_manifest.json').write_text(json.dumps({p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in PATHS},indent=2)+'\n')
    shutil.copy2(__file__,out/'execute.py')

def execute(out):
    manifest=json.loads((out/'source_manifest.json').read_text())
    for p,s in manifest.items():
        if hashlib.sha256((out/'source'/p).read_bytes()).hexdigest()!=s:raise RuntimeError('source changed '+p)
    sources=[str(out/'source'/p) for p in manifest]
    if True:
        with (out/'build.log').open('w') as f:
            subprocess.run(['verilator','--binary','--timing','-Wno-fatal','-j','2',
              '--top-module','tb_qkd_kv_replay_boundary','--Mdir',str(out/'obj'),*sources],stdout=f,stderr=subprocess.STDOUT,check=True)
    runs=[]
    cases=[(0,phase,jit) for phase in (137,637) for jit in (0,8,16)]
    cases += [(mode,137,16) for mode in (1,2,3,4)]
    for mode,phase,jit in cases:
        name=f'm{mode}_p{phase}_j{jit}'
        result=subprocess.run([str(out/'obj/Vtb_qkd_kv_replay_boundary'),f'+mode={mode}',f'+phase={phase}',f'+jit={jit}'],capture_output=True,text=True)
        text=result.stdout+result.stderr;(out/(name+'.log')).write_text(text)
        passed=result.returncode==0 and 'PASS actual replay/controller/front/ring' in text
        failed=result.returncode!=0 and 'BOUNDARY_FAIL' in text and 'MEASURE' in text
        if (not passed if mode==0 else not failed):raise RuntimeError('component case failed '+name)
        runs.append(dict(name=name,exit=result.returncode,mutant_rejected=bool(mode),measure=next(t for t in text.splitlines() if t.startswith('MEASURE'))))
    report=dict(status='PASS_COMPONENT_ONLY',source_sha256=manifest,
      gate_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      binary_sha256=hashlib.sha256((out/'obj/Vtb_qkd_kv_replay_boundary').read_bytes()).hexdigest(),
      physical_qualified=False,production_installable=False,full_token_qualified=False,
      actual_blocks=['PROFILE0 persistent controller + pcport/ECC','4x8 elastic front','DEPTH8 dual-clock return ring','HBM64 and CORE33 boot-flop replay'],
      independent_contract=dict(pc=0,sector_count=8,sector_bits=256,row=67,epoch=7,layer=3,
        desc_cycle=10,go_cycle=40,reservation_cycles=list(range(60,68)),blk_go_cycle=115,
        phy_rl=23,phy_extra_window=[0,16],hbm_period_ps=1024,core_period_ps=833.334,
        origin='internal leaf start edge index101 in each domain',
        core_first='ceil((HBM_origin+160*1024-CORE_origin)/833.334)',
        physical_cycle_inputs='DECLARED_COMPONENT_BOUNDARY_STIMULI_NOT_MEASURED_PATHS',
        discovery_or_output_trace_used=False),
      fault_cases={'1':'reservation time image +1; independently fixed PHY edge checker fails',
                  '2':'block release image -1; independently fixed front edge checker fails',
                  '3':'CORE expected-sector image XOR1; actual ring metadata check fails',
                  '4':'last PHY read +32 beyond declared window; real front hold/slot mismatch fails'},
      runs=runs,
      missing=['512-sector K/V/full128PC/full36 stage calendar and actual consumer/landing lifetimes',
               'persistent HOST boot/ingest/writeback state and physical path/phase schedule',
               'full-image control storage/boot loader/slot grant/TT/FF/DRC and total cost',
               'writer and return integration adoption; both remain HELD'],
      limitation='One full8-sector block is the minimum actual mechanism proof; arbitrary payloads and metadata are external test stimuli, no production die ties or missing producer substitution. Native fullshape schedule remains OPEN.')
    (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(runs),'actual ABI cases')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path)
    p.add_argument('--prepare-only',action='store_true');p.add_argument('--execute-only',action='store_true')
    a=p.parse_args();a.out=a.out.resolve()
    if not a.execute_only:prepare(a.out)
    if not a.prepare_only:execute(a.out)

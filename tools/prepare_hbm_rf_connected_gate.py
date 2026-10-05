#!/usr/bin/env python3
"""Prepare source-pinned RF connected gate only; never launch compilation."""
import ast,hashlib,json,subprocess,sys
import full_sm_rf_verilator_gate as G
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAXWELL='01d277491e6b0b504947658a7c0a750b694ef142'
OUT=ROOT/'results/uarch/hbm_rf_visibility_fence_20261002'
PROPOSAL='prepared_gate_runner_r3.json'
V=Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator')
RUNNER_CAPS=dict(cpus=[24,25,26,27],memory_bytes=32*1024**3,swap_bytes=0,whole_wall_s=2220,per_file_bytes=1024**3,aggregate_output_bytes=8*1024**3,disk_headroom_bytes=12*1024**3,poll_s=1,kill_grace_s=5,sequential_targets=True,build_jobs=4)
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(rev,p):return subprocess.check_output(['git','show',rev+':'+p],cwd=ROOT)
def prepare():
    tree=ast.parse(blob(MAXWELL,'tools/hbm_connected_service_model.py'))
    lists={}
    for n in tree.body:
        if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('COMMON','EXTRA','PROVIDER'):
            lists[n.targets[0].id]=ast.literal_eval(n.value)
    originals=lists['COMMON']+lists['EXTRA']+lists['PROVIDER']
    for p in originals:
        rev='2e75bab2efa022f60d98bd8511a3027da56951ce' if p in lists['PROVIDER'] else 'e72abea5ae169d3167dddc89543013f0e6bb3a7a'
        assert (ROOT/p).read_bytes()==blob(rev,p),p+' changed original'
    for local,parent in [('ot_gpu_matrix_capture_audit.sv','ot_gpu_matrix_capture_audit.sv'),('scale_sram_model.sv','scale_sram_model.sv')]:
        assert (ROOT/'rtl/test/hbm_rf_visibility'/local).read_bytes()==blob(MAXWELL,'rtl/test/hbm_connected_service/'+parent)
    new=['rtl/gpu/ot_gpu_rf_visibility_fence.sv','rtl/test/hbm_rf_visibility/ot_gpu_matrix_capture_audit.sv','rtl/test/hbm_rf_visibility/scale_sram_model.sv','rtl/test/hbm_rf_visibility/tb_connected_rf_visibility.sv']
    sources=originals+new
    assert len(set(sources))==len(sources) and not any('blackbox' in p for p in sources)
    shared='tools/full_sm_rf_verilator_gate.py'
    assert (ROOT/shared).read_bytes()==blob('b764cc45e57a632a8ea32284dad8ca30ebf8091a',shared), 'verified runner architecture changed'
    toolchain=G.prepare()['toolchain']
    toolchain['files_sha256'][str(Path(sys.executable).resolve())]=sha(Path(sys.executable).resolve().read_bytes())
    commands={}
    for q,label in [(0,'DS'),(1,'Qwen')]:
        obj=f'<fresh-output>/{label}/obj'
        commands[label]=[
          dict(phase='frontend',timeout_s=300,argv=[str(V),'--cc','--exe','--main','--timing','--assert','--top-module','tb_connected_rf_visibility',f'-GQWEN={q}','--prefix','Vconnected','--Mdir',obj,'--threads','1','--compiler','gcc','-O0','--unroll-count','512','-Wno-fatal','--output-split','10000','--output-split-cfuncs','500','-CFLAGS','-O0']+sources),
          dict(phase='CXX',timeout_s=600,argv=['make','-C',obj,'-f','Vconnected.mk','-j4','CXX=/usr/bin/g++','LINK=/usr/bin/g++','OPT_FAST=-O0','OPT_SLOW=-O0','OPT_GLOBAL=-O0']),
          dict(phase='simulation',timeout_s=180,argv=[obj+'/Vconnected'],stdout=f'<fresh-output>/{label}/actual_sim.log'),
          dict(phase='trace',timeout_s=30,argv=['python3','tools/check_hbm_rf_connected_trace.py',f'<fresh-output>/{label}/actual_sim.log','--out',f'<fresh-output>/{label}/trace_verdict.json'])]
    return dict(schema='opentallas.hbm-RF-connected.prepared-gate.v1',source_base='b764cc45e57a632a8ea32284dad8ca30ebf8091a',matrix_handoff=MAXWELL,
        source_sha256={p:sha((ROOT/p).read_bytes()) for p in sources},
        gate_tool_sha256={p:sha((ROOT/p).read_bytes()) for p in ['tools/check_hbm_rf_connected_trace.py','tools/prepare_hbm_rf_connected_gate.py','tools/test_hbm_rf_connected_preparation.py','tools/run_hbm_rf_connected_gate.py','tools/full_sm_rf_verilator_gate.py','tools/test_hbm_rf_connected_runner.py']},
        review_pins={p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in sorted(OUT.glob('model*.json'))},
        runner_caps=RUNNER_CAPS,verified_toolchain=toolchain,
        runner=dict(path='tools/run_hbm_rf_connected_gate.py',GO_schema='opentallas.hbm-RF-connected.GO.v1',argv=['<pinned-python>','tools/run_hbm_rf_connected_gate.py','--proposal','results/uarch/hbm_rf_visibility_fence_20261002/prepared_gate_runner_r3.json','--go','<committed-parent-GO.json>','--go-commit','<parent-GO-SHA>','--out','<fresh-output>'],parent_launch_affinity='taskset --cpu-list 24-27; runner verifies exactly four cores, never cpu.max',requires_named_service=True,external_monitor_required='Parent monitors named service terminal result/memory.events and preserves OOM/SIGKILL/whole-timeout if runner cannot write final verdict',permission_or_configuration_changes=False),
        compiler=dict(verilator=subprocess.check_output([str(V),'--version'],text=True).strip(),verilator_wrapper_sha256=sha(V.read_bytes()),verilator_binary_sha256=sha((V.parent/'verilator_bin').read_bytes()),gxx=subprocess.check_output(['/usr/bin/g++','--version'],text=True).splitlines()[0],gxx_sha256=sha(Path('/usr/bin/g++').read_bytes())),
        caps=dict(proposed_local_CPUs=[24,25,26,27],memory_GiB=32,swap_GiB=0,build_jobs=4,sequential_targets=True,whole_timeout_s=2220,FSIZE_bytes=1073741824,output_cap_GiB=8,disk_min_free_GiB=12,fresh_parent_admission_required=True,no_PVE2_PVE3=True),
        commands=commands,launch=False,GO=False,
        acceptance='Both native DS/Qwen exit0; connected and reset PASS markers; four case summaries; trace checker PASS on actual logs; all source/tool/log/binary hashes archived; preserve any timeout or failure without retry.',
        measurements='Integer cycles first/last actual matrix rv -> actual RF write/ACK visible/retired -> fence -> two in-place ADD passes -> actual RF read -> optional scratch -> actual x SRAM write -> next actual matrix issue. No host rewrite between passes.',
        limitations=['Directed exact power-of-two stimulus; not exhaustive arithmetic','Actual matrix reduction trees/stack retained; general vector reducer/SFU absent','10ns bench clock gives no1.2GHz/SSFF credit','Functional SRAM and seven-cycle HBM stimulus are not physical qualification','One full-op capture reservation, not a token workload or rate proof','Runtime output monitoring must enforce aggregate8GiB, terminate and preserve failure if exceeded'])
if __name__=='__main__':
    p=OUT/PROPOSAL;data=(json.dumps(prepare(),indent=2,sort_keys=True)+'\n').encode()
    if p.exists():assert p.read_bytes()==data
    else:p.write_bytes(data)
    print(p)

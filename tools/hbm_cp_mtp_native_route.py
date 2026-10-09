#!/usr/bin/env python3
"""Fresh full CPsouth physical candidate; actual pins and memory, no old LEF."""
import argparse,hashlib,json,subprocess
from pathlib import Path
import hbm_cp_mtp_native_model as MODEL
import hbm_cp_mtp_native_gate as GATE
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--job-root',required=True,type=Path);p.add_argument('--gate',required=True,type=Path);p.add_argument('--prepare-only',action='store_true');a=p.parse_args()
    gate=json.loads(a.gate.read_text());assert gate['verdict']=='PASS'
    for name,h in gate['source_sha256'].items():assert digest(ROOT/name)==h,name
    am=gate.get('native_CP_to_MTP_bits')==197
    mx1=gate.get('reset_contract')=='MX1_drained'
    model=MODEL.model(am,mx1);assert model['model_ready_for_build']
    job=a.job_root.resolve();job.mkdir(parents=True,exist_ok=False)
    master=model['master'];folder='collar_mx1' if mx1 else 'collar_am197' if am else 'collar'
    collar='physical/hbm_cp_mtp_native/'+folder+'/'+master+'/io_place.tcl'
    sources=[s for s in gate['source_sha256'] if not s.startswith('physical/hbm_cp_mtp_native/rtl/tb_') and not 'asap7_memory_macros' in s]
    argv=['python3','tools/run_abi3_physical.py','--view','asap7','--top',master,
        '--param','ENABLE_MTP=1','--clock-port','ck','--clock-period-ns','0.833',
        '--clock-uncertainty-ns','0.06','--clock-uncertainty-hold-ns','0.025',
        '--orfs-corner','TC' if mx1 else 'WC','--hold-corners','TC,BC' if mx1 else 'WC,BC','--io-delay-fraction','0.2',
        '--stages','pnr','--die-area','0','0','1399.656','701.976',
        '--core-area','0','0.54','1399.656','701.436','--place-density','0.55',
        '--routing-layers','M2','M7','--macro-view',
        'ot_sram_2rw_512x64_m4_r2c2=physical/asap7_memory_macros/ot_sram_2rw_512x64_m4_r2c2',
        '--macro-place-halo','5','5','--orfs-var','ADDER_MAP_FILE=',
        '--orfs-var','PDN_TCL=/src/physical/hbm_accel_die_views/cmdproc/pdn_cmdproc.tcl',
        '--orfs-var','IO_CONSTRAINTS=/src/'+collar,
        '--orfs-var','MACRO_PLACEMENT_TCL=/src/physical/hbm_cp_mtp_native/macro_place.tcl',
        '--orfs-var','SYNTH_KEEP_MODULES=ot_hfd_oreg1 ot_hfd_oreg2 ot_hfd_oreg3 ot_hfd_oreg4 ot_hfd_oreg5 ot_hfd_sink1',
        '--orfs-var','CTS_ARGS=-sink_clustering_enable -repair_clock_nets -apply_ndr none',
        '--step-tcl','POST_SYNTH=physical/hbm_accel_die_views/common/inout_retype_post_synth.tcl',
        '--slew-margin-percent','60','--hold-margin-ns','0.015','--purpose','signoff_target',
        '--nickname-tag','cp_s_mtp_native_candidate','--synth-timeout-seconds','unlimited',
        '--flow-timeout-seconds','unlimited','--keep-workdir',str(job/'work'),'--output',str(job/'physical.json')]
    for s in sources:argv+=['--source',s]
    pins=ROOT/'physical/hbm_cp_mtp_native'/folder/master/'ports.json'
    record=dict(schema='opentallas.hbm.cp-mtp-native-route.v1',argv=argv,model=model,
        sources=gate['source_sha256'],gate_sha256=digest(a.gate),pin_record_sha256=digest(pins),
        io_tcl_sha256=digest(ROOT/collar),fresh_master=True,old_closed_LEF_used=False,
        clocks=dict(setup_corner='TT/TC' if mx1 else 'SS/WC',hold_corner='FF/BC',period_ns=.833,setup_uncertainty_ns=.060,hold_uncertainty_ns=.025),
        die_link_budgets_qualified=False,mutable_MTP_state_protected=False,backend_translation_bound=False,
        physical_qualification=False,adopted=False,headline_rate=None,
        reservation_GiB=80,reservation_basis='existing full CPsouth physical job spec80GiB; same macro, slot and AR source; adds bounded1408 state bits and zero facade state',
        build_inventory=dict(command_macro_count=1,guard_register_upper=model['area']['checked_join_register_bits_upper'],emit_queue_storage=model['area']['emit_queue_storage_bits'],emit_queue_other_state_upper=model['area']['emit_queue_other_state_bits_upper']))
    if mx1:
        record.update(reset_contract='MX1_drained',control_storage='plain flops; no control ECC/mirrors or external epoch',physical_intake_owner='Claude',SS_sensitivity_required=True,acceptance=model['acceptance'])
    (job/'prepared.json').write_text(json.dumps(record,indent=2)+'\n')
    if a.prepare_only:return 0
    with (job/'run.log').open('w') as log:r=subprocess.run(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    (job/'terminal.exit').write_text(str(r.returncode)+'\n');return r.returncode
if __name__=='__main__':raise SystemExit(main())

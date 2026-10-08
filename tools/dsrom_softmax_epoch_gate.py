#!/usr/bin/env python3
"""Run one protected row transport component, preserving each campaign label."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCES=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/hbm_accel/service/ot_hbm_accel_r5a_ecc_pkg.sv','rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv','rtl/hbm_accel/collective_clock_entry_20261007/ot_hbm_collective_reset_entry.sv','rtl/hbm_accel/collective_cdc_20261007/ot_hbm_collective_protected_cdc.sv','physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']+['rtl/experimental/dsrom_softmax_transport_20261007/'+p for p in ['ot_dsrom_softmax_ecc_lane.sv','ot_dsrom_softmax_serial_row.sv','ot_dsrom_softmax_core_replay.sv','ot_dsrom_softmax_sram_join.sv','ot_dsrom_softmax_phase.sv','ot_dsrom_softmax_epoch_join.sv','tb_epoch_join.sv']]
def main():
 p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--variant',choices=['positive','epoch_negative','completion_negative'],default='positive');a=p.parse_args()
 out=ROOT/'results/rtl/dsrom_softmax_transport_20261007';record=out/(a.label+'.json');log=out/(a.label+'.log')
 if record.exists() or log.exists():raise RuntimeError('Immutable campaign label already exists')
 defines={'positive':[],'epoch_negative':['-DSOFTMAX_EPOCH_IGNORE_EPOCH'],'completion_negative':['-DSOFTMAX_EPOCH_EARLY_COMPLETION']}[a.variant]
 work=Path(tempfile.mkdtemp(prefix='softmax_epoch_'));image=work/'gate.vvp';cmd=['iverilog','-g2012',*defines,'-s','tb_epoch_join','-o',str(image),*SOURCES]
 hashes={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in SOURCES}
 with log.open('w') as f:
  comp=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  run=subprocess.run(['vvp',str(image)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT) if comp.returncode==0 else None
 content=log.read_text();expected={'positive':'PASS_EPOCH_JOIN','epoch_negative':'STALE_EPOCH_ESCAPED','completion_negative':'EARLY_VISIBLE_COMPLETION'}[a.variant]
 passed=comp.returncode==0 and run is not None and (run.returncode==0 if a.variant=='positive' else run.returncode!=0) and expected in content
 pre=ROOT/'results/uarch/dsrom_softmax_transport_20261007/epoch_join_prebuild.json'
 data=dict(schema='opentallas.softmax_epoch_gate.v1',variant=a.variant,passed=passed,adopted=False,source_sha256=hashes,compile=cmd,compile_returncode=comp.returncode,run_returncode=run.returncode if run else None,expected_marker=expected,prebuild_model=str(pre.relative_to(ROOT)),prebuild_sha256=hashlib.sha256(pre.read_bytes()).hexdigest(),scope='One full-width protectedCDC/phase/actualSRAM row; external E/BF16 visible receipts modeled by bench, numerical engine/config and physical timing unqualified',log=str(log.relative_to(ROOT)))
 record.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data));raise SystemExit(0 if passed else 1)
if __name__=='__main__':main()

"""Opt-in actual R55 execution after enrolled-loader dual-constructor PASS.
Original source proofs, arithmetic, capture, seal and cold restore unchanged.
"""
import argparse,json,sys
from pathlib import Path
import ds_hbm_checkpointed_prefix_r55 as original
import ds_hbm_dual_resources_r56 as resources
import ds_hbm_registered_loader_r57 as enrollment
from ds_hbm_connected_prepare_r37 import sha

def validate_preflight(record):
    if record.get('status')!='PASS_ACTUAL_PRODUCER_AND_COLD_ADDITIVE_CONSTRUCTORS':
        raise ValueError('actual dual constructors PASS required')
    if record.get('expected_outputs')!=1664 or record.get('native_PCs_executed')!=0 or record.get('actual_restore_executed') is not False:
        raise ValueError('exact nonnumerical constructor scope required')
    if record.get('cold_data_identity_exact') is not True or record.get('cold_role_proof')!=record.get('role_proof') or not record.get('role_proof'):
        raise ValueError('exact cold identity and unchanged scope proof required')

def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--actual-pc10',action='store_true',required=True);args=p.parse_args()
    plan=json.loads(args.plan.read_bytes())
    if plan.get('numerical_GO') is not True or plan.get('preflight_only') is not False:
        raise ValueError('explicit actual checkpoint continuation enrollment required')
    # Includes the actual preflight receipt, its exact original source plan and
    # every original source pin. No guard exemptions or constructor substitutes.
    original.source_gate(plan,available_bytes=sum(json.loads((resources.ROOT/plan['storage_proof']['path']).read_bytes())[k] for k in ('journal_new_bytes','checkpoint_new_bytes','other_new_bytes')))
    proof=plan['actual_dual_constructor_preflight']
    record=json.loads((resources.ROOT/proof['receipt']).read_bytes())
    validate_preflight(record)
    if record['source_plan_sha256']!=sha(resources.ROOT/proof['plan']):raise ValueError('actual preflight plan lineage differs')
    projection=json.loads((resources.ROOT/plan['storage_proof']['path']).read_bytes())
    interp=projection['RAM']['interpreter']
    if sys.implementation.name!=interp['implementation'] or sys.version!=interp['version']:raise ValueError('priced interpreter changed')
    raw=bytes(range(256))
    if any(raw[i] is not int(str(i)) for i in range(256)):raise ValueError('source-byte cache identity differs')
    enrollment.install()
    sys.argv=[sys.argv[0],'--plan',str(args.plan),'--out',str(args.out)]
    original.main() # Fresh prefix -> sealed actual PC9 -> separate cold restore -> PC10.

if __name__=='__main__':main()

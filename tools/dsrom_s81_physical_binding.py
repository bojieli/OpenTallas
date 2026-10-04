#!/usr/bin/env python3
"""Bind selected S81 physical inputs; metadata census, never allocator or placement."""
import argparse
from collections import Counter
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / 'results/uarch/dsrom_s81_physical_binding_20261004'

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()

def require(ok, message):
    if not ok: raise ValueError(message)

def load_inputs(base=BASE):
    p = base / 'inputs'
    manifest = json.loads((p/'source_binding.json').read_text())
    for name, sha in manifest['local_sha256'].items():
        require(digest(p/name) == sha, 'changed input: '+name)
    return {f.stem: json.loads(f.read_text()) for f in p.glob('*.json')}

def validate(d):
    i, s, c, r = (d[k] for k in ('inventory','stage_map','return_connectivity','return_model'))
    require((i['stages'],i['TP'],i['pairs_per_rank_die'],i['BF_dual_pairs']) == (81,4,2417,519), 'wrong selected geometry')
    require(i['rows']==4096 and i['macros_per_pair']==4 and i['padding_pairs']==0, 'wrong macro/padding policy')
    require(not i['ROM_ECC'], 'no-ECC selection changed')
    require(i['physical_ROM4096_per_layer_die']==9668, 'leaf census')
    expected = [{'die_id':4*stage+rank,'rank':rank,'stage':stage} for stage in range(81) for rank in range(4)]
    require(s['rank_dies']==expected and c['rank_dies']==expected, 'rank ownership mismatch')
    bf = [j*2417//519 for j in range(519)]
    require(s['BF_site_IDs']==bf and c['BF_site_IDs']==bf, 'BF site identity mismatch')
    require(c['pairs']==2417 and c['RD']==64 and c['ROOTD']==128 and c['no_READY'], 'native return parameters')
    nodes=c['nodes']; roots=c['roots']
    require(len(nodes)==5090 and sum(n['unilateral'] for n in nodes)==384, 'unary/node omission')
    require(len(roots)==128 and all(not n['removed'] for n in roots), 'root omission')
    require(len({n['id'] for n in nodes})==5090, 'duplicate node identity')
    require(r['retained_storage_bits']==5090*8386+128*16768==44831044, 'storage conservation')
    require(r['removed_empty_side_storage_credit_bits']==0 and r['removed_root_storage_bits']==0, 'unsupported storage credit')
    require(r['inventory_bound'] and r['canonical_matrix_map_pinned'], 'unbound inventory')
    for name in ('inventory.json','stage_map.json'):
        require(r['source_sha256'][str(Path(d['source_binding']['owners']['canonical_source_worktree'])/'results/uarch/dsrom_s81_released_binding_20261004/canonical'/name)]==d['source_binding']['local_sha256'][name], 'Rawls canonical identity')


def census(matrix):
    count=0; bystage=Counter(); indexer=[]
    with gzip.open(matrix,'rt') as f:
        for line in f:
            row=json.loads(line); count+=1; bystage[row['stage']]+=1
            tensor=row['tensor']
            if '.indexer.' in tensor and tensor.endswith(('.wk.weight','.wq_b.weight')):
                slices=row['rank_slices']
                require(len(slices)==4 and all(x==slices[0] for x in slices), 'indexer not fully replicated on four ranks: '+tensor)
                indexer.append({'tensor':tensor,'stage':row['stage'],'rows':row['rows'],'K':row['K'],'format':row['format'],
                    'rank_slices':slices,'plans_sha256':hashlib.sha256(json.dumps(row['plans'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                    'plan_count':len(row['plans']), 'reservation_scope':'inside existing compiled site ledger on each rank; no extra macro footprint debit'})
    require(count==46671, 'canonical declaration count')
    require(indexer, 'missing replicated indexer')
    return {'declarations':count,'declarations_by_stage':dict(sorted(bystage.items())), 'indexer_replicated_declarations':indexer}


def budget(d):
    # Frozen Peirce screen is a reservation, not measured or placed area.
    old=Decimal(str(d['Peirce_composition']['area']['contracted_Claude_screen_mm2']))
    correction=Decimal(str(d['return_model']['compact_additional_debit_not_removed_by_dead_pruning_mm2']))
    strict=old+correction
    require(abs(strict-Decimal(str(d['Peirce_composition']['area']['screen_mm2']))) < Decimal('0.000000000001'), 'Peirce strict-return screen mismatch')
    proposal=Decimal('843.5278') # user-reported Ampere branch, not native implementation
    return {'reticle_mm2':858, 'max_width_mm':26,'max_height_mm':33,
        'historical_contracted_screen_mm2':float(old),'strict_unary_storage_delta_mm2':float(correction),
        'source_inventory_baseline_screen_mm2':float(strict),'baseline_margin_mm2':float(Decimal(858)-strict),
        'Ampere_proposal':{'area_mm2':float(proposal),'margin_mm2':float(Decimal(858)-proposal),
            'margin_percent':float((Decimal(858)-proposal)/Decimal(858)*100),
            'increment_over_strict_baseline_mm2':float(proposal-strict),
            'provenance':'user-reported strict return plus proposed lookahead; native proposal not implemented',
            'implemented':False,'physical_fit':False},
        'original_2_19_percent_unspent':False,
        'native_logic_clock_PG_route_containment_resolved':False,
        'unresolved_costs_not_zero':['native unary/control/root object containment','IO/PHY and supply hierarchy','clock/reset regional CTS and shield routes','native placement/halo/OBS and detailed route']}


def build(base=BASE, matrix=None):
    d=load_inputs(base);validate(d)
    m=d['source_binding']['matrix_metadata']; matrix=Path(matrix or m['path'])
    require(digest(matrix)==m['sha256'], 'matrix metadata changed')
    counts=census(matrix)
    require(digest(matrix)==m['sha256'], 'matrix metadata changed during census')
    v=d['mapping_verdict']; a=d['auxiliary_obligations'];s=d['stage_map']
    return {'schema':'opentallas.dsrom.S81.physical-binding.v1','selection':{'stages':81,'TP':4,'pairs_per_rank_die':2417,'BF':519,'Q':1898,'depth':4096,'macros_per_pair':4,'layer_dies':324,'total_dies':368},
        'source_binding':d['source_binding'],'canonical_metadata_census':counts,
        'physical_instances':{'weight_macro_leaves_per_die':9668,'weight_macro_leaves_layer_total':3132432,
            'return_nodes_per_die':5090,'unilateral_per_die':384,'roots_per_die':128,
            'identity_tables':'inputs/return_connectivity.json and inputs/stage_map.json; logical source identities, not fabricated placed DEF paths',
            'native_placed_instance_census':None},
        'return_storage':d['return_model'],'area_budget':budget(d),
        'configuration':{'required_PHW_stage_histogram':dict(sorted(Counter(s['PHW_required_by_stage'].values()).items())) if isinstance(s['PHW_required_by_stage'],dict) else dict(sorted(Counter(s['PHW_required_by_stage']).items())),
            'physical_macro_census':None,'source_72bit_provider_max_macros_per_pair':7,'uniform_template_selected':False},
        'auxiliary':{'storage_bytes':a['storage_bytes'],'tensors':len(a['tensors']),'placement_qualified':a['placement_qualified'],'no_omission_credit':a['no_omission_credit']},
        'historical_metadata_limits':{'owner_schema':v['schema'],'entire_shipped_checkpoint_exactonce_PASS':v['entire_shipped_checkpoint_exactonce_PASS'],'legacy_RD_label_not_selected_geometry':True},
        'source_only_no_payload_reads':True,'new_RTL':False,'allocator_rerun':False,'physical_fit':False,'PnR_admitted':False,'SSFF_qualified':False,'token_rate_qualified':False,
        'next_construction':'Bind native q/BF and typed unary/root objects, actual supply upfeeds and Clock-C regional hierarchy to selected placement; native DEF/IO/cell union before selected PDN/GRT admission.'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--matrix-map',type=Path);p.add_argument('--verify',action='store_true');args=p.parse_args()
    model=build(matrix=args.matrix_map); text=json.dumps(model,sort_keys=True,indent=2)+'\n'
    if args.verify: require((BASE/'model.json').read_text()==text,'model replay differs')
    if args.out: args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(text)
    print(json.dumps({'canonical_declarations':model['canonical_metadata_census']['declarations'],'strict_baseline_mm2':model['area_budget']['source_inventory_baseline_screen_mm2'],'physical_fit':False,'verified':args.verify}))
if __name__=='__main__':main()

"""Price measured full-column area at fixed density and existing replica counts."""
import hashlib
import json
from decimal import Decimal as D
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = '5841685418f16fcb6f46645613dd72960cdb3984'
MEASURED = 'd982580d48bc16f24f30ab85bc7aef018c5edb8f'


def generate():
    pins = {}
    def read(commit,path):
        blob = subprocess.check_output(['git','show',f'{commit}:{path}'],cwd=ROOT)
        pins[path] = dict(commit=commit,sha256=hashlib.sha256(blob).hexdigest())
        return json.loads(blob)
    ready = read(MEASURED,'results/uarch/w10_baseline_wake/fullmap_r2/readiness.json')
    strict = read(MEASURED,'results/uarch/w10_baseline_wake/fullmap_r2/strict_structure.json')
    full = read(BASE,'results/uarch/w10_baseline_wake/fullgoal_bound.json')
    owners = read(BASE,'results/arch/v41_stage_owner_product.json')
    area = ready['area']
    std,macro = D(str(area['measured_synthesis_stdcell_um2'])),D(str(area['measured_synthesis_macro_um2']))
    # Exact core dimensions supplied by physical owner, not rounded historic anchor.
    core = D('998.57')*D('138.24')
    density = D(str(area['requested_placement_density']))
    reserve = D(str(area['escape_reservation_um2']))
    outline = D(str(full['elements']['column']['outline_um'][0]))*D(str(full['elements']['column']['outline_um'][1]))
    assert density == D('.5') and full['full_size']['bf16_column_pairs_per_die']==1024
    assert owners['stage_count']==41 and owners['layer_dies']==164
    assert ready['structure']['icg_count']==8 and len(ready['structure']['macros'])==4
    needed = macro+std/density
    reserved = needed+reserve
    copies = 1024*164
    def number(v): return float(v)
    scenarios = []
    for name,need in [('uniform_50pct_before_escape',needed),('uniform_50pct_exclusive_escape',reserved)]:
        scenarios.append(dict(name=name,required_element_um2=number(need),
            shortfall_vs_actual_core_um2=number(need-core),
            shortfall_vs_existing_gross_outline_um2=number(need-outline),
            core_shortfall_per_layer_die_mm2=number((need-core)*1024/D(1000000)),
            gross_outline_shortfall_per_layer_die_mm2=number((need-outline)*1024/D(1000000)),
            core_shortfall_all_164_layer_dies_mm2=number((need-core)*copies/D(1000000)),
            gross_outline_shortfall_all_164_layer_dies_mm2=number((need-outline)*copies/D(1000000)),
            required_column_area_per_layer_die_mm2=number(need*1024/D(1000000)),
            fits_actual_core=False,fits_even_gross_existing_outline=False))
    return dict(schema='opentallas.w16.w10.fullmap-area-price.v1',source_pins=pins,
        verdict='HOLD_FULLGOAL_AREA_BEFORE_PHYSICAL_BUILD',adopted=False,physical_admission=False,
        scope='Measured standard-cell synthesis and macro area priced using conservative uniform50% density and exclusive pin reserve. Not routed fit, final abstract, die rebase or rate qualification.',
        measured_element=dict(top='ot_v41_rom_elem_wake_w10',NB=2,BF16=1,XF=8,FAST=1,PP=1,FRONT_PAR=0,
            physical_rom_count=4,distinct_wake_count=8,stdcell_um2=number(std),macro_um2=number(macro),
            core_um2=number(core),density=number(density),exclusive_escape_reserve_um2=number(reserve),
            mapping='One complete model column element with two logical banks times two ping-pong macros; do not divide mapped area by golden N4 array qualification.',
            exactness_scope=ready['exactness'],structure_scope=ready['structure']['verdict']),
        inherited_baseline=dict(column_outline_um=full['elements']['column']['outline_um'],
            column_gross_outline_um2=number(outline),column_replicas_per_layer_die=1024,
            total_column_replicas=copies,stages=41,layer_dies=164,head_dies=8,table_dies=36,total_dies=208,
            maximum_pairs_per_die=max(owners['pairs_per_die_by_stage']),
            maximum_q_pairs_per_die=max(owners['pairs_per_die_by_stage'])-1024,
            column_allocated_gross_area_per_layer_die_mm2=number(outline*1024/D(1000000)),
            note='Existing modeled counts, not new adopted placement. No mapped-area transfer to separate q top, head or table elements.'),
        scenarios=scenarios,
        old_sizing_record=dict(path='results/uarch/w10_baseline_wake/fullgoal_bound.json',
            original_verdict=full['verdict'],original_column_fit=full['elements']['column']['fit'],
            preserved=True,limitation='Old incremental area versus gross spare is not a proof that complete measured column fits at50% macro-excluded density. This additive record does not overwrite historical PASS.'),
        die_impact=dict(fixed_outline_changed=False,density_changed=False,
            required_new_layer_die_count=None,required_total_die_count=None,token_cycles=None,rate_credit=False,
            note='Current column slot fails conservative test even when compared with its entire gross outline. Area shortfalls are allocation pressure, not permission to enlarge die or a ceil(area) die count. Actual repacking/storage/owner-stage schedule, q-element area, local pin contiguity, hub and routing reserves must be composed before any revised die count or latency.'),
        prerequisites=['Root all-pin escape/orientation/track/site/PDN legality and local contiguous reserve.',
            'Complete-element floorplan feasibility at unchanged50% density and outline; reject physical launch while held.',
            'Full unified-model field/storage capacity and stage ownership if a separate design change is proposed; price extra stage hops and latency before build.',
            'Contextual SS setup/FF hold, final abstracts, hub-layer acceptance, measured clock power and actual-element IR.'],
        other_tracks='Qwen ROM and both HBM comparators unchanged; Halley non-SM resident contract proceeds independently.')


if __name__=='__main__':
    (HERE/'area_price.json').write_text(json.dumps(generate(),indent=2)+'\n')

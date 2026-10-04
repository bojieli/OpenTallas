"""Compose Epicurus' ONE proposed lookahead with current S81 retained costs.

No source adoption, area credit, simulation/P&R, stage/die regeneration or rate
prediction. Baseline and successor physical failures remain independent.
"""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/rtl/dsrom_xneed_context_20261004'
INPUTS=('epicurus_construction.json','selected_S81.json','retained_RD64.json')

def compose(base=BASE):
    c,s,r=[json.loads((base/'inputs'/p).read_text()) for p in INPUTS]
    a=s['decision']['area']
    if (a['stages'],a['pairs'])!=(81,2417):raise ValueError('owner selected S81 changed')
    # Source owner selected BF count; literal actual BF site IDs are not frozen.
    bf=519;q=a['pairs']-bf
    candidates=[v for v in s['priced'].values() if v['area']['stages']==81]
    if len(candidates)!=1:raise ValueError('ambiguous selected full-field model')
    total_dies=candidates[0]['system']['total_dies']
    dies=candidates[0]['system']['layer_dies']
    if (dies,total_dies)!=(324,368):raise ValueError('source selected S81 die count changed')
    con=c['construction'];cost=c['cost']
    if con['total_FF_increment']!=252 or con['accepted_beat_II_cycles']!=1 or con['fill_cycles_increment']!=0 or con['recurrence_extra_cycles']!=0:
        raise ValueError('ONE source-owner construction changed; reprice first')
    cell=q*cost['combined_incremental_cell_area_reserve_um2']/1e6
    placed=q*cost['placed_area_at_50pct_um2']/1e6
    return_debit=r['compact_additional_debit_not_removed_by_dead_pruning_mm2']
    conditional=a['die_mm2']+return_debit+placed
    return dict(schema='dsrom-xneed-S81-context-price-r1',
        source_pins={p:hashlib.sha256((base/'inputs'/p).read_bytes()).hexdigest() for p in INPUTS},
        construction_owner='Epicurus',construction_commit='4d5c70aea6b67af143f42892d7e51ddfe7974cf6',
        source_status='MODEL_ONLY; candidate RTL not written and actual functional terminal absent',
        selected_S81=dict(stages=81,layer_rankdies=dies,total_dies=total_dies,pairs_per_rankdie=a['pairs'],BF_pairs_per_rankdie=bf,
            q_only_pairs_per_rankdie=q,BF_site_ID_binding=None,actual_S81_inventory_binding=None),
        increments_per_qpair=dict(FFs=252,data_FFs=249,async_valid_FFs=3,
            MAC_per_cycle=0,external_bits_per_cycle=0,memory_bytes_per_cycle=0,
            cell_area_reserve_um2=cost['combined_incremental_cell_area_reserve_um2'],
            placed_area_50pct_reserve_um2=cost['placed_area_at_50pct_um2'],
            clock_buffer_reserve=37,control_buffer_reserve=120,
            internal_metadata_logical_wire_reserve=252,actual_tracks=None),
        rankdie_increment=dict(FFs=q*252,clock_buffer_reserve=q*37,control_buffer_reserve=q*120,
            cell_area_reserve_mm2=cell,placed_area_50pct_reserve_mm2=placed),
        nonlayer_dies=dict(count=total_dies-dies,qpair_inventory=None,lookahead_increment=None,
            scope='head/table dies are not replicated layer fields; do not multiply by368'),
        fullfield_increment=dict(q_only_sites=q*dies,FFs=q*252*dies,
            cell_area_reserve_mm2=cell*dies,placed_area_50pct_reserve_mm2=placed*dies),
        latency=dict(lookahead_proposed_increment_cycles=0,accepted_II_cycles=1,
            inherited_qpipe_Rcap0_cycles=2,inherited_qpipe_Rcap1_cycles=3,
            actual_selected_measured_increment_cycles=None,actual_token_latency_delta=None,
            two_cycle_walker_permitted=False,old_nA_nB_nQ2_storage_doublecharged=False),
        once_only_fit=dict(selected_compact_screen_mm2=a['die_mm2'],
            retained_return_additional_reservation_mm2=return_debit,
            retained_return_nodes=r['retained_nodes'],unilateral_nodes=r['retained_unilateral_nodes'],
            conditional_die_mm2_with_retained_return_and_placed_lookahead=conditional,
            reticle_mm2=s['reticle_mm2'],remaining_reserve_mm2=s['reticle_mm2']-conditional,
            conditional_margin_frac=(s['reticle_mm2']-conditional)/s['reticle_mm2'],
            meets_2pct_model_reserve=(conditional<=s['reticle_mm2']*.98),
            physical_slot_fit=None,clock_reset_PG_RC_tracks='not yet constructed/mapped; logical wires are not route capacity'),
        historical_failure=c['observed_baseline'],
        physical_policy=dict(period_ps=833,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
            physical_launch_allowed=False,no_qelement_timing_overlap=True),
        remaining=['Epicurus selected actual RTL + corrected caller decoder + functional terminal/II1/latency',
            'actual S81 q/BF site identity and finite control/clock/reset/PG slot allocation',
            'source-matched existing parent mapped/routed context and actual root/producer arrivals'],
        verdict='NOT_ADMITTED_SOURCE_AND_PHYSICAL_MISSING',adoption=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    with a.out.open('x') as f:json.dump(compose(),f,sort_keys=True,indent=2);f.write('\n')
if __name__=='__main__':main()

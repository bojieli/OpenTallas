"""Fixed fullshape selector fixture + unchanged literal allowed-cell cuts.

Source/model preparation only. No frontend or execution. Primitive PASS and a
fresh component GO are required separately from integrated physical admission.
"""
import argparse
import gzip
import json
from pathlib import Path
import prepare_dsrom_balanced_selector_gate as G
import prepare_dsrom_selector_allowed_cuts as C
import prepare_dsrom_full_selector_dma_fixture as V

ROOT=V.ROOT
BASE=ROOT/'results/rtl/dsrom_full_selector_allowed_cut_gate_prepare_20261003'

def context():
    origins=json.loads((BASE/'inputs/origins.json').read_text())
    for name,e in origins.items():
        data=(BASE/'inputs'/name).read_bytes()
        if V.sha(data)!=e['sha256'] or len(data)!=e['bytes']:raise ValueError('selected c9 archive changed: '+name)
    m=json.loads((BASE/'inputs/selected_c9_model.json').read_text())
    selected=m['selected_selector_clock_construction']
    if selected['core_clock70406']!=70406 or m['prior51ae_annex_charge_mm2']!=0:raise ValueError('one selected clock bank required')
    sites=[json.loads(line) for line in gzip.decompress((BASE/'inputs/selected_clock_cells.jsonl.gz').read_bytes()).splitlines()]
    if len(sites)!=70406 or len({x['instance'] for x in sites})!=70406:raise ValueError('clock instance ledger changed')
    if any(x['master']!='BUFx4_ASAP7_75t_R' for x in sites):raise ValueError('unallowed clock cell master')
    if V.sha((BASE/'inputs/selected_clock_cells.jsonl.gz').read_bytes())!=selected['source_cells_hash']:raise ValueError('selected site source binding changed')
    if m['contextual_PR_admitted'] or m['SSFF'] or m['actual_consumer_deadline'] is not None:raise ValueError('no inherited physical/deadline admission')
    return dict(selected_clock_bank=selected,site_instances=70406,
                literal_source_to_clock_site_assignment_present=False,
                raw_clock_corrections_separate_not_selector_recharge=m['positive_new_relay_and_pad_BUF'],
                c9_physical_admitted=False,c9_consumer_deadline=None)

def mapped_bench(source):
    if source.count('ot_w15_coll_dma_balanced_station_prepare #(')!=1:raise ValueError('one full candidate required')
    if source.count('.TK_BALANCED(MUTANT==4?0:1)')!=1:raise ValueError('defaultoff profile anchor changed')
    source=source.replace('module bench_dsrom_balanced_selector_gate_prepare #(',
                          'module bench_dsrom_full_selector_allowed_cut_prepare #(')
    source=source.replace('ot_w15_coll_dma_balanced_station_prepare #(',
                          'ot_w15_coll_dma_balanced_allowed_cut_prepare #(')
    return source.replace('.TK_BALANCED(MUTANT==4?0:1)',
                          '.TK_CELL_MAP(MUTANT==4?0:1),.TK_BALANCED(MUTANT==4?0:1)')

def prepare(out):
    if out.exists():raise ValueError('fresh full literal-cut package required')
    model=json.loads((BASE/'component_model.json').read_text())
    for p,h in model['source_pins'].items():
        if V.sha((ROOT/p).read_bytes())!=h:raise ValueError('old fullshape source pin changed: '+p)
    joined=context()
    out.mkdir(parents=True)
    G.prepare(out/'gate')
    C.prepare(out/'allowed')
    bench=out/'gate/fixture/bench_dsrom_balanced_selector_gate_prepare.sv'
    (out/'bench_dsrom_full_selector_allowed_cut_prepare.sv').write_text(mapped_bench(bench.read_text()))
    # Old complete gate and its manifest remain unchanged. Only the new bench
    # and two literal modules are selected instead of the old bench/caller.
    inventory=['bench_dsrom_full_selector_allowed_cut_prepare.sv',
        'allowed/candidate/ot_w15_coll_dma_balanced_allowed_cut_prepare.sv',
        'allowed/candidate/ot_topk_allowed_cut_packet_prepare.sv']
    inventory += ['gate/candidate/'+n for n in ['ot_chip_v41x_coll_transpose.sv','ot_coll_topk_merge.sv',
        'ot_coll_topk_merge_balanced_prepare.sv','ot_coll_topk_merge_staged_impl_prepare.sv',
        'ot_topk_fixed_packet_delay_prepare.sv','ot_w15_coll_dma.sv']]
    inventory += ['allowed/library_sources/'+n for n in ['asap7sc7p5t_SEQ_RVT_TT_220101.v',
        'asap7sc7p5t_INVBUF_RVT_TT_201020.v','asap7sc7p5t_SIMPLE_RVT_TT_201020.v']]
    V.write_json(out/'sourceplan.json',dict(schema='opentallas.fullselector.literal-cut.functional-package.v1',
        component_model_sha256=V.sha((BASE/'component_model.json').read_bytes()),
        source_inventory=inventory,top='bench_dsrom_full_selector_allowed_cut_prepare',
        include_path='gate/fixture',run_cwd='gate/fixture',profiles=[0,1,2,3,4],
        gate_and_allowed_original_packages_unchanged=True,full_geometry=model['geometry'],
        prepared_counts=model['tests_prepared'],same_complete_fault_contract=True,
        same_independent_expected_values=True,same_strict_completion_checker='tools/verify_dsrom_balanced_selector_completion.py',
        primitive_gate_PASS_required=True,component_GO_required=True,
        selected_clock_context=joined,source_clock_binding='all original/inferred core and actual literal cut CLK bind unchanged fixtureclk; physical sink assignments absent',
        mapped_cuts=True,core_physical_cell_mapping_qualified=False,
        actual_field_accepted_trace=False,no_new_ACK_or_timeout=True,timeout4096_adopted=False,
        compile_GO=False,physical_admitted=False,integrated_parent_admitted=False,fulltoken_credit=False))
    V.write_json(out/'artifact_manifest.json',{str(p.relative_to(out)):V.sha(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.out)

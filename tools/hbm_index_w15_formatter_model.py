#!/usr/bin/env python3
"""One no-cache, single-port source formatter; no authority/layout invention."""
import ast
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def proposal():
    source = ROOT/'tools/uarch_model.py'
    tree = ast.parse(source.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'hbm_index_ordered_adapter_model')
    ns = {'__file__': str(source)}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), ns)
    base = ns['hbm_index_ordered_adapter_model']()
    codec = ROOT/'results/uarch/dsrom_native_masked_backend_prepare_20261003/model.json'
    cells = json.loads(codec.read_text())['SRAM_protection_candidate']
    ff = 3*8*72 + 3*2*72  # score/ID/reply seats; held frame/span/control.
    nand2 = 8*64*4+32*12+1024  # half mux, checked address compare/add, control allowance.
    codec_pairs = 8
    cell_um2 = ff*(.2916+.2) + nand2*.08748 + codec_pairs*cells['pair_cell_body_um2'] + ((ff+5)//7)*.10206
    requests = 96*512//8
    reads = requests*2
    baseline = base['serial_service_budget_edges']
    # Existing priced service9/checked read. Every pair request now requires
    # two such reads, plus six real admission/assembly/held response edges.
    # Conservative serial plan: no compute/read overlap or free second port.
    formatter_edges = requests*(2*9+6)
    composed = base['serial_selection_edges']+formatter_edges+6144
    return {
      'schema':'hbm.index.w15.source_formatter.minimum.v1',
      'selection':'one checked512b port, two separate-plane reads per8-pair response; no cache/no new backing SRAM',
      'default_enabled':False,
      'actual_source':'rtl/chip/ot_w15_coll_dma.sv::vm_raddr/tk_wi/gather_addr',
      'layout':{'address_unit':'512b VM word','pairs_per_rank':512,'score_words_per_rank':32,'ID_words_per_rank':32,'rank_stride_words':64,'score_address':'held_gather_base + rank*64 + (pair_word>>1)','ID_address':'score_address+32','half':'pair_word[0] chooses8 of16 lanes'},
      'source_fact_boundary':'TOPK mode feeds gathered o_data directly to selector, not a gathered VM copy. Rank-major VM extent is a REQUIRED enclosing producer/owner binding; formatter never creates one.',
      'held_extent_words':6144,'held_extent_bytes':393216,
      'pre_admission':['actual existing extent base/limit in512b VM words','actual exclusive full frame lease and all accepted writers drained','single borrowed checked provider port','no overlap/new writer until returned formatter+adapter debt released'],
      'pair_requests':requests,'checked_reads512':reads,'old_assumed_pair_reads512':requests,'additional_checked_reads512':reads-requests,
      'actual_read_traffic_bytes':reads*64,'additional_read_traffic_bytes':requests*64,
      'cache_bytes':0,'new_backing_SRAM_bytes':0,'protected_staging_FF':ff,
      'staging':'score512 + ID512 + reply512, each8W6stripes; frame/span/control3x128b protected allowance',
      'codec_pairs':codec_pairs,'NAND2_allowance':nand2,'estimated_body_um2':cell_um2,
      'estimated_placement_at50pct_mm2':2*cell_um2*1.05/1e6,
      'model_positive_exclusions':'actual PHY/sharedVM protection/port arbiter/CDC, loaded clock/route, reset rearm and wholeN96 control hardening; not free installed resources',
      'checked_read_service_edges':9,'explicit_internal_edges_per_pair':6,
      'internal_edges':'pair admission1, score/ID transitions+assembly1, checked held reply3, actual acceptance1; no immediate/free response',
      'formatter_serial_edges':formatter_edges,
      'additional_reads_minimum_edges':requests*9,
      'existing_adapter_model_edges':baseline,'explicit_consumer_load_edges':6144,
      'composed_serial_planning_edges':composed,'composed_us_at_target1p2':composed/1200,
      'delta_from_adapter_with_explicit_load_edges':composed-(baseline+6144),
      'rate_credit':0,'target_clock_qualified':False,'physical_build_admitted':False,'adopted':False,
      'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['rtl/chip/ot_w15_coll_dma.sv','rtl/chip/ot_coll_topk_merge.sv','rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','tools/uarch_model.py','tools/hbm_index_w15_formatter_model.py']}}

if __name__=='__main__':
    print(json.dumps(proposal(), indent=2))

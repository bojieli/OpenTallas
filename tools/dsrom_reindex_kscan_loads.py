#!/usr/bin/env python3
"""Source KScan first captures and real corner pin bounds; no parent PASS.

Uses the repository's retained SEQ liberties, verified byte-identical to the
live r9 container. Source replicas can merge: bounds are not mapped fanout or
wire capacitance, and cannot replace Noether's actual CTS/capture reports.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from uarch_topk_station_SSFF_cell_model import groups

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/topk_station_SSFF_cell_model_20261002/inputs'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def inputs():
    pins={};rows={}
    for corner in ('SS','FF'):
        p=BASE/f'asap7sc7p5t_SEQ_RVT_{corner}_nldm_220123.lib'
        text=p.read_text();pins[str(p.relative_to(ROOT))]=sha(p)
        assert re.search(r'capacitive_load_unit\s*\(\s*1\s*,\s*ff\s*\)',text)
        cells=dict(groups(text,'cell'));rows[corner]={}
        for name in ('DFFHQNx1_ASAP7_75t_R','DFFHQNx2_ASAP7_75t_R','DFFHQNx3_ASAP7_75t_R','DFFHQx4_ASAP7_75t_R'):
            body=cells[name];lp=dict(groups(body,'pin'));caps={}
            for n in ('D','CLK'):
                assert re.search(r'direction\s*:\s*input',lp[n])
                caps[n]=float(re.search(r'\bcapacitance\s*:\s*([0-9.eE+-]+)',lp[n])[1])
            rows[corner][name]=dict(input_pin_capacitance_fF=caps,cell_definition_sha256=hashlib.sha256(body.encode()).hexdigest())
    sources=['rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv','rtl/dsrom_sys/ot_dsrom_idx_edge.sv',
             'rtl/dsrom_sys/integration/ot_dsrom_reindex_chain.sv',
             'physical/dsrom_qx10_parent_context/ot_v41_qx10_native_parent.sv',
             'physical/dsrom_qx10_parent_context/boundary.sdc',
             'results/physical/dsrom_qx10_native_parent_20261005/slang_r4/record.json',
             'tools/dsrom_reindex_kscan_loads.py','tools/uarch_topk_station_SSFF_cell_model.py',
             'tools/run_abi3_physical.py','tools/orfs_allcorner_spef.py']
    pins.update({p:sha(ROOT/p) for p in sources})
    native=(ROOT/sources[0]).read_text()
    assert 'rkey <= k_key;' in native and 'rkv <= k_kv;' in native and 'rv <= k_v && rst_n;' in native
    bounds={c:dict(single_D_pin_fF=[min(x['input_pin_capacitance_fF']['D'] for x in r.values()),max(x['input_pin_capacitance_fF']['D'] for x in r.values())],
                   unmerged_four_capture_D_pins_fF=[4*min(x['input_pin_capacitance_fF']['D'] for x in r.values()),4*max(x['input_pin_capacitance_fF']['D'] for x in r.values())],
                   unmerged_quarter_query_sixteen_D_pins_fF=[16*min(x['input_pin_capacitance_fF']['D'] for x in r.values()),16*max(x['input_pin_capacitance_fF']['D'] for x in r.values())]) for c,r in rows.items()}
    return dict(source_sha256=pins,corner_cells=rows,pin_bounds=bounds,
        source_shape=dict(NS=4,NK=4,NB=4,IH=32,chunks_per_slice=4,key_bits_per_beat=16*544,
                          source_rkey_capture_bits=4*4*4*544),
        source_receiver_family='u_score.g_slice[s].u.engine.g_ch[c].u_c.{rkey,rkv,rv}; source register family, not invented mapped pins',
        key_bit_source_capture_fanout=4,identical_capture_opt_merge_possible=True,
        key_bit_mapped_capture_count_bound=[1,4],
        query_bit_source_capture_fanout_per_quarter=16,
        query_first_capture='g_slice[s].u.engine.g_ch[c].u_c.{rql_codes,rql_sc,rql_w,rql_head}; direct ROOT clock',
        query_bit_mapped_capture_count_bound_per_quarter=[1,16],
        query_scope='One quarter NS4/NK4; full four-stack query broadcast has separate replication/transport and needs its actual loaded source contract',
        capture_clock='posedge clk ROOT in native idx_chunk_l; no gated-clock substitution',
        QX_clocks=dict(root='clk/core_clk',gated='q_gated from u_qx.u_e.g_cg.u_cg.u_icg/GCLK',
                       XS='gated',configuration_go_and_root_capture='root',root_and_gated_must_remain_distinct=True),
        actual_root_gated_CTS_evidence='Existing Noether physical source6512685dd, controller3597753/exec3598462; synthesis at pinned launch record, await actual CTS insertion. Do not use standalone Z18 insertion as enclosing-parent proof.',
        matched_live_libs='SHA256 matched actual route_r9 containerf37c73c98a89 SEQ SS/FF libraries',
        mapped_receiver_pins_qualified=False,extracted_wire_load_qualified=False,
        root_gated_insertion_qualified=False,parent_qualified=False,adopted=False,
        next_binding='Use actual selected receiver master/D pins, connected fanout and root/gated CTS insertion from source-bound samegeometry parent; do not treat these positive library bounds as a full-parent PASS')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=inputs();a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f:f.write(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r['pin_bounds'],indent=2))

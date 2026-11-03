#!/usr/bin/env python3
"""Prepare a disabled SOURCE13 +2-edge L730 event; never edits the input source."""
import argparse, hashlib, json, re
from pathlib import Path

CTL = 'w_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q'
XO = 'xo_u_sfucore_Q_ctl_u_core_u_engine_u_arithmetic_procdff_71639_Q__0'
A = 'w_u_sfucore_Q_opstore_a_cmd0_Q'
B = 'w_u_sfucore_Q_opstore_b_cmd0_Q'
PAYLOAD = '{'+B+'[895:576], '+A+'[895:576], '+CTL+'[1021:0]}'

def prepare(source, destination):
    source, destination = Path(source), Path(destination)
    text = source.read_text()
    lines = [line for line in text.splitlines() if ' u_bout_L730_o ' in line]
    if len(lines) != 1:
        raise ValueError('expected one actual L730 face register')
    old = lines[0]
    if '.clk(clk), .rst_n(rst_n)' not in old: raise ValueError('native source clock/reset changed')
    if '.d('+PAYLOAD+')' not in old or '.ea(rst_n)' not in old:
        raise ValueError('selected native L730 payload/epoch changed')
    required = f'.q({XO}[1021:0]), .eq({XO}[1022])'
    if required not in text:
        raise ValueError('exact existing first-edge ctl XO provider missing')
    if 'u_l730_src_store_s0' in text:
        raise ValueError('event already present')
    prefix = f'''    // Disabled-event output: +2 edges on L730 only; existing XO outputs unchanged.
    wire [639:0] l730_store_s0;
    wire l730_store_s0_epoch;
    wire [1661:0] l730_src_s1;
    wire l730_src_s1_epoch;
    ot_dp_st #(.W(640)) u_l730_src_store_s0 (.clk(clk), .rst_n(rst_n), .d({{{B}[895:576], {A}[895:576]}}), .ea(rst_n), .q(l730_store_s0), .eq(l730_store_s0_epoch));
    ot_dp_st #(.W(1662)) u_l730_src_s1 (.clk(clk), .rst_n(rst_n), .d({{l730_store_s0, {XO}[1021:0]}}), .ea(l730_store_s0_epoch & {XO}[1022]), .q(l730_src_s1), .eq(l730_src_s1_epoch));
'''
    new = old.replace('.d('+PAYLOAD+')', '.d(l730_src_s1)').replace('.ea(rst_n)', '.ea(l730_src_s1_epoch)')
    patched = text.replace(old, prefix + new)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(patched)
    return dict(input=str(source), input_sha256=hashlib.sha256(text.encode()).hexdigest(), output=str(destination), output_sha256=hashlib.sha256(patched.encode()).hexdigest(), original_face=old, replacement_face=new)

def downstream(source, destination, slot, old_count, width=1662):
    source, destination = Path(source), Path(destination)
    text = source.read_text()
    pattern = rf"^.*ot_dp_st #\(\.W\({width}\)\) u_ft_{slot}_o_(\d+) .*?$"
    lines = re.findall(pattern, text, re.M)
    if sorted(map(int, lines)) != list(range(old_count)):
        raise ValueError(f'{slot}: exact selected native count changed')
    old = next(x for x in text.splitlines() if f' u_ft_{slot}_o_{old_count-1} ' in x)
    if '.clk(clk), .rst_n(rst_n)' not in old: raise ValueError('native FT clock/reset changed')
    final = slot+'_o'
    wire = f'{final}_s{old_count-1}'
    if f'.q({final}[{width-1}:0]), .eq({final}[{width}])' not in old:
        raise ValueError('native final data/epoch endpoints changed')
    renamed = old.replace(f'.q({final}[', f'.q({wire}[').replace(f'.eq({final}[', f'.eq({wire}[')
    added = f'    ot_dp_st #(.W({width})) u_ft_{final}_{old_count} (.clk(clk), .rst_n(rst_n), .d({wire}[{width-1}:0]), .ea({wire}[{width}]), .q({final}[{width-1}:0]), .eq({final}[{width}]));'
    patched = text.replace(old, f'    wire [{width}:0] {wire};\n'+renamed+'\n'+added)
    destination.write_text(patched)
    return dict(input=str(source), input_sha256=hashlib.sha256(text.encode()).hexdigest(), output=str(destination), output_sha256=hashlib.sha256(patched.encode()).hexdigest(), slot=slot, old_stages=old_count, new_stages=old_count+1, data_bits=width, epoch_bits=1, added_FF=width+1, added_cycles=1, added_ps=833, original_final=old, renamed_final=renamed, added_instance=added)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source-dir', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--include-cohort-ft', action='store_true', help='also exact NW_L5 and paired L731 native gaps; NE_L5 unchanged')
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    records = [prepare(args.source_dir / (m+'.sv'), args.out / (m+'.sv')) for m in ('hbm_arch_q_b113', 'hbm_arch_q_b113__physical_v1')]
    downstream_records = [downstream(args.source_dir/(m+suffix+'.sv'), args.out/(m+suffix+'.sv'), slot, count) for m,slot,count in [('hbm_arch_q_su00','L730x1',7),('hbm_arch_q_spu0','L730x5',5),('hbm_arch_q_su11','L730x7',7)] for suffix in ('','__physical_v1')]
    cohort_records = [downstream(args.source_dir/(m+'.sv'), args.out/(m+'.sv'), slot, count, width) for m,slot,count,width in [('hbm_arch_q_su31__physical_v1','L5r0_1',7,128),('hbm_arch_q_b002','L731x2',9,596),('hbm_arch_q_b002__physical_v1','L731x2',9,596)]] if args.include_cohort_ft else []
    event = dict(additional_cohort_records=cohort_records, native_FF_cohort_delta_vs_SOURCE13=15909 if args.include_cohort_ft else 14586, NW_L5=dict(native_data_bits=128,native_added_FF=129,plan_capacity_data_bits=2725,plan_capacity_added_FF=2726,payload_capacity_pin_clock_join='UNJOINED',NE_unchanged=True), already_matching_NATIVE_SOURCE13=dict(L203=5,L203m=5,L700=19,L96m=19,L96m_pad='actual ot_dp_dly W23 D7'), downstream_records=downstream_records, logical_price=dict(selected_SOURCE13_actual_edges=42, downstream_added_edges=3, upstream_proposed_added_edges=2, proposed_full_edges=47, current_SOURCE13_mutated=False, physical_exact_upstream_edges=None, new_FF_per_lane=7293, new_FF_paired=14586, reused_XO_FF_per_lane_not_new=1023), status='DISABLED_SOURCE_EVENT_NOT_ADOPTED', enabled=False, source13_mutated=False, records=records, new_native_instances=[dict(name='u_l730_src_store_s0', data_bits=640, epoch_bits=1), dict(name='u_l730_src_s1', data_bits=1662, epoch_bits=1)], reused_existing_instance='u_bout_'+XO, added_data_FF=2302, added_epoch_FF=2, added_total_FF_per_type=2304, added_cycles=2, added_ps=1666, clock_ps=833, existing_XO_output_cycles_changed=0, original_L730_face_preserved=True, source_clock='clk', delivered_reset='rst_n', data_reset=False, new_independent_START_ports=0, START_calendar_requirement='consumer availability and dependent issue/fence dates +2 edges; no installed programme dates invented', physical_status='HOLD until exact selected provider ports, row sites, epoch routes, clock/reset/START/source joins', epoch_local_group_alternative=dict(added_total_FF=2306, added_epoch_FF=4, extra_FF_over_shared=2, extra_cycles=0, condition='explicit per-group second stages with local first-stage epochs; still requires physical epoch route audit'))
    (args.out/'event.json').write_text(json.dumps(event, indent=2)+'\n')

if __name__ == '__main__':
    main()

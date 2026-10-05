"""One source-pinned selector station and selected field caller proposal.

No synthesis/STA/route. LUT envelopes are proposed enforced domains, not
admitted propagated timing. Historical intrinsic slew diagnostic stays open.
"""
import argparse
import difflib
import gzip
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/uarch/dsrom_selector_station_parent_binding_20261002'
FLAGS = ('FIX_SECOND_ROW_INDEX', 'WAKE_REG', 'GRADUAL_RNE')

def sha(b):
    return hashlib.sha256(b).hexdigest()

def block(text, pos):
    start = text.index('{', pos); end = start + 1; depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}'); end += 1
    return text[start + 1:end - 1]

def numbers(s):
    return [float(v) for v in re.findall(r'[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?', s)]

def lut(cell, kind, slew, cap, maximum=True):
    results = []
    for m in re.finditer(r'\b' + kind + r'\s*\(', cell):
        b = block(cell, m.start())
        axes = [numbers(re.search(r'index_' + str(i) + r'\s*\((.*?)\);', b, re.S)[1]) for i in (1, 2)]
        values = numbers(re.search(r'values\s*\((.*?)\);', b, re.S)[1])
        if len(values) != len(axes[0]) * len(axes[1]):
            raise ValueError('nonrectangular library table')
        if slew > max(axes[0]) or cap > max(axes[1]):
            raise ValueError('outside characterized table')
        a = next(i for i, v in enumerate(axes[0]) if v >= slew)
        c = next(i for i, v in enumerate(axes[1]) if v >= cap)
        vals = [values[i * len(axes[1]) + j] for i in range(a + 1) for j in range(c + 1)]
        results.append((max if maximum else min)(vals))
    if not results:
        raise ValueError('missing library table')
    return (max if maximum else min)(results)

def cap(cell, pin):
    p = re.search(r'\bpin\s*\(' + re.escape(pin) + r'\)\s*\{', cell)
    return float(re.search(r'\bcapacitance\s*:\s*([\d.eE+-]+)', block(cell, p.start()))[1])

def constraint(cell, timing_type):
    vals = []
    for m in re.finditer(r'\btiming\s*\(', cell):
        b = block(cell, m.start())
        if 'timing_type : ' + timing_type + ';' in b:
            for v in re.finditer(r'\bvalues\s*\((.*?)\);', b, re.S):
                vals += numbers(v[1])
    if not vals:
        raise ValueError('missing constraint')
    return max(vals)

def propose_field(source):
    if any(flag in source for flag in FLAGS):
        raise ValueError('caller changed; review rather than silently patch')
    anchor = '    parameter integer PHW = 6\n'
    if source.count(anchor) != 1:
        raise ValueError('ambiguous declaration anchor')
    declarations = ''.join('    parameter integer ' + f + ' = 0,\n' for f in FLAGS)
    result = source.replace(anchor, declarations + anchor)
    anchor2 = '.EARLY(EARLY), .PHW(PHW),'
    if result.count(anchor2) != 1:
        raise ValueError('ambiguous pair caller')
    forwards = ' '.join('.' + f + '(' + f + '),' for f in FLAGS)
    result = result.replace(anchor2, '.EARLY(EARLY), ' + forwards + ' .PHW(PHW),')
    # Exact inverse: declarations and named parameter forwarding are the ONLY
    # changed characters. Payload, clocks, ports and reductions unchanged.
    inverse = result.replace(declarations, '').replace(forwards + ' ', '')
    if inverse != source:
        raise ValueError('non-parameter source change')
    return result

def tree_count(total, input_cap, pin_budget):
    if input_cap >= pin_budget or min(input_cap, pin_budget) <= 0:
        raise ValueError('nonfinite tree')
    n = math.ceil(total / pin_budget); levels = [n]
    while n > 1:
        n = math.ceil(n * input_cap / pin_budget); levels.append(n)
    return {'levels': levels, 'cells': sum(levels)}

def load():
    origins = json.loads((BASE / 'origins.json').read_text()); result = {}
    for name, origin in origins.items():
        data = (BASE / 'inputs' / name).read_bytes()
        if sha(data) != origin['sha256']:
            raise ValueError('source input changed: ' + name)
        result[name] = data
    # Reproduce every used body from retained libraries, rather than trusting
    # an opaque numeric snapshot. Template labels remain untouched; this does
    # NOT resolve the independent propagated-slew diagnostic.
    for corner in ('ss','ff'):
        selected = {}
        for family in ('seq','invbuf'):
            s = gzip.decompress(result[family+'_'+corner+'.lib.gz']).decode()
            for m in re.finditer(r'\bcell\s*\((\w+)\)\s*\{', s):
                if m[1] in ('DFFHQNx1_ASAP7_75t_R','DFFASRHQNx1_ASAP7_75t_R','BUFx4_ASAP7_75t_R'):
                    selected[m[1]] = block(s, m.start())
        if selected != json.loads(result[corner.upper()+'_driver_cells.json'])['cell_bodies']:
            raise ValueError('selected library cells are not exact source')
    return result, origins

def build():
    raw, origins = load()
    source = raw['ot_v41_field_w17w10.sv'].decode(); prepared = propose_field(source)
    pair = raw['ot_v41_pair_w17w10_rne_wake_prepare.sv'].decode()
    for flag in FLAGS:
        if not re.search(r'parameter integer ' + flag + r'\s*=\s*0', pair):
            raise ValueError('pair default changed')
        if '.' + flag + '(' + flag + ')' not in pair:
            raise ValueError('pair-to-element forwarding missing')
        for kind in ('q', 'bfcolumn'):
            if '-chparam ' + flag + ' 1' not in raw[kind + '_map.ys'].decode():
                raise ValueError('selected measured configuration mismatch')
    element = raw['selected_element.sv'].decode()
    for pattern in (r'parameter integer NCHB\s*=\s*8', r'parameter integer CG\s*=\s*1', r"parameter \[8:0\] CUT\s*=\s*9'b1_0111_1011", r'parameter integer FRONT_PAR\s*=\s*0'):
        if not re.search(pattern, element):
            raise ValueError('implicit pair-to-element defaults no longer match measured map')
    ss = json.loads(raw['SS_driver_cells.json'])['cell_bodies']
    ff = json.loads(raw['FF_driver_cells.json'])['cell_bodies']
    dff = 'DFFHQNx1_ASAP7_75t_R'; buf = 'BUFx4_ASAP7_75t_R'
    lef = gzip.decompress(raw['cells.lef.gz']).decode()
    def area(master):
        b = re.search(r'^MACRO ' + master + r'\s*$(.*?)^END ' + master + r'\s*$', lef, re.M | re.S)[1]
        w, h = map(float, re.search(r'SIZE ([\d.]+) BY ([\d.]+)', b).groups())
        return w * h
    barea = area(buf); farea = area(dff)
    bp = max(cap(ss[buf], 'A'), cap(ff[buf], 'A'))
    dp = max(cap(ss[dff], 'D'), cap(ff[dff], 'D'))
    qmax = max(lut(ss[dff], k, 320, 5.76) for k in ('cell_rise', 'cell_fall'))
    qslew = max(lut(ss[dff], k, 320, 5.76) for k in ('rise_transition', 'fall_transition'))
    if qslew > 160:
        raise ValueError('DFF cannot drive first buffer domain')
    first = max(lut(ss[buf], k, 160, 11.52) for k in ('cell_rise', 'cell_fall'))
    regular = max(lut(ss[buf], k, 80, 11.52) for k in ('cell_rise', 'cell_fall'))
    for slew in (80, 160):
        if max(lut(ss[buf], k, slew, 11.52) for k in ('rise_transition', 'fall_transition')) > 80:
            raise ValueError('buffer slew fails recursive domain')
    setup = constraint(ss[dff], 'setup_rising'); hold = constraint(ff[dff], 'hold_rising')
    qmin = min(lut(ff[dff], k, 320, 5.76, False) for k in ('cell_rise', 'cell_fall'))
    bmin = min(lut(ff[buf], k, 160, 11.52, False) for k in ('cell_rise', 'cell_fall'))
    # Source setRC, not a nominal velocity. Cap-limited repeated construction.
    rc = raw['setRC.tcl'].decode()
    layers = {m[1]: (float(m[2]), float(m[3])) for m in re.finditer(r'set_layer_rc -layer (M\d+) -resistance ([\d.Ee+-]+) -capacitance ([\d.Ee+-]+)', rc)}
    if not all(k in layers for k in ('M2','M3','M4','M5')):
        raise ValueError('selector tier RC absent')
    # Actual assigned tiers, independent maximum R/C across them. The generic
    # signal RC would undercharge M3 resistance and M4 capacitance here.
    R = max(layers[k][0] for k in ('M2','M3','M4','M5'))
    C = max(layers[k][1] for k in ('M2','M3','M4','M5'))
    via_rc = 2 * .0172 * 11.52  # two source V2/V3 turns reserved per hop
    first_wire_cap = 5.76 - bp; regular_wire_cap = 11.52 - max(bp, dp)
    first_len = first_wire_cap / C; regular_len = regular_wire_cap / C
    initial_rc = R * first_len * (first_wire_cap / 2 + bp) + via_rc
    regular_rc = R * regular_len * (regular_wire_cap / 2 + max(bp, dp)) + via_rc
    T = 1000 / 1.2; uncertainty = 60; skew = 25
    def stage(n):
        return qmax + initial_rc + first + (n - 1) * regular + n * regular_rc + setup + uncertainty + skew
    n = 1
    while stage(n + 1) <= T:
        n += 1
    if stage(n) > T:
        raise ValueError('no positive registered construction')
    span = first_len + n * regular_len
    hold_margin = qmin + n * bmin - hold - 25 - skew
    tracks = json.loads(raw['selector_tracks.json']); baseline = json.loads(raw['selector_baseline.json'])
    length = tracks['full_allocated_lane_path']['maximum_length_um']
    placement = baseline['placement']; c = placement['collective_reserved_bbox_DBU']; v = placement['VM_reserved_bbox_DBU']
    sink_length = (max(c[2], v[2]) - min(c[0], v[0]) + max(c[3], v[3]) - min(c[1], v[1])) / 1000
    segments = math.ceil(length / span); sink_segments = math.ceil(sink_length / span)
    inw, outw, writew = 2122, 2088, 2112
    if sum(baseline['ports']['bit_inventory']['inputs'].values()) != inw or sum(baseline['ports']['bit_inventory']['outputs'].values()) != outw:
        raise ValueError('full public interface width changed')
    bits = (inw + outw) * (segments - 1) + (writew + 1) * (sink_segments - 1)
    cycles = 2 * (segments - 1) + sink_segments - 1
    # Every segment gets its own finite data repeater chain; station-to-station
    # is not a single unsupported long buffer. End segments also charged.
    routed_bits_segments = (inw + outw) * segments + (writew + 1) * sink_segments
    data_buffers = n * routed_bits_segments
    # Hold floor: one additional buffer per registered bit, reserved not proof.
    hold_buffers = bits
    clock_pin = max(cap(ss[dff], 'CLK'), cap(ff[dff], 'CLK'))
    clock = tree_count(bits * clock_pin, bp, 23.04)
    # One valid/control reset register per station lane group, data reset-free:
    # validity clears before GO and must fence all old payload on reset.
    reset_bits = 2 * (segments - 1) + sink_segments - 1
    reset_area = reset_bits * area('DFFASRHQNx1_ASAP7_75t_R')
    cell_area = bits * farea + (data_buffers + hold_buffers + clock['cells']) * barea + reset_area
    prior = json.loads(raw['prior_reticle.json'])['area']['screen_with_corridor_mm2']
    diagnostic = json.loads(raw['intrinsic_diagnostic.json'])
    if diagnostic['physical_admission']:
        raise ValueError('historical diagnostic unexpectedly admitted')
    return dict(schema='opentallas.dsrom.selector-station-parent-binding.v1', candidate='DS4096-TP4-S58-PAR2-NP2048', sourcepins=origins,
        caller=dict(historical_field_missing=list(FLAGS), historical_pair_defaults={f: 0 for f in FLAGS}, measured_element={f: 1 for f in FLAGS}, selected_field_parameters=dict(NP=2048,R=64,NBF=362,PHW=10,FAST=1,PP=1,BP=0,NSEG=8,NCH=16,XFQ=4,XFB=8,LV=5,MTP=1,EARLY=1,**{f:1 for f in FLAGS}), inherited_element_defaults_checked=dict(CUT=379,NCHB=8,CG=1,FRONT_PAR=0), proposed_field_sha256=sha(prepared.encode()), default_off=True, all_pair_sites_forwarded=True, exact_inverse_source_gate=True, proposed_source_configuration_join=True, actual_current_field_configuration_join=False, elaborated_or_numerically_qualified=False, added_register_edges=0, parameter_forwarding_area_delta_vs_measured_elements_um2=0, measured_elements_not_historical_field_credit=True),
        historical_intrinsic=dict(physical_admission=False, slew_diagnostic_still_open=True, diagnostic=diagnostic['blocking_source_fact'], remaining_409p969_not_admitted=True, extra_capture_edge_selected=False, two_edge_capture_remaining_ps=2*T-60-839.0934),
        station=dict(clock_period_ps=T, setup_uncertainty_ps=60, hold_uncertainty_ps=25, additional_skew_ps=skew, DFF_master=dff, BUF_master=buf, DFF_area_um2=farea, BUF_area_um2=barea, DFF_SS_clkQ_ps=qmax, DFF_SS_output_slew_ps=qslew, DFF_SS_setup_ps=setup, DFF_FF_hold_ps=hold, DFF_FF_clkQ_lower_ps=qmin, FF_BUF_cell_lower_ps=bmin, FF_hold_margin_before_extra_reserved_hold_buffer_ps=hold_margin, FF_hold_reserved_buffer_not_credited_in_margin=True, first_BUF_SS_delay_ps=first, regular_BUF_SS_delay_ps=regular, source_R_kohm_per_um=R, source_C_fF_per_um=C, RC_tiers=['M2','M3','M4','M5'], two_source_via_RC_ps_per_hop=via_rc, first_wire_cap_fF=first_wire_cap, regular_wire_cap_fF=regular_wire_cap, first_wire_length_um=first_len, regular_wire_length_um=regular_len, first_wire_Elmore_ps=initial_rc, regular_wire_Elmore_ps=regular_rc, BUF_per_registered_segment=n, total_stage_upper_ps=stage(n), next_BUFFER_count_stage_ps=stage(n+1), maximum_positive_segment_um=span, constraints_are_conditional_LUT_domains=True, propagated_slew_or_wire_not_admitted=True),
        transport=dict(max_source_allocated_lane_length_um=length, sink_rectangle_L1_um=sink_length, source_rectangle_not_obstacle_detour_bound=True, input_width=inw, return_width=outw, formed_write_width=writew, segments_each_direction=segments, sink_segments=sink_segments, intermediate_FF_bits=bits, data_BUF_cells=data_buffers, reserved_hold_BUF_cells=hold_buffers, clock_tree=clock, reset_valid_FF_count=reset_bits, per_call_additional_cycles=cycles, nine_call_cycles=9*cycles, nine_call_us=9*cycles/1200, six_position_verification_us=6*9*cycles/1200, MTP_drafter_commit_rollback_unbound=True, old_wire_only_cycles=43, old_wire_only_20_segments_unadopted=True, station_arithmetic_unchanged=True, fixed_total_weights=True, no_new_ACK=True, no_output_ready_invented=True, reset_valid_fence_required=True),
        area=dict(FF_only_mm2_at50pct=bits*farea*2/1e6, full_station_cell_floor_mm2_at50pct=cell_area*2/1e6, FF_only_old_0p052811676_replaced_not_added=True, predecessor_no_station_screen_mm2=prior, noncontainment_screen_plus_station_floor_mm2=prior+cell_area*2/1e6, selector_core_1p68242_charged_once=True, clock_cell_floor_included=True, clock_routes_PG_pinaccess_and_detours_unpriced=True, actual_station_row_placement=False),
        admission=dict(parameter_only_proposal_review_ready=True, existing_mapped_cone_characterization_can_proceed=True, full_context_PR_admitted=False, selector_station_PR_admitted=False, required_own_gates=['resolve propagated/dcalc slew disagreement before admitting wire timing','selected field elaboration must show all three1 on every q/BF pair, historical default0 unchanged','Arch selector-specific PG/via/LEF58 pin-access overlay and station sites; q PDN is not a substitute','finite station clock/reset route, hold and skew within charged source domains','actual formed-write path and source accepted drain/owner visibility join'], fulltoken_not_required_for_local_characterization=True), jobs_launched=0, generator_sha256=sha(Path(__file__).read_bytes()))

def emit(out):
    out.mkdir(parents=True, exist_ok=False)
    raw, _ = load(); source = raw['ot_v41_field_w17w10.sv'].decode(); prepared = propose_field(source)
    (out / 'proposed_field.sv').write_text(prepared)
    (out / 'field_parameter_only.patch').write_text(''.join(difflib.unified_diff(source.splitlines(True), prepared.splitlines(True), fromfile='pinned_field', tofile='proposed_field')))
    model = build()
    (out / 'model.json').write_text(json.dumps(model, indent=2, sort_keys=True) + '\n')
    tracks = json.loads(raw['selector_tracks.json']); baseline = json.loads(raw['selector_baseline.json'])
    hx = baseline['placement']['horizontal_escape_bbox_DBU'][0]
    hy = baseline['placement']['vertical_escape_to_collective_lower_boundary_bbox_DBU'][3]
    count = model['transport']['segments_each_direction']
    records = []
    for e in tracks['assignments']:
        if e['pin'] in ('clock', 'reset'):
            continue  # clock/reset are never converted into data pipeline bits
        dx = e['vertical_x_DBU'] - hx; dy = hy - e['horizontal_y_DBU']
        if min(dx, dy) < 0:
            raise ValueError('source-aligned route changed')
        for i in range(1, count):
            d = (dx + dy) * i / count
            x, y = (hx + d, e['horizontal_y_DBU']) if d <= dx else (e['vertical_x_DBU'], e['horizontal_y_DBU'] + d - dx)
            records.append(dict(pin=e['pin'], station=i, preferred_DBU=[x, y], row_snapped_preferred_DBU=[math.ceil(x/54)*54, math.ceil(y/270)*270], actual_cell_placement=False))
    payload = ''.join(json.dumps(r, sort_keys=True, separators=(',', ':')) + '\n' for r in records).encode()
    (out / 'preferred_source_stations.jsonl.gz').write_bytes(gzip.compress(payload, mtime=0))
    (out / 'station_request.json').write_text(json.dumps(dict(source_aligned_data_station_bits=len(records), expected=(2122+2088)*(count-1), PG_scope='selector-specific including corridor: do not substitute q bottom PDN', actual_cell_placement=False, formed_write_station_pins_unknown=True, dimensions_DBU_site=[54,270], source_station_max_span_um=model['station']['maximum_positive_segment_um'], per_segment_BUF_cells=model['station']['BUF_per_registered_segment'], required='disjoint legal DFF/BUF/clock/reset sites, all macro/PG/OBS/via exclusions, source endpoint access and bank/formed-write pin geometry', no_clock_reset_data_retiming=True), indent=2, sort_keys=True)+'\n')

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    emit(p.parse_args().out)

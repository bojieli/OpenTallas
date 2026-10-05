#!/usr/bin/env python3
"""Source-elaborated Qwen reset census; no technology mapping or admission.

Replay from the committed proc JSON gzip records. WIDTH counts are elaborated
register bits before optimization, not mapped cell survival or pin capacitance.
"""
import argparse
import collections
import gzip
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/uarch/qwen_rom_reset_producer_g0_20261002'


def load(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def census(net):
    modules = net['modules']
    top, = [n for n, m in modules.items() if int(str(m['attributes'].get('top', '0')), 2)]
    groups = collections.defaultdict(collections.Counter)
    registers = []
    primitives = collections.Counter()

    def visit(module, path, ports):
        m = modules[module]
        aliases = {}
        for name, port in m['ports'].items():
            for i, bit in enumerate(port['bits']):
                connected = ports.get(name, [])
                aliases[bit] = connected[i] if i < len(connected) else path + '/' + name + '[' + str(i) + ']'

        def resolve(bits):
            return [aliases.get(b, str(b) if isinstance(b, str) else path + '/net' + str(b)) for b in bits]

        for name, c in m['cells'].items():
            typ = c['type']; cp = path + '/' + name
            conn = c['connections']
            if typ in modules and not modules[typ]['attributes'].get('blackbox'):
                visit(typ, cp, {p: resolve(v) for p, v in conn.items()})
            elif typ in ('$dff', '$adff', '$sdff', '$dffe', '$adffe', '$sdffe'):
                width = int(c['parameters']['WIDTH'], 2)
                clock = resolve(conn['CLK'])[0]
                reset = resolve(conn.get('ARST', conn.get('SRST', [])))
                group = '/'.join(path.split('/')[1:3]) if '/' in path else 'tile_or_die_local'
                groups[group]['clock_bits'] += width
                groups[group]['async_reset_bits'] += width if 'ARST' in conn else 0
                groups[group]['sync_reset_bits'] += width if 'SRST' in conn else 0
                registers.append(dict(path=cp, type=typ, width=width, clock=clock,
                                      reset=reset, source=c['attributes'].get('src', '')))
            elif not typ.startswith('$'):
                primitives[typ] += 1
            elif typ in ('$memrd_v2', '$memwr_v2', '$meminit_v2'):
                if int(c['parameters'].get('CLK_ENABLE', '0'), 2):
                    group = '/'.join(path.split('/')[1:3]) if '/' in path else 'tile_or_die_local'
                    groups[group]['memory_clock_ports'] += 1
                    registers.append(dict(path=cp, type=typ, width=0,
                        clock=resolve(conn['CLK'])[0], reset=[],
                        source=c['attributes'].get('src', '')))
            elif 'CLK' in conn or typ in ('$dlatch', '$adlatch'):
                raise ValueError('Unaccounted sequential cell: ' + cp + ' ' + typ)

    visit(top, top, {})
    totals = {key: sum(g[key] for g in groups.values()) for key in
              ['clock_bits', 'async_reset_bits', 'sync_reset_bits', 'memory_clock_ports']}
    domains = collections.defaultdict(collections.Counter)
    for row in registers:
        domains[row['clock']]['clock_bits'] += row['width']
        if row['reset']:
            domains[row['clock']]['reset_bits'] += row['width']
    return dict(top=top, totals=totals, groups=dict(groups), clock_groups=dict(domains), primitives=dict(primitives),
                registers=registers, scope='Complete elaborated hierarchy, proc only; no opt/map/CTS. Register WIDTH is a source load inventory, not mapped pins.')


def startup(first_go_edge=3, ireg=1):
    """Discrete positive-edge schedule, external release before edge 1.

    s2 sees old s1. go_q and active likewise see pre-edge inputs. Caller must
    retain a request until the first acceptable edge, with ib/x stable there.
    """
    s1 = s2 = go_q = active = 0
    rows = []
    for edge in range(1, 9):
        reset_before = s2
        go = int(edge == first_go_edge)
        seen_go = go_q if ireg else go
        read = int(bool(reset_before and active))
        next_active = int(bool(reset_before and (active or seen_go)))
        rows.append(dict(edge=edge, reset_before=reset_before, ib_go=go,
                         engine_go=seen_go, producer_read_after=read))
        go_q = go if reset_before else 0
        active = next_active
        s2, s1 = s1, 1
    return rows


def reset_constraint_envelopes():
    """All characterized RESETN slew grid values, no interpolation/extrapolation.

    A conservative envelope is a release requirement, not a parent arrival.
    """
    from qwen_rom_hold_capture_loaded_map import block
    result = {}
    for corner in ['ss', 'ff']:
        raw = gzip.decompress((OUT / ('inputs/seq_' + corner + '.lib.gz')).read_bytes()).decode()
        unit = re.search(r'time_unit\s*:\s*"([^"]+)"', raw)[1]
        if unit != '1ps':
            raise ValueError('Unexpected Liberty timing unit ' + unit)
        cell = block(raw, re.search(r'cell\s*\(\s*DFFASRHQNx1_ASAP7_75t_R\s*\)', raw).start())
        pin = block(cell, re.search(r'pin\s*\(\s*RESETN\s*\)', cell).start())
        arcs = []
        for match in re.finditer(r'\btiming\s*\(', pin):
            timing = block(pin, match.start())
            kind = re.search(r'timing_type\s*:\s*(\w+)', timing)[1]
            if kind not in ['recovery_rising', 'removal_rising', 'min_pulse_width']:
                continue
            for tm in re.finditer(r'\b(?:rise_constraint|fall_constraint)\s*\(', timing):
                table = block(timing, tm.start())
                values = table.split('values', 1)[1]
                numbers = [float(n) for n in re.findall(r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?', values)]
                arcs.append(dict(type=kind, min_ps=min(numbers), max_ps=max(numbers),
                    condition=(re.search(r'when\s*:\s*"([^"]+)"', timing)[1]
                               if 'when' in timing else 'unconditional')))
        result[corner] = arcs
    return result


def persistent_kv_context():
    contract = load(OUT / 'inputs/russell_contract_r8.json')
    calendar = load(OUT / 'inputs/russell_full_calendar_r8.json')
    handoff = load(OUT / 'inputs/russell_handoff_r8.json')
    r = contract['candidate_resources']
    return dict(source_commit='31292146b5d034b4776f48e1ae3fe56d6c8ebdfe',
        status=contract['status'], source_ports=contract['source_ports'],
        resources=r, blockers=contract['blockers'],
        owner_bindings=handoff['next_binding'],
        clock_reset=dict(service_Hz=1000000000, streaming_Hz=1200000000, serial_Hz=900000000,
            source='r14 clock_bridge has src_clk/fast_clk/dst_clk and shared rst_n. FIFO/held-route reset users are a separate service branch, not tile metadata sinks.',
            physical_release='Parent must coordinate service/FIFO reset and credits with tile readiness; tile two-FF streaming root cannot release the 1GHz service or 0.9GHz serial domain.',
            payload='Reset may clear validity/control only under drain/quarantine contract. Host stage KV reset does not establish persistent state; never erase persistent KV on layer hop.'),
        slot=dict(service_macro_count_per_stack=r['actual_service_macro_count_per_stack'],
            service_macro_area_mm2_per_stack=r['actual_service_macro_area_mm2_per_stack'],
            inherited_service_slot_mm2_per_stack=r['inherited_service_slot_mm2_per_stack'],
            current_slot_fit=r['slot_fit'], current_channel_capacity=r['channel_capacity'],
            fill_boundary_tracks=r['required_parallel_signal_tracks_at_fill_boundary'],
            complete_control_CDC_demux_area_mm2=None,
            note='Service SRAM inventory exists; macro fit alone is not complete service/reset/CTS/PGOBS/routing fit.'),
        latency=dict(existing_read_bytes_charged_once=contract['ledger']['read_bytes_charged_once'],
            incremental_full_reload_bytes=0,
            conservative_composition=calendar['analytical_calendar']['composition'],
            conservative_seconds=calendar['analytical_calendar']['analytical_token_latency_seconds'],
            qualification=handoff['bound'], selected_production_policy=False,
            admitted_latency_or_rate=False,
            reset_startup_addition='Two streaming startup edges only once, conditional on joined domain readiness; never repeat per layer or per token, never add another KV read charge.'),
        lowered_window_gap='Current r33 lowered-window integration remains unjoined. No actual TP4 persistent producer/stage owner join, retained allocation receipt, validated reverse-credit/quarantine, or full selected prefetch/fill release trace. No numerical second-position run.',
        fill_capture=dict(register_clock_bits=1032, asynchronous_reset_bits=1,
            fields=dict(ce=1,address=7,data=512,mask=512),
            edges_to_macro_visibility=2, address_rows_per_tile=54,
            note='Source wrapper registers kvw_*; only kvw_ce_q resets. Added once to logic-only census; two 128x256 SRAM clocks counted separately.'),
        adoption=False)


def build(*, model_extension):
    if model_extension != 'qwen-reset':
        raise ValueError('Explicit qwen-reset model extension selection required')
    from uarch_model_qwen_reset import qwen_rom_reset_context_price
    tile = census(load(OUT / 'tile_proc.json.gz'))
    die = census(load(OUT / 'die_proc.json.gz'))
    inputs = load(OUT / 'inputs/reset_producer_price_inputs_r1.json')
    provider = load(OUT / 'inputs/provider_context_r1.json')
    price = qwen_rom_reset_context_price(tile['totals'], die['totals'], inputs)
    envelopes = reset_constraint_envelopes()
    ff_removal = max(a['max_ps'] for a in envelopes['ff'] if a['type'] == 'removal_rising')
    ss_recovery = max(a['max_ps'] for a in envelopes['ss'] if a['type'] == 'recovery_rising')
    release_window = dict(
        deassert_min_ps_after_previous_root_posedge=ff_removal + 25,
        deassert_max_ps_after_previous_root_posedge=1e12 / 1.2e9 - ss_recovery - 60,
        reset_low_pulse_min_ps=max(a['max_ps'] for arcs in envelopes.values() for a in arcs if a['type'] == 'min_pulse_width'),
        characterized_clock_and_reset_slew_ps=[5, 320],
        scope='Conservative external-root pin requirement across Liberty grids, before wire/skew. Both root FFs must meet it. This is not an observed provider phase, internal closure, or recovery/removal waiver.')
    for scope, stem in [(tile, 'tile_registers_r1'), (die, 'die_registers_r1')]:
        registers = scope.pop('registers')
        raw = json.dumps(registers, sort_keys=True, separators=(',', ':')).encode()
        inventory = OUT / (stem + '.json.gz')
        if gzip.decompress(inventory.read_bytes()) != raw:
            raise ValueError('Register census replay mismatch ' + stem)
        scope['register_inventory'] = dict(path=str(inventory.relative_to(ROOT)),
            register_cell_count=len(registers),
            sha256=hashlib.sha256(inventory.read_bytes()).hexdigest())
    sourcepins = load(OUT / 'sourcepins-r2.json')
    for path, digest in sourcepins['sha256'].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise ValueError('Source pin changed: ' + path)
    return dict(schema='opentallas.qwen-rom-reset-context-g0.v1',
        selected_model_extension='tools/uarch_model_qwen_reset.py',
        status='SOURCE_COMPOSED_PHYSICAL_PARENT_DEPENDENCIES_OPEN',
        sourcepins=sourcepins, tile=tile, die_bench_hardware=die, price=price,
        protocol=dict(assertion='Asynchronous low assertion, no ROM ECC added; reset valid/control, not ROM payload.',
            release='Two same-streaming-clock DFFASR/QN plus two INV. External RESETN on both; SETN tied high. No arbitrary-phase recovery/removal waiver.',
            acceptance='Release after edge 2; first downstream acceptance edge 3. IREG captures ib/x/go then; engine accepts at edge 4; first ROM producer re/address after edge 5; macro accepts edge 6; MEM_EXTRA capture edge 7.',
            bench='rt_rst_n NBA at cyc5. Synchronizer stages sample at cyc6/7; downstream reset available at cyc8. Bench start NBA at cyc7 is first sampled at cyc8. This is a source schedule, not a physical inputdelay.',
            queue='Tile ready()/idle() are unconnected. No ready handshake or request queue exists at ib_go. Parent must hold/schedule ib_go and ib/x through first acceptance; never silently add a queue.',
            scope='Per-tile producer resets complete tile control. Die/core remain a distinct upstream reset branch. A global owner must coordinate starts and streaming/serial readiness.',
            startup_trace=startup(), per_token_added_cycles=0, per_layer_added_cycles=0),
        source_ports=dict(producer='u_me.g_issue_fast: registered wrom_re, wrom_addr<=cur; address has no reset assignment and is qualified only by accepted CE.',
            address_width_bits=24, low_address_bits=12, macro_address_sinks=120,
            extra_strobe_D_sinks=4, bank_strobe_loads=[6,6,5], hold_term_loads=[8,8],
            metadata_reset_leaf_loads=[8]*11+[2], memory_MACs_per_cycle=64,
            ROM_ports=10, ROM_physical_bits_per_active_port=266, payload_bits_per_active_pair=512,
            note='64 MAC/cycle describes existing W16/TG4 tile; reset block performs zero MACs and zero memory transfers.'),
        staging=dict(MEM_EXTRA=1, data_capture_bits=2560, existing_consumer_bits=512,
            no_new_data_stage=True, no_lane_or_arithmetic_reordering=True, default_off=True),
        persistent_KV=persistent_kv_context(),
        parent_milestone=dict(commit='68a05aca992a86da70c2ef362a0815508a69a506',
            literal_review=load(OUT / 'inputs/parent_Qwen_bank5_context_parent_review.json'),
            provider_additive_manifest=load(OUT / 'inputs/parent_manifest.json'),
            hardware_qualification=False,
            restored_original_observer=True, r33_lowered_window_join_complete=False),
        clock_domains=dict(source_tile='All tile registers clocked by clk; same 1.2GHz streaming proposal.',
            source_die='clk plus core.g_me_cg.u_me_cg.u_icg gated me_clk; enable forced by !rst_n; CXX tiles receive direct clk.',
            required_physical='Streaming 1.2GHz, serial 0.9GHz. No separate 0.9GHz clock/reset/CDC port exists in this fixture. Two streaming FFs cannot alone release a physical serial domain.',
            serial_release='Parent must provide distinct serial-domain release and readiness join; its hardware cost is not included in 0.84564um2.'),
        constraints=provider['constraints'],
        root_RESETN_constraint_grid_envelopes=envelopes,
        conditional_external_release_window=release_window,
        release_equations=dict(external_root_removal='RESETN_min - root_CLK_max >= FF removal(slews, condition) +25ps',
            external_root_recovery='next_root_CLK_min - RESETN_max >= SS recovery(slews, condition) +60ps',
            tile_removal='root_stage2_CLKQ_min + INV_min + reset_distribution_min - downstream_CLK_skew_max >= FF removal +25ps',
            tile_recovery='Tstream - root_stage2_CLKQ_max - INV_max - reset_distribution_max - skew_max >= SS recovery +60ps',
            address_hold='registered_address_CLKQ_min + two_BUF_min + wire_min - macro_CLK_skew_max >= 42.422199ps',
            no_waivers='Apply at both external rootFF RESETN pins, every tile reset pin and every active macro capture endpoint. Grid envelopes do not establish slew or arrival bounds.'),
        ranked_release_dependencies=[
            dict(rank=1, owner='Qwen die/reset parent', missing='Physical external RESETN min/max phase, pulse width, recovery/removal at both root FFs; coordinated streaming/serial reset and start contract.'),
            dict(rank=2, owner='Qwen tile context parent', missing='Mapped complete-tile clock/reset pin classes and loads, full reset distribution, CTS slew/skew, source address/strobe CLKQ SS/FF. Source register census below is complete for the explicit fixture.'),
            dict(rank=3, owner='Qwen physical slot parent', missing='Incremental reset/clock tree cells and wire, pin/OBS/PG slot placement and routing-layer/corridor capacity receipt.'),
            dict(rank=4, owner='Euclid/context STA', missing='Only after 1-3 compose: actual two-FF/INV path FF hold, SS setup, recovery/removal, macro capture, pulse width, complete tile SS/FF. No input-zero-delay failure relabeling.')],
        admission=dict(root_RTL=False, new_mapping=False, tile_PR=False, hardware_adoption=False,
                       generic_literal_gate_is_not_hardware_admission=True,
                       external_zero_delay_is_not_internal_failure=True))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model-extension', choices=['qwen-reset'], required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    with args.output.open('x') as f:
        json.dump(build(model_extension=args.model_extension), f, indent=2, sort_keys=True); f.write('\n')

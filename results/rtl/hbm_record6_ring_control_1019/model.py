#!/usr/bin/env python3
"""R6 integer-edge resource model; no RTL simulation or macro timing claim."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
family = HERE / 'family'
macro = json.loads((family / 'ot_sram_1r1w2c_128x64_m1.json').read_text())
prior = json.loads((HERE / 'inventory_exact.json').read_text())
producer = json.loads((HERE / 'producer_records.json').read_text())
records = {x['k_layer']: x for x in producer['records']}
assert records[5]['outputs']['O']['sha256'] == records[6]['inputs']['A']['sha256']
sectors = []
for g in range(4):
    for q in range(4):
        count = 16 if q in (0, 2) else 4
        item = next(x for x in prior['groups'] if x['group'] == g and x['quarter'] == q)
        first = item['roles']['A']['first']
        for k in range(count):
            port = k % 8
            row = 2 * g + k // 8 if count == 16 else g
            sectors.append(dict(group=g, quarter=q, store_group=k, store_row=g,
                vm_port=port, vm_row=row, physical_vm_sector=(q << 13) | (row << 3) | port,
                fill_command_serial=row, fill_commit_serial=row + 21,
                logical_words=list(range(first + 8*k, first + 8*k + 8))))
all_words = [w for x in sectors for w in x['logical_words']]
assert sorted(all_words) == list(range(46336, 47616))
assert len(set(all_words)) == 1280 and len(sectors) == 160
assert len(set((x['quarter'], x['vm_port']) for x in sectors)) == 24
assert len(set((x['quarter'], x['vm_port'], x['fill_command_serial']) for x in sectors)) == 160
assert max(x['fill_commit_serial'] for x in sectors) == 28

rings = []
checks = 0
ff_checks = 0
for chunk in range(64):
    for k in range(2, 8):
        delay = (k - 1) * 7
        depth = delay - 2
        rings.append(dict(chunk=chunk, source_lane_in_chunk=k, logical_delay=delay,
            macro_index=len(rings), used_rows=depth, used_bits_per_row=43,
            write_address='t mod N', read_address='(t+1) mod N',
            data='[31:0] FP32,[32] valid,[34:33] issue-group,[42:35] epoch',
            clock='same serial root on rclk/wclk; physical skew remains unqualified'))
        # Edge-level disjoint-row model, including an input and output face.
        # Every reset starts with arbitrary stale memory and invalid face state.
        for reset_at in (0, 1, 2, delay-1, delay, 2*delay+1):
            mem = [('stale', -1)] * depth
            pin = rd = out = ('invalid', -1)
            t_local = 0
            for t in range(reset_at, reset_at + 3*delay + 10):
                w = t_local % depth
                r = (t_local+1) % depth
                assert w != r
                out = rd
                rd = mem[r]
                mem[w] = pin
                pin = ('epoch', t)
                if t_local >= delay-1:
                    assert out == ('epoch', t-delay+1), (delay, t, out)
                    checks += 1
                t_local += 1
        for reset_at in (0, 1, 2, delay-1, delay, 2*delay+1):
            mem = [('stale', -1)] * (delay-1)
            for age in range(3*delay+10):
                t = reset_at + age
                p = age % (delay-1)
                q = mem[p]  # actual FF nonblocking OLD, unlike dual-clock macro task
                mem[p] = ('epoch', t)
                if age >= delay-1:
                    assert q == ('epoch', t-delay+1)
                    ff_checks += 1
count = len(rings)
assert count == 384
physical = macro['area']
result = dict(scope='MODEL ONLY; integer-edge feasibility, no RTL/numerical/native qualification',
    producer=dict(image_index=5, k_layer=5, tag=records[5]['tag'],
        output_sha256=records[5]['outputs']['O']['sha256'],
        priced_complete_stream=1463.31, requested_start_stream=1479.31,
        available_priced_prefetch_stream=16.0, actual_sector_visibility=None),
    consumer=dict(image_index=6, k_layer=6, price_index=4, tag='q_norm.ss', occurrence=0,
        R_word=49920, R_gold='40a2a1ed', downstream_image=10,
        downstream_price_index=8, full_token=False),
    fill=dict(sectors=sectors, total_words=1280, distinct_banks=24,
        first_command_serial=0, last_command_serial=7, last_commit_serial=28,
        prefetch_before_actual_producer=False, placement_relocation_cost=None),
    ff_pointer_rings=dict(independent_streams=384, per_stream_payload_width=33,
        max_independent_indexed_bits=41*33,
        total_indexed_payload_ff=64*33*sum(d-1 for d in (7,14,21,28,35,42)),
        output_ff=384*33, pointer_ff=64*sum((d-2).bit_length() for d in (7,14,21,28,35,42)),
        maturity_ff=64*sum((d-1).bit_length() for d in (7,14,21,28,35,42)),
        input_capture_ff=16896,
        payload_capture_area_lower_um2=(297792+12672+16896)*0.2916,
        payload_capture_tt_clk_cap_ff=(297792+12672+16896)*0.474736,
        optional_identity_width=43, optional_identity_max_independent_bits=41*43,
        indexed_write_ports_per_stream=1, indexed_read_ports_per_stream=1,
        old_semantics='FF nonblocking read-before-write at the same private pointer',
        integer_identity_checks=ff_checks,
        physical_qualified=False),
    rings=dict(mapping=rings, macros=count, physical_capacity_bits=count*8192,
        occupied_row_bits=sum(x['used_rows']*43 for x in rings),
        face_payload_ff=count*2*43, prior_capture_ff=16896,
        pointer_ff_upper=count*7, warmup_ff_upper=count*6,
        macro_area_um2=count*physical['macro_area_um2'],
        macro_clock_contacts=count*2,
        macro_tt_clock_cap_ff=count*2*macro['timing']['tt']['clk_cap_ff'],
        ring_integer_checks=checks, timing_qualified=False,
        mathematical_aggregate_capacity_bound_not_port_mapping=37),
    source_hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
        sorted(family.iterdir()) if p.is_file()},
    unresolved=['actual per-sector COLL→VM producer visibility/physical placement',
        'exact emitted per-stage lane controls at source-selected pin/leaf/fetch profile',
        'fragment-tap pin layout and dedicated global-root-to-qcore operand connection',
        'actual reducer→RF route count, RF read/write lifetime and R VM placement',
        'native clocks/earliest SRAM CQ/hold, all-driver fanout, geometry and parent slot',
        'full compiler/host/calendar lowering and source-only numerical prototype authorization'])
(HERE / 'model.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(dict(scope=result['scope'], words=len(all_words), sectors=len(sectors),
    banks=result['fill']['distinct_banks'], ring_checks=checks,
    ff_pointer_rings=result['ff_pointer_rings'],
    rings={k:v for k,v in result['rings'].items() if k != 'mapping'})))

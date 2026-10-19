#!/usr/bin/env python3
"""Bounded source/geometry arithmetic; no RTL simulation or physical qualification."""
import collections
import hashlib
import json
import math
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load(n):
    return json.loads((HERE / 'inputs' / n).read_text())

raw = load('reader_row_raw_plan.json')
current = load('current_mu3_plan.json')
facts = load('raw_facts.json')
native = ROOT / 'physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2'
lef = next(native.glob('*.lef'))
t = lef.read_text()
w, h = map(float, re.search(r'SIZE ([\d.]+) BY ([\d.]+)', t).groups())
contacts = collections.Counter()
for name, body in re.findall(r'  PIN (\S+)\n(.*?)  END \1', t, re.S):
    if 'USE POWER' in body or 'USE GROUND' in body:
        continue
    rect = list(map(float, re.search(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)', body).groups()))
    contacts['W' if rect[0] < .05 else 'E' if rect[2] > w - .05 else 'interior'] += 1

# The source compiler's exact midpoint tree, without importing its numpy/fixture machinery.
def tree(a, b, out):
    out[a] = []
    if b - a == 2:
        out[a] = [a+1]
        tree(a+1, b, out)
    elif b - a > 2:
        m = a + 1 + (b-a-1)//2
        out[a] = [a+1, m]
        tree(a+1, m, out)
        tree(m, b, out)
    return out

def subtree(ch, d):
    return [d] + [x for c in ch[d] for x in subtree(ch, c)]

tx = []
for k in (3, 6):
    ch = tree(0, k, {})
    n = 262144
    step = math.ceil(n/k)
    for rank in range(4):
        for d in range(1, k):
            ds = subtree(ch, d)
            lo = rank*n + min(n, min(ds)*step)
            end = rank*n + min(n, (max(ds)+1)*step)
            first, last = lo//16, (end-1)//16
            nw = last-first+1
            tx.append(dict(k=k, rank=rank, die=d, subtree=ds, begin=lo, end_exclusive=end,
                           key_span=end-lo, first_window=first, last_window=last,
                           windows=nw, modulo8192_injective=nw <= 8192))

reach = []
for l in raw['links']:
    if l['i'] in ('is_tail', 'iq_src_l0', 'iq_src_l1', 'hrq_01', 'hrd_01'):
        m = max(abs(s[2]-s[0])+abs(s[3]-s[1]) for s in l['h'])
        reach.append(dict(name=l['i'], bits=l['b'], path_um=l['L'], stations=l['s'],
                          station_points=l['sp'], endpoints=l['e'], max_polyline_segment_um=m,
                          analytic_reserve_um=405-m, native_pin_reach_pass=None,
                          registered_phase_latency_edges=None))

rb = {b['name']:b for b in raw['blocks']}
cb = {b['name']:b for b in current['blocks']}
lk = []
for name in sorted(n for n in cb if n.startswith('lk_')):
    old, new = rb[name], cb[name]
    lk.append(dict(name=name, raw={k:old[k] for k in ('master','x','y','w','h')},
                   current_mu3={k:new[k] for k in ('master','x','y','w','h')},
                   area_delta_um2=new['w']*new['h']-old['w']*old['h']))

out = dict(schema='opentallas.s81.l20.parent_model.v1', status='MODEL_BLOCKED_NOT_A_GATE',
  source_commit='2b7827041', current_mu3_commit='293b25c2f',
  hashes={str(p.relative_to(ROOT)):sha(p) for p in [
      ROOT/'rtl/dsrom_sys/s81_dv/idx/dsdv_idx_tree.sv',
      ROOT/'tools/s81_dv/layer_prog/lower_bk.py', lef,
      *sorted((HERE/'inputs').glob('*.json'))]},
  capacity=dict(old_slots=1130, new_slots=1070, lost_slots=60,
                loss_pct=100*60/1130, ideal_die_increase_pct=100*60/1070,
                exact_production_total_dies=None, exact_production_rank_map=None,
                reason='No per-stage/per-rank production ROM payload or repacking manifest binds these slots.',
                conditional_integer_sensitivities=[
                    dict(assumption='Every baseline die fully occupies 1130 interchangeable ROM slots; global pooling',
                         baseline=base, lower_bound_dies=math.ceil(base*1130/1070),
                         tp4_group_lower_bound_dies=4*math.ceil(base*1130/(4*1070))) for base in (388,440,520)],
                layer_group_sensitivity=dict(assumption='Each old 10-die layer copy fills all ROM slots, freely repackable within its copy',
                                             old_dies=10,new_dies=11,
                                             eight_duplicated_groups_old_dies=80,
                                             eight_duplicated_groups_new_dies=88),
                production_tp=4, su_l20_dies_per_rank=6, su_l20_rank_dies=24,
                mu_l20_old_model_owner_dies=10, mu_l20_old_model_helper_dies=10,
                mu_copy_AB_helper_shared=True,
                mu_after_capacity_exact_dies=None),
  reader=dict(count=16, outline_um=[518.4,777.6], std_synth_area_um2=196973,
              outline_area_um2=518.4*777.6,
              std_over_outline=196973/(518.4*777.6), native_macro_count=6,
              native_macro_area_um2=6*w*h,
              std_over_outline_minus_macros=196973/(518.4*777.6-6*w*h),
              outline_granted=False, legal_native_pin_escape=None, legal_macro_grid=None,
              pg_contacts=None, clock_regions=None,
              source_kit_outline_um=[1058.4,1101.6]),
  native_macro=dict(master=native.name, size_um=[w,h], non_pg_contacts=dict(contacts),
                    full_face_density_per_um={s:n/h for s,n in contacts.items() if s in ('W','E')},
                    face_rule_pass=all(n/h <= 6 for s,n in contacts.items() if s in ('W','E')),
                    face_rule='<=6 distinct native contacts per full face um, clock counted',
                    widened_native_view=None),
  tx=dict(source_score_store_bits=8192*256, actual_index_buffer_useful_bits=64*512,
          score_store_macro_count=32, index_buffer_macro_count=2,
          implemented_macro_count=34, implemented_macro_bits=34*256*256,
          area_if_reader_native_family_bound_um2=34*w*h, exact_physical_macro_binding=None,
          transmitting_range_checks=tx, all_ranges_injective=all(r['modulo8192_injective'] for r in tx),
          checked_scope='All contiguous subtree windows; includes more windows than sparse selected children actually write.',
          comment_correction='Largest transmitting L20 subtree [131073,262144):131071 keys,8192 windows; not131073 keys.',
          memory_contract='masked1R1W; same-edge read returns OLD; disabled read holds; capture is always on',
          behavioral_default_sram_macro=0, die_section_sram_macro=1,
          reset_clears_memory=False, repeated_job_write_before_use_proof=None,
          same_address_collision_lifetime_proof=None, residual_indexed_queue_native_proof=None),
  parent=dict(current_lk_rev2=lk, lk_extra_area_um2=sum(r['area_delta_um2'] for r in lk),
              lk_slot_overlay_only=True, current_complete_link_retarget=None,
              svc_available_um2=1252*1235, svc_old_estimate_um2=1491000,
              svc_old_estimate_fit=(1252*1235)/1491000,
              svc_actual_synth_area_um2=None, svc_actual_fit=None,
              path_reach=reach, parent_fit=False, source_513bit_query_to_2x276_link_binding=None,
              die_link_latency_record_edges=729, current_source_bound_die_link_latency_edges=None,
              crossing_activity_bits=None, actual_link_energy_pj=None,
              energy_formula='sum_over_links(real_transferred_bits * actual_energy_pj_per_bit) + repeater/register/clock energy',
              token_su_latency_edges=None, token_mu_period_edges=None,
              note='Raw cut0.5663/bit-mm396572/relaybits846540 are historical, not current LKrev2 composition.'),
  evidence=dict(tree_positive='historical/tree2_m0.log:k3+k6 PASS; corrupt FAIL',
                tree_mutants='historical/tree2_m1,m2,m3.log:all FAIL as intended',
                reader_open_lanes='historical/rd_campaign.log:fourpositive+MUT6FAIL/om0PASS',
                tree_tx_sram_macro=0,
                qf_historical='historical/qf.log:old positive FAIL retained',
                qf_current='qf/fleet.log:5.050 positive nerr0 PASS; MUT1 nerr67 FAIL',
                qf_current_source_sha256=sha(ROOT/'rtl/dsrom_sys/s81_dv/idx/dsdv_idx_tree.sv'),
                full_su_mu_token_qualified=False))
(HERE/'model.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print('MODEL_BLOCKED: native faces >6/um; production integer rank/payload/fit/phase/energy/lifetime unknown')

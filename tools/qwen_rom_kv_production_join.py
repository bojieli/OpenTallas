#!/usr/bin/env python3
"""Opt-in source producer/state and transport receipt joins. No RTL admission.

Callbacks must expose real payloads and receipts. Unit fixtures demonstrate
protocol invariants only. A source shape profile is never a production trace.
"""
import argparse
import hashlib
import json
from pathlib import Path
from qwen_rom_persistent_kv_g0 import Owner, Homes, ROOT
from qwen_rom_kv_identity_binding import validate


def decoded_fp8(code):
    """Literal tile e4m3_f32 decoding; no new rounding point."""
    e, m = (code >> 3) & 15, code & 7
    if e:
        fe, fm = e + 120, m << 20
    elif m & 4:
        fe, fm = 120, (m & 3) << 21
    elif m & 2:
        fe, fm = 119, (m & 1) << 22
    elif m & 1:
        fe, fm = 118, 0
    else:
        fe, fm = 0, 0
    return ((code >> 7) << 31) | (fe << 23) | fm


CANONICAL = {decoded_fp8(c): c for c in range(256) if c not in (128, 127, 255)}


def producer_byte(bits):
    if bits not in CANONICAL:
        raise ValueError('payload is not a canonical current KV_FP8 producer value')
    return CANONICAL[bits]


class ProducerJoin:
    """Bind accepted SU issues and actual lane writes to a pinned stage image.

    Explicit 512-byte current row state per owner, at most one live row/rank.
    No issue is inferred from fetch, no backing prefix inferred from lane output.
    """
    def __init__(self, image, owner, position):
        import hdc_isa as I
        from hdc_qwen_fullshape_isa_w12 import decode_instruction
        if not 0 <= position < 8192:
            raise ValueError('position')
        self.owner, self.position = owner, position
        self.image_sha256 = hashlib.sha256(image).hexdigest()
        words = [int(x, 16) for x in image.decode().split()]
        if not 0 < len(words) <= 4096 or any(w >= 1 << 1024 for w in words):
            raise ValueError('stage image aperture')
        dyn = [0, 0, position*64, (position//16)*128*16+position%16,
               position*128, position+1, position//(16*6144)+1]
        self.expected, self.accepted, self.bytes = {}, set(), {}
        for pc, word in enumerate(words):
            f = decode_instruction(word)
            if f['unit'] != I.UNIT_SU or f['dst'] != I.DST_KV:
                continue
            if f['d_d'] not in (I.DYN_KWRITE, I.DYN_VWRITE):
                raise ValueError('unbound KV destination dynamic')
            addresses = {f['d_base']+dyn[f['d_d']]+o*f['d_so']+i*f['d_si']
                         for o in range(f['su_nout']) for i in range(f['su_nin'])}
            if len(addresses) != f['su_nout']*f['su_nin']:
                raise ValueError('aliased producer instruction')
            self.expected[pc] = addresses
        wanted = {self.address(k, h, d) for k in ('K', 'V')
                  for h in range(2) for d in range(128)}
        all_addresses = [a for values in self.expected.values() for a in values]
        if len(all_addresses) != 512 or set(all_addresses) != wanted:
            raise ValueError('stage image does not produce exactly the TP4 KV row')

    def address(self, kind, head, dim):
        p = self.position
        return (((head*512+p//16)*128+dim)*16+p%16 if kind == 'K'
                else 2*8192*128+(head*8192+p)*128+dim)

    def issue(self, pc):
        if pc not in self.expected or pc in self.accepted:
            raise ValueError('unrecognized or duplicate accepted issue')
        self.accepted.add(pc)

    def lane_write(self, pc, address, fp32_bits):
        if pc not in self.accepted or address not in self.expected[pc] or address in self.bytes:
            raise ValueError('write lacks unique accepted producer issue')
        self.bytes[address] = producer_byte(fp32_bits)

    def state(self):
        if len(self.bytes) != 512:
            raise ValueError('incomplete producer row')
        return {k: bytes(self.bytes[self.address(k, h, d)] for h in range(2)
                         for d in range(128)) for k in ('K', 'V')}


class Receipts:
    """Finite per-stack tag quarantine through consumed grant and reader drain.

    Keys retain full request identity, endpoint, physical tag, generation and
    beat. LEN is a count of 32B sectors (1..32); sector is the burst base.
    Source allocation is supplied, never guessed from request or queue index.
    """
    def __init__(self, reader_limit=1024):
        if not 1 <= reader_limit <= 1024:
            raise ValueError('source-sized assembly reader bound')
        self.live, self.last_generation = {}, {}
        self.clock = -1
        self.reader_limit = reader_limit

    def apply(self, e):
        t = e['service_cycle']
        if not isinstance(t, int) or t < self.clock:
            raise ValueError('nonmonotone service clock')
        word = int(e['identity'], 16)
        owner = Owner(**e['owner'])
        identity = validate(word, e['endpoint'], owner, e['producer_pc'])
        key = (e['endpoint'], identity['die'], e['stack'], e['physical_tag'])
        if identity['stack'] != e['stack'] or not 0 <= key[3] < 4096:
            raise ValueError('allocation routing')
        op = e['event']
        if op == 'allocate':
            n = e['sectors']
            if key in self.live or not 1 <= n <= 32 or e['write'] not in (False, True):
                raise ValueError('live tag reuse or burst aperture')
            if identity['sector']+n > 703125000:
                raise ValueError('burst exceeds provider aperture')
            if identity['transport'] <= self.last_generation.get(key, -1):
                raise ValueError('stale tag generation')
            if any(k[:3] == key[:3] and x['slot'] == identity['irs_slot']
                   for k,x in self.live.items()):
                raise ValueError('live source burst slot reuse')
            if e['write'] and sum(x['write'] for k,x in self.live.items() if k[:3] == key[:3]) >= 4:
                raise ValueError('four source write resident slots exhausted')
            payload = bytes.fromhex(e['payload_hex']) if e['write'] else None
            if e['write'] and len(payload) != 32*n:
                raise ValueError('allocation requires actual write payload')
            x = dict(identity=word, owner=owner, pc=e['producer_pc'], n=n,
                     write=e['write'], returned=set(), credited=set(), granted=set(),
                     backing={}, columns={}, readers=set(), payload=payload, slot=identity['irs_slot'])
            self.live[key] = x
            self.last_generation[key] = identity['transport']
        else:
            if key not in self.live:
                raise ValueError('receipt has no live allocation')
            x = self.live[key]
            if (word, owner, e['producer_pc']) != (x['identity'], x['owner'], x['pc']):
                raise ValueError('receipt identity mismatch')
            beat = e.get('beat')
            if op != 'retire' and (not isinstance(beat, int) or not 0 <= beat < x['n']
                                  or e['sector'] != identity['sector']+beat):
                raise ValueError('receipt sector/beat mismatch')
            if op == 'write_command':
                if not x['write'] or beat in x['columns']:
                    raise ValueError('duplicate or read write command')
                x['columns'][beat] = t
            elif op == 'backing':
                if (not x['write'] or beat in x['backing'] or beat not in x['columns']
                        or t-x['columns'][beat] < 8):
                    raise ValueError('duplicate, read or premature backing receipt')
                if bytes.fromhex(e['payload_hex']) != x['payload'][beat*32:(beat+1)*32]:
                    raise ValueError('backing payload differs from allocated write')
                x['backing'][beat] = t
            elif op == 'return':
                if beat in x['returned'] or (x['write'] and beat not in x['backing']):
                    raise ValueError('duplicate return or premature write visibility')
                if not x['write'] and len(bytes.fromhex(e['payload_hex'])) != 32:
                    raise ValueError('read return requires actual sector payload')
                x['returned'].add(beat)
            elif op == 'acquire':
                if not isinstance(e['reader'], int) or not 0 <= e['reader'] < 1024:
                    raise ValueError('assembly reader ID width')
                lease = (beat, e['reader'])
                if x['write'] or beat not in x['returned'] or beat in x['credited'] or lease in x['readers']:
                    raise ValueError('unavailable or duplicate reader')
                if sum(len(v['readers']) for k,v in self.live.items() if k[:3] == key[:3]) >= self.reader_limit:
                    raise ValueError('finite assembly reader credits exhausted')
                x['readers'].add(lease)
            elif op == 'drain':
                lease = (beat, e['reader'])
                if lease not in x['readers']:
                    raise ValueError('unowned reader drain')
                x['readers'].remove(lease)
            elif op == 'credit':
                if beat not in x['returned'] or beat in x['credited'] or any(b == beat for b,r in x['readers']):
                    raise ValueError('duplicate, premature or undrained reverse credit')
                x['credited'].add(beat)
            elif op == 'grant_consumed':
                if beat not in x['credited'] or beat in x['granted']:
                    raise ValueError('unbacked or duplicate consumed grant')
                x['granted'].add(beat)
            elif op == 'retire':
                if x['granted'] != set(range(x['n'])) or x['readers']:
                    raise ValueError('early physical tag retirement')
                del self.live[key]
            else:
                raise ValueError('unknown receipt')
        self.clock = t


class RefillJoin:
    """Finite actual residence calendar with payload-bearing demand fills.

    No layer-hop refill assumed. User epoch and layer remain in every line key.
    An explicit descriptor demand drives fills; hits cost no backing read.
    Open K tail is separately retained per owner across layer hops. Closed tails
    may not be evicted before backing visibility. Flush deadlines come from
    actual reuse/demand, never a guessed overlap. Service receipt timing is
    authoritative; this class does not derive HBM bandwidth from bridge cycles.
    """
    def __init__(self, capacity_sectors, owners=144):
        if capacity_sectors <= 0 or not 1 <= owners <= 144:
            raise ValueError('finite residence capacity')
        self.capacity, self.owners = capacity_sectors, owners
        self.resident, self.tails = {}, {}
        self.read_bytes = self.hits = 0

    def demand(self, owner, keys, provider):
        keys = set(keys)
        if any(not isinstance(k, tuple) or len(k) != 4 or
               k[:2] != (owner.rank>>1, owner.rank&1) or
               not 0 <= k[2] < 4 or not 0 <= k[3] < 703125000 for k in keys):
            raise ValueError('descriptor sector home aperture/owner')
        if len(keys) > self.capacity:
            raise ValueError('descriptor exceeds finite window; split required')
        wanted = {(owner, k) for k in keys}
        # One descriptor window, explicit eviction. Pending readers are outside
        # this API: caller must drain its receipt leases before each transition.
        missing = wanted - self.resident.keys()
        self.hits += len(wanted)-len(missing)
        payload = {k: provider(owner, k[1]) for k in missing}
        if any(not isinstance(v, bytes) or len(v) != 32 for v in payload.values()):
            raise ValueError('missing actual backing payload')
        self.resident = {k:v for k,v in self.resident.items() if k in wanted}
        self.resident.update(payload)
        self.read_bytes += 32*len(missing)
        return len(missing)

    def append_k(self, owner, position, raw):
        if not 0 <= position < 8192 or len(raw) != 256:
            raise ValueError('K tail row aperture')
        if owner not in self.tails:
            if len(self.tails) >= self.owners or position % 16:
                raise ValueError('tail requires sourced prefix or capacity')
            self.tails[owner] = (position//16, [])
        tile, rows = self.tails[owner]
        if position != tile*16+len(rows) or len(rows) == 16:
            raise ValueError('tail overwrite before visibility or nonsequential prefix')
        rows.append(bytes(raw))
        return len(rows) == 16

    def bind_open_k(self, owner, published_count, provider):
        """Recover only actual bytes in the current incomplete 16-row tile."""
        if owner in self.tails or not 0 <= published_count <= 8192 or len(self.tails) >= self.owners:
            raise ValueError('initial tail binding')
        provider.validate(owner, published_count)
        tile, count = divmod(published_count, 16)
        if count:
            rows = [bytes(provider.read_byte(owner, 'K', h, tile*16+p, d)
                          for h in range(2) for d in range(128)) for p in range(count)]
            self.tails[owner] = (tile, rows)

    def read_k(self, owner, head, position, dim, provider):
        if not (0 <= head < 2 and 0 <= position < 8192 and 0 <= dim < 128):
            raise ValueError('K read aperture')
        if owner in self.tails:
            tile, rows = self.tails[owner]
            if position//16 == tile and position%16 < len(rows):
                return rows[position%16][head*128+dim]
        return provider.read_byte(owner, 'K', head, position, dim)

    def closed_k(self, owner):
        tile, rows = self.tails[owner]
        if len(rows) != 16:
            raise ValueError('tail not closed')
        # 2 heads x 128 dims x 16 positions, literal dimension-major K words.
        return bytes(rows[p][h*128+d] for h in range(2) for d in range(128) for p in range(16))

    def retire_k(self, owner, visible_payload):
        if visible_payload != self.closed_k(owner):
            raise ValueError('closed tail lacks exact backing visibility')
        del self.tails[owner]


def producer_write_plan(join, residence):
    """Full-sector source-tail candidate, from actual accepted producer bytes.

    Returns demand only. A caller may not report visibility from this plan;
    Kepler's actual allocation/backing/retirement receipts remain mandatory.
    Uses previous source-pinned candidate Homes, not a claimed current ROM port.
    Closed K rows must be retained until exact provider visibility; no RMW.
    """
    state = join.state()
    owner, pos = join.owner, join.position
    closed = residence.append_k(owner, pos, state['K'])
    homes, sectors, pcs = Homes(), {}, {}
    pc_for_address = {a: pc for pc, addresses in join.expected.items() for a in addresses}
    kinds = ['V'] + (['K'] if closed else [])
    for kind in kinds:
        positions = range(pos//16*16, pos//16*16+16) if kind == 'K' else [pos]
        for h in range(2):
            for p in positions:
                for d in range(128):
                    key, offset = homes.byte(owner, kind, h, p, d)
                    pcs.setdefault(key, set()).add(pc_for_address[join.address(kind, h, d)])
                    raw, mask = sectors.setdefault(key, (bytearray(32), bytearray(32)))
                    if mask[offset]:
                        raise ValueError('aliased full-sector write')
                    raw[offset] = (residence.tails[owner][1][p%16][h*128+d]
                                   if kind == 'K' else state['V'][h*128+d])
                    mask[offset] = 1
    if any(sum(mask) != 32 for raw, mask in sectors.values()):
        raise ValueError('partial-sector source tail mapping')
    if any(len(values) != 1 for values in pcs.values()):
        raise ValueError('sector crosses accepted producer PC partition')
    return dict(owner=vars(owner), program_sha256=join.image_sha256,
                closing_accepted_pcs=sorted(join.accepted), position=pos,
                state='demand_only_requires_real_allocation_and_backing_receipts',
                requests=[dict(endpoint=k[0], die=k[1], stack=k[2], sector=k[3],
                               producer_pc=next(iter(pcs[k])), payload_hex=raw.hex())
                          for k,(raw,mask) in sorted(sectors.items())])


SOURCE_PATHS = [
    'tools/hdc_program.py', 'tools/hdc_isa.py', 'tools/hdc_qwen_fullshape_isa_w12.py',
    'tools/hdc_qwen_fullshape_program_w12.py', 'rtl/hdc/ot_hdc_vstream_lane.sv',
    'tools/qwen_rom_rt_core_emit_w12.py',
    'rtl/hdc/ot_qwen_rom_tile_w12.sv', 'rtl/hdc/ot_hdc_core_vector_weight.sv',
    'rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12.sv',
    'rtl/test/qwen_rom_runtime/qwen_rom_rt_w12.cpp',
    'rtl/hdc/kv/ot_hdc_qwen_kv_write_adapter.sv',
    'rtl/hdc/kv/ot_hdc_qwen_kv_vector_bridge.sv',
    'rtl/model_ready_hbm_r14/ot_hbm_r14_tag_owner.sv',
    'rtl/model_ready_hbm_r14/ot_hbm_causal_command_provider.sv',
    'physical/asap7_memory_macros/index.json',
    'rtl/hdc/kv/ot_hdc_qwen_kv_system.sv']


def tail_sizing():
    """Mandatory state-retention candidate with literal current macro abstract.

    Source two-parity x64-lane banking retained. New layer owner selects four
    rows/head-dimension partition per layer. Prototype LOG_TW2 is not 8K:
    LOG_TW9 drops all512 tile bits. No port or slot closure inferred from area.
    """
    macro = json.loads((ROOT/'physical/asap7_memory_macros/index.json').read_text())['macros'][
        'ot_sram_1r1w_512x128_m4_r2c2']
    banks, rows = 128, 36*2*2
    return dict(state='analytical_candidate_not_admitted', macro=macro['spec']['name'],
        source_SW=64, required_LOG_TW=9, source_prototype_LOG_TW_default=2,
        banks_per_rank=banks, owner_rows_per_bank=rows,
        row_equation='layer*4 + head*2 + dim//64; bank=(tile%2)*64 + dim%64',
        mutable_state_bytes_per_rank=banks*rows*16,
        macro_capacity_bytes_per_rank=banks*512*16,
        macro_area_mm2_per_rank=banks*macro['area_um2']/1e6,
        macro_area_mm2_TP4=4*banks*macro['area_um2']/1e6,
        ports_per_bank=dict(read_bytes_per_stream_cycle=16, write_bytes_per_stream_cycle=16),
        aggregate_write_bytes_per_cycle_max=64,
        flush_read_bytes_per_cycle_candidate=32,
        port_arbitration='Consumer reads and closed-tail flush share each 1R port; '
                         'source tail_collision must reject simultaneous bank use. '
                         'No overlap credited without accepted port calendar.',
        SS_macro_min_period_ps=macro['min_period_ps']['ss'],
        SS_macro_clk_to_q_ps=macro['clk_to_q_ps']['ss'],
        stream_period_ps=10000/12, setup_uncertainty_ps=60,
        capture_budget_ps_before_cell_setup_route_mux=10000/12-60-macro['clk_to_q_ps']['ss'],
        row_mask_bits_per_bank=16,
        excluded_from_macro_area='Owner directory, lane conversion, masks, SRAM protection, '
                                 'read/write muxes, serial/stream CDC, capture, CTS, routes.',
        area_slot_fit=None, channel_tracks=None, per_user_latency=None,
        admission='Full service/calendar model and measured SS/FF closure required before hardware.')


def contract():
    sources = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCE_PATHS}
    peers = {
      'Euclid': {
        'provide': 'Pinned stage program.hex SHA256, user16/rank2/layer6/epoch32/position13; '
                   'accepted su_go PC12 (not fetch), cycle and domain; every kv_we lane '
                   'address24/value32 with immutable issue ticket; descriptor accepted '
                   'K/V read coordinates and consumer acquire/drain receipts.',
        'consume': 'ProducerJoin exact 512B row and source PC partition; canonical '
                   'FP8 inverse rejects unrounded payload; resident ownership survives layer hops.',
        'blocker': 'Wrapper kv_ok=1 and kv_write_drained=1 cannot supply state/visibility.'},
      'Kepler': {
        'provide': 'ALLOC on actual av&&ar: endpoint1, stack2, physical_tag12, identity192, '
                   'LEN count1..32, write1, service_cycle; accepted WR command then backing '
                   'commit at least8 provider cycles later with exact written bytes; owned returns '
                   'beat5/sector34/payload256; reverse-credit accept and grant_consumed; '
                   'physical retirement after all beats/drains/grants. Preserve generation32.',
        'consume': 'Receipts rejects cross-owner/stale/duplicate/missing allocations, read '
                   'credits without returns, and physical tag reuse before consumed grant.',
        'blocker': 'Current owner frees physical tag at final PC return and provider accepts '
                   'read credits unconditionally; allocation receipt is not exported.'},
      'Ampere': {
        'provide': 'Selected production stage/descriptor demand trace plus actual backing '
                   'state callback and initial resident/open-tail state, timed receipts for '
                   'shared channels; area/slot and mux/CDC/assembly dimensions; policy selection pin.',
        'consume': 'Demand missing sectors only; no compulsory layer refill; open K tail '
                   '4KiB/owner, closed flush128 sectors per16 rows; V8 sectors perrow. '
                   '64B V beat split into two32B requests before one-sector adapter; '
                   'retained producer state and receipt credit bound priced separately.',
        'blocker': 'Cold serialized calendar r8 is reference only; no selected sustainable '
                   'schedule or production payload trace exists in this join.'}}
    return dict(schema='opentallas.qwen-kv-production-join.v1', status='G0_BLOCKED',
        source_sha256=sources, physical_build_ready=False, synthetic_final_qualification=False,
        peers=peers, production_policy_selected=False,
        physical_context=tail_sizing(),
        receipt_schema=dict(common=['event','service_cycle','endpoint','stack','physical_tag',
          'identity(hex192)','owner(user,rank,layer,epoch)','producer_pc'],
          allocate=['sectors(count1..32)','write','payload_hex(required_for_write)'],
          per_beat=['beat','sector(base+beat)'],
          events=['allocate','write_command','backing','return','acquire','drain','credit',
                  'grant_consumed','retire'],
          readers='acquire/drain require reader10; 1024 concurrent assembly readers per stack max',
          data='backing requires exact allocated32B beat; read return requires actual32B payload',
          clock='service_cycle is provider clk cycle; accepted WR to backing minimum8 source cycles'),
        demand_home='(package_endpoint1,provider_die1,stack2,sector34); full Owner retained in window key',
        boundary=dict(producer_bits_per_64lane_beat=64*(1+24+32),
          packed_payload_bytes_per_beat=64, v_sector_splits=2,
          raw_row_bytes=512, k_tail_bytes_per_owner=4096,
          k_tail_bytes_144_owners=589824, closed_k_sectors=128,
          v_sectors_per_row=8, k_full_tail_average_sectors_per_row=8,
          domains_hz=dict(stream=1200000000, serial=900000000, service_candidate=1000000000)),
        pricing='Production demand reads replace existing uarch KV/HBM read bytes and cycles '
                'once, never add them again. Writes/CDC/tail access/split/visibility/drain '
                'costs remain explicit. No overlap credit absent source-timed proof.',
        remaining='Production input traces, initial actual state, safe source receipt exporter, '
                  'finite read-reader bound, tail ports/area, full calendar and slot composition.')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--result', required=True)
    p.add_argument('--receipts')
    args = p.parse_args()
    result = contract()
    if args.receipts:
        path = Path(args.receipts)
        ledger = Receipts()
        result['receipt_replay'] = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        completed = 0
        try:
            for line in path.read_text().splitlines():
                if line.strip():
                    ledger.apply(json.loads(line))
                    completed += 1
        except (ValueError, KeyError, TypeError) as error:
            result['status'] = 'FAIL_RECEIPT_TRACE_G0_BLOCKED'
            result['receipt_replay']['failure'] = str(error)
        result['receipt_replay'].update(events_accepted=completed, live_tags=len(ledger.live))
    path = Path(args.result)
    with path.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    if result['status'].startswith('FAIL'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()

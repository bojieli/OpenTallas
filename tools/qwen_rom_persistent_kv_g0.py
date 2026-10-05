#!/usr/bin/env python3
"""Opt-in Qwen ROM persistent KV transport contract and finite callback adapter.

No RTL, new arithmetic, implicit zero state or fabricated backing completion.
Functional fixtures qualify only adapter invariants. Calendar is an analytical
reservation candidate, not measured r14 service or physical admission.
"""
import argparse
import copy
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = '5cb27e9464d756630ad9636116d94e0025324826'
SOURCES = [
 'tools/uarch_model.py', 'tools/arch_budget_qwen3.py', 'tools/hdc_program.py',
 'tools/hdc_qwen_fullshape_program_w12.py', 'tools/qwen_kv_bank_prototype.py',
 'tools/qwen_rom_rt_token_w12.py', 'rtl/test/qwen_rom_runtime/qwen_rom_rt_w12.cpp',
 'rtl/hdc/ot_qwen_rom_tile_w12.sv', 'rtl/hdc/kv/ot_hdc_qwen_kv_system.sv',
 'rtl/hdc/kv/ot_hdc_qwen_hbm_sector_bridge.sv',
 'rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv',
 'rtl/model_ready_hbm_r14/ot_hbm_causal_command_provider.sv',
 'rtl/model_ready_hbm_r14/ot_hbm_r14_tag_owner.sv',
 'rtl/model_ready_hbm_r14/ot_hbm_r14_pc.sv',
 'physical/asap7_memory_macros/index.json',
 'tools/qwen_hbm_controller_calendar_r2.py', 'tools/qwen_hbm_controller_events_r1.py',
 'tools/qwen_rom_kv_residence_gate.py', 'tools/qwen_rom_kv_transport_candidate.py',
 'tools/qwen_hbm_complete_executor.py',
 'rtl/model_ready_hbm_r14/ot_hbm_r14_clock_bridge.sv',
 'rtl/model_ready_hbm_r14/ot_hbm_r14_fifo2.sv',
 'rtl/model_ready_hbm_r14/ot_hbm_r14_route.sv',
 'tools/qwen_hbm_endpoint_preflight_r14.py',
 'tools/qwen_hbm_complete_program.py', 'tools/hdc_golden.py',
 'tools/qwen_o4_kv_slice_map_w12.py',
 'rtl/test/model_ready_hbm_r14/tb_hbm_finite_stage.sv',
]

@dataclass(frozen=True)
class Owner:
    user: int
    rank: int
    layer: int
    epoch: int
    def __post_init__(self):
        if not (0 <= self.user < 65536 and 0 <= self.rank < 4 and
                0 <= self.layer < 36 and 0 <= self.epoch < 2**32):
            raise ValueError('owner aperture')

class Homes:
    """Candidate explicit user aperture; source k_element/v_element equations.

    Rank-local logical bytes, striped in128B units across four die-local stacks.
    Two TP2 package endpoints bind rank=(package<<1)|provider_die. Never truncate
    TP4 rank to r14's one-bit die. No checkpoint KV state is manufactured here.
    """
    def __init__(self, context=8192):
        if context != 8192:
            raise ValueError('only source-selected 8K geometry')
        self.context = context
        self.kind_bytes = 36*2*context*128
        self.user_bytes = 2*self.kind_bytes
    def byte(self, owner, kind, head, position, dim):
        from qwen_kv_bank_prototype import k_element, v_element
        if kind not in ('K', 'V') or not (0 <= head < 2 and
                0 <= position < self.context and 0 <= dim < 128):
            raise ValueError('coordinate aperture')
        f = k_element if kind == 'K' else v_element
        args = dict(kv_heads=2)
        args.update(position_tiles=512) if kind == 'K' else args.update(
            max_positions=self.context, v0_element=self.kind_bytes)
        a = owner.user*self.user_bytes + f(owner.layer, head, position, dim, **args)
        line, low = divmod(a, 128)
        stack, local_line = line % 4, line // 4
        sector, offset = divmod(local_line*128+low, 32)
        if sector >= 703125000:
            raise ValueError('provider capacity')
        return (owner.rank >> 1, owner.rank & 1, stack, sector), offset
    def tile(self, kind, head, position, dim):
        # Restates the source tile address map, including group/quarter ownership.
        if kind == 'K':
            t = position//16
            group = (t % 48)*128+dim
            row = (t//48)*2+head
            lane = position%16
        elif kind == 'V':
            group = (dim//16)*512+position%512
            row = 22+(position//512)*2+head
            lane = dim%16
        else:
            raise ValueError('kind')
        return group//4, row, (group%4)*16+lane

class Delivery:
    """16 finite burst leases per stack; payload read from caller-owned provider.

    The same sector cannot have two writer leases. ACK must identify the entire
    immutable owner/tag/generation. Reuse requires ACK, reverse credit and reader
    drain. Publication and tile visibility are distinct events.
    """
    def __init__(self, read_sector, credits=16, read_byte=None):
        if credits < 1 or credits > 16:
            raise ValueError('credit aperture')
        self.read_sector = read_sector
        self.read_byte = read_byte
        self.credits = credits
        self.homes = Homes()
        self.live = {}
        self.locks = set()
        self.prefix = {}
        self.readers = {}
        self.windows = {}
        self.serial = 0
    def reserve(self, owner, position, k_bytes, v_bytes):
        if len(k_bytes) != 256 or len(v_bytes) != 256:
            raise ValueError('actual FP8 producer rows required')
        if self.prefix.get(owner, 0) != position or owner in self.readers:
            raise ValueError('publication order or live reader')
        if any(x['owner'].rank == owner.rank for x in self.live.values()):
            raise ValueError('writer already live')
        sectors = {}
        for kind, payload in [('K', k_bytes), ('V', v_bytes)]:
            for h in range(2):
                for d in range(128):
                    key, offset = self.homes.byte(owner, kind, h, position, d)
                    sectors.setdefault(key, {})[offset] = payload[h*128+d]
        # Writer uses one credit per sector; admission is all-or-none. The
        # hardware scheduler must split into finite waves (at most16/stack).
        if any(key in self.locks for key in sectors):
            raise ValueError('sector locked')
        if len(sectors) != 136:
            raise ValueError('source writer descriptor count')
        if self.serial >= 2**32: raise ValueError('transport generation exhausted; drain required')
        token = self.serial; self.serial += 1
        self.live[token] = dict(owner=owner, position=position, sectors=sectors,
                                active={}, ack=set(), retired=set())
        return token
    def issue(self, token):
        w = self.live[token]; result = []
        used = {}
        for x in self.live.values():
            for key in x['active']:
                used[key[:3]] = used.get(key[:3], 0)+1
        for key, patches in w['sectors'].items():
            if key in w['active'] or key in w['ack']:
                continue
            channel = key[:3]
            if used.get(channel, 0) >= self.credits or key in self.locks:
                continue
            # Read existing payload from real state provider for partial RMW;
            # no absent-sector fallback. Full writes need no old-sector read.
            old = bytes(32) if len(patches) == 32 else self.read_sector(key)
            if len(old) != 32:
                raise ValueError('sector width')
            data = bytearray(old)
            for offset, value in patches.items(): data[offset] = value
            w['active'][key] = bytes(data); self.locks.add(key)
            used[channel] = used.get(channel, 0)+1
            result.append((token, w['owner'], key, bytes(data)))
        return result
    def acknowledge(self, token, owner, key, backing_data):
        w = self.live[token]
        if owner != w['owner'] or key not in w['active'] or key in w['ack']:
            raise ValueError('stale or duplicate backing ACK')
        if backing_data != w['active'][key]:
            raise ValueError('backing payload mismatch')
        w['ack'].add(key)
    def reverse_credit(self, token, owner, key):
        w = self.live[token]
        if owner != w['owner'] or key not in w['ack'] or key in w['retired']:
            raise ValueError('unbacked or duplicate credit')
        w['active'].pop(key); self.locks.remove(key); w['retired'].add(key)
    def publish(self, token):
        w = self.live[token]
        if len(w['retired']) != len(w['sectors']):
            raise ValueError('writer not drained')
        self._prefix(w['owner'], w['position']+1)
        del self.live[token]
    def _prefix(self, owner, count):
        for old in list(self.prefix):
            if (old.rank,old.layer) == (owner.rank,owner.layer) and old != owner:
                if old in self.readers: raise ValueError('old owner still leased')
                del self.prefix[old]
        self.prefix[owner] = count
        assert len(self.prefix) <= 144

    def bind_published(self, provider, owner, count):
        provider.validate(owner, count)
        if self.live or owner.rank in self.windows:
            raise ValueError('bind requires drained adapter')
        self._prefix(owner, count)

    def acquire(self, owner, count):
        if not 0 < count <= self.prefix.get(owner, 0) or any(
                old.rank == owner.rank for old in self.readers):
            raise ValueError('unpublished prefix or reader already live')
        self.readers[owner] = count
    def fill(self, owner):
        if owner not in self.readers:
            raise ValueError('no reader lease')
        rank = owner.rank
        if rank in self.windows:
            raise ValueError('previous layer window not drained')
        words = {}; cache = {}
        for kind in ('K', 'V'):
            for h in range(2):
                for p in range(self.readers[owner]):
                    for d in range(128):
                        key, offset = self.homes.byte(owner, kind, h, p, d)
                        if self.read_byte is None:
                            if key not in cache: cache[key] = self.read_sector(key)
                            if len(cache[key]) != 32: raise ValueError('sector width')
                            value = cache[key][offset]
                        else:
                            value = self.read_byte(owner, kind, h, p, d)
                            if not 0 <= value < 256: raise ValueError('raw byte width')
                        tile, row, lane = self.homes.tile(kind, h, p, d)
                        data, mask = words.setdefault((tile, row), (bytearray(64), bytearray(64)))
                        data[lane] = value; mask[lane] = 255
        # Fill register edge then macro write edge, then visibility fence. The
        # caller supplies those actual edges before read admission.
        self.windows[rank] = (owner, False)
        return words
    def visible(self, owner):
        if self.windows.get(owner.rank) != (owner, False):
            raise ValueError('stale fill fence')
        self.windows[owner.rank] = (owner, True)
    def drain(self, owner):
        if self.windows.get(owner.rank) != (owner, True):
            raise ValueError('window not visible')
        del self.windows[owner.rank]; del self.readers[owner]


class PublishedProvider:
    """Read existing executor.PersistentMemory raw bytes without re-encoding.

    Its TP/extent identity is checked. Existing TP2 backing is projected to
    TP4 homes by global head identity (source die=rank//2,head=2*(rank%2)+head).
    This is storage translation only; TP2 numerical evidence is not transferred. Software fence is software publication,
    never promoted to r14 backing completion. Caller explicitly binds one user
    and epoch; no state from another epoch is borrowed.
    """
    def __init__(self, memory, user, epoch):
        c = memory.program['config']
        if (memory.program['TP'] not in (2,4) or c['head_dim'] != 128 or
            c['num_key_value_heads'] != 8 or memory.program['context_capacity'] != 8192):
            raise ValueError('provider geometry differs from ROM TP4')
        self.memory, self.user, self.epoch = memory, user, epoch
        self.provider_tp = memory.program['TP']
    def validate(self, owner, count):
        if owner.user != self.user or owner.epoch != self.epoch or not 0 < count <= 8192:
            raise ValueError('provider owner')
        rank = owner.rank if self.provider_tp == 4 else owner.rank//2
        for p in range(count):
            if (owner.layer, rank, p) not in self.memory.published:
                raise ValueError('actual provider prefix absent')
    def read_byte(self, owner, kind, head, position, dim):
        self.validate(owner, position+1)
        # Actual provider dictionary lookup deliberately refuses missing state.
        rank = owner.rank if self.provider_tp == 4 else owner.rank//2
        head = head if self.provider_tp == 4 else (owner.rank%2)*2+head
        return self.memory.bytes[self.memory._address(rank, owner.layer,
                                                     kind, head, position, dim)]


def compose(compute_cycles, delivery_cycles, existing_kv_cycles, overlap_cycles=0):
    """Replace old KV bound; only proven overlap may hide finite service."""
    if min(compute_cycles, delivery_cycles, existing_kv_cycles, overlap_cycles) < 0:
        raise ValueError('negative cycles')
    if overlap_cycles > min(compute_cycles, delivery_cycles):
        raise ValueError('invalid overlap')
    total = compute_cycles+delivery_cycles-overlap_cycles
    return dict(compute_cycles=compute_cycles, finite_delivery_cycles=delivery_cycles,
                existing_kv_bound_cycles=existing_kv_cycles, existing_kv_bound_replaced=True,
                incremental_read_bytes=0, proven_overlap_cycles=overlap_cycles,
                token_cycles=total, delta_from_old_max=total-max(compute_cycles, existing_kv_cycles))


def idle_refresh(bank, now, bus):
    """Source PC IDLE refresh obligations, including channels with empty queues.

    Reserve actual PREALL/REF commands on one stack bus, preserve bank recovery
    and refresh blocking. This is a conservative analytical candidate scheduler.
    It avoids treating idle time as unserviced refresh debt.
    """
    from qwen_hbm_controller_calendar_r2 import edge
    def command(time):
        time=edge(time,bank.period)
        while time in bus: time+=bank.period
        bus.add(time)
        return time
    for p in sorted(range(32),key=lambda p:bank.next_ref[p]):
        while bank.next_ref[p] <= now:
            due=bank.next_ref[p]
            opened=[b for b in bank.b[p] if b.open]
            at=max(due,bank.last_col[p]+bank.t['BURST_PS'])
            if bank.last_ref[p] is not None: at=max(at,bank.last_ref[p]+bank.t['RFC_PS'])
            if opened:
                pre=command(max([at]+[b.preok for b in opened]))
                bank.log('PREall',pre,p)
                at=pre+bank.t['RP_PS']
            refresh=command(at)
            bank.log('REF',refresh,p)
            bank.last_ref[p]=refresh
            for b in bank.b[p]:
                b.open=False;b.actok=max(b.actok,refresh+bank.t['RFC_PS'])
            bank.next_ref[p]+=bank.t['REFI_PS']
    # Only reservations near the next issue can collide; old bus timestamps
    # need no stored lifetime. No unbounded hardware calendar is implied.
    bus.intersection_update(t for t in bus if t>=now-bank.period)


def calendar(sectors, start=0):
    """Finite conservative one-sector-at-a-time reservation per stack.

    Reuses source-pinned bank/refresh/turnaround calendar, then prices r14
    scanning/lookup and explicit candidate CDC/fill guards. Sequential service
    deliberately leaves capacity unused. Candidate guards are NOT RTL bounds.
    """
    from qwen_hbm_controller_calendar_r2 import BankCalendar, crossed, edge, bankmap
    from qwen_hbm_controller_events_r1 import Beat, source_timing
    timing = source_timing()
    # r14_pc source ceil-cycle constraints, all priced at its1GHz candidate.
    timing.update(REQ_PS=10000, RP_PS=17000, RRDS_PS=3000, RRDL_PS=4000,
                  FAW_PS=15000, RAS_PS=29000, RCDRD_PS=20000, RCDWR_PS=10000,
                  BURST_PS=2000, TCCDL_PS=3000, CWL_PS=7000, WTRL_PS=7000,
                  WTRS_PS=5000, RTW_PS=10000, WR_PS=21000, RTP_PS=6000,
                  REFI_PS=3900000, RFC_PS=350000, RL_PS=25000)
    bank = BankCalendar(timing, 1000)
    now = Fraction(start); max_tag = 0; bus=set()
    reads = writes = 0; previous=None
    for serial, item in enumerate(sectors):
        sector, write = item if isinstance(item, tuple) else (item, False)
        if write and previous == (sector,False): now += 27*Fraction(10000,9)
        previous=(sector,write)
        if write: writes += 1
        else: reads += 1
        # Source preflight maximum35CORE edges for16entry freeze/scan;
        # serialization uses one sector, so there is no head swapping.
        accepted = crossed(now+42*Fraction(2500,3), 1000)
        req = Beat(sector, serial%4096, 0, 0, write=write, accepted_ps=accepted)
        scheduled=accepted+35000
        pc=bankmap(sector)['pc']
        while True:
            idle_refresh(bank,scheduled,bus)
            if scheduled+50000 >= bank.next_ref[pc]:
                scheduled=max(scheduled,bank.next_ref[pc]+1000)
                idle_refresh(bank,scheduled,bus)
            # Tentative reservation copies only the touched PC. No accepted
            # command or source event is moved after issue.
            trial=copy.copy(bank); trial.events=[]
            trial.b=list(bank.b);trial.b[pc]=[copy.copy(b) for b in bank.b[pc]]
            for name in ('last_act','last_col','last_rd','last_wr','last_wr_bg','last_ref','next_ref'):
                setattr(trial,name,list(getattr(bank,name)))
            for name in ('last_act_bg','faw','last_col_bg'):
                values=list(getattr(bank,name));values[pc]=list(values[pc]);setattr(trial,name,values)
            column=trial.plan(req,scheduled)
            collision=next((e['ps'] for e in trial.events if e['ps'] in bus),None)
            if collision is None: break
            scheduled=max(scheduled+1000,collision+1000)
        new_events=trial.events;events=bank.events;events.extend(new_events);trial.events=events;bank=trial
        for event in new_events: bus.add(event['ps'])
        due = column+(8000 if write else timing['RL_PS'])
        # Seven arb + acceptance +12 lookup +held acceptance + credit edge.
        now = crossed(due+22000+42*Fraction(2500,3), Fraction(2500,3))
        now += 2*Fraction(2500,3) # registered fill + macro visibility
        now = crossed(now+42*Fraction(2500,3), 1000) # reverse credit
        now = crossed(now+1000+42*Fraction(2500,3), Fraction(2500,3)) # held grant
        max_tag = max(max_tag, 1)
    from qwen_hbm_controller_calendar_r2 import audit_bank_events
    audit = audit_bank_events(bank.events,timing)
    return dict(read_sectors=reads,write_sectors=writes,command_audit=audit,end_ps=str(now), cycles_1p2GHz=-(-now//Fraction(2500,3)),
                max_live_sectors=max_tag, banks=32, pseudo_channels=32,
                dram_events=len(bank.events), timing_source_sha256=hashlib.sha256(
                    subprocess.check_output(['git','show',
                      '4535be1001d69bc43669e0fdf0401896be4034a6:rtl/hdc/kv/ot_hdc_hbm_model.sv'],cwd=ROOT)).hexdigest())


def burst_assembly():
    """Worst per-burst destination count, derived from actual byte/tile map.

    Reserve every unique destination before accepting burst to avoid a held
    provider response waiting on unallocated assembly state. Each destination
    can flush masked quarters; it need not wait for unrelated future bursts.
    """
    homes=Homes(); result={}
    for kind,base in [('K',0),('V',homes.kind_bytes)]:
        peak=0
        for stack in range(4):
            # One layer's full local32sector bursts; macroaddress period repeats.
            first=base//128
            for sector0 in range(first,first+16384,32):
                slots=set()
                for sector in range(sector0,sector0+32):
                    for offset in range(32):
                        local=sector*32+offset
                        line,low=divmod(local,128)
                        byte=(line*4+stack)*128+low-base
                        if kind=='K':
                            word,lane=divmod(byte,16)
                            ht,dim=divmod(word,128); head,tile=divmod(ht,512)
                            position=tile*16+lane
                        else:
                            hp,dim=divmod(byte,128);head,position=divmod(hp,8192)
                        dest=homes.tile(kind,head,position,dim)
                        slots.add(dest[:2])
                peak=max(peak,len(slots))
        result[kind]=peak
    assert result=={'K':16,'V':64},result
    return dict(per_burst_destinations=result,burst_bytes=1024,
                burst_credits_per_stack=16,required_slots_per_stack=16*max(result.values()),
                prior16_slot_proposal_sufficient=False,
                slot_retirement='registered masked SRAM fill accepted and write visibility precede credit return')

def report(full_calendar=False, progress_dir=None):
    from qwen_rom_kv_residence_gate import generate
    reconciliation = generate(); pins = {}
    for p in SOURCES:
        raw = (ROOT/p).read_bytes()
        original = subprocess.check_output(['git', 'show', BASE+':'+p], cwd=ROOT)
        if raw != original: raise ValueError('pinned original changed: '+p)
        pins[p] = hashlib.sha256(raw).hexdigest()
    macros = json.loads((ROOT/'physical/asap7_memory_macros/index.json').read_text())['macros']
    service_macro_area = (64*macros['ot_sram_1r1w_64x512_m1_r2c2']['area_um2']+
                          32*macros['ot_sram_1r1w_128x256_m1_r2c2']['area_um2'])/1e6
    read = int(reconciliation['byte_ledger']['existing_fp8_kv_read_bytes_per_TP4_die'])
    assert read == 36*4194304
    # 128B striping gives equal131072-sector layer /4 stack extents.
    rows = []; writer_rows = []
    model_point = None
    if full_calendar:
        import uarch_model as U
        model_point = U.qwen_tp_point(4,6144,'ucie_measured',clock_hz=1.2e9,ctx=8192,su_width=64)
        homes = Homes()
        for layer in range(36):
            owner = Owner(0,0,layer,0)
            # Explicit conservative layer-hop K drain, source raw byte layout.
            masks = {}
            for kind in ('K','V'):
                for head in range(2):
                    for dim in range(128):
                        key, offset = homes.byte(owner,kind,head,8191,dim)
                        masks[key] = masks.get(key,0) | (1<<offset)
            stacks = []
            for stack in range(4):
                transactions = []
                for key, mask in sorted(masks.items()):
                    if key[2] == stack:
                        if mask != 0xffffffff: transactions.append((key[3],False))
                        transactions.append((key[3],True))
                stacks.append(calendar(transactions))
            writer_rows.append(dict(layer=layer,stacks=stacks,
                cycles_1p2GHz=max(int(x['cycles_1p2GHz']) for x in stacks)))
            # Symmetric128B striping, identical read demands on four stacks.
            sectors = list(range(layer*16384, (layer+1)*16384))
            sectors += list(range(36*16384+layer*16384,36*16384+(layer+1)*16384))
            rows.append(dict(layer=layer, **calendar(sectors)))
            if progress_dir is not None:
                with (progress_dir/f'layer_{layer:02d}.json').open('x') as f:
                    json.dump(dict(read=rows[-1],writer=writer_rows[-1]),f,indent=2); f.write('\n')
                print(f'layer{layer}: read_cycles={rows[-1]["cycles_1p2GHz"]} write_cycles={writer_rows[-1]["cycles_1p2GHz"]}',flush=True)
    delivery = (sum(int(r['cycles_1p2GHz']) for r in rows)+
                sum(int(r['cycles_1p2GHz']) for r in writer_rows)) if rows else None
    composition = compose(model_point['cycles'],delivery,
        read/(4*900000000000)*1.2e9) if model_point else None
    return dict(schema='opentallas.qwen-rom-persistent-kv-g0.v1',
      status='CANDIDATE_FUNCTIONAL_CONTRACT_G0_BLOCKED',adoption=False,physical_build_ready=False,
      base=BASE,source_sha256=pins,
      successor_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
        ['tools/qwen_rom_persistent_kv_g0.py','tests/test_qwen_rom_persistent_kv_g0.py',
         'tests/test_qwen_rom_persistent_kv_source_join.py']},
      homes=dict(existing_policy='die-local HBM own KV heads, next-layer prefetch and current-row tail',
        runtime='host stage KV, KV_LOCAL0; no persistent provider joined',
        candidate='all36 layer extents per rank and user; K dimension/position-tile major, V position major; raw E4M3 bytes',
        package_rank_binding='rank=(package_endpoint<<1)|r14_die; two endpoint pairs, four ranks',
        bytes_per_user_rank=read, bytes_per_layer_rank=4194304, heads_per_rank=2,
        local_residence='one active layer per tile array; next-layer fetch cannot overwrite it before reader drain; no unproved overlap',
        layer_hop='release SCORES/PV readers, wait backing ACK/reverse credits, drain fill leases, switch owner, fill, macro visibility fence'),
      source_ports=dict(sector_bridge=dict(bytes=32,len=1,outstanding=1,write_completion='request acceptance only'),
        r14=dict(stacks_per_rank=4,pseudo_channels_per_stack=32,request_entries_per_PC=64,
          return_entries_per_PC=32,tags_per_stack=4096,write_residence_per_stack=4,
          reverse_wire_bits=404,return_wire_bits=467,command_bits_per_stack=339,commands_per_edge=1,owner_lookup_edges=12,
          return_arbitration_edges=7,owned_bits=465,request_bits=455),
        tile=dict(fill_data_bytes_per_edge=64,mask_bits=512,address_bits=7,
          addressed_fill_bits=1048,replicas=1536,macro_write_bytes_per_edge=32,
          macros_per_tile=2,read_bytes_per_tile_edge=64,fill_capture_then_macro_write_edges=2)),
      candidate_resources=dict(assembly_binding=burst_assembly(),burst_sectors=32,outstanding_bursts_per_stack=16,
        reserved_response_bytes_per_stack=16384,assembly_entries_per_stack=1024,
        assembly_payload_bits_per_slot=787,burst_record_bits_per_slot=236,
        payload_storage_bits_per_rank=4*(16384*8+1024*787+16*236),
        directory_bits_per_rank=36*(16+32+14+2+1),
        fill_lanes_per_rank=1,fill_capacity_bytes_per_stream_edge=64,
        stack_boundary_bytes_per_service_edge=32,service_target_Hz=1000000000,
        stream_target_Hz=1200000000,serial_target_Hz=900000000,
        CDC='source r14 two depth2 FIFOs plus one held38FAST-edge route; preflight42FAST+3destination edges, per direction; request/return/reverse credit/held grant',
        byte_mask_to_bit_mask='each valid raw code expands to8 mask bits; no BF16 streamer conversion',
        area='payload/register lower bound only; allocator/CAM/mux/retirement/quarantine/CDC/control area still required',
        assembly_area_lower_bound_mm2=4*1024*787*.2916/1e6,
        actual_bridge_payload_bits_per_rank=4*(5*(455+467+404)+3*(2*26+7)),
        writer_pending_descriptor_bits_per_rank=136*(34+2+32+256+3),
        quarantine_bits_per_stack=16*(192+32+32+12+3),
        allocation_receipt_additional_bits=12,
        allocation_receipt_required=True,
        RMW_merge_serial_edges=27,
        source_address_map_rows_per_tile=54, historical_dimension_rows=44,
        macros_still_fit=True,
        writer_mode='Conservative candidate drains K tail to backing via partial-sector RMW on layer hop; V full sectors; zero overlap credited. This drain is newly priced, not production-measured.',
        fill_demux_outputs=1536,fill_demux_data_mask_bits=1024,
        destination_selector_bits=11,required_parallel_signal_tracks_at_fill_boundary=1048,
        channel_capacity=None,slot_fit=None,macs_per_cycle=0,
        actual_service_macro_count_per_stack=96,
        actual_service_macro_area_mm2_per_stack=service_macro_area,
        actual_service_macro_area_mm2_per_rank=4*service_macro_area,
        inherited_service_slot_mm2_per_stack=16.6015872,
        inherited_slot_is_not_current_fit=True,
        boundary_tracks=dict(request_per_stack=455,return_per_stack=467,reverse_per_stack=404,
                             command_per_stack=339,fill_lane=1048),
        macro_port_bytes_per_edge=dict(request_ram_read=64,request_ram_write=64,
            return_ram_read=64,return_ram_write=64,context_ram_read=32,context_ram_write=32),
        finite_control='136 pending writer descriptors per rank, one writer and reader per rank,144 total layer-directory entries, transport generations32bit with drain-before-wrap',
        compute_intensity_MAC_per_byte=0,communication_intensity='one raw byte per existing KV byte, masks additional'),
      ledger=dict(reconciliation=reconciliation['byte_ledger'],
        replacement='arch_budget_qwen3.rom_token max(compute,KV bound) replaced with compute+finite service-proven overlap; uarch_model.qwen_tp_point compute cycles lack exposed KV waits',
        old_aggregate_bandwidth_not_inherited=True,read_bytes_charged_once=read,
        write_bytes_per_token_rank=18432,
        write_transport='K partial sectors require RMW unless closed-tail producer supplies full sector; V full sectors. No omitted RMW traffic or implicit backing visibility.',
        model_entrypoint='tools.qwen_rom_persistent_kv_g0.compose; no default model or rate modified'),
      analytical_calendar=dict(mode='cold full8K layer reservations, one live sector/stack; four stacks parallel, layers sequential; not production-prefetch proof',
        guard_scope='source DRAM timing with explicit source preflight35CORE scan maximum and candidate22 return/owner edges plus source42FAST+3destination CDC in four directions; no claimed RTL upper bound',
        layers=rows,writer_layers=writer_rows,per_token_delivery_cycles=delivery,
        write_delivery_cycles=sum(int(r['cycles_1p2GHz']) for r in writer_rows) if writer_rows else None,
        cold_layer_bank_state=True,background_idle_refresh=True,shared_stack_command_bus=True,
        compute_cycles=model_point['cycles'] if model_point else None,
        composition=composition,
        analytical_token_latency_seconds=composition['token_cycles']/1.2e9 if composition else None,
        per_user_token_latency=None,
        model_scope='qwen_tp_point TP4/G6144/SU64 ucie_measured at assumed1.2GHz; arithmetic/wire/runtime identity not admitted; conservative analytical comparison only'),
      actual_payload_provider='Delivery.read_sector callback must read actual producer-owned persistent state; missing bytes raise. No synthetic final qualification.',
      handoff=dict(Euclid='consume Homes.tile and masked fill tuples only after owner ACK/reader lease/visibility contract; keep tilecontrol/resettiming untouched',
        Maxwell='compose finite service once, bind actual dispatch/release trace and all write/RMW costs; qualify scheduling guard then overlap',
        Kepler='TP4 wrapper and retained tag quarantine/reverse credit identity required; r14 read credits currently accept unvalidated identity'),
      blockers=['existing TP2 raw-state provider now translated by global head identity; actual ROM TP4 producer/stage owner state still unconnected',
        'r14 tag freed on owned acceptance before reverse credit and lacks caller-visible allocation receipt; provider successor must retain identity/quarantine and expose allocation tag',
        'r14 read reverse credit validation missing; no inherited runtime PASS',
        'calendar conservative scan/return reservations not measured service; full-program releases and runtime arithmetic identity unresolved',
        'complete service area, finite port arbitration, hub routing-layer capacity and current slot placement unresolved',
        'contextual SS60ps/FF25ps at source-matched1GHz service and1.2GHz fill unresolved'],
      heavy_jobs_launched=0,RTL_PnR_launched=0)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--result',type=Path,required=True)
    ap.add_argument('--full-calendar',action='store_true')
    ap.add_argument('--progress-dir',type=Path)
    args = ap.parse_args()
    if args.result.exists(): ap.error('immutable result already exists')
    if args.progress_dir is not None:
        if not args.full_calendar: ap.error('progress requires full calendar')
        args.progress_dir.mkdir(parents=True,exist_ok=False)
    result = report(args.full_calendar,args.progress_dir)
    args.result.parent.mkdir(parents=True,exist_ok=True)
    with args.result.open('x') as f: json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print(result['status'])
if __name__ == '__main__': main()

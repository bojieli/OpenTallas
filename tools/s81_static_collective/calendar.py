"""Static component calendar; native FIELD/VM release requires physical latency binding."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Slot:
    seq: int
    issue: int
    commit: int
    rows: tuple[int, int, int, int]
    last: bool

def shape(layer: int) -> int:
    if layer in (2, 8, 14): return 44
    if layer == 20: return 36
    return 28

def landing(layer: int, record: int, rank: int, kind: str = 'a') -> int:
    if not 0 <= rank < 4: raise ValueError('rank')
    if kind == 'router':
        if not 0 <= record < 6: raise ValueError('router requires six records/rank')
        return 5169 + 6 * rank + record
    if kind != 'a': raise ValueError('HC subword packer is a separate consumer')
    if not 0 <= record < shape(layer): raise ValueError('a record')
    if record < 20: return 4096 + 20 * rank + record
    if record < 28: return 4224 + 8 * rank + record - 20
    if record < 36: return 4816 + 8 * rank + record - 28
    return 4848 + 8 * rank + record - 36

def calendar(layer: int, start: int, *, kind: str = 'a', spacing: int = 4,
             phy_cycles: int = 0) -> tuple[Slot, ...]:
    # Two PHY beats + endpoint/receive registers; no dynamic resource response.
    if start < 0 or spacing < 2 or phy_cycles < 0: raise ValueError('invalid calendar')
    count = 6 if kind == 'router' else shape(layer)
    return tuple(Slot(j, start+j*spacing, start+j*spacing+4+phy_cycles,
                      tuple(landing(layer,j,r,kind) for r in range(4)), j==count-1)
                 for j in range(count))

def model() -> dict:
    return dict(scope='component-only; no die closure or native source claim',
      ranks=4, fp32_per_record=16, a_records_per_rank=[28,36,44],
      a_gather_fp32=[1792,2304,2816], router_records_per_rank=6,
      payload_bits=512, engine_record_bits=547, static_frame_bits=569,
      crc_bits=32, phy_beat_bits=512, phy_beats_per_frame=2,
      default_source_spacing_cycles=4, endpoint_and_digital_latency_cycles=4,
      payload_bits_per_cycle_per_link=128, required_phy_bits_per_cycle_per_link=256,
      buffers='one 89-bit TX tail and one512-bit RX head per directed digital link',
      mutable_buffer_bits_per_link=601,
      endpoint_output_register_bits=2048+60+4,
      vm_source_ports=[44,45,46,47], vm_producer_register_cycles=1,
      vm_sram_observation_from_source_pin_cycles=10,
      issue_to_vm_source_pin_cycles=5, issue_to_vm_observation_cycles=15,
      peer_links_per_die=3, local_loop='component bench only',
      existing_diagnostic_link_rates_bits_per_cycle=dict(package=3864,board=157.58),
      bandwidth_adoption_gate='New2beat512 framing atspacing4 requires256PHYbits/cycle, abovehistorical157.58 boardbudget; actualPHYwidth/calendar must be reconciled, no native speed credit',
      physical_status='UNQUALIFIED: static successor requires accepted DSCOLL slot/pins, actual lane/PHY width and measured pipeline',
      physical_constraints='Preserve closed masters; no reroute until real RTL change + die-owned window',
      latency_composition='commit=source_issue+4+uniform declared PHY flight; unequal flight requires real RTL alignment stages',
      native_joins_remaining=['actual FIELD source_valid/data and tag/sequence',
         'compiler exact per-job start/release and conflict-free VM reservation',
         'actual E10 VM producer port and write commit',
         'actual HC 6-value/rank packer',
         'physical DSCOLL endpoint/lane mapping, reset and clock phi-R checks'])

def vm_events(slots: tuple[Slot, ...], *, identity: int,
              reservations: dict[tuple[int, int], tuple[int, int]],
              drain_delays: dict[tuple[int, int], int]) -> list[dict]:
    """Require compiler-selected staging locations; never invent storage slots.

    Emit SOURCE PIN edges. Uniform native VM observes each write ten edges later.
    Rows/data are opaque transport. Native FIELD tags and fixed producer release
    edges must be checked by the integrating compiler before using these events.
    """
    if not 0 <= identity < 256: raise ValueError('VM identity must fit tag8')
    required={(s.seq,r) for s in slots for r in range(4)}
    if set(reservations) != required: raise ValueError('missing/extra VM staging reservations')
    if set(drain_delays) != required: raise ValueError('missing/extra VM bank drain calendar')
    result=[]
    for s in slots:
        for r,row in enumerate(s.rows):
            lane,storage=reservations[s.seq,r]
            drain=drain_delays[s.seq,r]
            if drain not in (0,1,2): raise ValueError('VM bank drain delay')
            if not 0 <= row < 16384: raise ValueError('VM row')
            if not 0 <= lane < 3 or not 0 <= storage < 3:
                raise ValueError('uniform native VM supports three capture lanes/storage slots')
            result.append(dict(source=44+r, edge=s.commit+1, row=row, mask=65535,
                               tag=identity, capture_lane=lane, storage_slot=storage,
                               sram_visibility_edge=s.commit+9+drain,
                               observation_edge=s.commit+11+drain, sequence=s.seq, rank=r,
                               bank_drain_delay=drain))
    return result

def fmt1_calendar(layer: int, start: int, *, kind: str = 'a') -> tuple[Slot, ...]:
    """Existing FMT1 protocol:3-in4 gearbox, board beat every4stream cycles.

    128physical bits/cycle < historical157.58boardbudget. Fixed source cadence
    4,4,8; measured component latency11. Realflight/epoch remain unqualified.
    """
    if start < 0: raise ValueError('start')
    count=6 if kind=='router' else shape(layer)
    return tuple(Slot(j,start+16*(j//3)+4*(j%3),start+16*(j//3)+4*(j%3)+11,
                      tuple(landing(layer,j,r,kind) for r in range(4)),j==count-1)
                 for j in range(count))

def fmt1_cycle_controls(slots: tuple[Slot, ...]) -> tuple[int, ...]:
    """Compile every beat/phase/frame reservation, including empty PHY slots.

    Bits[7:0]={txbeat,txphase2,txframe,rxbeat,rxphase2,rxframe}.
    Clock epoch,4cycle beat period and zero external flight match componentRTL.
    """
    if not slots or slots[0].issue % 16: raise ValueError('FMT1 phase epoch')
    start=slots[0].issue;count=len(slots)
    if [s.issue-start for s in slots] != [16*(j//3)+4*(j%3) for j in range(count)]:
        raise ValueError('unsupported FMT1 source calendar')
    end=start+((count+2)//3)*16+24
    controls=[]
    for c in range(end):
        tx=c>=3 and (c-3)%4==0;tp=((c-3)//4)%4
        tj=3*((c-start-3)//16)+tp
        tf=tx and c>=start+3 and tp!=3 and 0<=tj<count
        rx=c>=4 and (c-4)%4==0;rp=((c-4)//4)%4
        rj=3*((c-start-4)//16)+rp-1
        rf=rx and c>=start+4 and rp!=0 and 0<=rj<count
        controls.append((int(tx)<<7)|(tp<<5)|(int(tf)<<4)|(int(rx)<<3)|(rp<<1)|int(rf))
    return tuple(controls)

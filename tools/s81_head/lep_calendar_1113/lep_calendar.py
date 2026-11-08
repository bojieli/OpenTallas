"""Private HEAD LEP stage calendar. Dates are supplied by the production compiler.

This prices explicit register legs, never FIFO residence or a token period.
The vF physical candidate preserves the current N-face collective-0 pins.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Stages:
    ktx: int = 0
    krx: int = 0
    txi: int = 0
    pin: int = 0
    pout: int = 0
    plw: int = 0
    col0: int = 0

    def __post_init__(self):
        for name in ('ktx', 'krx', 'txi'):
            if not 0 <= getattr(self, name) <= 0xffff:
                raise ValueError(f'{name} must contain four unsigned 4-bit depths')
        for name in ('pin', 'pout', 'plw', 'col0'):
            if not 0 <= getattr(self, name) <= 15:
                raise ValueError(f'{name} stage depth outside 0..15')

    def lane(self, field, lane):
        if field not in ('ktx', 'krx', 'txi') or lane not in range(4):
            raise ValueError('expected a KTX/KRX/TXI lane 0..3')
        return (getattr(self, field) >> (4 * lane)) & 15

    def legs(self):
        """Forward tuples and reverse credit tuples have the same leg depth."""
        answer = {
            'input.lepk_i0+unit_i0+lepf_i0': self.pin,
            'output.lepk_o0+ctrl_o0+fault_o0': self.pout,
            'output.lw_o': self.plw,
            'collective0.input.live+fault+data': self.col0,
            'collective0.output.data': self.col0,
        }
        for i in range(4):
            answer[f'lane{i}.tx_fifo_ingress'] = self.lane('txi', i)
            answer[f'lane{i}.tx_k.forward.valid+data'] = self.lane('ktx', i)
            answer[f'lane{i}.tx_k.reverse.credit'] = self.lane('ktx', i)
            answer[f'lane{i}.rx_k.forward.valid+data+rxv+fault'] = self.lane('krx', i)
            answer[f'lane{i}.rx_k.reverse.credit'] = self.lane('krx', i)
        return answer

    def shift_events(self, events):
        """Each event is a sample at the input of the NAMED explicit register leg.

        Events retain identity and absolute compiler origin. A leg is charged
        once; callers must not also apply a whole-transaction blanket shift.
        """
        legs = self.legs()
        result = []
        for event in events:
            if event['leg'] not in legs or not isinstance(event['cycle'], int):
                raise ValueError('unknown register leg or noninteger cycle')
            row = dict(event)
            row['source_cycle'] = event['cycle']
            row['cycle'] += legs[event['leg']]
            row['added_cycles'] = legs[event['leg']]
            result.append(row)
        return result

    def state_bits(self):
        """Logical stage FF bits; excludes reset delivery and cell/clock overhead.

        Native LEP H=552, TX_NS=(H+8)//8=70, TX_NA=18. Each
        TXI stage holds W=553 plus NG+1=19 valid/group-control bits.
        """
        lanes = range(4)
        return (1150*self.pin + 1137*self.pout + 11*self.plw
                + (514+512)*self.col0
                + 555*sum(self.lane('ktx',i) for i in lanes)
                + 559*sum(self.lane('krx',i) for i in lanes)
                + 572*sum(self.lane('txi',i) for i in lanes))

    def params(self):
        return dict(CH_B="4'b1111", PAIR=1, KTX=f"16'h{self.ktx:04x}",
                    KRX=f"16'h{self.krx:04x}", TXI=f"16'h{self.txi:04x}",
                    PIN=self.pin, POUT=self.pout, PLW=self.plw, COL0=self.col0)

VF = Stages(ktx=0x0000, krx=0x1220, txi=0x1221, pin=2, pout=3, plw=3, col0=2)
STRESS = Stages(ktx=0x3333, krx=0x4444, txi=0x4444, pin=4, pout=4, plw=4, col0=2)


def require_matching_receipt(stages, receipt, programme_sha256):
    """A measured handoff reservation qualifies only its exact stage tuple."""
    if (len(programme_sha256) != 64 or any(c not in '0123456789abcdef' for c in programme_sha256)
            or receipt.get('programme_sha256') != programme_sha256):
        raise ValueError('handoff receipt programme differs from selected static programme')
    actual = {key: receipt['params'][key] for key in stages.params()}
    if actual != stages.params():
        raise ValueError('handoff receipt stage tuple differs from selected provider')
    if receipt.get('static_replay') != 'PASS' or receipt.get('removed_reservation_mutant') != 'CAUGHT':
        raise ValueError('fixed static replay and removed-reservation control required')
    return tuple(receipt['handoff_idle_cycles'])


def provider_port_contract(plan, stages=VF, part='lep0N'):
    """Match provider legs to real plan endpoints WITHOUT changing lane delay.

    Plan lane latency ends at partition faces. These registers are inside
    noidx_core. The compiler traverses network edges plus provider legs once.
    Coherent ports name one group; their depths are never summed together.
    """
    by_bus = {
        'lepk_i0': ('in','input.lepk_i0+unit_i0+lepf_i0'),
        'unit_i0': ('in','input.lepk_i0+unit_i0+lepf_i0'),
        'lepf_i0': ('in','input.lepk_i0+unit_i0+lepf_i0'),
        'lepk_o0': ('out','output.lepk_o0+ctrl_o0+fault_o0'),
        'ctrl_o0': ('out','output.lepk_o0+ctrl_o0+fault_o0'),
        'fault_o0': ('out','output.lepk_o0+ctrl_o0+fault_o0'),
        'lw_o': ('out','output.lw_o'),
        'coll_i0': ('in','collective0.input.live+fault+data'),
        'coll_o0': ('out','collective0.output.data'),
    }
    by_bus.update({f'coll_{d}{i}':('in' if d=='i' else 'out',None)
                   for i in range(1,4) for d in ('i','o')})
    lanes = {x['id']:x for x in plan['lanes']}
    port_lanes = {}
    for lane in lanes.values():
        for pid in lane.get('ports',[]):
            port_lanes.setdefault(pid,[]).append(lane['id'])
    ports = []
    found = set()
    for port in plan['ports']:
        for endpoint, direction in (('dst','in'),('src','out')):
            ep = port.get(endpoint,{})
            if ep.get('part') != part:
                continue
            bus = ep['bus']
            expected, leg = by_bus[bus]
            if direction != expected or port['id'] not in port_lanes:
                raise ValueError(f'provider endpoint direction/lane mismatch: {bus}')
            found.add(bus)
            ports.append(dict(bus=bus, direction=direction, port=port['id'],
                              lanes=port_lanes[port['id']], provider_leg=leg,
                              provider_added_cycles=stages.legs()[leg] if leg else 0))
    if found != set(by_bus):
        raise ValueError(f'provider ports differ: missing {sorted(set(by_bus)-found)}')
    selected = {lane for row in ports for lane in row['lanes']}
    return dict(partition=part, params=stages.params(), provider_ports=ports,
                die_lane_added_cycles={lane:0 for lane in sorted(selected)},
                die_lane_fixed_cycles_before={lane:lanes[lane].get('fixed_cycles',0)
                                              for lane in sorted(selected)},
                internal_lane_legs={k:v for k,v in stages.legs().items() if k.startswith('lane')},
                consumption_rule='keep external lane fixed_cycles unchanged; compose each '
                                 'traversed provider leg once; coherent port depths are not summed',
                programme_qualified=False)


def check_external_lane_calendar_unchanged(before, after, contract):
    """Reject charging provider stages a second time on their external lanes."""
    for key in ('before','after'):
        plan = before if key=='before' else after
        lanes = {x['id']:x for x in plan['lanes']}
        for lane, fixed in contract['die_lane_fixed_cycles_before'].items():
            if lane not in lanes or lanes[lane].get('fixed_cycles',0) != fixed:
                raise ValueError(f'{key}: provider stage double-charged on external lane {lane}')
    b = before.get('latency',{}).get('lanes',{})
    a = after.get('latency',{}).get('lanes',{})
    for lane in contract['die_lane_added_cycles']:
        if lane in a and lane in b and a[lane].get('cycles') != b[lane].get('cycles'):
            raise ValueError(f'external lane {lane} latency changed in provider-only event')
    return True

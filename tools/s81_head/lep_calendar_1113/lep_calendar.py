"""Private HEAD LEP stage calendar. Dates are supplied by the production compiler.

This prices explicit register legs, never FIFO residence or a token period.
The vF physical candidate preserves the current N-face collective-0 pins.
"""
from dataclasses import dataclass, replace as replace_stages

@dataclass(frozen=True)
class Stages:
    ktx: int = 0
    krx: int = 0
    txi: int = 0
    pin: int = 0
    pout: int = 0
    plw: int = 0
    col0: int = 0
    pair: int = 1
    rxh: int = 0      # HEAD-PLAN-R4 NF15f: RX head rank (u_lep g_rxh) before ri / ml_wd
    kcred: int = 12   # FABLE-PLAN-HEAD-NF15F 1: K-link credit depth, both ends (u_lep DR / CRED, lane CORE_CRED)

    ktr: int | None = None  # TX credit-return depths; omitted means KTX, as in the RTL.

    def __post_init__(self):
        if self.pair not in (0,1):
            raise ValueError('PAIR must select original lanes0 or hardened pairs1')
        for name in ('ktx', 'krx', 'txi'):
            if not 0 <= getattr(self, name) <= 0xffff:
                raise ValueError(f'{name} must contain four unsigned 4-bit depths')
        if self.ktr is not None and not 0 <= self.ktr <= 0xffff:
            raise ValueError('ktr must contain four unsigned 4-bit depths')
        for name in ('pin', 'pout', 'plw', 'col0'):
            if not 0 <= getattr(self, name) <= 15:
                raise ValueError(f'{name} stage depth outside 0..15')
        if self.rxh not in (0, 1):
            raise ValueError('RXH is one RX head rank (0 or 1)')
        if not 2 <= self.kcred <= 32:
            raise ValueError('KCRED outside the credit SRAM shape 2..32 (ot_link_credit_rx_b64)')

    # K-link credit round trip in edges, MEASURED by tb_head_lepk_stages LEPK_RTT at the u_lep boundary (11-17): RX = credit
    # out -> next beat in (exact while credit-bound: KRX 6 lanes 21 at D 12) + beat in -> credit out; TX = beat out -> credit
    # back + turnaround (upper bound, the bench never starves TX).  Per lane at 0 stages: RX 14 / 12 / 12 / 17, TX 15; each
    # paired K stage adds two edges. KTR can price the return leg independently.
    # A link of depth D runs at D / RTT beats per cycle; the pre-R4 tuples run RX lanes 1 / 2 at 12 / 16 = 0.75,
    # under the 0.764 off-die lane cap, so they pass; NF15f needs D >= 24 (bench: 16 FAIL, 24 / 28 PASS).
    TX_RTT0, RX_RTT0 = 15, (14, 12, 12, 17)

    def credit_rtt(self, lane):
        return dict(tx=self.TX_RTT0 + self.lane('ktx', lane) + self.lane('ktr', lane),
                    rx=self.RX_RTT0[lane] + 2 * self.lane('krx', lane))

    def credit_ok(self):
        return all(self.kcred >= max(self.credit_rtt(i).values()) for i in range(4))

    def lane(self, field, lane):
        if field not in ('ktx', 'ktr', 'krx', 'txi') or lane not in range(4):
            raise ValueError('expected a KTX/KTR/KRX/TXI lane 0..3')
        depths = getattr(self, field)
        if depths is None:
            depths = self.ktx
        return (depths >> (4 * lane)) & 15

    def legs(self):
        """Price each forward and credit-return leg at its own depth."""
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
            answer[f'lane{i}.tx_k.reverse.credit'] = self.lane('ktr', i)
            answer[f'lane{i}.rx_k.forward.valid+data+rxv+fault'] = self.lane('krx', i)
            answer[f'lane{i}.rx_k.reverse.credit'] = self.lane('krx', i)
        # RXH: shared by the four lanes (pair release -> ri / mu_rt / ml_w); forward only, no credit leg
        answer['rx_head.ri+mu_rt+ml_w'] = self.rxh
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
                + 554*sum(self.lane('ktx',i) for i in lanes)
                + sum(self.lane('ktr',i) for i in lanes)
                + 559*sum(self.lane('krx',i) for i in lanes)
                + 572*sum(self.lane('txi',i) for i in lanes)
                + (4*552 + 44)*self.rxh)       # RXH: 2,208 head-word bits + 44 ring-side control copies

    def params(self):
        return dict(CH_B="4'b1111", PAIR=self.pair, KTX=f"16'h{self.ktx:04x}",
                    KRX=f"16'h{self.krx:04x}", TXI=f"16'h{self.txi:04x}",
                    PIN=self.pin, POUT=self.pout, PLW=self.plw, COL0=self.col0,
                    **({'RXH': self.rxh} if self.rxh else {}),   # RXH 0: the pre-R4 parameter set, unchanged
                    **({'KCRED': self.kcred} if self.kcred != 12 else {}),   # KCRED 12: unchanged
                    **({'KTR': f"16'h{self.ktr:04x}"} if self.ktr is not None else {}))

VF = Stages(ktx=0x0000, krx=0x1220, txi=0x1221, pin=2, pout=3, plw=3, col0=2)
NF15F = Stages(ktx=0x1111, krx=0x2660, txi=0x2442, pin=6, pout=8, plw=3, col0=2, rxh=1, kcred=28)   # HEAD-PLAN-R4 11-17
NF15F_R13 = replace_stages(NF15F, ktr=0x3112)
STRESS = Stages(ktx=0x3333, krx=0x4444, txi=0x4444, pin=4, pout=4, plw=4, col0=2, pair=0)


def require_matching_receipt(stages, receipt, programme_sha256):
    """A measured handoff reservation qualifies only its exact stage tuple."""
    if (len(programme_sha256) != 64 or any(c not in '0123456789abcdef' for c in programme_sha256)
            or receipt.get('programme_sha256') != programme_sha256):
        raise ValueError('handoff receipt programme differs from selected static programme')
    expected = stages.params()
    source_params = receipt['params']
    actual = {key: source_params[key] for key in expected if key != 'KTR'}
    if 'KTR' in expected:
        actual['KTR'] = source_params.get('KTR', actual['KTX'])
    if actual != expected or source_params.get('KTR', actual['KTX']) != expected.get('KTR', expected['KTX']):
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
                internal_lane_legs={k:v for k,v in stages.legs().items() if k.startswith(('lane','rx_head'))},
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

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

    def params(self):
        return dict(CH_B="4'b1111", PAIR=1, KTX=f"16'h{self.ktx:04x}",
                    KRX=f"16'h{self.krx:04x}", TXI=f"16'h{self.txi:04x}",
                    PIN=self.pin, POUT=self.pout, PLW=self.plw, COL0=self.col0)

VF = Stages(ktx=0x0000, krx=0x1220, txi=0x1221, pin=2, pout=3, plw=3, col0=2)
STRESS = Stages(ktx=0x3333, krx=0x4444, txi=0x4444, pin=4, pout=4, plw=4, col0=2)


def require_matching_receipt(stages, receipt):
    """A measured handoff reservation qualifies only its exact stage tuple."""
    actual = {key: receipt['params'][key] for key in stages.params()}
    if actual != stages.params():
        raise ValueError('handoff receipt stage tuple differs from selected provider')
    if receipt.get('static_replay') != 'PASS' or receipt.get('removed_reservation_mutant') != 'CAUGHT':
        raise ValueError('fixed static replay and removed-reservation control required')
    return tuple(receipt['handoff_idle_cycles'])

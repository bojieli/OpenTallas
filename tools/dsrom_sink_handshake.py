"""Default-off actual XU/Sinkhorn acceptance; no golden or campaign launch."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NAMES=('ot_hdc_v41_xu.sv','ot_hdc_sinkhorn_mc.sv')
SUCCESSOR=ROOT/'rtl/hdc/v41/dspark_sink_handshake'


def select(sources, *, enable=False):
    paths=list(map(Path,sources))
    if not enable:return dict(sources=paths,defines=[],enabled=False)
    for name in NAMES:
        matches=[p for p in paths if p.name==name]
        if len(matches)!=1:raise ValueError('missing/ambiguous Sinkhorn source: '+name)
        if not (SUCCESSOR/name).is_file():raise FileNotFoundError(SUCCESSOR/name)
    return dict(sources=[SUCCESSOR/p.name if p.name in NAMES else p for p in paths],
                defines=['+define+OT_MTP_SINK_HANDSHAKE=1'],enabled=True,
                arithmetic_changed=False, added_completion_cycles=0,
                acceptance_state_bits=3, wave2_admitted=False)

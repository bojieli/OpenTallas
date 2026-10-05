"""Default-off actual XU/Sinkhorn acceptance; no golden or campaign launch.

The successor sources (rtl/hdc/v41/dspark_sink_handshake) clear the XU's Sinkhorn request on the unit's
actual acceptance, not on busy (busy also spans the previous result's out_valid window, which dropped a
request raised right after a result: the MTP ITER deadlock at pc 4386).  The XU and the multicycle wrapper
are always replaced; the v41x XU adapter (its own copy of the request logic, used when the sel / eg units
are re-specified) is replaced whenever it is in the source list.

The same switch enables the second back-to-back hazard the op-major MTP verify pass exposes: the as-built
hyper-connection projection engine (ot_hdc_v41_hcproj) wrote an op's sums at the NEXT op's obase when HE ops
issued back to back (one per slot); its successor carries each op's write-back tag (OT_MTP_HE_TAG)."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NAMES=('ot_hdc_v41_xu.sv','ot_hdc_sinkhorn_mc.sv')
OPTIONAL=('ot_hdc_v41x_xu_adapt.sv','ot_hdc_v41_hcproj.sv')
SUCCESSOR=ROOT/'rtl/hdc/v41/dspark_sink_handshake'


def select(sources, *, enable=False):
    paths=list(map(Path,sources))
    if not enable:return dict(sources=paths,defines=[],enabled=False)
    for name in NAMES+OPTIONAL:
        matches=[p for p in paths if p.name==name]
        if len(matches)>1 or (name in NAMES and not matches):
            raise ValueError('missing/ambiguous Sinkhorn source: '+name)
        if not (SUCCESSOR/name).is_file():raise FileNotFoundError(SUCCESSOR/name)
    return dict(sources=[SUCCESSOR/p.name if p.name in NAMES+OPTIONAL else p for p in paths],
                defines=['+define+OT_MTP_SINK_HANDSHAKE=1','+define+OT_MTP_HE_TAG=1'],enabled=True,
                arithmetic_changed=False, added_completion_cycles=0,
                acceptance_state_bits=3, wave2_admitted=True)

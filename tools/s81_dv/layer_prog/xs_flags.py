"""S81-ROMOPT-A (owner 10-20 ~08:45): release defaults of the S81 die field-compiler options (ROM contents + compiler
only; no RTL or physical-view change).

Release default (env unset):
  OT_XS_GU_MERGE=1      O1: a SwiGLU expert's gate ++ up rows = one placed matrix (S81-ROMCAP)
  OT_XS_QPAIRS=12       O2: all 12 physical q pairs a frame, pair subset rotated per phase (S81-ROM12)
  OT_XS_CAL_SEGMENT=1   reused / rebased calendar intervals in the one 4096-row calendar ROM pair (S81-ROM12)
  OT_XS_TOPO=1          rows dealt over the PHYSICAL frames of each slice (122-frame p4l-MU die; S81-RATE3)
  OT_XS_PROP=1          free-ownership ops (wo_b, down, wo_a groups) dealt in proportion to the frames (S81-RATE3)
  OT_XS_COMPACT_TAILS=0 not adopted (see results/rtl/s81_romopt_1020/a/README.md)
Any variable set in the environment wins ('=0' selects the legacy behaviour of that option; OT_XS_QPAIRS=10 = O1 only).
OT_XS_LEGACY=1 makes the legacy values (all 0, QPAIRS 10) the defaults, which reproduces every pre-10-20 record.
"""
import os

RELEASE = dict(OT_XS_GU_MERGE='1', OT_XS_QPAIRS='12', OT_XS_CAL_SEGMENT='1', OT_XS_TOPO='1', OT_XS_PROP='1',
               OT_XS_COMPACT_TAILS='0')
LEGACY = dict(OT_XS_GU_MERGE='0', OT_XS_QPAIRS='10', OT_XS_CAL_SEGMENT='0', OT_XS_TOPO='0', OT_XS_PROP='0',
              OT_XS_COMPACT_TAILS='0')


def get(name):
    base = LEGACY if os.environ.get('OT_XS_LEGACY', '0') == '1' else RELEASE
    return os.environ.get(name, base[name])


def on(name):
    return get(name) == '1'


def describe():
    """the effective option values (for every compile / bench record)"""
    return dict({k: get(k) for k in RELEASE}, OT_XS_LEGACY=os.environ.get('OT_XS_LEGACY', '0'))

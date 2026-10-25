"""Production coll_ftm clock correction: replace its two overloaded glue taps.

Apply after the QC generator's type/FT placement is complete. Only clock topology
changes; ports, data/reset RTL and all public lane latencies remain unchanged.
"""
from copy import deepcopy

PROFILE = dict(tap_mode="density", tap_max_sinks=1000, tap_target_sinks=800,
               tap_radius_um=180.0, tap_min_sinks=0, tap_refine_iters=6)


def apply(raw):
    types = raw.get("partition_types", {})
    if "coll_ftm" not in types:
        raise ValueError("coll_ftm clock correction requires the production type")
    clock = types["coll_ftm"].setdefault("clock", {})
    # An explicit list supersedes the generated inventory. Retaining these two
    # glue taps would keep the original 2.5k-sink trees despite a finer pitch.
    clock.pop("taps", None)
    clock.update(deepcopy(PROFILE))
    return raw

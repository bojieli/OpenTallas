"""Explicit SAFE2 phase40 source profile; legacy caller behavior is the default.

The root has separate quarter-sum and gathered-mix paths. QCHX prices the
quarter-sum path only; it must not shift a gathered-mix event window arbitrarily.
This model does not qualify RTL execution or generate a selected die contract.
"""
from __future__ import annotations

LEGACY = "legacy11"
SAFE2_P40 = "safe2_phase40_qchx12"


def source_profile(name=LEGACY):
    if name not in (LEGACY, SAFE2_P40):
        raise ValueError(f"unknown HC source profile {name!r}")
    safe2 = name == SAFE2_P40
    qdrly, qchx, tla = 2, 12 if safe2 else 11, 7
    # Exact ot_hbm_hc_root_static source equations (XRD=XRU=0).
    sys_lat0 = 1 + 7 * (7 + 1 + 1) + 3 + 2 + (2 - 2) + 8 + 7 + 1 + 2*qdrly + qchx
    sys_lat = sys_lat0 + 1 + 0 + 1 + 6*tla + 1 + 0 + 1
    # Existing run_hbm_hc_eng4_ring.sh compiler RAW0 formula, CPR=1.
    raw0 = 165 + 11 + 2*(qdrly-1) + int(safe2)
    return dict(name=name, hub=dict(DRLY=2, CHX=11, SAFE=2 if safe2 else 0,
                                   RD_CAPTURE=39, GATHER_PHASE=39, GATHER_PERIOD=40, DONE_LAT=35),
                root=dict(QDRLY=qdrly, QCHX=qchx), quarter_sys_lat0=sys_lat0,
                quarter_sys_lat=sys_lat, ring_RAW0=raw0,
                qcen_landing_delta=int(safe2), gather_transport_period=40,
                hcp_arithmetic_period=24, execution_qualified=False)


def root_rows_for_profile(legacy_root_rows, parameters, response_phase, *, profile=None, npos=1):
    """Keep legacy rows by default; explicitly bind the separate SAFE2 model.

    G22 MIX_POST uses the gathered-mix store and tail, not quarter reductions.
    The actual source captures gathered inputs in one root pin edge in both
    profiles. Therefore G0, table-fetch, tail and emit retain the same offsets.
    QCHX12 changes SYS_LAT100->101 / SYS146->147 and ring RAW178->179 for
    quarter reductions; those paths require their own matching programme price.
    """
    if profile is None:
        return legacy_root_rows(parameters, response_phase)
    if npos != 1:
        raise ValueError("existing G22 root_rows programme covers only k31 npos1; no multi-position calendar qualification")
    model = source_profile(profile)
    if response_phase != 39:
        raise ValueError("explicit phase40 profiles require response phase39")
    table, words, schedule = legacy_root_rows(parameters, response_phase)
    schedule = dict(schedule, source_profile=model,
                    quarter_reduction_active=False,
                    fixture_scope="rank0 fixture k31 HC.HC_MIX_POST (priced record30 hc_attn)",
                    npos=1, K=20480,
                    gather_calendar_delta_vs_legacy11=0,
                    qualification="source_model_only; separate SAFE2 coupled witness required")
    return table, words, schedule

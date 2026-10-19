"""Measured GUNIT HC calendar candidates, bound to exact RTL and physical evidence.

This module does not change lower_gu's historical constants. Unknown RTL is
refused; recognized timing candidates remain blocked until a reviewed manifest
pins a successful native audit and its exact gate receipt. CTS diagnostics here
only admit this calendar contract, never a routed/signoff or die-fit claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import re

MANIFEST_PATH = Path(__file__).with_suffix('.json')
LEGACY_HC_LAT_N, LEGACY_HC_LAT_S = 759, 757


class HCContractError(ValueError):
    pass


@dataclass(frozen=True)
class HCCalendar:
    source_id: str
    lat_n: int
    lat_s: int
    origin: str
    admitted: bool
    blocked_reason: str

    def require_admitted(self) -> 'HCCalendar':
        if not self.admitted:
            raise HCContractError(f'{self.source_id}: {self.blocked_reason}')
        return self


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _native_block(variant: dict, native_audit: Path | None,
                  gate_result: Path | None) -> str:
    # Approval is committed in the manifest. A caller cannot turn admission on
    # by passing an unrelated PASS file or by setting a boolean in compile ctx.
    nh, gh = variant.get('native_audit_sha256'), variant.get('gate_result_sha256')
    if not nh or not gh:
        return variant['blocked_reason']
    if native_audit is None or gate_result is None:
        return 'pinned native audit and gate receipt are required'
    if _digest(native_audit) != nh or _digest(gate_result) != gh:
        return 'physical receipt digest differs from reviewed manifest'
    native, gate = json.loads(native_audit.read_text()), json.loads(gate_result.read_text())
    if (gate.get('schema') != 'opentallas.ref_tile.gate_result.v2'
            or gate.get('kit') != 'dsdv_gunit_l5'
            or gate.get('verdict') not in ('PASS', 'WARN')
            or gate.get('cts') is not True
            or any(i.get('severity') == 'FAIL' for i in gate.get('items', []))):
        return 'GUNIT CTS gate is not successful'
    binding = gate.get('source_binding', {})
    if binding.get('remote_archive_verified') is not True:
        return 'gate consumed archive was not verified'
    files = {}
    for f in binding.get('files', []):
        path = f.get('path')
        if path in files and files[path] != f.get('sha256'):
            return 'gate has conflicting source entries'
        files[path] = f.get('sha256')
    # The native receipt is for leaf L5. The source match in resolve covers
    # the complete GU pin-age vehicle, including the rung and other leaves.
    # Unrelated archived files are not consumed by the L5 synthesis.
    if any(files.get(p) != h for p, h in variant['native_sources'].items()):
        return 'gate consumed different timing RTL'
    if (native.get('schema') != 'opentallas.ref-tile.cts-native-probe.v1'
            or native.get('gate_result_sha256') != gh
            or native.get('diagnostic_pass') is not True
            or native.get('measured_reference_coverage') is not True
            or native.get('launch_over') != 0 or native.get('capture_over') != 0
            or native.get('comb_pins') != []):
        return 'native audit is failing, incomplete, or belongs to another gate'
    for key in ('library_sha256', 'insertion_sha256', 'probe_tcl_sha256'):
        if not re.fullmatch(r'[0-9a-f]{64}', str(native.get(key, ''))):
            return 'native audit lacks immutable probe/library/clock provenance'
    if (not native.get('clock_refs')
            or native.get('gate_source_commit') != binding.get('start_commit')
            or not binding.get('start_commit')):
        return 'native clock references or source provenance are incomplete'
    for key, limit in (('launch', 220), ('capture', 190)):
        value = native.get(key, {}).get('ps')
        if not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= limit:
            return f'native {key} exceeds existing budget or is unmeasured'
    spreads = list(native.get('spread_ps', {}).values()) + [native.get('ff_spread_ps')]
    if len(spreads) < 2 or any(not isinstance(v, (int, float))
                              or not math.isfinite(v) or not 0 <= v <= 80 for v in spreads):
        return 'TT/FF pin spread is unmeasured or exceeds existing budget'
    return ''


def resolve_hc_calendar(root: Path, *, compile_options: dict | None = None,
                        native_audit: Path | None = None,
                        gate_result: Path | None = None) -> HCCalendar:
    """Return a measured candidate with explicit admission; never guess latency.

    Compilers must call require_admitted before scheduling a release. Callers
    preparing measurement kits can inspect blocked candidates explicitly.
    """
    manifest = json.loads(MANIFEST_PATH.read_text())
    if manifest.get('schema') != 'opentallas.s81.gu_hc_contract.v1':
        raise HCContractError('unsupported HC timing manifest')
    root = Path(root)
    options = {} if compile_options is None else compile_options
    for variant in manifest['variants']:
        if options != variant['compile_options']:
            continue
        if not all((root / p).is_file() and _digest(root / p) == h
                   for p, h in variant['sources'].items()):
            continue
        blocked = _native_block(variant, native_audit, gate_result)
        return HCCalendar(variant['id'], variant['lat_n'], variant['lat_s'],
                          variant['origin'], not blocked, blocked)
    raise HCContractError('unqualified GUNIT RTL/compile options; no legacy-calendar fallback')

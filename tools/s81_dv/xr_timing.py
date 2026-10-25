"""Source-qualified V-CTL injection timing shared by compiler and replay.
Unversioned historical programmes retain six edges. XR2 adds its registered
classify stage; a new programme must name a qualified RTL SHA, also checked
against the reused simulator source inventory before a replay can PASS.
"""
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace

XR_PATH = "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xr.sv"
QUALIFIED = {"cc31c2d1607af9e0ac41357d3afaf19e6665b4f94ce4911e2dcaf078ec1167c3": 7,
             # TOK-FUNC-S81 (10-21): main 039ab4cbc xr.sv = cc31c2 (c977ce092) + XR5/XR6/XR7/SMWIRE/S81MERGE/S81POST/XR1F-PIN,
             # every one "0 data cycles" (XR6 adds +1 FAULT visibility only); the token-pass replays assert the 7 edges
             "e51bcf9e2cd5178ac5524865eecb9a8089cf20a7da919cbb49f342193181a9d2": 7}

XRT_PATH = 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv'
# Source model only: the necessary selected-XRT HOST/control cut is still
# running. This is not an entry in QUALIFIED and cannot pass check_run_source.
XRT_MODEL = {'cfc3feb9b99bf96dada241b4f6323c116e888eddd25d0ad504f5cde0ba170b64': 7,
             # TOK-DS NORM-DESKEW 10-25: main xrt (d266e908) + the static per-leaf norm partial deskew (PDSK 15'o01234);
             # the change is on the leaf-partial path only, the V-CTL injection is unchanged (7 edges)
             '18850f53ef8b664223ecd247083d62939ddfcad5372db0d2844020b4dabfd31c': 7,
             # the same deskew on the fc31 die source (cfc3feb9 + PDSK; the TOK-DS deskewed fc31 cuts)
             'ec43bbd4be16faa8428c107e7db613f21f0b760ed79711da31f068879c7d6282': 7}


def source_contract(tree, fallback, instances=None):
    if instances is not None:
        from layer_prog.slice_source import resolve
        root = Path(os.environ.get('OT_S81_SELECTED_SOURCE_ROOT') or tree)
        if not (root/'rtl/dsrom_sys/s81_dv/slice').exists():
            root = Path(fallback)
        die = SimpleNamespace(inst=instances)
        selected = {}
        pins = {}
        for name, inst in instances.items():
            if not inst['master'].startswith('ot_s81sl_slice'):
                continue
            r = resolve(die, name, root)
            path = r['xr_source_path']; sha = r['source_sha256'][path]
            family = 'XRT' if r['xr'].startswith('ot_s81sl_xrt') else 'XR'
            known = XRT_MODEL if family == 'XRT' else QUALIFIED
            if sha not in known:
                raise ValueError('unqualified selected '+family+' source model '+sha)
            if pins.setdefault(path, sha) != sha:
                raise ValueError('selected transports disagree on source '+path)
            selected[name] = dict(master=r['xr'], family=family, source_path=path, source_sha256=sha,
                                  wrapper_chain=r['wrapper_chain'])
        if not selected:
            raise ValueError('actual die has no selected slice transport')
        ages = {(XRT_MODEL if p['family'] == 'XRT' else QUALIFIED)[p['source_sha256']]
                for p in selected.values()}
        if len(ages) != 1:
            raise ValueError('mixed selected transport ages require per-path lowering')
        return dict(schema='opentallas.s81.selected_transport_timing.v2', v_ctl_inject=ages.pop(),
                    selected_transports=selected, transport_sources=pins,
                    source_root=str(root),
                    runtime_qualification='PENDING_SELECTED_XRT' if any(p['family']=='XRT' for p in selected.values()) else 'PASS_LEGACY_XR_COMPONENT',
                    basis='selected module source model; XRT runtime proof remains required')
    p = Path(tree) / XR_PATH
    if not p.exists(): p = Path(fallback) / XR_PATH
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    if sha not in QUALIFIED:
        raise ValueError("unqualified XR injection timing for RTL SHA " + sha)
    return dict(xr_source_sha256=sha, v_ctl_inject=QUALIFIED[sha],
                basis="rstop iv/dl_vb -> xr vb/classify/ci_r -> rstop ci_q/ro: 7 registered edges")

def inject_cycles(schedule):
    c = schedule.get("timing_contract")
    if c is None: return 6   # byte-compatible interpretation of archived programmes
    if c.get('schema') == 'opentallas.s81.selected_transport_timing.v2':
        selected = c.get('selected_transports') or {}
        if not selected:
            raise ValueError('selected transport source contract is empty')
        for p in selected.values():
            known = XRT_MODEL if p['family'] == 'XRT' else QUALIFIED
            if known.get(p['source_sha256']) != c.get('v_ctl_inject') \
                    or c['transport_sources'].get(p['source_path']) != p['source_sha256']:
                raise ValueError('selected transport source model mismatch')
        return c['v_ctl_inject']
    sha = c.get("xr_source_sha256")
    if sha not in QUALIFIED or c.get("v_ctl_inject") != QUALIFIED[sha]:
        raise ValueError("unqualified or inconsistent XR timing contract")
    return c["v_ctl_inject"]

ENTRY_SCHEMA = 'opentallas.s81_tokfunc.entry_replay.v1'
SELF_ENTRY = 'self-entry'


def xrt_runtime_proof(proof, contract):
    """The selected-XRT HOST/control runtime proof (TOKi-S81E 10-23).  `proof` is either SELF_ENTRY -- the caller is
    the native entry replay (run_entry_replay.py) on the HOST/control cut, i.e. this run IS the proof and its own entry
    verdict (bench fault 0, line bit-exact, every job) carries it -- or the path of a terminal entry_replay.json with
    verdict PASS_CUT_COMPONENT whose recorded transport sources equal the contract's.  Returns the proof basis string;
    anything else raises (the PENDING guard of 28ae20d13 stands)."""
    if not proof:
        raise ValueError('selected XRT source pinned, but current HOST/control runtime proof remains PENDING')
    if proof == SELF_ENTRY:
        return SELF_ENTRY
    import json
    d = json.loads(Path(proof).read_text())
    if d.get('schema') != ENTRY_SCHEMA or d.get('verdict') != 'PASS_CUT_COMPONENT':
        raise ValueError('XRT runtime proof is not a PASS_CUT_COMPONENT entry replay: ' + str(proof))
    got = d.get('xrt_transport_sources') or {}
    for path, sha in contract['transport_sources'].items():
        if got.get(path) != sha:
            raise ValueError('XRT runtime proof covers other transport source: ' + path + ' ' + str(got.get(path)))
    return 'ENTRY ' + str(proof)


def check_run_source(contract, run, runtime_proof=None):
    if contract is None: return
    inject_cycles({'timing_contract': contract})
    p = Path(run) / "sources.sha256"
    inventory = [line.split() for line in p.read_text().splitlines()]
    if contract.get('schema') == 'opentallas.s81.selected_transport_timing.v2':
        for path, sha in contract['transport_sources'].items():
            actual = {parts[0] for parts in inventory if len(parts)==2 and parts[1].endswith(path)}
            if actual != {sha}:
                raise ValueError('selected transport does not match simulator source: '+path+' '+str(actual))
        if any(p['family']=='XRT' for p in contract['selected_transports'].values()):
            return xrt_runtime_proof(runtime_proof, contract)
        return
    if any(len(parts)==2 and parts[1].endswith(XRT_PATH) for parts in inventory):
        raise ValueError('legacy XR-only contract cannot qualify an XRT-containing kit; selected-wrapper contract required')
    actual = {parts[0] for parts in inventory if len(parts) == 2 and parts[1].endswith(XR_PATH)}
    if actual != {contract["xr_source_sha256"]}:
        raise ValueError("replay XR timing contract does not match simulator sources: " + str(actual))

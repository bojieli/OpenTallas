"""Opt-in BFQG registration review. Reports candidates; preserves every raw gate."""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex

import reset_d_mask as canary


def proof_input_identity(kit, native_reset=4):
    """Read-only input join using the normal lec_async.sh identity protocol.

    No shell execution, proof reuse manufacture, or geometry/gate exemption.
    Only the qualified fixed native4 proof environment is reconstructed;
    other environment-dependent proof variants are refused.
    """
    forbidden = [k for k in os.environ if k.startswith('OT_LEC_') and k not in
                 ('OT_LEC_ASYNC', 'OT_LEC_ASYNC_POLL', 'OT_LEC_MEM_GB')]
    if forbidden:
        raise ValueError('environment-dependent proof identity unsupported: ' + ','.join(sorted(forbidden)))
    if native_reset != 4:
        raise ValueError('only the qualified native reset4 identity is supported')
    h = hashlib.sha256()
    # The actual native watcher records this explicit proof environment.
    h.update(b'OT_LEC_RESET_CYCLES=4')
    cfg = (kit/'config.mk').read_text()
    paths = [kit/'lec.py'] + [kit/n for n in ('lec_options.json', 'lec_hints.json', 'reset_contract.json') if (kit/n).is_file()]
    if (kit/'reset_contract.json').exists():
        receipt = json.loads((kit/'reset_contract.json').read_text()).get('proof', {}).get('receipt')
        if receipt:
            paths.append(kit/receipt[6:] if receipt.startswith('/work/') else kit/receipt)
    for line in cfg.splitlines():
        if re.match(r'^(?:override )?export (?:DESIGN_NAME|VERILOG_FILES|VERILOG_DEFINES|SYNTH_HDL_FRONTEND|ADDITIONAL_LIBS)\s*=', line):
            h.update(line.encode())
            if 'VERILOG_FILES' in line or 'ADDITIONAL_LIBS' in line:
                for name in shlex.split(line.split('=', 1)[1]):
                    if '$' not in name:
                        paths.append(kit/name[6:] if name.startswith('/work/') else Path(name))
    paths += sorted((kit/'rtl').rglob('*'))
    ready = kit/'lec_async.ready'
    h.update(ready.read_bytes())
    args = shlex.split('\n'.join(ready.read_text().splitlines()[1:]))
    try:
        name = args[args.index('--netlist')+1]
    except (ValueError, IndexError):
        raise ValueError('normal native proof has no explicit mapped input')
    mapped = kit/name[6:] if name.startswith('/work/') else Path(name)
    if not mapped.is_file() or not mapped.resolve().is_relative_to(kit):
        raise ValueError('mapped proof input is missing or outside kit')
    paths.append(mapped)
    for path in sorted(set(paths), key=str):
        if path.is_file():
            try:
                label = str(path.relative_to(kit))
            except ValueError:
                label = str(path)
            h.update(label.encode())
            h.update(path.read_bytes())
    return h.hexdigest(), mapped


def review(dump, kit, typed_dump):
    kit = Path(kit).resolve()
    if not (kit/'lec_async.done').exists() or (kit/'lec_async.rc').read_text().strip() != '0':
        raise ValueError('normal native proof has not completed successfully')
    lec = json.loads((kit/'lec/lec.json').read_text())
    provenance = json.loads((kit/'PROVENANCE.json').read_text())
    canary.proof_gate(lec, provenance, kit/'rtl')
    identity, mapped = proof_input_identity(kit, lec['reset_contract']['used'])
    if identity != (kit/'lec_async.identity').read_text().strip():
        raise ValueError('actual source/mapped proof identity changed')
    expected = lec.get('netlist', '')
    if expected != '/work/' + str(mapped.relative_to(kit)):
        raise ValueError('canonical EQ receipt refers to a different mapped input')
    cells = canary.mapped_cells(mapped.read_text())
    result = canary.qualify_cones(cells)
    result['physical_join'] = canary.physical_join(cells, dump, result['candidates'], json.loads(Path(typed_dump).read_text()))
    result.update(status='SOURCE_QUALIFIED_REVIEW_CANDIDATES_ONLY', proof_input_identity=identity,
                  registration_release=False, gating_changed=False, generic_comb_waiver=False,
                  raw_registration_failures_preserved=True)
    return result

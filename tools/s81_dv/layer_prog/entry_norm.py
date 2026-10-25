#!/usr/bin/env python3
"""Emit the native entry NORMR/XFIN producer commands, without sealing a job.

Input residency comes from entry_inputs, never an operation-result image. Dates
here order commands at the real walker interface; they are not qualified dates
for the NX reduction, rstd broadcast, VQ output or XS gather. In particular the
real issue+5 ACK does not license END while those producers are still active.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'tools/s81_dv'), str(Path(__file__).parent)]
import dv_layer_compile as D
from entry_inputs import compile_inputs


class PinDie:
    """Read only actual slice masks/SIDs; never synthesize a link timing model."""
    def __init__(self, path):
        raw = path.read_bytes()
        if path.suffix == '.gz':
            raw = gzip.decompress(raw)
        self.die_sha = hashlib.sha256(raw).hexdigest()
        self.path = str(path.resolve())
        self.selected = {}
        for line in raw.decode().splitlines():
            m = D.INST_RE.match(line)
            if not m or not m.group(1).startswith('ot_s81sl_slice'):
                continue
            master, params, name, body = m.groups()
            conns = {c.group(1): c.group(2).strip() for c in D.CONN_RE.finditer(body)}
            sid = re.fullmatch(r"\d+'([dh])([0-9a-fA-F]+)", conns.get('sid', ''))
            if not sid or name in self.selected:
                raise ValueError('actual die slice SID absent/duplicate: '+name)
            self.selected[name] = dict(master=master, params=params or '',
                sid=int(sid.group(2), 16 if sid.group(1) == 'h' else 10),
                clocks={k:v for k,v in conns.items() if k.startswith(('ck_', 'rst_'))})

    def slices(self):
        return self.selected


def compile_norm(die, entry, eps_bits, first_issue=20):
    if type(eps_bits) is not int or not 0 < eps_bits < 0x7f800000:
        raise ValueError('require explicit positive finite FP32 model epsilon bits')
    if type(first_issue) is not int or first_issue < 0:
        raise ValueError('first issue must be a nonnegative integer')
    if entry['die_sha256'] != die.die_sha:
        raise ValueError('entry residency and programme refer to different dies')
    readers = {(r['sid'] if 'sid' in r else die.slices()[r['slice']]['sid'], r['leaf']): r
               for r in entry['readers']}
    if set(readers) != {(sid, leaf) for sid in range(16) for leaf in range(5)}:
        raise ValueError('require exact 80-leaf entry residency')
    prog = D.Prog(die)
    commands = []
    # The two real command engines may each issue one row per edge. A slice's
    # 5 NORMRs go on 5 CONSECUTIVE edges (leaf k at slice base + k): the xrt
    # masters' per-leaf norm deskew (PDSK, TOK-DS NORM-DESKEW 10-25) aligns
    # partials staggered by exactly k edges; any other leaf spacing (the former
    # 8-edge round-robin) is a sticky collector fault.  No result or completion
    # signal affects these immutable dates.
    for tier, engine in [('N', D.ENG['VN']), ('S', D.ENG['VS'])]:
        slices = sorted((s for s in die.slices() if s.endswith(tier)),
                        key=lambda s: die.slices()[s]['sid'])
        if len(slices) != 8:
            raise ValueError('require eight actual slices per command engine')
        for leaf in range(5):
            for col, sl in enumerate(slices):
                sid = die.slices()[sl]['sid']; r = readers[sid, leaf]
                if r['normr_a0'] != 1008 or r['global_beat'] != 5*sid+leaf:
                    raise ValueError('entry delayed-pre/global beat contract differs')
                payload = D.ctl_payload(1 << sid, 0, 1 << leaf,
                    D.vp_cmd(D.VP['NORMR'], a0=r['normr_a0'], a1=r['global_beat'], n=1))
                issue = first_issue + 5*col + leaf
                t = prog.template(f'entry.NORMR.{sl}.k{leaf}', payload)
                prog.vrow(engine, issue, t, what=f'entry NORMR {sl} leaf{leaf} q-only')
                commands.append(dict(kind='NORMR', slice=sl, sid=sid, leaf=leaf,
                    issue=issue, template=t, pre_row=1008, global_beat=5*sid+leaf,
                    q=True, bf16=False))
        for col, sl in enumerate(slices):
            sid = die.slices()[sl]['sid']; issue = first_issue + 40 + col
            t = prog.template('entry.XFIN_GO.'+sl, D.ctl_payload(1 << sid, 1, 0, D.xfin_go(eps_bits)))
            prog.vrow(engine, issue, t, what='entry actual XFIN_GO '+sl)
            commands.append(dict(kind='XFIN_GO', slice=sl, sid=sid, issue=issue, template=t))
    rows = sorted(prog.rows, key=lambda r: (r['issue'], r['eng']))
    if len(rows) != 96 or len(prog.templates) != 96:
        raise ValueError('expected 80 distinct NORMR +16 distinct XFIN commands')
    if D.SEQ['done_v'] != 5:
        raise ValueError('current source ACK contract changed')
    for r in rows:
        r['row76'] = f'{D.pack_row(r["done"], r["issue"], r["eng"], r["arg"]):019x}'
    return dict(schema='opentallas.s81.entry_norm_native.v1', status='PARTIAL',
        die_sha256=die.die_sha, input_sources=entry['input_sources'],
        selected_slices=die.slices(),
        fixture_meta_sha256=entry['fixture_meta_sha256'], eps_fp32_bits=f'{eps_bits:08x}',
        commands=commands, rows=rows,
        templates=[dict(i=i, name=name, payload186=f'{payload:047x}')
                   for i, (name, payload) in enumerate(zip(prog.tnames, prog.templates))],
        command_count=96, normr_count=80, xfin_count=16, ack_edges=5,
        output_mode='q-only for a_proj; no unused BF16 family injected into gather',
        input_residency_required='same fixture entry jobs target5/HLOAD/GAIN completed before this job launch',
        residency_observed=False, source_command_dates_qualified=False,
        native_job_sealed=False, host_boot=None, end_age=None,
        global_exchange_dates_qualified=False, full_stage=False, full_token=False,
        holds=['execute entry HOST jobs and bind same incoming descriptor/residency',
               'actual selected 16-slice NX reduction and rstd broadcast with per-wrapper clocks/reset',
               'actual VQ/rstopt output trace from these inputs, then real XS gather windows',
               'derive fixed END/row lifetimes from actual mechanism, separately from issue+5 ACK'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument('--tree', type=Path, help='compiler tree with bind9/plan/land model')
    source.add_argument('--die-v', type=Path, help='actual materialized die.v; read only SIDs/source/clock pins')
    p.add_argument('--fixtures', type=Path, required=True)
    p.add_argument('--inference-config', type=Path, required=True,
                   help='exact fixture-pinned model config; use norm_eps, not hc_eps')
    p.add_argument('--first-issue', type=int, default=20)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('preserve previous immutable programme; use fresh output')
    die = PinDie(a.die_v) if a.die_v else D.Die(a.tree)
    entry = compile_inputs(die, a.fixtures)
    config_sha = hashlib.sha256(a.inference_config.read_bytes()).hexdigest()
    meta = json.loads((a.fixtures/'meta.json').read_text())
    config_key = 'compiler/models/deepseek-v4.1-flash/inference_config.json'
    if meta['sources'].get(config_key) != config_sha:
        raise ValueError('inference config does not match fixture source identity')
    config = json.loads(a.inference_config.read_text())
    eps_bits = struct.unpack('<I', struct.pack('<f', config['norm_eps']))[0]
    r = compile_norm(die, entry, eps_bits, a.first_issue)
    r['epsilon_source'] = dict(path=config_key, sha256=config_sha, key='norm_eps', value=config['norm_eps'])
    r['compiler_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(r, indent=1)+'\n')
    print('ENTRY_NORM_NATIVE PARTIAL commands96; END/global producer dates held')


if __name__ == '__main__':
    main()

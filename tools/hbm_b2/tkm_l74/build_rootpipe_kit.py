#!/usr/bin/env python3
"""Build the current stable-sort TKM root against its M5 plan interface.

Run through ot-run. This extracts the current repository RTL rather than an old
scratch CB21 cut, then invokes the standard core generator. External candidate
plans require --diagnostic-inputs; production inputs must live in the repository.
CTS remains held by the generator's common-domain multiport clock contract.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import build_rootpipe


ROOT = Path(__file__).resolve().parents[3]
MODULE = 'ot_hgi_coll_tkm_m_tp192__root'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--views', type=Path, required=True)
    ap.add_argument('--view', required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--diagnostic-inputs', action='store_true')
    args = ap.parse_args()
    if args.view.split('@', 1)[0] != MODULE:
        ap.error('this source bridge supports only the canonical TKM root')
    views = args.views.resolve()
    manifest = json.loads(views.read_text())
    candidates = [v for v in manifest['view_list'] if v['view'] == args.view]
    if len(candidates) != 1 or candidates[0].get('canonical_type') != 'tkm_root':
        ap.error('exactly one canonical tkm_root view is required')
    plan = (views.parent / manifest['plan']).resolve()
    if not args.diagnostic_inputs and not plan.is_relative_to(ROOT):
        ap.error('external plan requires --diagnostic-inputs')
    out = args.out.resolve()
    if out.exists() and any(out.iterdir()):
        ap.error('output must be new or empty; existing kits are never replaced')
    extracted = out / 'extracted'
    subprocess.run([sys.executable, str(ROOT / 'tools/hbm_b2/tkm_l74/build_rootpipe.py'),
                    '--out', str(extracted)], check=True)
    receipt = json.loads((extracted / 'source_receipt.json').read_text())
    original = extracted / receipt['output']
    # The physical master keeps its canonical name and cut map. Only the generated
    # extraction suffix changes; build_rootpipe checked every canonical cut port.
    generated = extracted / (build_rootpipe.BASE + '.sv')
    generated.write_text(original.read_text().replace(build_rootpipe.BASE + '__pfd21', build_rootpipe.BASE))
    commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    gen_path = ROOT / 'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py'
    spec = importlib.util.spec_from_file_location('rootpipe_coregen', gen_path)
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    recipe_key = candidates[0]['recipe_keys'][0]
    recipe = dict(gen.load_recipes()[recipe_key])
    if recipe['files'] != [build_rootpipe.CANON]:
        raise SystemExit('ROOTPIPE_SOURCE: canonical recipe closure changed; review the source bridge')
    profile = dict(name='tkm_root_stable_sort_m5', source_commit=commit,
                   builder=str(Path(__file__).resolve().relative_to(ROOT)),
                   source_inputs=receipt['inputs'], generated_source_sha256=gen.sha(generated),
                   data_cycle_delta=receipt['data_cycle_delta'],
                   diagnostic_inputs=args.diagnostic_inputs)
    sys.argv = [str(gen_path), '--views', str(views), '--view', args.view,
                '--out', str(out / 'kits'), '--hold-margin', '0', '--face-shell', 'on',
                '--face-shell-drop', 'off', '--core-insertion', 'none', '--clock-taps', 'density',
                '--route-ceiling', 'M5']
    gen.main(recipe_overrides={recipe_key: recipe},
             source_overrides={build_rootpipe.CANON: str(generated)}, source_profile=profile)


if __name__ == '__main__':
    main()

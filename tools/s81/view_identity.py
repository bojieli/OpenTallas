"""Validate source recipes against the actual die before variant attestation.

A caller cannot substitute candidate parameters or source files for those the die
actually instantiates. Missing/generated non-Git sources fail closed. This guard
is separate from library presence and from physical/native qualification.
"""
import json
from pathlib import Path
import variant_guard as VG


def attest(masters, recipes, bound, master_params, *, source_root, manifest_sources,
           manifest_defines, jobs_root, manifest_libdirs=(), repo=None, yosys='yosys'):
    root = Path(source_root).resolve()
    allowed = {str(Path(p).resolve()) for p in manifest_sources}
    out = dict(schema='opentallas.s81.view_identity.v1', verdict='FAIL', native_qualified=False, masters={})
    for master in sorted(masters):
        report = dict(verdict='FAIL', errors=[])
        out['masters'][master] = report
        try:
            recipe = dict(recipes.get(master) or {})
            if not recipe:
                raise ValueError('actual die recipe is absent; generated/non-Git masters need source evidence')
            if recipe.get('top', master) != master:
                raise ValueError('actual recipe top differs from die master')
            source_paths = recipe.get('sources') or []
            if not source_paths:
                raise ValueError('actual source list is absent')
            for source in source_paths:
                path = (root / source).resolve()
                if not path.is_relative_to(root) or str(path) not in allowed:
                    raise ValueError('source is not selected by the actual die RTL manifest: ' + source)
            # Parameters and defines come only from the ACTUAL die. A recipe
            # supplied for a routed candidate cannot silently select4/2 for0/0.
            recipe.update(top=master,
                          params={k:v for k,v in master_params.get(master, {}).items() if k != '_source'},
                          defines=list(manifest_defines), incdirs=list(manifest_libdirs))
            files = VG.source_bundle(recipe, repo or root)
            for source, text in files.items():
                path = (root / source).resolve()
                if not path.is_relative_to(root) or not path.is_file() or path.read_bytes().decode() != text:
                    raise ValueError('actual source/include bytes differ from the pinned recipe: ' + source)
            # Do not let a recipe select an inactive/ambiguous same-named
            # module from another file that happens to be in the manifest.
            defs = dict(d.split('=',1) if '=' in d else (d,'1') for d in manifest_defines)
            declarations = []
            for source in manifest_sources:
                path = Path(source).resolve()
                if not path.is_file():
                    continue
                text = VG.DB.preprocess(path.read_text(), defs)
                if any(module.name == master for module in VG.DB.parse_modules(text, str(path))):
                    declarations.append(path)
            if len(declarations) != 1 or str(declarations[0]) not in {str((root / p).resolve()) for p in source_paths}:
                raise ValueError('actual top declaration is missing/ambiguous or not selected by recipe')
            job = (bound.get(master) or {}).get('job')
            if not job:
                raise ValueError('bound view lacks its closing job identity')
            job_path = Path(jobs_root) / (job + '.json')
            if not job_path.is_file():
                raise ValueError('closing job archive is absent: ' + str(job_path))
            archived = json.loads(job_path.read_text())
            report.update(VG.compare_variants(recipe, archived, repo=repo or root, yosys=yosys))
        except (OSError, ValueError, KeyError) as exc:
            report['errors'].append(str(exc))
    if all(v['verdict'] == 'PASS' for v in out['masters'].values()):
        out['verdict'] = 'PASS'
    return out

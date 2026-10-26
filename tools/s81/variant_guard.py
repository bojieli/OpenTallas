#!/usr/bin/env python3
"""Opt-in source/parameter/hierarchy attestation; this is not physical qualification.

Both sides are elaborated afresh from Git objects. The bound recipe is read from
the closing job's archived route spec using the closure-loop identity helper.
Missing evidence or an unsupported elaboration fails closed. Planning callers
retain their historical behaviour unless they explicitly invoke this guard.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'closure_loop'))
import closed_stands
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import die_port_bind as DB

_ELAB_CACHE = {}
_SOURCE_CACHE = {}
_PARAM_CACHE = {}


class EvidenceError(ValueError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def git_show(repo, commit, path):
    p = subprocess.run(['git', '-C', str(repo), 'show', f'{commit}:{path}'], capture_output=True)
    return p.stdout.decode() if p.returncode == 0 else None


def job_recipe(job, repo):
    """Require the closing job's immutable commit and archived route spec."""
    commit = job.get('commit_full')
    spec = job.get('spec')
    if not commit or not isinstance(spec, dict):
        raise EvidenceError('bound job lacks commit_full or archived spec')
    declared = (spec.get('source') or {}).get('commit')
    if not declared or not (commit.startswith(declared) or declared.startswith(commit)):
        raise EvidenceError('bound job/spec source commits disagree or are missing')
    # rtl_boundary is an analysis override, not evidence of what synthesis ran.
    route_spec = {k: v for k, v in spec.items() if k != 'rtl_boundary'}
    recipe = closed_stands.route_recipe(route_spec, lambda c, p: git_show(repo, c, p))
    if not recipe or not recipe.get('top') or not recipe.get('sources'):
        raise EvidenceError('bound job route recipe cannot be recovered')
    # ref_tile records synthesis flags in the Git-pinned kit EXTRA array.
    cmd = ((spec.get('stages') or {}).get('route') or {}).get('cmd') or ''
    km = closed_stands.KIT_RE.search(cmd)
    flags = cmd
    if km:
        kit = git_show(repo, commit, km.group(1) + '/kit.env') or ''
        variables = closed_stands.rtl_boundary._cfg_vars(kit)
        kit_top = shlex.split(variables.get('TOP', ''))
        if kit_top != [recipe['top']]:
            raise EvidenceError('archived kit TOP differs from the bound job block or is missing')
        flags = variables.get('EXTRA', '()').strip('()')
    defines, incdirs = [], list(recipe.get('incdirs') or [])
    for token in shlex.split(flags):
        if token.startswith('VERILOG_DEFINES='):
            defines += [v[2:] for v in token.split('=', 1)[1].split() if v.startswith('-D') and v != '-DSYNTHESIS']
        if token.startswith('VERILOG_INCLUDE_DIRS='):
            incdirs += [v.removeprefix('/src/') for v in token.split('=', 1)[1].split()]
    return dict(recipe, commit=commit, defines=defines, incdirs=sorted(set(incdirs)))


def source_bundle(recipe, repo):
    cache_key = digest([str(Path(repo).resolve()), recipe.get('commit'), recipe.get('top'),
                        recipe.get('sources'), recipe.get('incdirs')])
    if cache_key in _SOURCE_CACHE:
        return _SOURCE_CACHE[cache_key]
    commit = recipe.get('commit')
    top = recipe.get('top')
    if not re.fullmatch(r'[0-9a-f]{40}', commit or '') or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*', top or ''):
        raise EvidenceError('actual recipe lacks pinned commit or legal top module')
    if not recipe.get('sources'):
        raise EvidenceError('recipe has no source list')
    files = {}
    incdirs = recipe.get('incdirs') or []
    if any(Path(p).is_absolute() or '..' in Path(p).parts for p in incdirs):
        raise EvidenceError('include directory is not Git-repository relative')

    def read(path):
        path = str(Path(path))
        if Path(path).is_absolute() or '..' in Path(path).parts:
            raise EvidenceError(f'non-repository source path: {path}')
        text = git_show(repo, commit, path)
        if text is None:
            raise EvidenceError(f'missing source at {commit}: {path}')
        files[path] = text
        return text

    pending = list(recipe['sources'])
    while pending:
        path = pending.pop()
        if path in files:
            continue
        text = read(path)
        if any(not rest.lstrip().startswith('"') for rest in re.findall(r'^\s*`include\b(.*)$', text, re.M)):
            raise EvidenceError(f'unsupported macro include in {path}')
        # Include payloads belong to the source identity too; unsupported macro
        # include paths fail during elaboration rather than borrowing host files.
        for name in re.findall(r'^\s*`include\s+"([^"]+)"', text, re.M):
            candidates = [str(Path(path).parent / name), name] + [str(Path(d) / name) for d in incdirs]
            found = next((p for p in candidates if git_show(repo, commit, p) is not None), None)
            if found is None:
                raise EvidenceError(f'missing include {name} required by {path}')
            pending.append(found)
    _SOURCE_CACHE[cache_key] = files
    return files


def parameter_signature(recipe, repo):
    """Cheap fail-closed early mismatch; a matching signature never proves PASS."""
    cache_key = digest([str(Path(repo).resolve()), recipe])
    if cache_key in _PARAM_CACHE:
        return _PARAM_CACHE[cache_key]
    files = source_bundle(recipe, repo)
    defs = recipe.get('defines') or []
    defs = dict(defs) if isinstance(defs, dict) else dict(d.split('=', 1) if '=' in d else (d, '1') for d in defs)
    defs['SYNTHESIS'] = '1'
    matches = [m for p, t in files.items() for m in DB.parse_modules(DB.preprocess(t, defs), p) if m.name == recipe['top']]
    if len(matches) != 1:
        raise EvidenceError('top declaration missing or ambiguous')
    module = matches[0]
    overrides = {k: v for k, v in (recipe.get('params') or {}).items() if k != '_source'}
    if set(overrides) - set(module.params):
        raise EvidenceError('unknown parameter overrides')
    env = {}
    for name, expr in module.params.items():
        value = DB.ev(str(overrides.get(name, expr)), env)
        if value is None:
            raise EvidenceError(f'unresolved parameter {name}')
        env[name] = value
    _PARAM_CACHE[cache_key] = env
    return env


def elaborate(recipe, repo, yosys='yosys'):
    """Nonflattened hierarchy and effective parameters, from pinned source bytes.

    Yosys hierarchy derives generate branches and parameterized child modules;
    proc permits write_json without flattening away the physical hierarchy.
    Never reuse a caller-supplied fingerprint or compare port counts.
    """
    recipe = dict(recipe, params={k: v for k, v in (recipe.get('params') or {}).items() if k != '_source'})
    cache_key = digest([str(Path(repo).resolve()), recipe, yosys])
    if cache_key in _ELAB_CACHE:
        return _ELAB_CACHE[cache_key]
    files = source_bundle(recipe, repo)
    top = recipe['top']
    effective = parameter_signature(recipe, repo)
    params = recipe.get('params') or {}
    for key, value in params.items():
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*', key) or any(c in str(value) for c in '\n;\\'):
            raise EvidenceError('unsupported parameter syntax')
    defines = recipe.get('defines') or []
    if isinstance(defines, dict):
        defines = [k + ('=' + str(v) if v is not None else '') for k, v in defines.items()]
    if any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:=[A-Za-z0-9_\x27]+)?', d) for d in defines):
        raise EvidenceError('unsupported preprocessor define syntax')
    with tempfile.TemporaryDirectory(prefix='s81-variant-') as td:
        root = Path(td)
        for path, text in files.items():
            dest = root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text)
        quote = lambda s: json.dumps(str(s))
        flags = ['-sv', '-DSYNTHESIS'] + ['-D' + d for d in defines]
        flags += ['-I' + quote(root / p) for p in recipe.get('incdirs') or []]
        script = 'read_verilog ' + ' '.join(flags + [quote(root / p) for p in recipe['sources']]) + ';\n'
        if params:
            script += 'chparam ' + ' '.join('-set ' + k + ' ' + str(v) for k, v in sorted(params.items())) + ' ' + top + ';\n'
        script += f'hierarchy -check -top {top}; proc; write_json ' + quote(root / 'hierarchy.json') + ';\n'
        (root / 'elaborate.ys').write_text(script)
        p = subprocess.run([yosys, '-Q', '-T', '-s', str(root / 'elaborate.ys')], cwd=root, capture_output=True, text=True)
        if p.returncode or not (root / 'hierarchy.json').exists():
            raise EvidenceError('pinned elaboration failed: ' + (p.stderr or p.stdout)[-1200:])
        data = json.loads((root / 'hierarchy.json').read_text().replace(str(root), '<SOURCE_ROOT>'))
    modules = data.get('modules') or {}
    if top not in modules:
        raise EvidenceError('elaboration did not retain requested top')
    # Canonicalize derived module names by their actual content, preserving the
    # child graph, child parameter values, connections, ports and process cells.
    memo = {}
    active = set()

    def module_identity(name):
        if name in memo:
            return memo[name]
        if name in active:
            raise EvidenceError('recursive/unresolved elaborated hierarchy')
        active.add(name)
        module = modules[name]
        if str((module.get('attributes') or {}).get('blackbox', '0')).strip('0'):
            raise EvidenceError(f'blackbox lacks elaborated source evidence: {name}')
        cells = {}
        for cell_name, cell in sorted((module.get('cells') or {}).items()):
            kind = cell['type']
            if kind in modules:
                kind = {'module_fingerprint': module_identity(kind)}
            elif not kind.startswith('$'):
                raise EvidenceError(f'unresolved child module {kind}')
            cells[cell_name] = {k: v for k, v in cell.items() if k not in ('attributes', 'type')}
            cells[cell_name]['type'] = kind
        payload = dict(parameters=effective if name == top else module.get('parameter_default_values') or {},
                       ports=module.get('ports') or {}, cells=cells)
        memo[name] = digest(payload)
        active.remove(name)
        return memo[name]

    hierarchy = module_identity(top)
    result = dict(schema='s81-source-param-hierarchy-v1', top=top, commit=recipe['commit'],
                effective_parameters=effective,
                source_sha256={p: hashlib.sha256(t.encode()).hexdigest() for p, t in sorted(files.items())},
                defines=sorted(defines), hierarchy_sha256=hierarchy, reachable_modules=len(memo))
    _ELAB_CACHE[cache_key] = result
    return result


def compare_variants(actual_recipe, bound_job, *, repo, yosys='yosys'):
    """Return an opt-in attestation. Any missing side is FAIL, never a waiver."""
    out = dict(schema='s81-variant-guard-v1', verdict='FAIL', native_qualified=False,
               bound_job=bound_job.get('name') or bound_job.get('id'), errors=[])
    try:
        bound_recipe = job_recipe(bound_job, repo)
        actual_params = parameter_signature(actual_recipe, repo)
        bound_params = parameter_signature(bound_recipe, repo)
        out.update(actual_parameters=actual_params, bound_parameters=bound_params)
        if actual_recipe['top'] != bound_recipe['top'] or actual_params != bound_params:
            out['errors'].append('top/effective_parameters mismatch before hierarchy elaboration')
            return out
        actual = elaborate(actual_recipe, repo, yosys)
        bound = elaborate(bound_recipe, repo, yosys)
        out.update(actual=actual, bound=bound)
        for key in ('top', 'effective_parameters', 'defines', 'hierarchy_sha256'):
            if actual[key] != bound[key]:
                out['errors'].append(key + ' mismatch')
        # Source bytes must also agree, even if optimization erased a change.
        if sorted(actual['source_sha256'].values()) != sorted(bound['source_sha256'].values()):
            out['errors'].append('transitive source contents mismatch')
        if not out['errors']:
            out['verdict'] = 'PASS'
    except (EvidenceError, OSError, ValueError, KeyError) as exc:
        out['errors'].append(str(exc))
    return out

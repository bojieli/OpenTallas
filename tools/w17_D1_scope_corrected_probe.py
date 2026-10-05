"""Scope-aware source checks for the additive D1 observation copy.

This is a bounded lexical check, not an HDL elaborator. Actual frontend PASS
remains required. Never launches a compiler, native link or simulation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import w17_D1_current_core_admission as previous

E = Path('results/uarch/w17_D1_scope_corrected_probe_20261002')
B = Path('rtl/test/w17_D1_scope_corrected_probe')
OLD = previous.EVIDENCE
WINDOW = ('w_v','w_rdy','w_we','w_addr','w_tag','w_sv','w_srdy','w_s_tag','w_s_beat','w_wdone')


def stripped(text):
    return re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"',
                  lambda m: ''.join('\n' if c=='\n' else ' ' for c in m.group()), text, flags=re.S)


def scope_at(text, offset):
    tokens = list(re.finditer(r'[A-Za-z_$][\w$]*|:', stripped(text)))
    stack = []
    for i, token in enumerate(tokens):
        if token.start() >= offset:
            break
        if token.group() == 'begin':
            label = tokens[i+2].group() if i+2<len(tokens) and tokens[i+1].group()==':' else None
            stack.append(label)
        elif token.group() == 'end':
            if not stack:
                raise ValueError('Unbalanced source begin/end')
            stack.pop()
    return tuple(x for x in stack if x is not None)


def declarations(text, names):
    """Return named begin scopes and lines of requested wire/reg/port declarations."""
    clean = stripped(text)
    result = {name: [] for name in names}
    for match in re.finditer(r'\b(?:wire|reg|input|output|bit|logic)\b([^;]*);', clean):
        body = re.sub(r'\[[^\]]*\]', '', match.group(1))
        for segment in body.split(','):
            ids = re.findall(r'[A-Za-z_$][\w$]*', segment.split('=')[0])
            if ids and ids[-1] in result:
                name = ids[-1]
                result[name].append({'scope': list(scope_at(text, match.start())),
                                     'line': text.count('\n',0,match.start())+1})
    return result


def instance(text, module, name, expected_scope):
    clean = stripped(text)
    found = []
    for match in re.finditer(r'\b'+re.escape(module)+r'\b\s*#\s*\(', clean):
        pos = match.end(); depth = 1
        while pos < len(clean) and depth:
            depth += (clean[pos]=='(') - (clean[pos]==')'); pos += 1
        tail = re.match(r'\s*([A-Za-z_$][\w$]*)\s*\(', clean[pos:])
        if tail and tail.group(1)==name:
            found.append(scope_at(text,match.start()))
    if found != [tuple(expected_scope)]:
        raise ValueError('Wrong ancestor instance/scope: '+module+' '+name)


def check_paths(observer, die, core):
    if re.search(r'\bdut\.(?:'+'|'.join(WINDOW)+r')\b', observer):
        raise ValueError('Unqualified root WINDOW bus reference')
    locations = declarations(die, WINDOW)
    for name in WINDOW:
        if not locations[name] or any(x['scope']!=['g_packed_kv'] for x in locations[name]):
            raise ValueError('Wrong WINDOW declaration scope: '+name)
        if 'dut.g_packed_kv.'+name not in observer:
            raise ValueError('Missing qualified WINDOW observation: '+name)
    # Resolve every actual core field referenced by the observer.
    names = set(re.findall(r'\bdut\.u_tile\.u_core\.(\w+)',observer))
    fields = declarations(core, names)
    for name in names:
        if not fields[name] or any(x['scope'] for x in fields[name]):
            raise ValueError('Wrong core declaration scope: '+name)
    return {'WINDOW':locations,'core':fields}


def verify(root):
    root=Path(root);e=root/E
    # Pin all prerequisite files; historical module-owner PASS is not hierarchy qualification.
    previous.verify(root)
    for item in json.loads((e/'artifact_manifest.json').read_text()):
        path=root/item['path'];data=path.read_bytes()
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Unsafe artifact path')
        if hashlib.sha256(data).hexdigest()!=item['sha256'] or len(data)!=item['bytes']:
            raise ValueError('Correction artifact changed')
    authority=root/OLD/'source_authority'
    read=lambda p:(authority/p).read_text()
    die=read('rtl/w17_runtime/chip/ot_chip_v41x_die.sv')
    tile=read('rtl/w17_runtime/chip/ot_chip_v41x_tile.sv')
    core=read('rtl/w17_runtime/hdc/v41x/fastpp_pc21/l0/ot_hdc_core_v41x.sv')
    source=read('rtl/chip/ot_chip_v41x_window_attn_source.sv')
    window=read('rtl/chip/ot_chip_v41x_window_kv_prefetch.sv')
    corrected=(root/B/'ot_v41_rt_die_D1_scope.sv').read_text()
    block=corrected.split('// D1_CURRENT_OBSERVATION_BEGIN')[1].split('// D1_CURRENT_OBSERVATION_END')[0]
    result=check_paths(block,die,core)
    instance(corrected,'ot_chip_v41x_die','dut',())
    instance(die,'ot_chip_v41x_tile','u_tile',())
    instance(tile,'ot_hdc_core_v41x','u_core',())
    instance(die,'ot_chip_v41x_window_attn_source','u_source',('g_packed_kv','g_window_hbm_attention'))
    instance(source,'ot_chip_v41x_window_kv_prefetch','u_window',())
    for name,locations in declarations(window,{'state','response_poison'}).items():
        if not locations or any(x['scope'] for x in locations):
            raise ValueError('Wrong provider field scope: '+name)
    for param in ('.FULL_SHAPE(1)','.WINDOW_HBM_ATTENTION(1)'):
        if param not in corrected:
            raise ValueError('Required generated branch inactive')
    # Prove exactly the namespace + 20 observer path substitutions from failed copy.
    old=(root/previous.BENCH/'ot_v41_rt_die_D1_current.sv').read_text()
    expected=old.replace('ot_v41_rt_die_D1_current','ot_v41_rt_die_D1_scope')
    expected=re.sub(r'\bdut\.(?:'+'|'.join(WINDOW)+r')\b',lambda m:'dut.g_packed_kv.'+m.group()[4:],expected)
    if expected!=corrected:
        raise ValueError('Change outside bounded observation correction')
    inverse=previous.inverse_wrapper(corrected.replace('ot_v41_rt_die_D1_scope','ot_v41_rt_die_D1_current'))
    if inverse!=read('rtl/test/v41_runtime/ot_v41_rt_die.sv'):
        raise ValueError('Original wrapper inverse mismatch')
    plan=json.loads((e/'plan.json').read_text());previous.validate_plan(plan)
    go=json.loads((e/'frontend_GO_template.json').read_text())
    if go['authorized'] is not False or go['native_authorized'] is not False or go['runtime_authorized'] is not False:
        raise ValueError('Template cannot authorize execution')
    if go['plan_sha256']!=hashlib.sha256((e/'plan.json').read_bytes()).hexdigest():
        raise ValueError('GO plan mismatch')
    return {'status':'SCOPE_CORRECTION_SOURCE_REVIEW_PASS_NOT_ELABORATED',
            'WINDOW_names':len(WINDOW),'core_fields':len(result['core']),
            'engine_changes':False,'compiled':False,'runtime_admitted':False,
            'prior_frontend_failure_preserved':True,'service_bound':'BOUND_MISSING'}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    print(json.dumps(verify(args.root),indent=2,sort_keys=True))

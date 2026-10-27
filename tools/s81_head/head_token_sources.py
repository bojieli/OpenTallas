#!/usr/bin/env python3
"""Make the native simulation file list for an already generated HEAD plan.

Physical manifests intentionally select black boxes. Native execution uses the
same interfaces with the checked-in behavioral models. Tile ROM prefixes must
be unique per partition; changing a prefix changes only simulation file lookup.
No pipeline, port, arithmetic or clock/reset signal is changed.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


def replace_once(text, pattern, value, description):
    result, count = re.subn(pattern, value, text, count=1)
    if count != 1:
        raise ValueError('missing unique '+description)
    return result


def prepare(root, plan_path, manifest, out):
    root, plan_path, manifest, out = [p.resolve() for p in (root, plan_path, manifest, out)]
    plan = json.loads(plan_path.read_text())
    out.mkdir(parents=True, exist_ok=False)
    src = list(dict.fromkeys(s.strip() for s in manifest.read_text().splitlines() if s.strip()))
    aliases = {}
    for s in src:
        if s.endswith('_bb.v'):
            aliases[s] = s[:-5]+'.v'
    cv = 'rtl/dsrom_sys/s81_head/ot_s81hd_elem_cv_bb.v'
    if cv not in src:
        raise ValueError('physical element CV interface must be explicit')
    aliases[cv] = 'rtl/dsrom_sys/s81_head/ot_s81hd_elem_cv.sv'
    models = [aliases.get(s, s) for s in src]
    models.append('rtl/dsrom_sys/s81_head/ot_s81hd_oreg.sv')
    models = list(dict.fromkeys(models))
    for s in models:
        p = root/s
        if not p.exists():
            data = subprocess.check_output(['git', '-C', str(root), 'show', 'HEAD:'+s])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        if re.search(r'\(\*\s*blackbox\s*\*\)', p.read_text()):
            raise ValueError('native manifest still contains blackbox '+s)
    tile = plan['partition_types']['hd_tile']
    wrapper = tile['module']
    generated = [s for s in models if Path(s).name == wrapper+'.sv']
    if len(generated) != 1:
        raise ValueError('expected exactly one generated tile wrapper')
    s = generated[0]
    text = (root/s).read_text()
    text = replace_once(text, r'\bmodule\s+'+re.escape(wrapper)+r'\s*\(',
                        'module '+wrapper+' #(parameter INSTANCE = "") (', 'tile wrapper header')
    # Keep all existing physical content parameters verbatim.
    text = replace_once(text, r'(\bot_s81hd_tile\s*#\s*\()', r'\1.INSTANCE(INSTANCE), ', 'tile content parameter list')
    target = out/(wrapper+'.sv'); target.write_text(text)
    models[models.index(s)] = str(target.relative_to(root))
    tops = [s for s in models if Path(s).name == 's81_head_top.sv']
    if len(tops) != 1:
        raise ValueError('expected exactly one generated die top')
    top = (root/tops[0]).read_text()
    tiles = [p for p in plan['partitions'] if p['type'] == 'hd_tile']
    names = []
    for p in tiles:
        name = p['name']
        pat = r'(\b'+re.escape(wrapper)+r')\s+('+re.escape(name)+r')\s*\('
        top = replace_once(top, pat, r'\1 #(.INSTANCE("'+name+r'")) \2 (', 'tile instance '+name)
        names.append(name)
    target = out/'s81_head_top.sv'; target.write_text(top)
    models[models.index(tops[0])] = str(target.relative_to(root))
    # This is the already-qualified HEAD link profile used by mesh_ep_bench
    # and head_host_ctl_bench, not an unqualified default linker branch.
    defines = ['OT_COLL_NATIVE32', 'OT_COLL_NATIVE32_OFF']
    include_dirs = sorted({str(Path(s).parent) for s in models})
    (out/'native.f').write_text('\n'.join(['+define+'+d for d in defines]+['+incdir+'+d for d in include_dirs]+models)+'\n')
    image_names = [name+core+'_'+str(bank)+'.viamap.hex' for name in names for core in ('a0','a1','a2','a3','b') for bank in (0,1)]
    report = dict(schema='opentallas.head.native_sources.v1', replacements=aliases,
        defines=defines, include_dirs=include_dirs, tile_instances=len(names), required_weight_images=image_names,
        unique_weight_images=len(set(image_names)), added_cycles=0,
        source_sha256={s: hashlib.sha256((root/s).read_bytes()).hexdigest() for s in models},
        qualification='source staging only; current physical-view equivalence, boot schedule and real numerical token execution pending')
    (out/'source_contract.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan',type=Path); ap.add_argument('manifest',type=Path); ap.add_argument('out',type=Path)
    a=ap.parse_args(); root=Path.cwd()
    report=prepare(root, a.plan, a.manifest, a.out)
    print('HEAD_NATIVE_SOURCES tiles=%d unique_images=%d cycles_added=0' % (report['tile_instances'],report['unique_weight_images']))
if __name__=='__main__':main()

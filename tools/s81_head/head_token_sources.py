#!/usr/bin/env python3
"""Make the native simulation file list for an already generated HEAD plan.

Physical manifests intentionally select black boxes. Native execution uses the
same interfaces with the checked-in behavioral models. Tile ROM identities must
be unique. Parameter mode specializes the wrapper image prefix; scope mode keeps
shared type parameters and selects images using the runtime ROM hierarchy.
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


def scope_rom_model(text):
    anchor = '    initial begin\n        for (init_i = 0;'
    if text.count(anchor) != 1:
        raise ValueError('ROM initialization anchor changed')
    extra = ('    string head_scope;\n'
             '    string head_dir;\n'
             '    string head_image_path;\n'
             '    integer head_image_fd;\n')
    text = text.replace(anchor, extra+anchor, 1)
    anchor = '        if ($value$plusargs("OT_ROM_DIR=%s", rom_dir) && INSTANCE != "")'
    branch = r'''        if ($value$plusargs("OT_HEAD_ROM_DIR=%s", head_dir) && VIAMAP == "") begin
            head_scope = $sformatf("%m");
            if (head_scope.len() > 4 && head_scope.substr(0,3) == "TOP.")
                head_scope = head_scope.substr(4,head_scope.len()-1);
            head_image_path = $sformatf("%s/%s.viamap.hex",head_dir,head_scope);
            head_image_fd = $fopen(head_image_path,"r");
            if (head_image_fd == 0) $fatal(1,"HEAD missing scope image %s",head_image_path);
            $fclose(head_image_fd);
            $readmemh(head_image_path,arr);
        end else'''
    if text.count(anchor) != 1:
        raise ValueError('ROM image selection anchor changed')
    return text.replace(anchor, branch+'\n'+anchor, 1)


def prepare(root, plan_path, manifest, out, rom_load='parameters', hierarchical=False, partition_only=False):
    if partition_only and (hierarchical or rom_load != 'parameters'):
        raise ValueError('partition-only vehicle uses explicit INSTANCE image parameters')
    if hierarchical and rom_load != 'scope':
        raise ValueError('hierarchical sharing requires runtime scope image loading')
    root, plan_path, manifest, out = [p.resolve() for p in (root, plan_path, manifest, out)]
    plan = json.loads(plan_path.read_text())
    out.mkdir(parents=True, exist_ok=False)
    src = list(dict.fromkeys(s.strip() for s in manifest.read_text().splitlines() if s.strip()))
    aliases = {}
    for s in src:
        if s.endswith('_bb.v'):
            aliases[s] = s[:-5]+'.v'
    # Native infrastructure interfaces have a declared functional substitution;
    # never guess their filename or fall back to a logical-port-only model.
    declared = {}
    for typ in list(plan['partition_types'].values()) + [plan.get('infrastructure') or {}]:
        for physical, functional in typ.get('simulation_substitutions', {}).items():
            if physical in declared and declared[physical] != functional:
                raise ValueError('conflicting simulation substitution '+physical)
            declared[physical] = functional
    aliases.update({physical: functional for physical, functional in declared.items() if physical in src})
    cv = 'rtl/dsrom_sys/s81_head/ot_s81hd_elem_cv_bb.v'
    native_cv = 'rtl/dsrom_sys/s81_head/ot_s81hd_elem_cv_bb_native.v'
    if cv in src:
        aliases[cv] = 'rtl/dsrom_sys/s81_head/ot_s81hd_elem_cv.sv'
    elif native_cv not in src or native_cv not in declared:
        raise ValueError('physical element CV interface needs explicit functional substitution')
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
    if rom_load == 'scope':
        macro = 'physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v'
        if macro not in models:
            raise ValueError('expected real HEAD weight ROM model')
        target = out/'ot_rom_4096x274_m8_scope.sv'
        target.write_text(scope_rom_model((root/macro).read_text()))
        models[models.index(macro)] = str(target.relative_to(root))
    tile = plan['partition_types']['hd_tile']
    wrapper = tile['module']
    content = tile.get('contents', [{}])[0].get('module', 'ot_s81hd_tile')
    if content not in ('ot_s81hd_tile', 'ot_s81hd_tile_native'):
        raise ValueError('unsupported HEAD tile content '+content)
    generated = [s for s in models if Path(s).name == wrapper+'.sv']
    if len(generated) != 1:
        raise ValueError('expected exactly one generated tile wrapper')
    s = generated[0]
    text = (root/s).read_text()
    if rom_load == 'parameters':
        text = replace_once(text, r'\bmodule\s+'+re.escape(wrapper)+r'\s*\(',
                            'module '+wrapper+' #(parameter INSTANCE = "") (', 'tile wrapper header')
    # Keep all existing physical content parameters verbatim.
        text = replace_once(text, r'(\b'+re.escape(content)+r'\s*#\s*\()', r'\1.INSTANCE(INSTANCE), ', 'tile content parameter list')
    if hierarchical:
        text = replace_once(text, r'(?s)(\bmodule\s+'+re.escape(wrapper)+r'\s*\(.*?\);)', r'\1\n/*verilator hier_block*/', 'shared tile module')
    target = out/(wrapper+'.sv'); target.write_text(text)
    models[models.index(s)] = str(target.relative_to(root))
    tops = [s for s in models if Path(s).name == 's81_head_top.sv']
    if not partition_only and len(tops) != 1:
        raise ValueError('expected exactly one generated die top')
    top = (root/tops[0]).read_text() if not partition_only else ''
    if partition_only:
        models = [s for s in models if s not in tops]
    tiles = [p for p in plan['partitions'] if p['type'] == 'hd_tile']
    names, bindings = [], []
    for p in tiles:
        name = p['name']
        pat = r'(\b'+re.escape(wrapper)+r')\s+('+re.escape(name)+r')\s*\('
        if partition_only:
            pass
        elif rom_load == 'parameters':
            top = replace_once(top, pat, r'\1 #(.INSTANCE("'+name+r'")) \2 (', 'tile instance '+name)
        elif len(re.findall(pat, top)) != 1:
            raise ValueError('missing unique tile instance '+name)
        for core in ('a0','a1','a2','a3','b'):
            elem = 'g_cvb.u_eB' if core == 'b' else 'g_cv.u_eA'+core[-1]
            for bank in (0,1):
                bindings.append((name+'.u_core.u_b.'+elem+'.u_m.u_rom'+str(bank)+'.arr', name+core+'_'+str(bank)+'.viamap.hex'))
        names.append(name)
    if not partition_only:
        target = out/'s81_head_top.sv'; target.write_text(top)
        models[models.index(tops[0])] = str(target.relative_to(root))
    # This is the already-qualified HEAD link profile used by mesh_ep_bench
    # and head_host_ctl_bench, not an unqualified default linker branch.
    defines = ['OT_COLL_NATIVE32', 'OT_COLL_NATIVE32_OFF']
    include_dirs = sorted({str(Path(s).parent) for s in models})
    (out/'native.f').write_text('\n'.join(['+define+'+d for d in defines]+['+incdir+'+d for d in include_dirs]+models)+'\n')
    image_names = [name+core+'_'+str(bank)+'.viamap.hex' for name in names for core in ('a0','a1','a2','a3','b') for bank in (0,1)]
    scope_images = []
    for path, _ in bindings:
        part, rest = path.split('.',1)
        scope_images.append('s81_head_top.'+part+'.'+(wrapper+'.' if hierarchical else '')+rest[:-4]+'.viamap.hex')
    report = dict(schema='opentallas.head.native_sources.v1', replacements=aliases,
        defines=defines, include_dirs=include_dirs, tile_content=content, infra_ports_per_tile=len(tile.get('infra_ports', [])), tile_instances=len(names), required_weight_images=image_names,
        unique_weight_images=len(set(image_names)), rom_load=rom_load, hierarchical=hierarchical, image_bindings=bindings, required_scope_images=scope_images if rom_load == 'scope' else [], added_cycles=0,
        generated_die_top=not partition_only, image_inventory_scope='plan partitions', vehicle='hd_tile_partition' if partition_only else 'die_source', source_sha256={s: hashlib.sha256((root/s).read_bytes()).hexdigest() for s in models},
        qualification='source staging only; current physical-view equivalence, boot schedule and real numerical token execution pending')
    (out/'source_contract.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan',type=Path); ap.add_argument('manifest',type=Path); ap.add_argument('out',type=Path)
    ap.add_argument('--rom-load',choices=['parameters','scope'],default='parameters')
    ap.add_argument('--hierarchical',action='store_true')
    ap.add_argument('--partition-only',action='store_true',help='Stage the real tile wrapper without generating or inventing a die top/provider')
    a=ap.parse_args(); root=Path.cwd()
    report=prepare(root, a.plan, a.manifest, a.out, a.rom_load, a.hierarchical, a.partition_only)
    print('HEAD_NATIVE_SOURCES tiles=%d unique_images=%d cycles_added=0' % (report['tile_instances'],report['unique_weight_images']))
if __name__=='__main__':main()

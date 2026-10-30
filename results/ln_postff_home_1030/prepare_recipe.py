"""Prepare ONLY the exact LN NST private G1 recipe; this never runs EDA.

Invocation authorizes writes to the caller's own copied kit. Root geometry/source
review and explicit one-G1 authority are required separately. No CTS/GRT/STA.
"""
import argparse,gzip,hashlib,json,re,shutil
from pathlib import Path

# Exact preexisting phase4 physical recipes, commit6577522.
RECIPE_SHA={'ln_pregpl.tcl': '5c3a4b8ecdaef8d665863445354455da58b297ff0b092a204010162ba8d82f37', 'face_flops_release.tcl': '5a63c10bfb17600847d692ca95deb78c0754b1ec9735eada46d3c7fbcc83f87d'}

def tq(v):
    return '"'+str(v).replace('\\','\\\\').replace('"','\\"').replace('$','\\$').replace('[','\\[').replace(']','\\]')+'"'

def read_packet(path):
    d=json.loads(gzip.decompress(path.read_bytes()))
    if d.get('schema')!='opentallas.ln_postff_home.v1' or d.get('outline_um')!=[112.32,112.32] or len(d['native_ffs'])!=8386 or len(d['targets'])!=109:
        raise ValueError('exact reviewed LN NST cohort required')
    if len({r['name'] for r in d['native_ffs']})!=8386 or len({r['name'] for r in d['targets']})!=109:
        raise ValueError('aliased native inventory')
    ff={r['name'] for r in d['native_ffs']}
    if any(r['name'] in ff or not re.match(r'^(BUF|INV)x',r['master']) or any(o['ff'] not in ff for o in r['owners']) for r in d['targets']):
        raise ValueError('post-FF-only ownership required')
    return d

def data(d):
    lines=['set ::ln_pf_ffs {}','set ::ln_pf_targets {}']
    for r in d['native_ffs']:
        vals=[r['master'],r['orient'],*r['rect_dbu'],r['clock_root']]
        lines.append('dict set ::ln_pf_ffs '+tq(r['name'])+' [list '+' '.join(tq(v) for v in vals)+']')
    for r in d['targets']:
        p=r['placement'];x,y=[round(v*1000) for v in p['origin_um']];w,h=[round(v*1000) for v in p['size_um']]
        vals=[r['master'],p['orient'],x,y,x+w,y+h,r['physical_group']]
        owners='[list '+' '.join('[list '+tq(o['ff'])+' '+tq(o['port'])+']' for o in r['owners'])+']'
        lines.append('dict set ::ln_pf_targets '+tq(r['name'])+' [list '+' '.join(tq(v) for v in vals)+' '+owners+']')
    return '\n'.join(lines)+'\n'

def family_hook(d):
    families=set()
    for r in d['native_ffs']:
        m=r['master']
        if not re.fullmatch(r'DFF[A-Za-z0-9_]*x[0-9][A-Za-z0-9]*_ASAP7_75t_[RL]',m):raise ValueError('unsupported native FF family')
        families.add(re.sub(r'x[0-9][0-9A-Za-z]*(_ASAP7_.*)$',r'x*\1',m))
    return '# Same process-local whole-family mechanism as c87cfe541; no FF DNT/SYNTH change.\nif {![info exists ::env(DONT_USE_CELLS)]} {set ::env(DONT_USE_CELLS) {}}\nforeach f [list '+' '.join(tq(f) for f in sorted(families))+'] {if {$f ni $::env(DONT_USE_CELLS)} {lappend ::env(DONT_USE_CELLS) $f}}\n'

def install(kit,packet):
    d=read_packet(packet);base=Path(__file__).parent
    texts={name:(kit/name).read_text() for name in ['ln_pregpl.tcl','face_flops_release.tcl','face_flops.tcl','config.mk']}
    for name,sha in RECIPE_SHA.items():
        if hashlib.sha256(texts[name].encode()).hexdigest()!=sha:raise ValueError('unknown existing phase4 recipe '+name)
    if 'source /work/ln_pregpl.tcl' not in texts['face_flops.tcl'] or 'ln_phase4_portbuffer_affinity' not in texts['ln_pregpl.tcl']:
        raise ValueError('exact before-GPL phase4 hook required')
    if 'LN_POSTFF_' in texts['ln_pregpl.tcl'] or (kit/'ln_postff_data.tcl').exists():raise ValueError('preserve prior preparation; choose a new copied kit')
    chains={}
    for key in ['PRE_RESIZE_TCL','POST_DETAIL_PLACE_TCL']:
        previous=re.findall(r'^export\s+'+key+r'\s*=\s*(\S+)\s*$',texts['config.mk'],re.M)
        if len(previous)>1 or (previous and not previous[0].startswith('/work/')):raise ValueError('unknown existing hook owner '+key)
        if previous and not (kit/previous[0][6:]).is_file():raise ValueError('missing chained hook '+key)
        chains[key]=previous[0] if previous else None
    # All preconditions checked. Data contains exact nativeFFs, no fabricated FT slots.
    (kit/'ln_postff_data.tcl').write_text(data(d));shutil.copyfile(base/'ln_postff_home.tcl',kit/'ln_postff_home.tcl')
    (kit/'ln_ff_family_preserve.tcl').write_text(family_hook(d))
    (kit/'ln_pregpl.tcl').write_text(texts['ln_pregpl.tcl']+'''\n# LN_POSTFF exact native physical ownership after buffer_ports / prior affinity.
source /work/ln_postff_home.tcl
source /work/ln_ff_family_preserve.tcl
rename ln_phase4_portbuffer_affinity ln_phase4_portbuffer_affinity_base
proc ln_phase4_portbuffer_affinity {command op} {
 ln_phase4_portbuffer_affinity_base $command $op
 ln_postff_prepare
}
''')
    (kit/'face_flops_release.tcl').write_text(texts['face_flops_release.tcl']+'\nsource /work/ln_postff_home.tcl\nln_postff_prepare\n')
    for key,file,tail in [('PRE_RESIZE_TCL','ln_postff_pre_resize.tcl','source /work/ln_ff_family_preserve.tcl\n'),('POST_DETAIL_PLACE_TCL','ln_postff_post_detail.tcl','source /work/ln_postff_home.tcl\nln_postff_verify\n')]:
        body=('source '+chains[key]+'\n' if chains[key] else '')+tail;(kit/file).write_text(body)
        texts['config.mk']+='\nexport '+key+' = /work/'+file+'\n'
    (kit/'config.mk').write_text(texts['config.mk'])
    (kit/'LN_POSTFF_PREPARED.json').write_text(json.dumps(dict(authority='G1_ONLY_AFTER_ROOT_REVIEW_NO_CTS_STA_GRT_ROUTE',source_packet_sha256=hashlib.sha256(packet.read_bytes()).hexdigest(),all8386FFfixed=True,postFF_BUF_INV=109),indent=2)+'\n')

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('copied_kit',type=Path);a.add_argument('--packet',type=Path,default=Path(__file__).with_name('native_candidate.json.gz'));x=a.parse_args();install(x.copied_kit,x.packet)

#!/usr/bin/env python3
"""Prepare exact mapped-instance physical hooks. Never launches a build.

Inputs are the selected full-shape mapped Yosys JSON and actual macro placement
inventory. No guessed cell area or broad ROM timing exceptions are accepted.
"""
import argparse, collections, hashlib, json, pathlib, re, sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from hbrom_floorplan import check_rectangles, lef

def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def quote(s):
    if any(c in s for c in '{}\n\r'): raise ValueError('Unsupported Tcl identifier '+s)
    return '{'+s+'}'
def mapped_flatten(design, top):
    """Resolve kept hierarchy into actual hierarchical instances and shared net IDs."""
    modules=design['modules']; result={'cells':{},'netnames':{}}; nextbit=[1]
    def visit(typ,prefix,ports):
        mod=modules[typ]; mapping={}
        for pn,bits in ports.items():
            for b,v in zip(mod['ports'][pn]['bits'],bits):
                if isinstance(b,int):mapping[b]=v
        def bind(b):
            if not isinstance(b,int):return b
            if b not in mapping:mapping[b]=nextbit[0];nextbit[0]+=1
            return mapping[b]
        for n,v in mod.get('netnames',{}).items():result['netnames'][prefix+n]=dict(v,bits=[bind(b) for b in v['bits']])
        for n,c in mod['cells'].items():
            con={p:[bind(b) for b in bs] for p,bs in c['connections'].items()}; child=modules.get(c['type'])
            black=child and str(child.get('attributes',{}).get('blackbox','0')).strip('0')
            if child and not black:visit(c['type'],prefix+n+'.',con)
            else:result['cells'][prefix+n]=dict(c,connections=con)
    visit(top,'',{});return result

def prepare(net, top, layout, out):
    design=json.loads(net.read_text()); mod=mapped_flatten(design,top); cells=mod['cells']
    spec=json.loads(layout.read_text()); macros=spec['macros']; names={m['instance'] for m in macros}
    actual={n for n,c in cells.items() if c['type'].startswith(('ot_rom_','ot_sram_'))}
    if actual!=names: raise ValueError('Exact macro census mismatch: '+str({'missing':sorted(actual-names),'extra':sorted(names-actual)}))
    if len(names)!=len(macros): raise ValueError('Duplicate placement instance')
    rom=[m for m in macros if cells[m['instance']]['type'].startswith('ot_rom_')]
    if len(rom)!=256*spec['tiles'] or spec['tiles'] not in (1,4): raise ValueError('Full selected 128-pair shape required')
    rects=[]; views={}
    for m in macros:
        name=m['instance']; master=cells[name]['type']; directory=ROOT/m['view']; geo=lef(directory/(master+'.lef'))
        for suffix in ('.lef','_ss.lib','_ff.lib','_bb.v'):
            p=directory/(master+suffix)
            if not p.is_file(): raise ValueError('Missing real macro view '+str(p))
            views[str(p.relative_to(ROOT))]=sha(p)
        if m.get('orient','R0') not in ('R0','MX','MY','R180'): raise ValueError('Unqualified macro rotation')
        rects.append(dict(name=name,x=m['x'],y=m['y'],w=geo['width'],h=geo['height']))
    errs=check_rectangles(rects,spec['die_um'])
    if errs: raise ValueError('; '.join(errs[:20]))
    # Named capture storage Q bits identify actual FF endpoints after mapping.
    capture_bits=set(); capture_identity={}; capture_words={}
    for n,v in mod['netnames'].items():
        match=re.fullmatch(r'(.*)feed\.captured\[(\d+)\]',n)
        if not match:continue
        prefix,index=match.groups(); expected=f'{prefix}g_rom[{index}].u_rom'
        offset=v.get('offset',0)
        indices={}
        for i,bit in enumerate(v['bits'],offset):
            if isinstance(bit,int):
                identity=(expected,i)
                if bit in capture_identity and capture_identity[bit]!=identity:
                    raise ValueError('Aliased capture bit identity '+n)
                capture_identity[bit]=identity;capture_bits.add(bit);indices[i]=bit
        if not set(range(272)).issubset(indices):
            raise ValueError('Missing meaningful capture bit in '+n)
        if not set(indices).issubset(range(274)):raise ValueError('Invalid capture bit index '+n)
        capture_words[expected]=sorted(indices)
    q_to_cap={}
    for n,c in cells.items():
        if 'DFF' not in c['type']: continue
        if len(c['connections'].get('D',[]))!=1: continue
        for p,bs in c['connections'].items():
            if c.get('port_directions',{}).get(p)=='output':
                for b in bs:
                    if b in capture_bits:q_to_cap[b]=(n,'D')
    if len(q_to_cap)!=len(capture_bits) or not capture_bits: raise ValueError('Capture Q netnames not fully resolved to mapped DFFs')
    # Backward combinational connectivity proves each exception starts at ROM.
    drivers={}
    for n,c in cells.items():
        for p,bs in c['connections'].items():
            if c.get('port_directions',{}).get(p)=='output':
                for i,b in enumerate(bs):
                    if isinstance(b,int):drivers[b]=(n,p,i)
    def origins(bit,seen):
        if not isinstance(bit,int) or bit in seen:return set()
        seen=seen|{bit}; d=drivers.get(bit)
        if not d:return set()
        n,p,i=d;c=cells[n]
        if n in actual:return {(n,p,i)} if c['type'].startswith('ot_rom_') and p=='rd_out' else set()
        if 'DFF' in c['type']:return set()
        return set().union(*(origins(b,seen) for ip,bs in c['connections'].items() if c.get('port_directions',{}).get(ip)=='input' for b in bs))
    caps=collections.defaultdict(list)
    for qbit,(n,p) in q_to_cap.items():
        src=origins(cells[n]['connections'][p][0],set())
        if len(src)!=1:raise ValueError('Capture has missing or multiple ROM sources '+n+str(src))
        origin=next(iter(src))
        if (origin[0],origin[2])!=capture_identity[qbit]:
            raise ValueError('Capture bit has wrong ROM/bit origin '+n+str(origin))
        caps[origin[0]].append(n+'/'+p)
    if set(caps)!={m['instance'] for m in rom}:raise ValueError('ROM capture coverage incomplete')
    if set(capture_words)!=set(caps):raise ValueError('Capture word identity coverage incomplete')
    if out.exists():raise ValueError('Refusing to overwrite campaign preparation')
    out.mkdir(parents=True)
    t=['source /src/physical/common/ot_macro_track_snap.tcl','set block [ord::get_db_block]','set found [dict create]','foreach i [$block getInsts] {dict set found [$i getName] $i}']
    for m in macros:
        n=quote(m['instance']);t += [f'if {{![dict exists $found {n}]}} {{error "Missing selected macro"}}',f'ot_mts::place [dict get $found {n}] {m["x"]} {m["y"]} {m.get("orient","R0")} FIRM']
    t += ['ot_mts::assert_on_track -label HBROM_ACTUAL_MACROS']
    (out/'macro_place.tcl').write_text('\n'.join(t)+'\n')
    s=['# Two-cycle data capture only; every selector/control/compute path remains single-cycle.','set byname [dict create]','foreach c [get_cells -hierarchical *] {dict set byname [get_full_name $c] $c}']
    for name,ends in sorted(caps.items()):
        s += [f'set rn {quote(name)}','if {![dict exists $byname $rn]} {error "Missing actual ROM"}','set data {}','foreach p [get_pins -of_objects [dict get $byname $rn]] {if {[string match */rd_out* [get_full_name $p]]} {lappend data $p}}',f'set endpoint_names {{{" ".join(quote(e) for e in sorted(ends))}}}','set endpoints {}','foreach en $endpoint_names {set slash [string last / $en]; set cn [string range $en 0 $slash-1]; if {![dict exists $byname $cn]} {error "Missing actual capture"}; foreach p [get_pins -of_objects [dict get $byname $cn]] {if {[get_full_name $p] eq $en} {lappend endpoints $p}}}',f'if {{[llength $data] !=274 || [llength $endpoints] !={len(ends)}}} {{error "ROM/capture timing census mismatch"}}','set_multicycle_path -setup 2 -through $data -to $endpoints','set_multicycle_path -hold 1 -through $data -to $endpoints']
    (out/'capture.sdc').write_text('\n'.join(s)+'\n')
    record=dict(schema='hbrom.context.physical.preparation.v1',top=top,tiles=spec['tiles'],mapped_json_sha256=sha(net),placement_sha256=sha(layout),macro_views=views,macro_count=len(macros),rom_count=len(rom),capture_count=sum(map(len,caps.values())),meaningful_capture_count=272*len(rom),padding_capture_count=sum(map(len,caps.values()))-272*len(rom),capture_word_bit_inventory=capture_words,meaningful_bit_contract='FP4 codes0:127,136:263 and scales128:135,264:271; FP8 codes0:255 scale256:263; BF16 bits0:255; union0:271; padding272:273 may optimize away',die_um=spec['die_um'],status='PREPARED_NOT_LAUNCHED',physical_closure=False,source_scope=spec['scope'],requirements=['source-pinned meaningful functional pass','actual mapped cell area and full macro inventory in selected floorplan','ROM capture flop placement and mux/return locality','measured fleet admission before remote launch','contextual SS833.333ps setup60ps FFhold25ps','real PG/CTS/OBS/hub restricted-layer route; zero overflow and DRC'],hooks={p.name:sha(p) for p in out.iterdir()})
    (out/'record.json').write_text(json.dumps(record,indent=2)+'\n');return record

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--mapped-json',type=pathlib.Path,required=True);a.add_argument('--top',required=True);a.add_argument('--placement',type=pathlib.Path,required=True);a.add_argument('--out',type=pathlib.Path,required=True);v=a.parse_args();print(json.dumps(prepare(v.mapped_json,v.top,v.placement,v.out),indent=2))
if __name__=='__main__':main()

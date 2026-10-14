#!/usr/bin/env python3
"""Actual native IDX glue census with source-exact closed-leaf ABI boundary."""
import argparse,collections,hashlib,json,re,subprocess
from pathlib import Path
def number(value):
    return int(value, 2) if isinstance(value, str) else int(value)


def census(path, top):
    mods = json.loads(path.read_text())['modules']
    roots = collections.Counter()
    rows, macros, unsupported = [], [], []

    def walk(name, scope, incoming):
        m = mods[name]
        resolve = lambda b: incoming.get(b, scope + ':' + str(b)) if isinstance(b, int) else str(b)
        row = {'instance': scope, 'module': name, 'local_ff_bits': 0,
               'local_memories': [], 'clock_ff_bits': collections.Counter()}
        for cname, c in m.get('cells', {}).items():
            typ, conn = c['type'], c.get('connections', {})
            if typ in mods and not number(mods[typ].get('attributes', {}).get('blackbox', 0)):
                imap = {}
                for pname, port in mods[typ].get('ports', {}).items():
                    for cb, pb in zip(port['bits'], conn.get(pname, [])):
                        if isinstance(cb, int):
                            imap[cb] = resolve(pb)
                walk(typ, scope + '/' + cname, imap)
            elif typ in mods:
                macros.append({'instance': scope + '/' + cname, 'type': typ,
                               'clock': [resolve(b) for b in conn.get('clk', [])]})
            elif typ.startswith('$mem'):
                p = c['parameters']
                if typ == '$mem_v2':
                    row['local_memories'].append({'name': cname, 'bits': number(p['WIDTH']) * number(p['SIZE']),
                                                 'width': number(p['WIDTH']), 'words': number(p['SIZE']),
                                                 'write_clocks': [resolve(b) for b in conn.get('WR_CLK', [])]})
            elif ('ff' in typ.lower() or typ.startswith('$_DFF')) and 'Q' in conn:
                clk = conn.get('CLK', conn.get('C', []))
                if len(clk) != 1:
                    unsupported.append({'instance': scope + '/' + cname, 'type': typ, 'clock_bits': clk})
                    continue
                width = len(conn['Q'])
                key = resolve(clk[0])
                row['local_ff_bits'] += width
                row['clock_ff_bits'][key] += width
                roots[key] += width
            elif 'latch' in typ.lower():
                unsupported.append({'instance': scope + '/' + cname, 'type': typ})
        row['clock_ff_bits'] = dict(row['clock_ff_bits'])
        rows.append(row)

    walk(top, top, {b: pname if len(p['bits']) == 1 else '%s[%d]' % (pname, i)
                   for pname, p in mods[top]['ports'].items() for i, b in enumerate(p['bits'])})
    return {'total_generic_ff_bits': sum(roots.values()), 'clock_ff_bits': dict(roots),
            'instances': rows, 'blackbox_macros': macros, 'unsupported_state': unsupported}


def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 source=Path('rtl/hdc/v41x/ot_hdc_v41x_idx_hslice.sv').read_text()
 # Preserve exact declarations/defaults/ports; skip body only for glue census.
 end=source.index(');',source.index('module ot_hdc_v41x_idx_hslice'))+2
 macro=source[source.index('module ot_hdc_v41x_idx_hslice'):end]+'\nendmodule\n'
 macro='(* blackbox *) '+macro
 (a.out/'hslice_abi.sv').write_text(macro)
 src=['rtl/hdc/v41x/ot_hbm_idx_owned_native.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv','rtl/hdc/ot_hdc_delay.sv','rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_prefix.sv','rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/lib/ot_rst_relay.sv']
 # Fixed full-native die NS16 without top-chparam parameter cache reprocessing.
 profile=Path(src[0]).read_text().replace('parameter integer NS=4,MUT=0','parameter integer NS=16,MUT=0')
 (a.out/'owned_profile.sv').write_text(profile)
 ys='read_verilog -defer -sv -D SYNTHESIS '+str(a.out/'owned_profile.sv')+' '+' '.join(src[1:])+'\nread_verilog -lib -sv '+str(a.out/'hslice_abi.sv')+'\nhierarchy -check -top ot_hbm_idx_array_owned_native\nproc\nopt\nmemory_dff\nmemory_collect\nopt_clean\nwrite_json '+str(a.out/'retained.json')+'\nmemory_map\nopt\nwrite_json '+str(a.out/'mapped.json')+'\n'
 (a.out/'census.ys').write_text(ys)
 with (a.out/'yosys.log').open('w') as f:
  r=subprocess.run([str(Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'),'-s',str(a.out/'census.ys')],stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:raise SystemExit(r.returncode)
 result=census(a.out/'mapped.json','ot_hbm_idx_array_owned_native')
 x={'source_sha256':{f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in src+['rtl/hdc/v41x/ot_hdc_v41x_idx_hslice.sv']},'profile':'NS16/NK4/IH32/NB4/FPL7/FML5/QL5','mapped_glue':result,'closed_leaf_macro_count':len(result['blackbox_macros']),'closed_leaf_measured_ff_sinks_each':15334,'macro_glue_combined_sink_count_scope':'Separate source-glue generic FF bits and measured closed standalone hslice sinks; no fullcellmapping or CTS','physical_qualified':False,'slots_assigned':False}
 (a.out/'receipt.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({'glue_ff_bits':result['total_generic_ff_bits'],'macros':len(result['blackbox_macros']),'roots':result['clock_ff_bits']}))
if __name__=='__main__':main()

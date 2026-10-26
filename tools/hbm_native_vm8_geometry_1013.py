#!/usr/bin/env python3
"""Import the current VM8 union's actual packed-range geometry, without a native wiring claim."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE='results/physical/vm8_codex_1013/candidate_geometry.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(out):
    d=json.loads((ROOT/SOURCE).read_text());children=[]
    for instance,row in d['instances'].items():
        master=row['master'];accepted=master=='vm_cp_slice2'
        base=f'physical/ref_tile/{master}/views/{master}'
        # Only slice2 has a source-selected accepted export. Other historical
        # views must not become native placeholders for the proposed M5 kits.
        children.append(dict(instance=instance,logical_module=master,xy_um=[row['x'],row['y']],
            w_um=row['w'],h_um=row['h'],orientation=row['orient'],
            geometry_source=row['geometry_source'],view_lef=base+'/'+master+'.lef' if accepted else None,
            view_lib={c:base+'/'+master+'_'+c+'.lib' for c in ['tt','ff','ss']} if accepted else {},
            pg_top='M7' if accepted else None,closure_status='ACCEPTED_SOURCE_VIEW_NATIVE_JOIN_OPEN' if accepted else 'OPEN_PROPOSED_NATIVE_M5_KIT',
            native_pin_binding_closed=False))
    rec=dict(schema='opentallas.hbm.native_geometry_component.v1',component='vm8_union',
        logical_module='hfd_vm_cp',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        geometry_source=SOURCE,geometry_source_sha256=sha(ROOT/SOURCE),outline_um=d['region'],children=children,
        packed_range_hops=d['hops'],hop_endpoint_failures=d['hops_endpoint_above500'],
        native_functional_bindings_valid=False,hard_parent_created=False,closed=False,
        unresolved=['The legacy CP root drops owner192 and shifts ACK through cfg: it is not the native typed owner/ACK join.',
                    'Root checker9, concurrent VM8 service and retained native producer require explicit composed bindings.',
                    'Packed-range endpoint <=496.8um is planning proof; exact per-bit route/PG/OBS/export gates remain open.',
                    '25 total tiles/19 unique kits is one union region across four logical quarter views.'])
    out.mkdir(parents=True,exist_ok=True);(out/'geometry_component.json').write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps(dict(children=len(children),real_lef=sum(bool(c['view_lef']) for c in children),outline=d['region'],native_join_closed=False)))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT/'results/arch/hbm_native_1013/vm8');main(p.parse_args().out)

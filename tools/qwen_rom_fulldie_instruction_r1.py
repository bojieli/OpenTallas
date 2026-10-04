"""Default-off, additive two-beat source projection into the full-die context.

Preserves the original generator and active case inputs. This prepares a source
projection only: actual system caller/drain and hotspot relief must be reviewed
before routing. Never launches OpenROAD or installs a fake numerical provider.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import qwen_rom_fulldie as original
import qwen_rom_fulldie_pg_r3 as PG
from uarch_model_qwen_instruction_transport_r1 import price

ROOT=Path(__file__).resolve().parents[1]

def selected_model(enabled=False):
    if not enabled:raise ValueError('two-beat instruction transport is default off')
    # Isolated module namespace; preserve globals used by historical generators.
    spec=importlib.util.spec_from_file_location('qwen_fulldie_instruction_private',original.__file__)
    variant=importlib.util.module_from_spec(spec);spec.loader.exec_module(variant)
    variant.CORRIDOR_BITS=451
    variant.TAP_BITS=325
    # Account the prepared PG pitch's real rounded coverage in GRT capacity.
    # Historical percentages are not valid for the additive bump-aligned grid.
    variant.REGION_PG={r:(.48/PG.bump_pitch(c,90) if c else 0.) for r,c in original.REGION_PG.items()}
    model=variant.build(tree_mode='banded')
    return variant,model

def prepare(work,enabled=False):
    variant,model=selected_model(enabled)
    work=Path(work)
    if work.exists() and any(work.iterdir()):raise ValueError('refuse existing evidence output')
    work.mkdir(parents=True,exist_ok=True)
    grt=work/'k16';real=work/'real_pg'
    variant.case_grt(model,grt,16,'selected_instruction_r1',iters=5)
    variant.case_real(model,real)
    # Use the new source-width masters, not the old 637-bit PG preparation.
    masters=variant.masters(model,1);widths=variant.port_widths(model,1)
    parts=[PG.powered_lef(m,1,{p:widths.get((name,p),0) for p in m.order})[0] for name,m in masters.items()]
    (real/'elements.lef').write_text('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n'+'\n'.join(parts)+'END LIBRARY\n')
    pdn=PG.write_pdn(real/'pdn.tcl',model,90)
    (real/'run_pg.tcl').write_text('read_db /work/floorplan.odb\nsource /work/pdn.tcl\npdngen\nwrite_db /work/pdn.odb\nputs {OT_SELECTED_PDN_GENERATED_NOT_IR_PASS}\n')
    pins=['rtl/qwen_sys/ot_qwen_w12_instruction_transport_r1.sv','rtl/qwen_sys/ot_qwen_w12_instruction_tile_adapter_r1.sv','rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',
      'tools/uarch_model_qwen_instruction_transport_r1.py','tools/qwen_rom_fulldie_instruction_r1.py',
      'tools/qwen_rom_fulldie.py','tools/qwen_rom_fulldie_pg_r3.py','rtl/hdc/ot_qwen_me_array_w12.sv','rtl/hdc/ot_qwen_rom_tile_w12.sv']
    record=dict(schema='QWEN_FULLDIE_SELECTED_INSTRUCTION_PREPARATION_R1',default_off=True,model=price(),
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in pins},
      instances=len(model['insts']),area_mm2=model['die']['mm2'],hard_reticle_mm2=858,
      selected_bus_bits={cl:sorted({bits for _,c,bits,_ in model['buses'] if c==cl}) for cl in ['corridor','head_chain','tap','link_spine']},
      pdn_metadata=pdn,pg_capacity_per_net=variant.REGION_PG,
      pg_reservation_scope='prospective rounded-pitch capacity; actual full-die PDN/IR and macro grid overlap remain unqualified',
      run_admitted=False,system_caller_installed=False,
      mandatory_prerequisites=['Laplace exact W12 caller packing, accept/consumer retirement and all-copy warm drain source join',
        'Three-way head-chain/north/south broadcast acceptance ledger and explicit serializer/receiver physical endpoints; local tile adapter alone does not narrow a global net',
        'Real tile issue/x and top tag latency updated together; no ready-only retirement',
        'Source source-map proof candidate removes chosen congested-edge demand; unchanged link_spine remains 2112 bits',
        'Full-die actual PG sources/load and IR results; M9 reservation computed from generated grid, not old percentage',
        'Guarded aligned macro launch and complete actual instance census'],
      qualification=dict(numerical_full_system=False,changed_source_route=False,full_die_IR=False,SSFF=False),
      generated_sha256={str(p.relative_to(work)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(work.rglob('*')) if p.is_file()})
    (work/'preparation.json').write_text(json.dumps(record,indent=2)+'\n')
    return record

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',required=True,type=Path);p.add_argument('--enable-two-beat',action='store_true')
    a=p.parse_args();r=prepare(a.work,a.enable_two_beat)
    print(json.dumps({k:r[k] for k in ['area_mm2','selected_bus_bits','run_admitted','system_caller_installed']}))

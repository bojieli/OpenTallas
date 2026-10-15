#!/usr/bin/env python3
"""DVM leaf/tile identity; historical field coordinates are not new placement admission."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from qwen_split.compute_spine import ref_tile_id

def build(model):
    insts={i['n']:i for i in model['insts']};rows=[];tiles=[]
    for c in range(48):
        order=list(range(8,16))+list(range(7,-1,-1))
        for h in range(2):
            for j in range(4):
                selected=[]
                for rw in range(16):
                    lf=(rw>>1)if rw<8 else 4+((7-(rw-8))>>1)
                    tb=(rw&1)if rw<8 else ((7-(rw-8))&1)
                    if lf==4*h+j:
                        r=order[rw];name=f't_{c}_{r}';i=insts[name]
                        selected.append(dict(tile_bit=tb,tile=name,logical_column=c,logical_row=r,
                            reference_id=ref_tile_id(c,r),station=f's_{c}_{r}',historical_master=i['m'],
                            historical_reference_rect_um=[i[k]for k in('x','y','w','h')],actual_new_home=None))
                        tiles.append(name)
                selected.sort(key=lambda x:x['tile_bit'])
                assert [x['logical_row']for x in selected]==[8+2*j,9+2*j]if h==0 else [x['logical_row']for x in selected]==[2*j,2*j+1]
                rows.append(dict(column=c,chain='north'if h==0 else'south',chain_depth=j,
                    parent=f'h_{c}',source_path=f'h_{c}.u_c.g_ch[{h}].g_leaf[{j}].u_leaf',
                    parent_clock_port=f'ck{1+4*h+j}',leaf_clock_pin='clk',tiles=selected,
                    capture_successor=dict(master='qfd_xs_leaf_capture_parent',core_clock='clk',reset='rst_n',
                        banks=[dict(instance=f'u_capture{k}',master='qwen_glue_v514',clock=f'clk_wd{k}',
                            raw_data_bits=[512*k+511,512*k],valid_bit=513,epoch_bit=512,
                            actual_home=None)for k in range(2)],
                        sharing='Each512-bit data half is shared by BOTH logical tile slots; not one bank per tile.',
                        ages='Capture edge1, core store/WO edge2; common reset and compiler release/capture contract must be bound.',
                        extra_root_count=2,source_status='Owner q_dvm candidate; actual core gate pending')))
    assert len(rows)==384 and len(tiles)==768 and len(set(tiles))==768
    return dict(schema='opentallas.qwen.dvm-tile-cohort-map.v1',qualified=False,leaves=rows,
        source_evidence=['ot_qfd_xhead lf/tb in rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv',
            'qfd_xcol u_c.g_ch[h].g_leaf[j] in rtl/qwen_sys/dvm_20261014/ot_qfd_xslice_slots.sv',
            'compute_spine.ref_tile_id and tids order'],
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in [
            'rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv','rtl/qwen_sys/dvm_20261014/ot_qfd_xslice_slots.sv','tools/qwen_split/compute_spine.py']},
        counts=dict(leaves=384,unique_tile_identities=768,capture_banks=768,additional_clock_roots=768),
        limitations=['Coordinates are explicitly historical reference geometry, not actual successor homes or distances.',
            'Any 46-column or tile compression remap must preserve these logical identities and reference IDs.',
            'Two capture banks must feed the actual leaf; proximity to one historical tile alone proves no route timing.',
            'No automatic MY/flip symmetry or native pin/phase/PG qualification inferred.'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    m=json.loads(a.model.read_text());r=build(m);r['reference_model_sha256']=hashlib.sha256(a.model.read_bytes()).hexdigest();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()

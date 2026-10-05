#!/usr/bin/env python3
"""Source selection/emission for the real fullshape combined die (no build/run)."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
def selected(output:Path,near_hbm=False,*,hbm_layers=36):
    if type(hbm_layers) is not int or not 1 <= hbm_layers <= 36:
        raise ValueError('HBM layer extent must be an integer from 1 to 36')
    import qwen_rom_rt_token_w12_rm as baseline
    import qwen_rom_rt_core_emit_w12 as emitter
    output.mkdir(parents=True,exist_ok=True)
    gen=output/'gen';gen.mkdir(exist_ok=True)
    core=gen/'ot_qwen_rom_core.sv';core.write_text(emitter.emit(emitter.CORE.read_text()))
    su=gen/'ot_hdc_vstream_rt.sv';su.write_text(emitter.emit_vstream(emitter.VSTREAM.read_text()))
    combined=ROOT/'rtl/qwen_sys/combined'
    die=[p for p in baseline.DIE_RTL if p.name not in ('ot_qwen_rom_rt_die_w12_rm.sv','ot_qwen_tp_seq_w12.sv')]
    # The HBM ACK model remains available for external four-stack RTL models;
    # no C++ expected-response server is in this source selection.
    die += [core,su,combined/'ot_qwen_rom_combined_die.sv',combined/'ot_qwen_tp_seq_combined.sv',combined/'ot_qwen_combined_hbm_cdc.sv',
            ROOT/'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',ROOT/'rtl/lib/ot_async_fifo.sv',ROOT/'rtl/lib/ot_reset_sync.sv',
            ROOT/'rtl/hdc/nearhbm/ot_qwen_nearhbm_row_sectors.sv',ROOT/'rtl/hdc/nearhbm/ot_qwen_nearhbm_realmem_service.sv']
    if near_hbm:
        die += list((combined/'nearhbm').glob('*.sv'))+[ROOT/p for p in [
            'rtl/test/qwen_sys/ot_qwen_nearhbm_sys_tb_fenced.sv','rtl/qwen_sys/ot_qwen_d2d_link.sv',
            'rtl/link/ot_link_crc32.sv','rtl/test/qwen_sys/ot_qwen_d2d_chan.sv']]
    pkg=ROOT/'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv'
    die=[pkg]+[p for p in dict.fromkeys(die) if p!=pkg];tiles=list(dict.fromkeys(baseline.TILE_RTL));collective=list(dict.fromkeys(baseline.COLL_RTL))
    missing=[str(p) for p in dict.fromkeys(die+tiles+collective) if not p.is_file()]
    if missing:raise FileNotFoundError('Missing selected actual source(s): '+', '.join(missing))
    sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in dict.fromkeys(die+tiles+collective)}
    rec=dict(top='ot_qwen_rom_combined_die',die=list(map(str,die)),tile=list(map(str,tiles)),collective=list(map(str,collective)),
             include=[str(ROOT/'rtl/hdc')],parameters={'G':6144,'SW':64,'NW':18,'SNW':18,'D':4,'REAL_MEM':1,'NPC':32,'NEAR_HBM':int(near_hbm),'ENABLE_AR256':1,'SMIN':7,'SMAX':11,'TCUT':7,'BD':41,'XVM':1,'NWS':5,'TWS':38,'ORD':7,'MEM_EXTRA':1,'SCALE_BANKS':13,'CROM_WORDS':1048576,'HBM_LAYERS':hbm_layers,'EMBED_ROM':1,'FILL_LAT':8,'NRD':256,'LKA':512},
             collective_parameters={'N':4,'LANES':16,'TAGW':44,'DEPTH':1024,'LAT':339,'BPC_NUM':3600},
             tile_parameters={'GT':6144,'NW':18,'SMIN':7,'CODE_BANKS':5,'MEM_EXTRA':1,'KV_VB':131072,'KV_NH':2},source_sha256=sources,
             clocks={'core_service_tile':'clk','HBM':'hclk','reset':'rst_n/hrst_n independently conditioned by actual FIFO'},
             preload_arrays=['vm','prog_mem','desc_mem','crom_mem','crom_words','g_sc (unchanged ROM macro arrays)','embedding (unchanged baseline hierarchy)'],
             hbm='external four ot_qwen_hbm_model_ack per die; TAGW13/NPC32/WR_ACK1/PC_RDY1/CLK_PS agrees hclk',
             observation=['core_start_o','core_done_o','kv_layer_start_o','kv_arm_o','row_drained_o','kv_ok_o','kv_drained_o','mem_fault','kv_fault_code'],
             optional_candidates={'near_hbm':bool(near_hbm),'async_collective':False,'DSpark':False,'stream_controller':False,'clock_C':False},
             scope='source/emission only; combined runtime and physical qualification pending')
    (output/'sources.json').write_text(json.dumps(rec,indent=2)+'\n')
    (output/'die_sources.f').write_text('\n'.join(map(str,die))+'\n')
    return rec
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--near-hbm',action='store_true');p.add_argument('--hbm-layers',type=int,default=36);a=p.parse_args()
    r=selected(a.output,a.near_hbm,hbm_layers=a.hbm_layers);print(json.dumps({'top':r['top'],'sources':str(a.output/'sources.json'),'NEAR_HBM':r['parameters']['NEAR_HBM'],'HBM_LAYERS':r['parameters']['HBM_LAYERS']}))

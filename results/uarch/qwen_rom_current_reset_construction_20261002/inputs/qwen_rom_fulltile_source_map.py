#!/usr/bin/env python3
"""One pinned complete SMIN6 synthesis/map; no engine RTL, CTS, STA or P&R."""
import argparse,gzip,hashlib,json,os,re,resource,shutil,subprocess,time
from pathlib import Path
from uarch_model_qwen_rom_fulltile_slot import price,ROOT
from qwen_rom_hold_capture_loaded_map import merge_scoped,block
TOP='ot_qwen_rom_fulltile_tp4_context_top'
YOSYS='/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys'
SOURCES=['rtl/hdc/'+n+'.sv' for n in ('ot_hdc_delay','ot_hdc_fp32_mul_pipe','ot_hdc_fpu','ot_hdc_sfu','ot_hdc_fastfp','ot_hdc_fp32_add_lat','ot_hdc_prefix','ot_hdc_matvec','ot_qwen_w12_arith','ot_qwen_w12_matvec','ot_qwen_me_array_w12')]+['rtl/proto/ot_fp32_add_rne_pipe.sv','rtl/physical/ot_qwen_rom_bank5_control_distribution.sv','rtl/hdc/ot_qwen_rom_tile_context_candidate_r2.sv','rtl/physical/ot_qwen_rom_fulltile_tp4_context_top.sv']

def execute(command,work,log):
    with log.open('w') as out:
        p=subprocess.Popen(command,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)
        while p.poll() is None:
            disk=sum(f.stat().st_size for f in work.rglob('*') if f.is_file())
            if disk>16*1024**3 or shutil.disk_usage(work).free<64*1024**3:
                p.terminate();p.wait();raise RuntimeError('aggregate disk/headroom guard')
            time.sleep(2)
    if p.returncode:raise RuntimeError('command error '+str(p.returncode)+'; retained '+str(log))


def main(work):
    if work.exists():raise ValueError('refuse duplicate workspace')
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip():raise ValueError('source worktree not clean')
    work.mkdir(parents=True)
    for limit in (resource.RLIMIT_FSIZE,resource.RLIMIT_CPU):resource.setrlimit(limit,(resource.RLIM_INFINITY,resource.RLIM_INFINITY))
    model=price();(work/'model.json').write_text(json.dumps(model,indent=2)+'\n')
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}
    (work/'sourcepins.json').write_text(json.dumps(dict(commit=sha,top=TOP,optin=1,SMIN=6,files=pins),indent=2)+'\n')
    result=dict(status='LIVE_PREPARATION',commit=sha,work=str(work),synthesis_map_only=True,contextual_SSFF=False,tile_PR=False)
    try:
        libdir=work/'libraries';libdir.mkdir()
        # Exact installed image, five actual RVT SS families; no fake FF/RAM.
        shell='for f in /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_SS*; do case "$f" in *FAKE*) continue;; esac; cp "$f" /out/; done'
        execute(['docker','run','--rm','--entrypoint','sh','-v',str(libdir)+':/out','af971398d91e','-c',shell],work,work/'library_copy.log')
        libs=[]
        for f in sorted(libdir.iterdir()):
            if f.suffix=='.gz': p=f.with_suffix('');p.write_bytes(gzip.decompress(f.read_bytes()));libs.append(p)
            else:libs.append(f)
        text,cells,_=merge_scoped(libs);lib=work/'ss_merged.lib';lib.write_text(text)
        pins.update({str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in libs})
        macros=[ROOT/'physical/asap7_memory_macros'/name/(name+'_ss.lib') for name in ('ot_rom_4096x266_m8','ot_sram_1r1w_128x256_m1_r2c2')]
        lines=['read_liberty -lib '+str(lib)]+['read_liberty -lib '+str(p) for p in macros]+['read_verilog -sv -DSYNTHESIS '+' '.join(str(ROOT/p) for p in SOURCES), 'hierarchy -check -top '+TOP+' -chparam CONTROL_CONTEXT_CANDIDATE 1','proc','opt','flatten','opt','write_json '+str(work/'source_proc.json'),'synth -top '+TOP+' -noabc','dfflibmap -liberty '+str(lib),'abc -liberty '+str(lib)+' -D 773.333333','clean','stat -liberty '+str(lib),'write_verilog -noattr '+str(work/'mapped.v'),'write_json '+str(work/'mapped.json')]
        ys=work/'synth.ys';ys.write_text('\n'.join(lines)+'\n')
        (work/'inputpins.json').write_text(json.dumps({**pins,**{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in macros}},indent=2)+'\n')
        result['status']='LIVE_SYNTHESIS_MAP';(work/'status.json').write_text(json.dumps(result,indent=2)+'\n')
        cut=lines.index('write_json '+str(work/'source_proc.json'))+1
        ys.write_text('\n'.join(lines[:cut])+'\n')
        execute([YOSYS,'-T','-Q','-s',str(ys)],work,work/'source_synthesis.log')
        proc=json.loads((work/'source_proc.json').read_text())['modules'][TOP]
        clock_bits=reset_bits=0
        for c in proc['cells'].values():
            if c['type'] in ('$dff','$dffe','$adff','$adffe','$sdff','$sdffe','$sdffce'):
                width=int(c['parameters']['WIDTH'],2);clock_bits+=width
                if c['type'] in ('$adff','$adffe'):reset_bits+=width
        result.update(current_SMIN6_clock_bits_preopt=clock_bits,current_SMIN6_async_reset_bits_preopt=reset_bits)
        (work/'current_source_inventory.json').write_text(json.dumps(result,indent=2)+'\n')
        if clock_bits>model['slot']['source_clock_bit_budget_ceiling'] or reset_bits>model['slot']['source_async_reset_bit_budget_ceiling']:
            raise RuntimeError('current source exceeds explicit inventory budget; mapping not started')
        ys=work/'map.ys';ys.write_text('read_json '+str(work/'source_proc.json')+'\n'+'\n'.join(lines[cut:])+'\n')
        execute([YOSYS,'-T','-Q','-s',str(ys)],work,work/'mapping.log')
        net=json.loads((work/'mapped.json').read_text())['modules'][TOP];counts={};area=0
        for c in net['cells'].values():
            n=c['type'];counts[n]=counts.get(n,0)+1
            if n in cells:area+=float(re.search(r'\barea\s*:\s*([\d.]+)',cells[n])[1])
            elif n not in ('ot_rom_4096x266_m8','ot_sram_1r1w_128x256_m1_r2c2'):raise RuntimeError('unmapped cell '+n)
        if counts.get('ot_rom_4096x266_m8')!=10 or counts.get('ot_sram_1r1w_128x256_m1_r2c2')!=2:raise RuntimeError('incomplete actual macro inventory')
        result.update(mapped_cells=counts,mapped_cell_area_um2=area)
        if area>model['slot']['complete_cell_area_ceiling_um2']:raise RuntimeError('complete mapped cell area exceeds model ceiling')
        result['status']='PASS_COMPLETE_SOURCE_MAP_ONLY_CONTEXT_OPEN'
    except Exception as e:
        result.update(status='FAIL_SOURCE_MAP_RETAINED',error=str(e))
    finally:
        (work/'terminal.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
    return 0 if result['status'].startswith('PASS') else 1

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);a=p.parse_args();raise SystemExit(main(a.work.resolve()))

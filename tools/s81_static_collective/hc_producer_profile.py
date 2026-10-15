#!/usr/bin/env python3
"""Export exact compiled command/tag/HC row edges for a static consumer.

The tag is an explicit compiler identity, never a bit slice of cmd84. Export
only after the complete collective image passes its real reservation checks.
Visible-after-edge events and next-edge receiver samples are distinct. This
profile does not supply missing canonical FIELD/VM/clock/price evidence.
"""
from pathlib import Path
import argparse,hashlib,json
from controller_image import compile_image,command,ABI,CONTROL_BITS,ROM_BITS,LATENCIES

def profile(request,root):
    words=compile_image(request,root)
    jobs=[];active={};rows=[]
    for edge,cycle in enumerate(request['cycles']):
        if cycle['cmd_valid']:
            completion,count,mode=command(cycle['cmd84'])
            item=dict(command_index=len(jobs),command_external_sample_edge=edge,
                command84_hex=f'{cycle["cmd84"]:021x}',completion_tag8=completion,
                transport_tag32=cycle['transport_tag'],records_per_rank=count,
                mode='gather' if mode else 'reduce',consumer=cycle['consumer'],
                hc_row_count=0)
            jobs.append(item);active[cycle['transport_tag']]=item
        ctrl=cycle['controls']
        if ctrl['hc_emit_slot']:
            job=active[ctrl['hc_emit_tag']]
            ordinal=job['hc_row_count'];job['hc_row_count']+=1
            rows.append(dict(command_index=job['command_index'],command84_hex=job['command84_hex'],
                transport_tag32=ctrl['hc_emit_tag'],row_ordinal=ordinal,
                image_control_edge=edge,
                producer_visible_after_edge=edge+2,
                consumer_sample_edge_zero_flight=edge+3,
                payload_bits=8192,fp32_per_row=256,
                tag_meaning='exact compiled transport_tag32; no cmd84 packing'))
    image=''.join(f'{w:0{(ROM_BITS+3)//4}x}\n'for w in words)
    return dict(schema='opentallas.s81.static-hc-producer-profile.v1',collective_image_abi=ABI,
        control_bits=CONTROL_BITS,rom_bits=ROM_BITS,image_sha256=hashlib.sha256(image.encode()).hexdigest(),
        producer_ports=dict(data='t_hc_y[8191:0]',valid='t_hc_yv',tag='t_hc_tag[31:0]'),
        clocks='zero-flight common-epoch component; actual phi-R and interleaf delivery require a priced profile',
        command_to_row_identity='explicit cmd84/transport_tag32 mapping preserved below',
        event_convention='ROM row e -> controller output visible e+1 -> assembler output visible e+2 -> downstream synchronous sample e+3',
        jobs=jobs,rows=rows,latencies=LATENCIES,
        source_evidence=request['evidence'],native_source_binding=request['native_source_binding'],
        canonical_production=False,native_execution=False,
        qualification='compiled producer-consumer identity and edges only; actual canonical sources, receiver and physical bindings remain required')

def main():
    p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=profile(json.loads(a.request.read_text()),a.root)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(jobs=len(result['jobs']),rows=len(result['rows']),image_sha256=result['image_sha256'],canonical_production=False)))
if __name__=='__main__':main()

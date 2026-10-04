#!/usr/bin/env python3
"""Additive full-token host: execute the released head on existing combined RTL."""
import argparse
from pathlib import Path
import qwen_rom_combined_runtime_emit as predecessor

ROOT = Path(__file__).resolve().parents[1]
BASE_EMIT = predecessor.emit
HEAD_ABI = 'combined-head-host-v1'


def emit(root=ROOT):
    src = BASE_EMIT(root)
    def replace(old, new):
        nonlocal src
        if src.count(old) != 1:
            raise ValueError('head source anchor missing/ambiguous: '+old[:80])
        src = src.replace(old, new)
    # Existing Claude REAL_MEM head host uses exactly this no-KV sentinel.
    # It is not L36 and never initializes a fictitious 37th HBM region.
    replace('else fatal("REAL_MEM runs the embedding stage E and decoder-layer stages L<n> only");',
            'else if (st.name == "head") st.layer = -1; // existing no-KV sentinel 255\n'
            '            else fatal("combined head host requires E, L<n>, or head");')
    replace('const bool embed_stage = stages[0].layer < 0;',
            'const bool embed_stage = stages[0].name == "E";')
    # No data/VM reset is introduced at the L35 -> head transition. Existing
    # load_images/preload functions load released head programs and weights;
    # all current-token writes retired through LayerFence before this start.
    replace('        fclose(fp);\n        if (stages.empty()) fatal("no stages");',
            '''        fclose(fp);
        if(stages.size()!=38 || stages.front().name!="E" || stages.back().name!="head")
            fatal("full token requires E, L0..L35, head");
        for(int l=0;l<36;++l)if(stages[l+1].name!="L"+std::to_string(l))
            fatal("full token decoder stage order",l);
        if (stages.empty()) fatal("no stages");''')
    replace('                for (int d = 0; d < D; d++) {\n                    Vdie& v = *die[d];',
            '''                if(stages[cur].name=="head") {
                    // Consume only the sequencer's actual completed gather.
                    // RTL checks rank order and strictly-greater wins; ties
                    // keep the earlier rank/lower row. No host argmax exists.
                    for(int d=0;d<D;++d) {
                        if(die[d]->seq_ntok>=151936)fatal("head token out of vocabulary",d);
                        if(die[d]->seq_ntok!=die[0]->seq_ntok || die[d]->seq_nval!=die[0]->seq_nval)
                            fatal("head collective result differs between ranks",d);
                        printf("HEAD_RANK head die%d next_token=%u next_val=%08x\\n",
                               d,die[d]->seq_ntok,die[d]->seq_nval);
                        FILE* result=fopen((dir+"/head_die"+std::to_string(d)+"_result.hex").c_str(),"w");
                        if(!result)fatal("head result output file",d);
                        fprintf(result,"%08x %08x\\n",die[d]->seq_ntok,die[d]->seq_nval);
                        fclose(result);
                        FILE* norm=fopen((dir+"/head_die"+std::to_string(d)+"_xnorm.hex").c_str(),"w");
                        if(!norm)fatal("head normalized input output file",d);
                        // Released vm_map H=8192; existing oracle records the
                        // identical range (qwen_o4_token_oracle_w12.py).
                        for(int i=0;i<H;++i)fprintf(norm,"%08x\\n",rm_vm(die[d]->rootp)[8192+i]);
                        fclose(norm);
                    }
                }
                for (int d = 0; d < D; d++) {
                    Vdie& v = *die[d];''')
    return '// HEAD_HOST_ABI '+HEAD_ABI+'\n'+src


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    text=emit()
    with args.out.open('x') as output:output.write(text)


if __name__=='__main__':main()

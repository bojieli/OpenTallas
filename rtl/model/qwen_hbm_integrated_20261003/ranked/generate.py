"""Source-derived sibling of the preserved128-total enclosing assembly.

No engine leaf changes. Model must be committed before this generator is used.
The existing checked grant key retains rank; real reverse sender rank is an
independent pin and cannot be reconstructed from the expected grant.
"""
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
BASE=OUT.parent


def replace_once(text, old, new):
    if text.count(old)!=1:raise ValueError('source derivation changed: '+old[:70])
    return text.replace(old,new)


def main():
    model=json.loads((OUT/'model.json').read_text())
    source=BASE/'generate.py'
    expected=model['source_sha256'][str(source.relative_to(ROOT))]
    if hashlib.sha256(source.read_bytes()).hexdigest()!=expected:raise ValueError('priced source changed')
    # Preserve all source-selected leaves/ports/clock. Reuse generator machinery
    # in a sibling output directory and bind each transform to exact old source.
    text=source.read_text()
    text=replace_once(text,'ROOT = Path(__file__).resolve().parents[3]','ROOT = Path(__file__).resolve().parents[4]')
    text=replace_once(text,"128, '.OPT_EXACT(ENABLE),.OPT_RESET_QUARANTINE(ENABLE),.PC_ID(7\\'(i))'", "256, '.OPT_EXACT(ENABLE),.OPT_RESET_QUARANTINE(ENABLE),.PC_ID(7\\'(i%128))'")
    text=replace_once(text,'    joined_kv()','    # Reuse unchanged joined controller source; never generate a second controller.')
    text=replace_once(text,'    instances = []', '''    pins.update({
      'sector_map_rank':dict(direction='input',bits=1,count=1,leaf='map_rank',block='sector'),
      'sector_reverse_rank':dict(direction='input',bits=1,count=1,leaf='reverse_rank',block='sector'),
      'sector_rank_refusal':dict(direction='output',bits=1,count=1,leaf='rank_refusal',block='sector')})
    instances = []''')
    text=replace_once(text, "            if prefix=='kv' and name in shared:", '''            if prefix=='sector' and name in ('alloc_valid','map_valid'):
                expression='rank_checked_'+name
            elif prefix=='sector' and name=='alloc_ready':
                expression='rank_raw_alloc_ready'
            elif prefix=='sector' and name=='reverse_valid':
                expression='rank_checked_reverse_valid'
            elif prefix=='sector' and name=='reverse_ready':
                expression='rank_raw_reverse_ready'
            if prefix=='kv' and name in shared:''')
    text=text.replace('selected_PC*{bits}','selected_index*{bits}')
    text=text.replace('raw_w2_req_rdy[selected_PC*6','raw_w2_req_rdy[selected_index*6')
    text=replace_once(text,'wire [6:0] selected_PC = sector_grant_live ? sector_grant_identity[45:39] : sector_map_PC;','wire [6:0] selected_PC;')
    text=replace_once(text,'wire [767:0] raw_w2_req_rdy', """wire [7:0] selected_index;
wire rank_raw_alloc_ready,rank_raw_reverse_ready;
wire rank_checked_alloc_valid,rank_checked_map_valid,rank_checked_reverse_valid;
ot_gpu_qwen_rank_boundary #(.ENABLE(ENABLE)) rank_boundary(
 .grant_live(sector_grant_live),.grant_identity(sector_grant_identity),
 .alloc_valid(sector_alloc_valid),.map_valid(sector_map_valid),.map_rank(sector_map_rank),
 .alloc_source(sector_alloc_source),.map_PC(sector_map_PC),.raw_alloc_ready(rank_raw_alloc_ready),
 .reverse_valid(sector_reverse_valid),.reverse_rank(sector_reverse_rank),.raw_reverse_ready(rank_raw_reverse_ready),
 .alloc_valid_checked(rank_checked_alloc_valid),.map_valid_checked(rank_checked_map_valid),.alloc_ready(sector_alloc_ready),
 .reverse_valid_checked(rank_checked_reverse_valid),.reverse_ready(sector_reverse_ready),
 .selected_PC(selected_PC),.selected_index(selected_index),.rank_refusal(sector_rank_refusal));
wire [1535:0] raw_w2_req_rdy""")
    text=replace_once(text,'p<128','p<256')
    text=text.replace('selected_PC==p','selected_index==p')
    text=text.replace('ot_gpu_qwen_hbm_integrated', 'ot_gpu_qwen_hbm_integrated_ranked')
    # The dependency list must select sibling top, not a nonexistent old-path renamed file.
    text=text.replace('rtl/model/qwen_hbm_integrated_20261003/ot_gpu_qwen_hbm_integrated_ranked.sv',
                      'rtl/model/qwen_hbm_integrated_20261003/ranked/ot_gpu_qwen_hbm_integrated_ranked.sv')
    text=text.replace('W2_PC_count=128','W2_PC_per_rank=128, W2_total=256')
    text=text.replace('SM=64 W2=128','SM=64 W2=256 RANKS=2 PC_PER_RANK=128')
    ns={'__file__':str(OUT/'generate.py'),'__name__':'ranked_source_derivation'}
    exec(compile(text,str(source),'exec'),ns)
    ns['main']()
    top=OUT/'ot_gpu_qwen_hbm_integrated_ranked.sv'
    sv=top.read_text()
    start=sv.index('for(genvar i=0;i<256;i=i+1) begin:g_w2')
    bank=sv[start:]
    bank=replace_once(bank,'for(genvar i=0;i<256;i=i+1) begin:g_w2',
      'for(genvar rank=0;rank<2;rank=rank+1) begin:g_rank\n for(genvar i=0;i<128;i=i+1) begin:g_w2')
    bank=bank.replace(".PC_ID(7'(i%128))", ".PC_ID(7'(i))")
    bank=bank.replace('[i*','[(rank*128+i)*').replace('[i]','[rank*128+i]')
    bank=replace_once(bank,' end\nendmodule',' end\nend\nendmodule')
    top.write_text(sv[:start]+bank)
    deps=(OUT/'sources.f').read_text().splitlines()
    guard='rtl/model/qwen_hbm_integrated_20261003/ranked/ot_gpu_qwen_rank_boundary.sv'
    deps.insert(len(deps)-1,guard)
    (OUT/'sources.f').write_text('\n'.join(deps)+'\n')
    book=json.loads((OUT/'ports.json').read_text())
    book['source_sha256'][guard]=hashlib.sha256((ROOT/guard).read_bytes()).hexdigest()
    p=str(top.relative_to(ROOT));book['source_sha256'][p]=hashlib.sha256(top.read_bytes()).hexdigest()
    book['derivation_inputs_sha256'][str(source.relative_to(ROOT))]=expected
    book['rank_contract']={'grant_rank_bit':136,'alloc_source_rank_bit':56,
        'inner_PC_bits':7,'bank_select':'rank*128+PC','reverse_sender_rank':'sector_reverse_rank',
        'outer_reverse_bits':81,'rank_refusal':'combinational, no ownership or release credit'}
    book['rank_model_sha256']=hashlib.sha256((OUT/'model.json').read_bytes()).hexdigest()
    book['unresolved'].append('physical outer rank mux/load/RC and real sender rank retained across reverse CDC')
    (OUT/'ports.json').write_text(json.dumps(book,indent=2)+'\n')


if __name__=='__main__':main()

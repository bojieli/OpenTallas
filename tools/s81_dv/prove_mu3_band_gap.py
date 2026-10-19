#!/usr/bin/env python3
"""Bounded source proof of actual MU3 band bits. Does not grant pad exceptions."""
import argparse, hashlib, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
REC = ROOT / 'results/arch/s81_dv_1016/bind_mu3_source_trace_1019/classification.json'

def prove(text):
    block = re.search(r"always @\(\*\) begin\s+snd = \{W\{1'b0\}\};(.*?)end", text, re.S)
    assert block, 'missing explicit zero-initialized snd combinational block'
    expected = [(0,0,"1'b1"),(1,3,'s_kind'),(4,8,'s_hops'),(9,12,'sid_c'),(13,20,"8'd0"),
                (21,36,'s_mask'),(37,39,'s_leaf'),(40,49,'s_row'),(50,51,'s_np'),(52,1075,'pk')]
    got=[]
    for statement in block.group(1).split(';'):
        statement=statement.strip()
        if not statement: continue
        m=re.fullmatch(r'snd\[(\d+)(?:\s*:\s*(\d+)|\s*\+:\s*(\d+))?\]\s*=\s*(.+)',statement)
        assert m, 'unsupported snd assignment'
        n=int(m[1]); lo=int(m[2]) if m[2] else n; hi=n+int(m[3])-1 if m[3] else n
        got.append((lo,hi,m[4]))
    assert got==expected, 'SEND bit ownership changed; no literal-zero proof'
    assert re.search(r'parameter\s+(?:integer\s+)?W\s*=\s*1104',text), 'packet width changed'
    assert "bo_r <= (pk_go && s_dir[3]) ? snd : {W{1'b0}};" in text, 'actual registered bo changed'
    assert 'assign bo = bo_r;' in text, 'bo no longer exact registered packet'
    # Constructive dependency: changing upper pk bit 512 changes actual snd bit 564,
    # while changing lower pk bit 0 changes wired q bit 52. Both are functional.
    def pack(pk): return 1 | (pk << 52)
    assert (pack(0)^pack(1<<512)) == (1<<564)
    assert (pack(0)^pack(1)) == (1<<52)
    return {'literal_zero':[1076,1103], 'functional_upper_payload':[564,1075], 'functional_header':[[1,12],[21,51]], 'reserved_zero_header':[13,20]}

def main():
    r=json.loads(REC.read_text());
    for rel, expected in r['source_sha256'].items():
        assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==expected, 'source identity changed: '+rel
    rel='rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xr.sv'; text=(ROOT/rel).read_text()
    result=prove(text)
    mutants={
      'upper_payload_tie':text.replace('snd[52 +: 1024] = pk;',"snd[52 +: 1024] = 1024'd0;"),
      'top_bit_live':text.replace('snd[52 +: 1024] = pk;','snd[52 +: 1024] = pk; snd[1076] = pk[0];'),
      'truncated_payload':text.replace('snd[52 +: 1024] = pk;','snd[52 +: 512] = pk[511:0];'),
      'bo_bypass':text.replace('assign bo = bo_r;', 'assign bo = snd;')}
    for name,mut in mutants.items():
        assert mut != text, 'mutant did not edit actual source'
        try: prove(mut)
        except AssertionError as e: print('EXPECTED_FAIL',name,str(e))
        else: raise AssertionError('mutant escaped: '+name)
    assert sum(2*x['bits_each'] for x in r['unread_classes'])==1182
    assert r['producer_programme']['selected_slice_SEND_compiled'] is False
    print('CLASSIFIER_PASS',json.dumps(result,sort_keys=True))
    print('RELEASE_FAIL functional unread1110; no selected producer SEND programme; no SM target')
if __name__=='__main__': main()

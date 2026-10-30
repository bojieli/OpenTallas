"""Make every flit() dependency explicit; unchanged Boolean/reset/cycle mapping."""
from pathlib import Path
OLD='''function automatic [279:0] flit(input integer d,input [2:0] tag,input [255:0] data);
        flit={1'b1,gath?2'd3:(tx_result?2'd2:2'd1),qid,gath?qid:tx_dst,
              gath?tx_ttl[d*2+:2]:(tx_result?2'd3:2'd0),MUT_TAG?(tag^3'd1):tag,1'b0,11'b0,data};'''
NEW='''function automatic [279:0] flit(
        input integer d,input [2:0] tag,input [255:0] data,
        input gather_mode,result_mode,input [1:0] source_qid,target_qid,
        input [3:0] ttl_by_direction,input integer tag_mutant
    );
        flit={1'b1,gather_mode?2'd3:(result_mode?2'd2:2'd1),source_qid,gather_mode?source_qid:target_qid,
              gather_mode?ttl_by_direction[d*2+:2]:(result_mode?2'd3:2'd0),tag_mutant?(tag^3'd1):tag,1'b0,11'b0,data};'''
CALL='flit(d,tx_tag,state_tx)';NEWCALL='flit(d,tx_tag,state_tx,gath,tx_result,qid,tx_dst,tx_ttl,MUT_TAG)'
def fix(s):
 assert s.count(OLD)==1 and s.count(CALL)==1
 return s.replace(OLD,NEW).replace(CALL,NEWCALL)
if __name__=='__main__':
 import sys
 for name in sys.argv[1:]:
  p=Path(name);p.write_text(fix(p.read_text()))

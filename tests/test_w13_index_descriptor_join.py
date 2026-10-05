import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w13_index_descriptor_join as M

def test_actual_source_descriptor_payload_join():
    d=M.join();assert len(d['rows'])==8
    assert {r['format'] for r in d['rows']}=={1,2}
    for r in d['rows']:
        assert r['software_bit_exact']
        assert r['writer_and_reader_sector_transfers']==(8 if r['format']==1 else 34)
        assert r['writer_and_reader_port_bytes']==(256 if r['format']==1 else 1088)
        assert r['production_command_count'] is None
        assert r['software_payload_request_length_sectors']==(3 if r['format']==1 else 16)
        assert r['stack_PC_distribution'] is None and r['physical_visible_ACK'] is None
    assert d['physical_admission']=='FAIL_CLOSED' and d['rate_credit']==0

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
import su_bank_clock as S
import transport_gate as G

SOURCE = '''consumer su_SW0 (
 .pg_clk(stream)
);
hbfd_rly_624_EW_tw #(.TW(298)) rf0001_s000_l0 (
 .ck(serial),
 .rs(serial_reset),
 .i({su_SW0__lg_wq[280:0],su_SW0__lg_rq[16:0]}),
 .o(rf0001_s000_l0__o)
);
consumer vmb_SW0 (
 .clk(stream),
 .rst_n(stream_reset),
 .rq0(rf0001_s000_l0__o[16:0]),
 .wq0(rf0001_s000_l0__o[297:17])
);
'''

def test_clock_mutant_and_successor(tmp_path):
    p=tmp_path/'die.v';p.write_text(SOURCE)
    r=S.audit(p)
    assert r['verdict']=='FAIL'
    assert len(r['paths'])==2
    assert len(r['repair_relays'])==1
    p.write_text(S.repaired_source(p,r))
    assert S.audit(p)['verdict']=='PASS'
    # Reset follows the corrected clock domain too.
    assert '.rs(stream_reset)' in p.read_text()
    # Restore the wrong clock: must fail even though nominal stage count is identical.
    p.write_text(p.read_text().replace('.ck(stream)', '.ck(serial)'))
    assert S.audit(p)['verdict']=='FAIL'


def test_packed_valid_bits(tmp_path):
    import coll_transport as C
    p=tmp_path/'die.v';p.write_text(SOURCE)
    i=C.parse_instances(p,{'su_SW0','vmb_SW0'})
    assert S.trace_bit(i,'vmb_SW0','rq0',16)[1]=='su_SW0__lg_rq[16]'
    assert S.trace_bit(i,'vmb_SW0','wq0',280)[1]=='su_SW0__lg_wq[280]'


def test_hier_parameter_defaults(tmp_path):
    p=tmp_path/'die.v'
    p.write_text('ot_hbm_su_static_pgslice_lg_hw0 su_SW0 (\n .pg_clk(stream)\n);\n')
    (tmp_path/'hier_wraps.sv').write_text('module ot_hbm_su_static_pgslice_lg_hw0 #(localparam integer QID = 0, localparam READ_RETURN = 22, localparam WRITE_RETURN = 19) (\n')
    assert G.params(p,{'su_SW0'})['su_SW0']['READ_RETURN']==22
    assert G.params(p,{'su_SW0'})['su_SW0']['WRITE_RETURN']==19

"""Coefficient-service demand differs from encoded operand count."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w11_dsrom_crom_demand as D
I=D.I

def decoded(**fields):return I.decode(I.encode(full_shape=True,unit=I.UNIT_SU,**fields),full_shape=True)
def binding(axis,base,count):return dict(operand=axis,kind='checkpoint_CROM',tensor='fixture',tensor_base=base,tensor_end=base+count)

def test_gamma5120_five_bursts_and_actual_oneport_cost():
 f=decoded(su_nout=1,su_nin=5120,a_si=1,c_src=I.SRC_CLO,c_base=10000,c_si=1,e1=I.E1_MULC,dst=I.DST_VM,o_si=1)
 d=D.demand(f,[binding('c',10000,5120)])
 assert d['emit_bursts']==5 and d['peak_unique_words_per_emit']==1024
 assert d['one_port_cycles_within_emit_dedup']==5120
 assert d['ideal_command_prefetch_cycles']==5120
 assert d['required_values_per_serial_emit_cycle']==1024
 assert d['equivalent_values_per_fast_cycle_at_continuous_serial_emit']==768
 assert d['peak_unique_response_boundary_bits']==65536
 assert d['operand_demands'][0]['unique_address_ranges']==[[10000,15120]]

def test_scalar_reuse_broadcast_needs_buffer():
 f=decoded(su_nout=1,su_nin=5120,a_si=1,b_src=I.SRC_CLO,b_base=77,m1=I.M1_AB,dst=I.DST_VM,o_si=1)
 d=D.demand(f,[binding('b',77,1)])
 assert d['logical_lane_uses']==5120 and d['unique_words_per_command']==1
 assert d['one_port_cycles_within_emit_dedup']==5
 assert d['ideal_command_prefetch_cycles']==1
 assert d['operand_demands'][0]['reuse_factor']==5120

def test_simultaneous_distinct_operands_are_serial_port_conflict():
 f=decoded(su_nout=1,su_nin=4,c_src=I.SRC_CLO,c_base=10,c_si=1,d_src=I.SRC_CLO,d_base=20,d_si=1,sfu=I.SFU_SIGM)
 d=D.demand(f,[binding('c',10,4),binding('d',20,4)])
 assert d['peak_unique_words_per_emit']==8 and d['emit_bursts']==1
 assert d['one_port_cycles_within_emit_dedup']==8

def test_row_stride_and_half_reuse_not_contiguous_guess():
 f=decoded(su_nout=2,su_nin=4,a_so=8,a_si=1,b_src=I.SRC_CLO,b_base=100,b_so=10,b_si=1,b_half=1)
 d=D.demand(f,[binding('b',100,12)])
 assert d['operand_demands'][0]['unique_address_ranges']==[[100,102],[110,112]]
 assert d['logical_lane_uses']==8 and d['unique_words_per_command']==4

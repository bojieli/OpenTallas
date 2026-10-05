"""Verify bounded service arithmetic and incomplete gates, no evaluation."""
import json
from fractions import Fraction
from pathlib import Path
import generate

here=Path(__file__).resolve().parent
x=json.loads((here/'partial_price.json').read_text())
assert x==generate.generate()
hc=x['hc_partial_price']; ports=x['ports']
assert hc['coefficient_bytes_all_ranks_token']==15099494400
assert hc['operator_issue_cycles_serial_domain']==2000
assert hc['operator_tail_cycles_serial_domain']==69
ns=Fraction(960*833,1000)+Fraction(2069*1000000000,900000000)
assert abs(hc['no_overlap_ingress_plus_issue_tail_floor_ns']-float(ns))<1e-9
assert abs(hc['per_user_token_80operator_floor_us']-float(ns*80/1000))<1e-9
assert ports['required_coefficient_read_GB_s_per_rank']==921.6
assert ports['required_activation_read_GB_s_per_rank']==460.8
assert ports['hcp_staging_bytes_per_rank']==2007040
assert x['address_policy']['regions_checked']==12768
assert x['address_policy']['sector_bits_candidate']==27
assert x['full_token_latency'] is None
assert x['area_and_routes']['die_slot_fit'] is None
assert not x['adoption'] and not x['physical_build_admitted'] and not x['connected_rate_credit']
assert any('SU N16/LV7' in dep for dep in x['completion_dependencies'])
print('PASS:14 candidate source pins;12768 aligned disjoint candidate regions; independent rational HC phase arithmetic; finite ports/staging counts; SU legality and all incomplete gates retained')

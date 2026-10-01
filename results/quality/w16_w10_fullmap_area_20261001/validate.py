"""Independent decimal area/replica checks; no model sweep or physical flow."""
import json
from decimal import Decimal as D
from pathlib import Path
import generate

here=Path(__file__).resolve().parent
record=json.loads((here/'area_price.json').read_text())
assert record==generate.generate()
a=record['measured_element']; b=record['inherited_baseline']; s=record['scenarios']
assert b['total_column_replicas']==167936
assert b['layer_dies']+b['head_dies']+b['table_dies']==b['total_dies']==208
assert a['distinct_wake_count']==8 and a['physical_rom_count']==4
assert s[0]['required_element_um2']==156937.3
assert abs(s[0]['shortfall_vs_actual_core_um2']-18894.9832)<1e-8
assert abs(s[1]['required_element_um2']-163894.64272)<1e-8
assert abs(s[1]['shortfall_vs_actual_core_um2']-25852.32592)<1e-8
for scenario in s:
    # Independent dimensional identity: area(delta)*copies converts um2->mm2.
    delta=D(str(scenario['shortfall_vs_actual_core_um2']))
    total=delta*D(b['total_column_replicas'])/D(1000000)
    assert abs(float(total)-scenario['core_shortfall_all_164_layer_dies_mm2'])<1e-8
    assert not scenario['fits_actual_core'] and not scenario['fits_even_gross_existing_outline']
assert record['old_sizing_record']['preserved']
assert record['die_impact']['required_total_die_count'] is None
assert not record['physical_admission'] and not record['adopted']
assert not record['die_impact']['rate_credit']
print('PASS: source-bound reproduction; exact decimal area;167936 column replicas; both fixed-area tests fail; historical PASS preserved; no outline/density/rate/adoption changes')

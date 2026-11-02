"""Apply exactly the COORD-approved source event, never a bound/halo waiver."""
import argparse,json,pathlib,copy
ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('output');a=ap.parse_args()
p=json.loads(pathlib.Path(a.input).read_text());tn='col_h10_r0_p1__t1__cl574cc59d';c=p['partition_types'][tn]['clock'];rows=[x for x in c['added_taps'] if x['name']=='clk_t28'];assert len(rows)==1
assert rows[0]['xy']==[1126.44,980.6],('unexpected current clock site',rows[0]['xy']);assert c.get('tap_radius_um',200)==200
rows[0]['xy']=[1126.432,958.496]
pathlib.Path(a.output).write_text(json.dumps(p,separators=(',',':'))+'\n')
print('Applied sole clk_t28 physical coordinate event; regenerate native185 relay graph and retain physical halo hold')

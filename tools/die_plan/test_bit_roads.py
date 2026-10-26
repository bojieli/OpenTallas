import copy
import pytest
import bit_roads as B
class P:
 parts={'p':{'type':'t'}}
 ports={'i':{'face':'W','src':{'part':'@die'}},'o':{'face':'E','src':{'part':'p'}}}
 def __init__(self):self.s={'width':1,'stations':2,'bit_site_cell_um':[2,2],'bit_sites_um':[[[149,-1],[149,9]]]}
 def slot(self,*_):return self.s
 def rect(self,*_):return (0,0,302,20)
 def port_pins(self,p):return [(0,'M5',0),(1,'M5',10)]
 def to_die(self,p,xy):return xy
 def type_top_layer(self,t):return 'M7'
def test_indexed_epoch_and_crossed_station_negative():
 p=P();chains,stats=B.indexed_chains(p,'p','s','i','o',151.)
 assert stats['bits']==2 and stats['hops']==4 and stats['epoch_included']
 p.s['bit_sites_um'][0].reverse()
 with pytest.raises(ValueError,match='bit 0 hop 0'):B.indexed_chains(p,'p','s','i','o',151.)
def test_incomplete_index_inventory_fails_closed():
 p=P();p.s['bit_sites_um'][0].pop()
 with pytest.raises(ValueError,match='station bit coverage'):B.indexed_chains(p,'p','s','i','o')

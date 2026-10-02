import sys
from pathlib import Path
from fractions import Fraction
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_capture_publication_credit as C
import dsrom_capture_physical_shard_paths as P

def ctx(user=0):return {n:(user if n=='user' else 0) for n,w in C.FIELDS}
def test_visible_and_positive_return_before_source_reuse():
 x=ctx();d=C.PublicationDebt(x,1,Fraction(4,3))
 assert d.issue(0,x,0,10,True);d.reply(0,x,0,11)
 with pytest.raises(ValueError):d.return_credit(0,x,0,12)
 assert not d.issue(1,x,0,12,True)
 d.visible(0,x,12,True)
 with pytest.raises(ValueError):d.return_credit(0,x,0,13)
 assert not d.issue(1,x,0,13,True)
 d.return_credit(0,x,0,Fraction(40,3));assert not d.issue(1,x,0,Fraction(40,3),True);assert d.issue(1,x,0,14,True)

def test_user_upper16_not_dropped():
 x=ctx(1<<16);d=C.PublicationDebt(x,1,1);d.issue(0,x,0,1,True)
 with pytest.raises(ValueError):d.reply(0,ctx(0),0,2)
 assert len(d.debts)==1

def test_all576_rows_singlelease_separate_shards():
 x=ctx();d=C.PublicationDebt(x,1,1)
 for row in range(576):
  s=P.owner(row)['physical_shard'];e=row*4+1
  assert d.issue(row,x,s,e,True);d.reply(row,x,s,e+1);d.visible(row,x,e+2,True);d.return_credit(row,x,s,e+3)
 assert d.next_visible==576 and not d.debts

@pytest.mark.parametrize('delay',[0,-1])
def test_zero_negative_credit_delay_refused(delay):
 with pytest.raises(ValueError):C.PublicationDebt(ctx(),1,delay)

def test_held_and_wrongshard_preserve_matching_debt():
 x=ctx();d=C.PublicationDebt(x,1,2);d.issue(0,x,0,1,True)
 with pytest.raises(ValueError):d.reply(0,x,1,2)
 assert not d.issue(1,x,0,2,True)
 d.reply(0,x,0,3)
 with pytest.raises(ValueError):d.visible(0,x,4,False)
 assert not d.issue(1,x,0,4,True)

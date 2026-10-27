"""Focused wide PG spacing controls; parent R28 cut policy is not integrated."""

def test_router_wide_pg_spacing():
    """R28: an 8w clock wire must keep the 1.0 um wide-table spacing from a 1.92 um PG stripe (NDR space 0.08 alone
    is not enough); a narrow 0.48 PG stripe keeps the NDR space."""
    import die_clock_128 as C
    ix = C.MetalIndex(0.08)
    ix.add(("M8", "VDD", "pg", 10.0, 11.92, 0.0, 100.0))
    ix.add(("M8", "VSS", "pg", 20.0, 20.48, 0.0, 100.0))
    assert ix.hits(("M8", "ck", "clk", 12.5, 12.82, 0.0, 50.0), first=True)          # 0.58 < 1.0
    assert not ix.hits(("M8", "ck", "clk", 12.92, 13.24, 0.0, 50.0), first=True)     # 1.00
    assert not ix.hits(("M8", "ck", "clk", 12.5, 12.82, 0.0, 1.5), first=True)       # PRL 1.5 < 1.8
    assert not ix.hits(("M8", "ck", "clk", 19.6, 19.92, 0.0, 50.0), first=True)      # 0.08 to a 0.48 stripe

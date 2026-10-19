"""CLOSED a7 literals and actual default-only die instances must be audited."""
import sys
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_static_params as K


def test_closed_native_literals():
    assert K._vals(dict(AP_OFS="64'hffddffdeffdcffdc", FR_OFS="32'hfffffff9")) == dict(
        AP_OFS=[-36, -36, -34, -35], FR_OFS=-7)
    assert K._vals(dict(AP_OFS="64'h0002000200020002", FR_OFS=-7)) == dict(AP_OFS=[2]*4, FR_OFS=-7)
    assert K._vals(dict(AP_OFS="{16'hffdd,16'hffde,16'hffdc,16'hffdc}", FR_OFS="-7"))['AP_OFS'] == [-36,-36,-34,-35]


def test_unknown_or_overflow_literals_refused():
    for x in ("32'hxxxxxxxx", "8'h100", "0'h0"):
        try:
            K._literal(x)
        except ValueError:
            pass
        else:
            raise AssertionError(f'invalid literal accepted: {x}')


def test_default_only_and_explicit_die_instances_audited():
    for params in ('', '#(.Z_IN_STRIDE(4))', "#(.Z_IN_STRIDE(4),.AP_OFS(64'hffddffdeffdcffdc),.FR_OFS(-7))"):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'die.v'
            p.write_text(f'module die; qkd_ahub_static_dw {params} ahub (.ck(n_ck)); endmodule\n')
            rows = [v for k,v in K.hub_bound({},p) if k.startswith('die.v ')]
            assert len(rows) == 1
            assert rows[0] == (dict(AP_OFS=[-36,-36,-34,-35],FR_OFS=-7) if 'AP_OFS' in params else K.AHUB_DEFAULT)

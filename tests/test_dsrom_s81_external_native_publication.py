"""Only the new cross-writer ACK boundary; no native-provider gate rerun."""
from pathlib import Path
import subprocess
from test_dsrom_s81_published_span_accept_sink import CPP,ROOT

def test_external_ack_does_not_grant_on_assignment_or_wrong_tuple(tmp_path):
    source=tmp_path/'check.cpp';binary=tmp_path/'check'
    source.write_text(CPP.split('int main() {')[0]+r'''
int main(){
    {AcceptRun r;auto c=fixture_record(batch(46464),0);
     assert(!r.binder.source_span_lease(123,46464,1));
     VmReceipt ack{};ack.address=c.word.address;ack.mask=c.word.mask;ack.owner=c.word.owner;
     r.binder.external_scalar_visible(c,ack);
     assert(r.acks_seen==1&&r.binder.source_span_lease(123,46464,1));
     assert(!r.binder.source_span_lease(123,46464,2));
     assert(r.writes_seen==0); // method never fabricates native acceptance
    }
    {AcceptRun r;auto c=fixture_record(batch(46464),0);
     VmReceipt ack{};ack.address=c.word.address;ack.mask=c.word.mask;ack.owner=c.word.owner;
     ack.owner[0]^=1;
     refuses([&]{r.binder.external_scalar_visible(c,ack);});
     assert(r.acks_seen==0&&r.binder.fault()&&!r.binder.source_span_lease(123,46464,1));
    }
}
''')
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(ROOT/'tools/runtime/dsrom'),
                    '-I',str(ROOT/'rtl/test/v41_runtime'),str(source),'-o',str(binary)],check=True)
    subprocess.run([str(binary)],check=True)

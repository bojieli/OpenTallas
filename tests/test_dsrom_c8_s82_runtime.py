import importlib.util
import json
import socket
import struct
import subprocess
import sys
import threading
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_c8_s82_runtime_source as G
import dsrom_s82_native_word_server as S


def test_actual_host_copy_exact_regeneration_defaultoff():
    original=subprocess.check_output(['git','show',G.PIN+':'+G.SOURCE],cwd=ROOT,text=True)
    generated=G.transform(original)
    assert generated==(ROOT/'rtl/test/v41_runtime/w17_current_fastpp_c8_s82_rt.cpp').read_text()
    assert '#define DSROM_C8_S82 0' in generated
    assert 'return_owner[dsrom_s82::return_pair(pair)]=pair' in generated
    assert 'NL=8192;' in generated
    assert 'd->c8_context_restored=visible' in generated
    assert 'd->c8_visible_identity' in generated and 'd->c8_retire_identity' in generated
    assert 'legacy singleton driver is not a combined run' in generated
    assert 'unbound actual S82 cfg phase/address' in generated


def test_native_provider_fails_closed_partial_and_unowned(capsys):
    client,server=socket.socketpair()
    try:
        client.sendall(struct.pack('<4I',41,3,9551,4095));client.shutdown(socket.SHUT_WR)
        def reject(*args):raise ValueError('no unique physical payload owner')
        S.serve_connection(server,reject)
        reply=S.receive(client,40)
        assert struct.unpack('<I',reply[:4])[0]==1
        assert 'no unique physical payload owner' in capsys.readouterr().out
    finally:client.close();server.close()
    client,server=socket.socketpair()
    try:
        client.sendall(b'partial');client.shutdown(socket.SHUT_WR)
        with pytest.raises(EOFError):S.receive(server,16)
    finally:client.close();server.close()


def test_native_client_fullwidth_actual_mapping_and_retained_return(tmp_path):
    # Host transport test only. No RTL or replacement numerical producer.
    source=tmp_path/'client.cpp';exe=tmp_path/'client'
    source.write_text('''#include "dsrom_s82_rom_client.hpp"
#include <cstdio>
int main(){
 for(int p=0;p<2388;p++)std::printf("%d\\n",dsrom_s82::return_pair(p));
 auto w=dsrom_s82::read(41,3,2387,1,8191);
 if(w[0]!=0x12345678 || w[8]!=(1u<<17))return 2;
 try { dsrom_s82::read(41,3,2387,1,8191); }catch(const std::runtime_error&){return 0;}
 return 3;
}
''')
    subprocess.run(['g++','-std=c++17','-pthread','-I'+str(ROOT/'rtl/test/v41_runtime'),str(source),'-o',str(exe)],check=True)
    path=tmp_path/'native.sock'
    # Unix path must fit the native master; pytest's long path can exceed108.
    import tempfile,os
    with tempfile.TemporaryDirectory(prefix='s82-') as short:
        path=Path(short)/'native.sock';requests=[]
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as listener:
            listener.bind(str(path));listener.listen(1)
            def serve():
                with listener.accept()[0] as conn:
                    def read(*args):
                        requests.append(args)
                        if len(requests)>1:raise ValueError('deliberate invalid owner')
                        return (1<<273)|0x12345678
                    S.serve_connection(conn,read)
            thread=threading.Thread(target=serve);thread.start()
            result=subprocess.run([str(exe)],env=dict(os.environ,DSROM_S82_ROM_SOCKET=str(path)),capture_output=True,text=True,check=True)
            thread.join()
    slots=list(map(int,result.stdout.split()))
    sm=json.loads(subprocess.check_output(['git','show','717a32dcf:results/uarch/dsrom_s73_pair1_20261003/baseline_s82_successor_r1/stage_map.json'],cwd=ROOT))
    expected=[32*r+p-sm['region_bounds'][r] for r in range(128) for p in range(sm['region_bounds'][r],sm['region_bounds'][r+1])]
    assert slots==expected and len(set(slots))==2388
    assert all(0<=s<4096 for s in slots)
    assert requests==[(41,3,9551,4095)]*2


def test_owner_api_load_ignores_stale_bytecode(tmp_path):
    import importlib,os,py_compile
    module='c8_stale_owner';path=tmp_path/(module+'.py')
    path.write_text('value=13\n');stamp=path.stat().st_mtime
    py_compile.compile(str(path),doraise=True)
    path.write_text('value=42\n');os.utime(path,(stamp,stamp))
    finder=S.OwnerSourceFinder(tmp_path);sys.meta_path.insert(0,finder);sys.path.insert(0,str(tmp_path))
    try:
        assert importlib.import_module(module).value==42
    finally:
        sys.modules.pop(module,None);sys.path.pop(0);sys.meta_path.remove(finder)

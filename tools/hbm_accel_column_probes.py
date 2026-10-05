"""Additive, read-only simulation probes for the existing HA5 four-clock owner.

No ASIC ports/storage or arithmetic changes. These probes do not grant leases,
issue kernels, acknowledge completions or tick clocks. Old binaries refuse H.
"""
from pathlib import Path
from tools import hbm_accel_program_backend as backend


def emit_top(path, mem_words, *, enable=False):
    if not enable:
        raise ValueError('explicit column probe enable required')
    backend.emit_top(path, mem_words)
    path = Path(path)
    text = path.read_text()
    anchor = 'output wire [3:0] probe_fetch_request,probe_fetch_line'
    if text.count(anchor) != 1:
        raise ValueError('HA5 top source differs')
    text = text.replace(anchor, anchor + ',\n input wire [1:0] source_sm,source_kind,\n input wire [13:0] source_index,\n output reg [2127:0] source_data')
    body = 'always @* begin source_data=0; case(source_sm)\n'
    for die in range(2):
        for sm in range(2):
            base = f'dut.u_cluster.g_on.g_die[{die}].g_sm[{sm}].u_sm.g_on'
            body += f'{die*2+sm}: begin case(source_kind)\n'
            body += f'0: source_data[31:0]={base}.smem[source_index];\n'
            body += f'1: if(source_index<64) source_data={base}.g_bd.u_bdtc.xmem[source_index];\n'
            body += f'2: if(source_index<16) source_data[31:0]={base}.ur[source_index];\n'
            body += f'3: source_data[63:0]={base}.imem[source_index];\n'
            body += 'default: source_data=0; endcase end\n'
    body += 'endcase end\n'
    path.write_text(text.replace('endmodule\n', body + 'endmodule\n'))


def emit_driver(path, *, enable=False):
    if not enable:
        raise ValueError('explicit column probe enable required')
    text = Path(backend.__file__).with_suffix('.cpp').read_text()
    anchor = 'm.eval();\n    auto wide='
    if text.count(anchor) != 1:
        raise ValueError('HA5 driver source differs')
    text = text.replace(anchor, 'm.source_sm=0;m.source_kind=0;m.source_index=0;\n    ' + anchor)
    anchor = "} else if(op=='M'){"
    if text.count(anchor) != 1:
        raise ValueError('HA5 memory RPC source differs')
    handler = '''} else if(op=='H'){
            unsigned sm,kind,index;in>>sm>>kind>>index;
            if(!in || sm>3 || kind>3 || (kind==0 && index>=8192) ||
               (kind==1 && index>=64) || (kind==2 && index>=16) || index>=16384)return 6;
            m.source_sm=sm;m.source_kind=kind;m.source_index=index;m.eval();
            std::cout<<"HA5 "<<std::hex;wide(m.source_data,67);
            std::cout<<std::endl;continue;
        } else if(op=='M'){'''
    Path(path).write_text(text.replace(anchor, handler))


class SectorReadbackPins(backend.VerilatorPins):
    """Reuse the existing binary M RPC, once per sector rather than per byte."""
    def read_bytes(self, die, address, size, *, mem_words):
        if type(die) is not int or die not in (0,1) or type(address) is not int or type(size) is not int or min(address,size)<0 or address+size>mem_words*64:
            raise ValueError('actual partition range; no wrap')
        if not size:
            return b''
        result = bytearray()
        for at in range(address//32*32, ((address+size+31)//32)*32, 32):
            part = (at >> 7) & 1
            local = ((at >> 8) << 7) | (at & 127)
            word = int(self._rpc(f'M {die*2+part:x} {local//32:x}')[0],16)
            result.extend(word.to_bytes(32,'little'))
        return bytes(result[address%32:address%32+size])


class ColumnProbePins(SectorReadbackPins):
    def _source_word(self, die, sm, kind, index):
        if type(die) is not int or type(sm) is not int or die not in (0, 1) or sm not in (0, 1):
            raise ValueError('actual source SM identity')
        bounds = (8192, 64, 16, 16384)
        if type(kind) is not int or not 0 <= kind < 4 or type(index) is not int or not 0 <= index < bounds[kind]:
            raise ValueError('source probe range; no wrap')
        return int(self._rpc(f'H {die*2+sm:x} {kind:x} {index:x}')[0], 16)

    def read_shared(self, die, sm, address, size):
        if type(address) is not int or type(size) is not int or address < 0 or size < 0 or address+size > 32768:
            raise ValueError('actual shared byte range')
        out = bytearray()
        for word in range(address//4, (address+size+3)//4):
            out.extend(self._source_word(die, sm, 0, word).to_bytes(4, 'little'))
        return bytes(out[address%4:address%4+size])

    def read_bd_activation(self, die, sm, index):
        return self._source_word(die, sm, 1, index)

    def read_ur(self, die, sm, index):
        return self._source_word(die, sm, 2, index)

    def read_instruction(self, die, sm, index):
        return self._source_word(die, sm, 3, index)


def build_command(source, work, verilator, *, mem_words, jobs, enable=False):
    """Prepare ONE additive successor build; caller uses shared admission.

    Does not execute commands, load model/checkpoint data or start a runtime.
    """
    if not enable:
        raise ValueError('explicit column probe build enable required')
    import json
    command = backend.build_command(source, work, verilator, mem_words=mem_words, jobs=jobs)
    work = Path(work)
    top = work/'ha5_cp20_runtime.sv'
    driver = work/'ha5_column_runtime.cpp'
    emit_top(top, mem_words, enable=True)
    emit_driver(driver, enable=True)
    command[-1] = str(driver.resolve())
    record_path = work/'build_manifest.json'
    record = json.loads(record_path.read_text())
    record.update(command=command, top_sha256=backend.digest(top),
                  driver_sha256=backend.digest(driver), source_probes=True,
                  observer_only=True, extra_asic_state_bits=0)
    record_path.write_text(json.dumps(record, indent=2)+'\n')
    return command

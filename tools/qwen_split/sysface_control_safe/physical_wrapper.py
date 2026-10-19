"""Explicit existing paid boundary; used only by --physical-wrapper candidate."""

def wrapper(top,core,r,reference=False):
    ports=r['public_ports'];types=sorted({'$_DFF_P_', '$_DFF_PN0_', '$_DFF_PN1_', '$_DFFE_PP_', '$_DFFE_PN0P_', '$_DFFE_PN0N_', '$_SDFF_PP0_', '$_SDFF_PN0_'})
    kind=types.index('$_DFF_P_');lines=['\n(* ot_explicit_pin_regs=1, ot_explicit_reset_stages=2 *) module '+top+' #(parameter ROM_VIAMAP="", ROM_INSTANCE="sys_face_cfg", OVL_ROM_DIR="") (']
    lines += [',\n'.join(p['direction']+' wire '+('['+str(len(p['bits'])-1)+':0] ' if len(p['bits'])>1 else '')+n for n,p in ports.items()),');']
    index=100000
    def ff(d,q):
        nonlocal index
        lines.append('(* keep=1 *) sysface_safe_ff #(.KIND('+str(kind)+')) boundary_'+str(index)+'(.C(ck),.D('+d+'),.E(1\'b0),.R(1\'b0),.Q('+q+'));');index+=1
    con=[]
    for name,p in ports.items():
        if name=='ck':con.append('.ck(ck)');continue
        width=len(p['bits']);wire='face_'+name
        lines.append('wire ['+str(width-1)+':0] '+wire+';')
        if name=='rst_n':
            lines.append('wire face_reset_first;');ff('rst_n','face_reset_first');ff('face_reset_first',wire+'[0]')
        elif p['direction']=='input':
            for k in range(width):ff(name if width==1 else name+'['+str(k)+']',wire+'['+str(k)+']')
        else:
            for k in range(width):ff(wire+'['+str(k)+']',name if width==1 else name+'['+str(k)+']')
        con.append('.'+name+'('+wire+')')
    for cp in r['input_capture_copies']:
        name=cp['original_port'];w=len(ports[name]['bits']);wire='capture_'+cp['port']
        lines.append('wire '+wire+';');ff(name if w==1 else name+'['+str(cp['original_index'])+']',wire)
        con.append('.'+cp['port']+'('+wire+')')
    extra=(''.join('.'+k+'('+str(v)+'),' for k,v in r['manifest']['parameters'].items())) if reference else ''
    lines.append(core+' #('+extra+'.ROM_VIAMAP(ROM_VIAMAP),.ROM_INSTANCE(ROM_INSTANCE),.OVL_ROM_DIR(OVL_ROM_DIR)) core('+','.join(con)+');')
    lines+=['endmodule','']
    return '\n'.join(lines)

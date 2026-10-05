set pagination off
set confirm off
set debuginfod enabled off
set language c
set disable-randomization off
file /tmp/w17-D1-native-joined-20261002-r1/D1_current_prefix
set args +DIR=/tmp/w17-D1-native-diagnostic-result-20261002-r1/input
break *'_Z59Vtb_D1_scope_core___024root___eval_initial__TOP__Vtiming__2PZ59Vtb_D1_scope_core___024root___eval_initial__TOP__Vtiming__2P27Vtb_D1_scope_core___024rootE99_Z59Vtb_D1_scope_core___024root___eval_initial__TOP__Vtiming__2P27Vtb_D1_scope_core___024root.Frame.actor'+0x91d
commands 1
silent
set $frame = *(unsigned long long*)($rbp-0x48)
set $root = *(unsigned long long*)($frame+0x40)
printf "D1_ACTUAL_FATAL_MASK fault_r=0x%02x dbg_fs=0x%06x violations=0x%02x\n", *(unsigned char*)($root+0x28021), *(unsigned int*)($root+0x5f0fc), *(unsigned char*)($root+0x27fe2)
continue
end
info breakpoints
# Deliberately no run: fresh source/hash/resource/parent admission required.

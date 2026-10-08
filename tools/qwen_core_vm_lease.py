"""Default-off direct ME epoch lease; never feeds lease through PINREG supply.

Requires caller's full native-clock/collective ownership binding. The separately
exported original intent is for CAP; effective me_en remains every internal
ME execution/acceptance consumer's enable. No standalone closure claim.
"""
def apply(text):
    old='    parameter integer DEC_LA = 0';assert text.count(old)==1
    text=text.replace(old,'    parameter integer VM_OWNED_LEASE = 0,\n'+old,1)
    old='    input  wire              me_mem_ok,';assert text.count(old)==1
    text=text.replace(old,'    input wire vm_me_lease,\n    output wire vm_me_wanted,\n'+old,1)
    old='''    assign me_en = !rst_n_i || (((ME_STALL == 0) || me_mem_ok_i) &&
                              ((ME_IDLE_GATE == 0) || !me_idle || me_wake));'''
    assert text.count(old)==1
    new=old.replace('assign me_en =','assign vm_me_wanted =')+'''
    // Reset keeps the native ME reset path enabled; normal acceptance is leased.
    assign me_en = !rst_n_i || (vm_me_wanted &&
                       ((VM_OWNED_LEASE == 0) || vm_me_lease));'''
    text=text.replace(old,new,1)
    old='generate if (ME_STALL != 0 || ME_IDLE_GATE != 0) begin : g_me_cg'
    assert text.count(old)==1
    return text.replace(old,'generate if (VM_OWNED_LEASE != 0 || ME_STALL != 0 || ME_IDLE_GATE != 0) begin : g_me_cg',1)

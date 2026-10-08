"""Default-off raw ME intents for an explicitly owned VM ingress collar.

The matching collar MUST qualify every ME/MX seat using original pre-lease
source_me_wanted at CAP. This transform alone is not a valid core/die binding.
"""
def apply(text):
    old='    parameter integer DEC_LA = 0';assert text.count(old)==1
    text=text.replace(old,'    parameter integer VM_OWNED_RAW = 0,\n'+old,1)
    for old,new in [
      ('assign vw_me_we = me_o_we & {(G >> SMIN){me_en}};',
       'assign vw_me_we = me_o_we & {(G >> SMIN){(VM_OWNED_RAW != 0) || me_en}};'),
      ('assign vw_mx_we = me_mx_we & me_en;',
       'assign vw_mx_we = me_mx_we & ((VM_OWNED_RAW != 0) || me_en);')]:
        assert text.count(old)==1,old;text=text.replace(old,new,1)
    return text

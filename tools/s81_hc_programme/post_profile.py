"""Add default-off per-command POST age capture to the exact HC generator."""
def extend(seq,comb,cp):
    def change(text,old,new,count=1):
        if text.count(old)!=count:raise ValueError('HC dynamic POST source shape changed: '+old)
        return text.replace(old,new)
    seq=change(seq,'parameter integer POST_EXPLICIT = 0,','parameter integer POST_EXPLICIT = 0, COMMAND_POST_AGES = 0,')
    seq=change(seq,'    input wire [31:0] command_done_age,command_ss_age,command_scalar_age,','    input wire [639:0] command_post_ages,\n    input wire [31:0] command_done_age,command_ss_age,command_scalar_age,')
    seq=change(seq,'    always @(*)begin\n     y_take=0;', '''    // The cpin captures this held descriptor with n_cmd_v. It remains stable
    // through CMD_LAT and is captured once at actual fixed command acceptance.
    // This adds640 FF only in the explicit dynamic profile; no1280-bit pipe.
    wire [639:0] job_post_ages;
    generate if(COMMAND_POST_AGES!=0)begin:g_command_post_ages
     reg[639:0]held;
     always @(posedge sk)if(take)held<=command_post_ages;
     assign job_post_ages=held;
    end else begin:g_parameter_post_ages
     assign job_post_ages=POST_AGES;
    end endgenerate
    always @(*)begin
     y_take=0;''')
    seq=change(seq,'POST_EXPLICIT?POST_AGES[row*32+:32]','(POST_EXPLICIT||COMMAND_POST_AGES)?job_post_ages[row*32+:32]')
    cp=change(cp,'parameter integer NG = 256,','parameter integer COMMAND_POST_AGES = 0,\n    parameter integer NG = 256,')
    cp=change(cp,'    input wire [31:0] y_tag,','    input wire [639:0] command_post_ages,\n    output wire [639:0] n_command_post_ages,\n    input wire [31:0] y_tag,')
    cp=change(cp,'    // die pins','''    // Descriptor is held from command capture until the next command; it
    // shares the command's registered serial boundary without new cycles.
    // Disabled mode adds no state and preserves the previous parameter profile.
    // die pins''')
    cp=change(cp,'    // controller-clock domain:', '''    generate if(COMMAND_POST_AGES!=0)begin:g_command_post_ages
      reg[639:0]held;
      always @(posedge sk)if(c_cmd_v)held<=command_post_ages;
      assign n_command_post_ages=held;
    end else begin:g_no_command_post_ages
      assign n_command_post_ages=640'd0;
    end endgenerate
    // controller-clock domain:''')
    comb=change(comb,'CMD_LAT=2, VM_LAT=12, POST_EXPLICIT=0,','CMD_LAT=2, VM_LAT=12, POST_EXPLICIT=0, COMMAND_POST_AGES=0,')
    comb=change(comb,'    input wire [31:0] n_y_tag,','    input wire [639:0] command_post_ages,\n    input wire [31:0] n_y_tag,')
    comb=change(comb,'.POST_EXPLICIT(POST_EXPLICIT),.POST_AGES(POST_AGES))','.POST_EXPLICIT(POST_EXPLICIT),.POST_AGES(POST_AGES),.COMMAND_POST_AGES(COMMAND_POST_AGES))',2)
    comb=change(comb,'        .command_done_age(command_done_age),','        .command_post_ages(command_post_ages),\n        .command_done_age(command_done_age),')
    return seq,comb,cp

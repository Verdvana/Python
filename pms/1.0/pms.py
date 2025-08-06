import sys
import re
import os
import glob
import openpyxl
import shutil
from dataclasses import dataclass,field
from pathlib import Path
from datetime import datetime

#============================================================
# Define data class
@dataclass
class Path:
    top:str="None"
    top_path:str="None"
    rtl_path:str="None"
    rtl_list:str="None"
    tb_path:str="None"
    cons_path:str="None"
    mem_path:str="None"
    param:str="None"
    lib_path:str="None"
    sub_rtl_list:str="None"
@dataclass
class Range:
    min:str="None"
    max:str="None"
@dataclass
class Library:
    target:str="None"
    link:str="None"
    symbol:str="None"
    synthetic:str="None"
@dataclass
class DrivingCell:
    name:str="None"
    input:str="None"
    output:str="None"
    lib:str="None"
@dataclass
class ClockTree:
    source_latency:Range=field(default_factory=Range)
    network_latency:Range=field(default_factory=Range)
    trans:Range=field(default_factory=Range)
    skew:str="None"
    noise:str="None"
@dataclass
class Scale:
    sm:ClockTree=field(default_factory=ClockTree)
    md:ClockTree=field(default_factory=ClockTree)
    lg:ClockTree=field(default_factory=ClockTree)
    raw:ClockTree=field(default_factory=ClockTree)
@dataclass
class Config:
    path_root:str="None"
    path_sub:str="None"
    library:Library=field(default_factory=Library)
    signal_driving_cell:DrivingCell=field(default_factory=DrivingCell)
    clock_driving_cell:DrivingCell=field(default_factory=DrivingCell)
    signal_trans:Range=field(default_factory=Range)
    output_load:Range=field(default_factory=Range)
    output_trans:Range=field(default_factory=Range)
    output_delay:Range=field(default_factory=Range)
    input_delay:Range=field(default_factory=Range)
    input_trans:Range=field(default_factory=Range)
    wire_load_model:str="None"
    opera_condition:str="None"
    setup_margin:str="None"
    hold_margin:str="None"
    ct:Scale=field(default_factory=Scale)

def replace_in_file(file_path,target,replacement):
    if replacement is None:
        replacement = ""
    with open(file_path,'r+',encoding='utf-8') as f:
        content = f.read()
        f.seek(0)
        f.write(content.replace(target,replacement))
        f.truncate()
def error_exit(msg):
    print(f"错误：{msg}", file=sys.stderr)
    sys.exit(1)
def standardize_list(list):
    if not list:
        return ""
    elif list is None:
        return ""
    return list.replace(","," ").replace(";"," ").replace("\n"," ").replace("\r"," ")
def get_env_var(var,bak):
    if var in os.environ:
        return os.environ.get(var)
    else:
        return bak
def parse_path(sheet):
    path=Path()
    path.top = sheet['B1'].value
    if path.top is None or str(path.top).strip() == "":
        error_exit("Not define top module.")
    print(f"Design top module: {path.top}")
    path.top_path = get_env_var(path.top,sheet['B2'].value)
    path.top_path = re.sub(r"\$\{top\}",path.top,path.top_path,flags=re.IGNORECASE)
    if path.top_path is None:
        error_exit("Error: Not define design path")

    path.rtl_path = sheet['B3'].value
    path.rtl_path = re.sub(r"\$\{top_path\}",path.top_path,path.rtl_path,flags=re.IGNORECASE)
    print(f"Top RTL dir: {path.rtl_path}")
    rtl_pattern = ["*.v", "*.sv", "*.vhd", "*.vhdl"]
    path.rtl_list = []
    for pattern in rtl_pattern:
        path.rtl_list.extend(glob.glob(os.path.join(path.rtl_path, pattern)))

    if not path.rtl_list:
        error_exit(f"Not find RTL files in {path.rtl_path} with pattern {rtl_pattern}")
    path.rtl_list = " ".join(os.path.basename(f) for f in path.rtl_list)
    print(f"RTL files found: {path.rtl_list}")

    top_pattern = path.top+"."
    top_match = [item for item in path.rtl_list.split() if top_pattern in item]
    if len(top_match) == 1:
        top_file = top_match[0]
    else:
        print(f"Top-level file: {top_match}")
        error_exit("The top-level file is not unique or not found.")
    print(f"Top-level file: {top_file}")

    param_lines = []
    found_param = False
    with open(path.rtl_path+"/"+top_file,'r',encoding='utf-8') as file:
        for line in file:
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            if not found_param:
                if "parameter" in stripped:
                    found_param = True
                    param_lines.append(stripped)
            else:
                param_lines.append(stripped)
                if ")" in stripped:
                    break
    path.param = " ".join(param_lines).replace("\n"," ").replace("\r"," ")
    path.param = path.param[len("parameter"):].lstrip()
    path.param = path.param.split(")")[0].rstrip()
    print(f"Parameter of top design: {path.param}")




    path.tb_path = sheet['B4'].value
    path.tb_path = re.sub(r"\$\{top_path\}",path.top_path,path.tb_path,flags=re.IGNORECASE)

    path.cons_path = sheet['B5'].value
    path.cons_path = re.sub(r"\$\{top_path\}",path.top_path,path.cons_path,flags=re.IGNORECASE)

    path.mem_path = sheet['B6'].value
    path.mem_path = re.sub(r"\$\{top_path\}",path.top_path,path.mem_path,flags=re.IGNORECASE)

    path.lib_path = sheet['B7'].value
    path.lib_path = re.sub(r"\$\{top_path\}",path.top_path,path.lib_path,flags=re.IGNORECASE)

    path.sub_rtl_list = ""
    row_index   = 10
    while True:
        row = [cell.value for cell in sheet[row_index]]
        if row[0] is None:
            break
        sub_path = get_env_var(row[0],row[1])
        sub_sheet = openpyxl.load_workbook(os.path.join(sub_path,"pms",row[0]+".xlsx"))['path']
        sub_rtl_path = sub_sheet['B3'].value
        
        sub_rtl_path = re.sub(r"\$\{top_path\}",sub_path,sub_rtl_path,flags=re.IGNORECASE)

        print(f"sub_rtl_path:{sub_rtl_path}")
        path.sub_rtl_list += f" {sub_rtl_path}"
        row_index += 1

    if os.path.exists(path.cons_path):
        user_input = input(f"Warning: DIR {path.cons_path} existed, do you want to clean it and continue?(y/n):").strip().lower()
        if user_input == "y":
            shutil.rmtree(path.cons_path)
        elif user_input == "n":
            error_exit("User terminal script.")
        else:
            error_exit("Input error.")
    os.makedirs(path.cons_path)
    if os.path.exists(path.tb_path):
        user_input = input(f"Warning: DIR {path.tb_path} existed, do you want to clean it and continue?(y/n):").strip().lower()
        if user_input == "y":
            shutil.rmtree(path.tb_path)
        elif user_input == "n":
            error_exit("User terminal script.")
        else:
            error_exit("Input error.")
    os.makedirs(path.tb_path)

    return path

def parse_config(sheet,path):
    config=Config()
    config.path_root                    = sheet['B2'].value
    config.path_sub                     = standardize_list(sheet['C2'].value)
    config.library.target               = standardize_list(sheet['B5'].value)
    config.library.link                 = standardize_list(sheet['C5'].value)
    config.library.symbol               = sheet['D5'].value
    config.library.synthetic            = sheet['E5'].value
    config.signal_driving_cell.name     = sheet['B8'].value
    config.signal_driving_cell.output   = sheet['D8'].value
    config.signal_driving_cell.input    = sheet['E8'].value
    config.signal_driving_cell.lib      = sheet['F8'].value
    config.clock_driving_cell.name      = sheet['B9'].value
    config.clock_driving_cell.output    = sheet['D9'].value
    config.clock_driving_cell.input     = sheet['E9'].value
    config.clock_driving_cell.lib       = sheet['F9'].value
    config.signal_trans.min             = sheet['B12'].value
    config.signal_trans.max             = sheet['C12'].value
    config.output_load.min              = sheet['B13'].value
    config.output_load.max              = sheet['C13'].value
    config.output_trans.min             = sheet['B14'].value
    config.output_trans.max             = sheet['C14'].value
    config.output_delay.min             = sheet['B15'].value
    config.output_delay.max             = sheet['C15'].value
    config.input_delay.min              = sheet['B16'].value
    config.input_delay.max              = sheet['C16'].value
    config.input_trans.min              = sheet['B17'].value
    config.input_trans.max              = sheet['C17'].value
    config.wire_load_model              = sheet['F12'].value
    config.opera_condition              = sheet['F15'].value
    config.setup_margin                 = sheet['B19'].value
    config.hold_margin                  = sheet['B20'].value
    config.ct.sm.source_latency.min     = sheet['B25'].value
    config.ct.sm.source_latency.max     = sheet['C25'].value
    config.ct.sm.network_latency.min    = sheet['D25'].value
    config.ct.sm.network_latency.max    = sheet['E25'].value
    config.ct.sm.trans.min              = sheet['F25'].value
    config.ct.sm.trans.max              = sheet['G25'].value
    config.ct.sm.skew                   = sheet['H25'].value
    config.ct.sm.noise                  = sheet['I25'].value
    config.ct.md.source_latency.min     = sheet['B26'].value
    config.ct.md.source_latency.max     = sheet['C26'].value
    config.ct.md.network_latency.min    = sheet['D26'].value
    config.ct.md.network_latency.max    = sheet['E26'].value
    config.ct.md.trans.min              = sheet['F26'].value
    config.ct.md.trans.max              = sheet['G26'].value
    config.ct.md.skew                   = sheet['H26'].value
    config.ct.md.noise                  = sheet['I26'].value
    config.ct.lg.source_latency.min     = sheet['B27'].value
    config.ct.lg.source_latency.max     = sheet['C27'].value
    config.ct.lg.network_latency.min    = sheet['D27'].value
    config.ct.lg.network_latency.max    = sheet['E27'].value
    config.ct.lg.trans.min              = sheet['F27'].value
    config.ct.lg.trans.max              = sheet['G27'].value
    config.ct.lg.skew                   = sheet['H27'].value
    config.ct.lg.noise                  = sheet['I27'].value
    config.ct.raw.source_latency.min    = sheet['B28'].value
    config.ct.raw.source_latency.max    = sheet['C28'].value
    config.ct.raw.network_latency.min   = sheet['D28'].value
    config.ct.raw.network_latency.max   = sheet['E28'].value
    config.ct.raw.trans.min             = sheet['F28'].value
    config.ct.raw.trans.max             = sheet['G28'].value
    config.ct.raw.skew                  = sheet['H28'].value
    config.ct.raw.noise                 = sheet['I28'].value

    if config.library.target is None or str(config.library.target).strip() == "":
        error_exit("Not define target library")
    print(f"Target Library: {config.library.target}")
    config.library.link = config.library.target + " " + config.library.link + " *"
    print(f"Link Library: {config.library.link}")
    if config.library.symbol is None or str(config.library.symbol).strip() == "":
        error_exit("Not define symbol library")
    print(f"Symbol Library: {config.library.symbol}")
    print(f"Synthetic Library: {config.library.synthetic}")
    return config

def parse_clock(sheet):
    clock_dict  = {}
    row_index   = 4
    columns     = ['level','group','type','period','name','master','jsrc','jmn','jdc','root','comment']
    while True:
        row = [cell.value for cell in sheet[row_index]]
        if row[0] is None:
            break
        row_data = dict(zip(columns,row[:11]))
        name = row_data['name']
        if name:
            clock_dict[name] = row_data
        row_index += 1
    return clock_dict
def parse_rst(sheet):
    rst_dict  = {}
    row_index   = 3
    columns     = ['level','reset','type','edge','clock']
    while True:
        row = [cell.value for cell in sheet[row_index]]
        if row[0] is None:
            break
        row_data = dict(zip(columns,row[:5]))
        reset = row_data['reset']
        if reset:
            rst_dict[reset] = row_data
        row_index += 1
    return rst_dict
def parse_io(sheet):
    io_dict     = {}
    row_index   = 4
    columns     = ['level','pin','direction','clock','trans_min','trans_max','delay_min','delay_max','delay_cmd','load_min','load_max']
    while True:
        row = [cell.value for cell in sheet[row_index]]
        if row[0] is None:
            break
        row_data = dict(zip(columns,row[:11]))
        pin = row_data['pin']
        if pin:
            io_dict[pin] = row_data
        row_index += 1
    return io_dict

def gen_cms_cons_pt(pt_config):
    cons = ""

def gen_cms_cons_synth(synth_config,path):
    date=datetime.now().strftime("%Y-%m-%d")
    synth_config.path_root = path.top_path + "/" + synth_config.path_root 
    script_dir=os.path.dirname(os.path.abspath(__file__))
    synth_cons_temp = script_dir + "/templates/synthesis/synth.tcl"
    synopsys_setup_temp = script_dir + "/templates/synthesis/.synopsys_dc.setup"
    makefile_temp = script_dir + "/templates/synthesis/Makefile"
    sub_dir = synth_config.path_sub.split()

    top_cons = synth_config.path_root + "/scripts/" + path.top + ".tcl"
    synopsys_setup = synth_config.path_root+"/work/.synopsys_dc.setup"
    makefile = synth_config.path_root+"/Makefile"
    if os.path.exists(synth_config.path_root):
        user_input = input(f"Warning: DIR {synth_config.path_root} existed, do you want to clean it and continue?(y/n):").strip().lower()
        if user_input == "y":
            shutil.rmtree(synth_config.path_root)
        elif user_input == "n":
            error_exit("User terminal script.")
        else:
            error_exit("Input error.")
    for dir in sub_dir:
        new_dir = os.path.join(synth_config.path_root,dir)
        os.makedirs(new_dir)
    shutil.copy(synth_cons_temp,top_cons)
    shutil.copy(synopsys_setup_temp,synopsys_setup)
    shutil.copy(makefile_temp,makefile)

    budget = "array set ct_budget {"
    budget += f"\n    sm.source_latency.min    {synth_config.ct.sm.source_latency.min}"
    budget += f"\n    sm.source_latency.max    {synth_config.ct.sm.source_latency.max}"
    budget += f"\n    sm.network_latency.min   {synth_config.ct.sm.network_latency.min}"
    budget += f"\n    sm.network_latency.max   {synth_config.ct.sm.network_latency.max}"
    budget += f"\n    sm.trans.min             {synth_config.ct.sm.trans.min}"
    budget += f"\n    sm.trans.max             {synth_config.ct.sm.trans.max}"
    budget += f"\n    sm.skew                  {synth_config.ct.sm.skew}"
    budget += f"\n    sm.noise                 {synth_config.ct.sm.noise}"
    budget += f"\n    md.source_latency.min    {synth_config.ct.md.source_latency.min}"
    budget += f"\n    md.source_latency.max    {synth_config.ct.md.source_latency.max}"
    budget += f"\n    md.network_latency.min   {synth_config.ct.md.network_latency.min}"
    budget += f"\n    md.network_latency.max   {synth_config.ct.md.network_latency.max}"
    budget += f"\n    md.trans.min             {synth_config.ct.md.trans.min}"
    budget += f"\n    md.trans.max             {synth_config.ct.md.trans.max}"
    budget += f"\n    md.skew                  {synth_config.ct.md.skew}"
    budget += f"\n    md.noise                 {synth_config.ct.md.noise}"
    budget += f"\n    lg.source_latency.min    {synth_config.ct.lg.source_latency.min}"
    budget += f"\n    lg.source_latency.max    {synth_config.ct.lg.source_latency.max}"
    budget += f"\n    lg.network_latency.min   {synth_config.ct.lg.network_latency.min}"
    budget += f"\n    lg.network_latency.max   {synth_config.ct.lg.network_latency.max}"
    budget += f"\n    lg.trans.min             {synth_config.ct.lg.trans.min}"
    budget += f"\n    lg.trans.max             {synth_config.ct.lg.trans.max}"
    budget += f"\n    lg.skew                  {synth_config.ct.lg.skew}"
    budget += f"\n    lg.noise                 {synth_config.ct.lg.noise}"
    budget += f"\n    raw.source_latency.min   {synth_config.ct.raw.source_latency.min}"
    budget += f"\n    raw.source_latency.max   {synth_config.ct.raw.source_latency.max}"
    budget += f"\n    raw.network_latency.min  {synth_config.ct.raw.network_latency.min}"
    budget += f"\n    raw.network_latency.max  {synth_config.ct.raw.network_latency.max}"
    budget += f"\n    raw.trans.min            {synth_config.ct.raw.trans.min}"
    budget += f"\n    raw.trans.max            {synth_config.ct.raw.trans.max}"
    budget += f"\n    raw.skew                 {synth_config.ct.raw.skew}"
    budget += f"\n    raw.noise                {synth_config.ct.raw.noise}"
    budget += "\n}"
    budget += f"\nset SETUP_MARGIN  {synth_config.setup_margin}"
    budget += f"\nset HOLD_MARGIN   {synth_config.hold_margin}"


    replace_in_file(makefile,'__SCRIPT__',top_cons)
    replace_in_file(synopsys_setup,'__ROOT__',path.top_path)
    replace_in_file(synopsys_setup,'__LIB_PATH__',path.lib_path)
    replace_in_file(synopsys_setup,'__RTL_PATH__',path.rtl_path+path.sub_rtl_list)
    replace_in_file(synopsys_setup,'__TARGET_LIB__',synth_config.library.target)
    replace_in_file(synopsys_setup,'__LINK_LIB__',synth_config.library.link)
    replace_in_file(synopsys_setup,'__SYMBOL_LIB__',synth_config.library.symbol)
    replace_in_file(synopsys_setup,'__SYNTH_LIB__',synth_config.library.synthetic)
    replace_in_file(top_cons,'__DATE__',date)
    replace_in_file(top_cons,'__TOP__',path.top)
    replace_in_file(top_cons,'__TARGET_LIB__',synth_config.library.target)
    replace_in_file(top_cons,'__RTL_LIST__',path.rtl_list)
    replace_in_file(top_cons,'__PARAMETER__',path.param)
    replace_in_file(top_cons,'__TARGET_LIB__',synth_config.library.target)
    replace_in_file(top_cons,'__LIB_NAME__',synth_config.signal_driving_cell.lib)
    replace_in_file(top_cons,'__WIRE_LOAD_MODEL__',synth_config.wire_load_model)
    replace_in_file(top_cons,'__DRIVE_CELL__',synth_config.signal_driving_cell.name)
    replace_in_file(top_cons,'__DRIVE_PIN__',synth_config.signal_driving_cell.output)
    replace_in_file(top_cons,'__OPERA_CONDITION__',synth_config.opera_condition)
    replace_in_file(top_cons,'__CLOCK_TREE__BUDGET__',budget)

    replace_in_file(top_cons,'__CLOCKS_CONSTRAINT__',os.path.join(path.cons_path,path.top+"_clk.tcl"))
    replace_in_file(top_cons,'__RESET_CONSTRAINT__',os.path.join(path.cons_path,path.top+"_rst.tcl"))
    replace_in_file(top_cons,'__IO_CONSTRAINT__',os.path.join(path.cons_path,path.top+"_io.tcl"))

    cons = ""
    #cons += f"\n{synth_config.path}"

    
    print(cons)

def gen_cons_clk(clock_dict):
    cons = "\n#========================================\n#Clock Constraint"
    if not clock_dict:
        print("No clock data found.")
        return
    
    print(f"Starting to generate CMS clock constraints for {len(clock_dict)} clocks.")
    print("-"*20)

    for name,row_data in clock_dict.items():
        cons += f"\n#Clock {name} - {row_data['comment']}"
        if clock_dict[name]['root'] is None:
            cons += f"\n#----------------------------------------\ncreate_clock -name {name} -period {clock_dict[name]['period']}"
        else:
            if "/" in clock_dict[name]['root']:
                pin_or_port = "pins"
            else:
                pin_or_port = "ports"
            
            if clock_dict[name]['master'] is None:
                cons += f"\nset JITTER [expr {clock_dict[name]['jsrc']} + {clock_dict[name]['jmn']} + {clock_dict[name]['jdc']}]"
                cons += f"\nset SETUP_UNCERTAINTY [expr $ct_budget({clock_dict[name]['type']}.skew) + $ct_budget({clock_dict[name]['type']}.noise) + $JITTER + ({clock_dict[name]['period']} - $ct_budget({clock_dict[name]['type']}.skew) - $ct_budget({clock_dict[name]['type']}.noise) - $JITTER) * $SETUP_MARGIN]"
                cons += f"\nset HOLD_UNCERTAINTY [expr $ct_budget({clock_dict[name]['type']}.skew) + $ct_budget({clock_dict[name]['type']}.noise) + $HOLD_MARGIN]"
                cons += f"\ncreate_clock -name {name} -period {clock_dict[name]['period']} [get_{pin_or_port} {clock_dict[name]['root']}]"
                cons += f"\nset_ideal_network [get_{pin_or_port} {clock_dict[name]['root']}]"
                cons += f"\nset_dont_touch_network [get_{pin_or_port} {clock_dict[name]['root']}]"
                cons += f"\nset_drive 0 [get_{pin_or_port} {clock_dict[name]['root']}]"
                cons += f"\nset_clock_uncertainty  -setup $SETUP_UNCERTAINTY [get_{pin_or_port} {clock_dict[name]['root']}]"
                cons += f"\nset_clock_uncertainty  -hold $HOLD_UNCERTAINTY [get_{pin_or_port} {clock_dict[name]['root']}]"
                cons += f"\nset_clock_transition  -max $ct_budget({clock_dict[name]['type']}.trans.max) [get_{pin_or_port} {clock_dict[name]['root']}]"
                cons += f"\nset_clock_transition  -min $ct_budget({clock_dict[name]['type']}.trans.min) [get_{pin_or_port} {clock_dict[name]['root']}]"
                cons += f"\nset_clock_latency -source -max $ct_budget({clock_dict[name]['type']}.source_latency.max) [get_{pin_or_port} {clock_dict[name]['root']}]"
                cons += f"\nset_clock_latency -source -min $ct_budget({clock_dict[name]['type']}.source_latency.min) [get_{pin_or_port} {clock_dict[name]['root']}]"
                cons += f"\nset_clock_latency -max $ct_budget({clock_dict[name]['type']}.network_latency.max) [get_{pin_or_port} {clock_dict[name]['root']}]"
                cons += f"\nset_clock_latency -min $ct_budget({clock_dict[name]['type']}.network_latency.min) [get_{pin_or_port} {clock_dict[name]['root']}]"
            else:
                #mst_clk = 
                mst_source = clock_dict[clock_dict[name]['master']]['root']
                if not "/" in mst_source:
                    mst_source = f"[get_port {mst_source}]"
                if match := re.match(r"-div\s+(\d+)$",clock_dict[name]['period']):
                    generated_period = f"-divide_by {match.group(1)}"
                elif match := re.match(r"-multi\s+(\d+)$",clock_dict[name]['period']):
                    generated_period = f"-multiply_by {match.group(1)}"
                elif match := re.match(r"-edges\s+\{\s*\d+\s+\d+\s+\d+\s*\}$",clock_dict[name]['period']):
                    generated_period = clock_dict[name]['period']
                else:
                    generated_period = clock_dict[name]['period']
                cons += f"\ncreate_generated_clock -name {name} {generated_period} -source {mst_source} [get_{pin_or_port} {clock_dict[name]['root']}]" 
    cons += f"\n#----------------------------------------\n#Set var"

    return cons


def gen_cons_rst(rst_dict,clock_dict):
    cons = "\n#========================================\n#Reset Constraint"
    if not rst_dict:
        print("No Reset data found.")
        return
    
    print(f"Starting to generate CMS Reset constraints for {len(rst_dict)} reset.")
    print("-"*20)
    
    for reset,row_data in rst_dict.items():
        cons += f"\nset_ideal_network [get_port {reset}]"
        cons += f"\nset_dont_touch_network [get_port {reset}]"
        cons += f"\nset_drive 0 [get_port {reset}]"
        cons += f"\nset_false_path -from [get_port {reset}]"
    
    return cons

def gen_cons_io(io_dict,clock_dict):
    input_ports_except_clk = ""
    output_ports_except_clk = ""
    cons = "\n#========================================\n#IO Constraint"
    if not io_dict:
        print("No IO data found.")
        return
    
    print(f"Starting to generate CMS IO constraints for {len(io_dict)} pins.")
    print("-"*20)
    #for row in enumerate(clock_list,start=1):
    for pin,row_data in io_dict.items():
        if io_dict[pin]['direction'] in ("input","in"):
            input_ports_except_clk += f" {pin}"
            if io_dict[pin]['delay_min'] is not None:
                delay = clock_dict[io_dict[pin]['clock']]['period'] * io_dict[pin]['delay_min']
                cons += f"\nset_input_delay -clock {io_dict[pin]['clock']} -min {delay} [get_ports {pin}]"
            if io_dict[pin]['delay_max'] is not None:
                delay = clock_dict[io_dict[pin]['clock']]['period'] * io_dict[pin]['delay_max']
                cons += f"\nset_input_delay -clock {io_dict[pin]['clock']} -max {delay} [get_ports {pin}]"
        elif io_dict[pin]['direction'] in ("output","out"):
            output_ports_except_clk += f" {pin}"
            if io_dict[pin]['delay_min'] is not None:
                delay = clock_dict[io_dict[pin]['clock']]['period'] * io_dict[pin]['delay_min']
                cons += f"\nset_output_delay -clock {io_dict[pin]['clock']} -min {delay} [get_ports {pin}]"
            if io_dict[pin]['delay_max'] is not None:
                delay = clock_dict[io_dict[pin]['clock']]['period'] * io_dict[pin]['delay_max']
                cons += f"\nset_output_delay -clock {io_dict[pin]['clock']} -max {delay} [get_ports {pin}]"
            if io_dict[pin]['load_min'] is not None:
                load = io_dict[pin]['load_min']
                cons += f"\nset_load -min {load} [get_ports {pin}]"
            if io_dict[pin]['load_max'] is not None:
                load = io_dict[pin]['load_max']
                cons += f"\nset_load -max {load} [get_ports {pin}]"
    cons += "\n#----------------------------------------\n#Set var"
    cons += f"\nset NON_CLK_INPUT_PORTS [get_ports -quiet \"{input_ports_except_clk}\"]"
    cons += f"\nset NON_CLK_OUTPUT_PORTS [get_ports -quiet \"{output_ports_except_clk}\"]"
    cons += "\n#----------------------------------------\n#Set input"
    cons += "\nset_driving_cell -lib_cell ${DRIVE_CELL} -pin ${DRIVE_PIN} ${NON_CLK_INPUT_PORTS}"
    cons += "\n#----------------------------------------\n#Set output"
    cons += "\n"
    cons += "\n#----------------------------------------\n#Set false path"
    cons += "\nset_false_path -from ${NON_CLK_INPUT_PORTS} -thr ${NON_CLK_OUTPUT_PORTS}"
    return cons

def main(filename):
    cons = ""
    wb = openpyxl.load_workbook(filename)

    if 'path' in wb.sheetnames:
        path = parse_path(wb['path'])
    if 'pt' in wb.sheetnames:
        pt_config = parse_config(wb['pt'],path)
        #cons_pt = gen_cms_cons_pt(pt_config,design)
    if 'synth' in wb.sheetnames:
        synth_config = parse_config(wb['synth'],path)
        cons_synth = gen_cms_cons_synth(synth_config,path)

    if 'clock' in wb.sheetnames:
        clock_dict = parse_clock(wb['clock'])
        #print (clock_list)
        cons_clk = gen_cons_clk(clock_dict)
    if 'reset' in wb.sheetnames:
        rst_dict = parse_rst(wb['reset'])
        cons_rst = gen_cons_rst(rst_dict,clock_dict)
    if 'io' in wb.sheetnames:
        io_dict = parse_io(wb['io'])
        #print (io_list)
        cons_io = gen_cons_io(io_dict,clock_dict)
    #print(pt_config)
    #print(synth_config)
    #print(clock_list)
    with open(os.path.join(path.cons_path,path.top+"_clk.tcl"),"w",encoding="utf-8")as f:
        f.write(cons_clk)
    with open(os.path.join(path.cons_path,path.top+"_rst.tcl"),"w",encoding="utf-8")as f:
        f.write(cons_rst)
    with open(os.path.join(path.cons_path,path.top+"_io.tcl"),"w",encoding="utf-8")as f:
        f.write(cons_io)

    #print (cons)

    
    wb.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python cms.py <excel_file>")
        sys.exit(1)
    
    table_path = sys.argv[1]
    try:
        result = main(table_path)
    except Exception as e:
        print("Error:", e)

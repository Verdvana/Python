import sys
import re
import os
import glob
import openpyxl
from dataclasses import dataclass,field

#============================================================
# Define data class
@dataclass
class Design:
    path:str="None"
    top:str="None"
    rtl_path:str="None"
    rtl_list:str="None"
    tb_path:str="None"
    param:str="None"
    lib_list:str="None"

@dataclass
class Range:
    min:str="None"
    max:str="None"
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
class Config:
    signal_driving_cell:DrivingCell=field(default_factory=DrivingCell)
    clock_driving_cell:DrivingCell=field(default_factory=DrivingCell)
    signal_trans:Range=field(default_factory=Range)
    output_load:Range=field(default_factory=Range)
    output_trans:Range=field(default_factory=Range)
    output_delay:Range=field(default_factory=Range)
    input_delay:Range=field(default_factory=Range)
    input_trans:Range=field(default_factory=Range)
    setup_margin:str="None"
    hold_margin:str="None"
    sm_ct:ClockTree=field(default_factory=ClockTree)
    md_ct:ClockTree=field(default_factory=ClockTree)
    lg_ct:ClockTree=field(default_factory=ClockTree)
    raw_ct:ClockTree=field(default_factory=ClockTree)

def error_exit(msg):
    print(f"错误：{msg}", file=sys.stderr)
    sys.exit(1)


def parse_design(sheet):
    design=Design()
    design.top = sheet['B2'].value
    if design.top is None or str(design.top).strip() == "":
        error_exit("未定义顶层模块名称")
    print(f"Design top module name: {design.top}")
    if design.top in os.environ:
        print(f"Capture the environment variable {design.top} as the top module name.")
        raw_path = os.environ.get(design.top)
    else:
        raw_path = sheet['B1'].value
        if raw_path is None:
            error_exit("Error: Not define design path")

    design.rtl_path = sheet['B3'].value
    design.rtl_path = re.sub(r"\$\{top\}",raw_path,design.rtl_path,flags=re.IGNORECASE)
    rtl_pattern = ["*.v", "*.sv", "*.vhd", "*.vhdl"]
    design.rtl_list = []
    for pattern in rtl_pattern:
        design.rtl_list.extend(glob.glob(os.path.join(design.rtl_path, pattern)))

    if not design.rtl_list:
        error_exit(f"Error: Not find RTL files in {design.rtl_path} with pattern {rtl_pattern}")
    design.rtl_list = " ".join(os.path.basename(f) for f in design.rtl_list)
    print(f"RTL files found: {design.rtl_list}")

    design.lib_list = sheet['B5'].value
    if design.lib_list is None or str(design.lib_list).strip() == "":
        error_exit("Error: Not define library files")
    for ch in [",", ";", "\n", "\r"]:
        design.lib_list = design.lib_list.replace(ch, " ")
    design.lib_list = " ".join(design.lib_list.split())
    print(f"Library files: {design.lib_list}")


    return design

def parse_config(sheet):
    config=Config()
    
    config.signal_driving_cell.name     = sheet['B3'].value
    config.signal_driving_cell.output   = sheet['D3'].value
    config.signal_driving_cell.input    = sheet['E3'].value
    config.signal_driving_cell.lib      = sheet['F3'].value
    config.clock_driving_cell.name      = sheet['B4'].value
    config.clock_driving_cell.output    = sheet['D4'].value
    config.clock_driving_cell.input     = sheet['E4'].value
    config.clock_driving_cell.lib       = sheet['F4'].value
    config.signal_trans.min             = sheet['B7'].value
    config.signal_trans.max             = sheet['C7'].value
    config.output_load.min              = sheet['B8'].value
    config.output_load.max              = sheet['C8'].value
    config.output_trans.min             = sheet['B9'].value
    config.output_trans.max             = sheet['C9'].value
    config.output_delay.min             = sheet['B10'].value
    config.output_delay.max             = sheet['C10'].value
    config.input_delay.min              = sheet['B11'].value
    config.input_delay.max              = sheet['C11'].value
    config.input_trans.min              = sheet['B12'].value
    config.input_trans.max              = sheet['C12'].value
    config.setup_margin                 = sheet['B14'].value
    config.hold_margin                  = sheet['B15'].value
    config.sm_ct.source_latency.min     = sheet['B20'].value
    config.sm_ct.source_latency.max     = sheet['C20'].value
    config.sm_ct.network_latency.min    = sheet['D20'].value
    config.sm_ct.network_latency.max    = sheet['E20'].value
    config.sm_ct.trans.min              = sheet['F20'].value
    config.sm_ct.trans.max              = sheet['G20'].value
    config.sm_ct.skew                   = sheet['H20'].value
    config.sm_ct.noise                  = sheet['I20'].value
    config.md_ct.source_latency.min     = sheet['B21'].value
    config.md_ct.source_latency.max     = sheet['C21'].value
    config.md_ct.network_latency.min    = sheet['D21'].value
    config.md_ct.network_latency.max    = sheet['E21'].value
    config.md_ct.trans.min              = sheet['F21'].value
    config.md_ct.trans.max              = sheet['G21'].value
    config.md_ct.skew                   = sheet['H21'].value
    config.md_ct.noise                  = sheet['I21'].value
    config.lg_ct.source_latency.min     = sheet['B22'].value
    config.lg_ct.source_latency.max     = sheet['C22'].value
    config.lg_ct.network_latency.min    = sheet['D22'].value
    config.lg_ct.network_latency.max    = sheet['E22'].value
    config.lg_ct.trans.min              = sheet['F22'].value
    config.lg_ct.trans.max              = sheet['G22'].value
    config.lg_ct.skew                   = sheet['H22'].value
    config.lg_ct.noise                  = sheet['I22'].value
    config.raw_ct.source_latency.min    = sheet['B23'].value
    config.raw_ct.source_latency.max    = sheet['C23'].value
    config.raw_ct.network_latency.min   = sheet['D23'].value
    config.raw_ct.network_latency.max   = sheet['E23'].value
    config.raw_ct.trans.min             = sheet['F23'].value
    config.raw_ct.trans.max             = sheet['G23'].value
    config.raw_ct.skew                  = sheet['H23'].value
    config.raw_ct.noise                 = sheet['I23'].value
    
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

def gen_cms_cons_synth(synth_config,design):
    print (synth_config)
    cons = "\n#========================================\n#Add LIB"
    cons += f"\nread_db [list {design.lib_list}]"
    cons += f"\nset TOP_MODULE {design.top}"
    cons += f"\nanalyze -f sverilog [list {design.rtl_list}]"
    cons += f"\nelaborate $TOP_MODULE -parameter \" \""
    cons += f"\ncurrent_design TOP_MODULE"
    cons += "\nif {[check_design] == 0} {\n   echo \"Check Design Error!\";\n   exit;\n}"
    cons += "\nreset_design"
    cons += "\nuniquify"       
    cons += "\nset uniquify_naming_style   \“%s_%d\”"
    cons += "\nwrite -f ddc -hierarchy -output ${UNMAPPED_PATH}/${TOP_MODULE}.ddc"
    
    print(cons)

def gen_cms_cons_clk(clock_dict):
    cons = "\n#========================================\n#Clock Constraint"
    if not clock_dict:
        print("No clock data found.")
        return
    
    print(f"Starting to generate CMS clock constraints for {len(clock_dict)} clocks.")
    print("-"*20)

    for name,row_data in clock_dict.items():
        
        if clock_dict[name]['root'] is None:
            cons += f"\ncreate_clock -name {name} -period {clock_dict[name]['period']}"
        else:
            if "/" in clock_dict[name]['root']:
                pin_or_port = "pins"
            else:
                pin_or_port = "ports"
            
            if clock_dict[name]['master'] is None:
                cons += f"\ncreate_clock -name {name} -period {clock_dict[name]['period']} [get_{pin_or_port} {clock_dict[name]['root']}]"
                cons += f"\nset_ideal_network [get_{pin_or_port} {clock_dict[name]['root']}]"
                cons += f"\nset_dont_touch_network [get_{pin_or_port} {clock_dict[name]['root']}]"
                cons += f"\nset_drive [get_{pin_or_port} {clock_dict[name]['root']}]"
                cons += f"\nset_clock_uncertaity  -setup $CLK_SKEW [get_{pin_or_port} {clock_dict[name]['root']}]"
                cons += f"\nset_clock_transition  -max $CLK_TRAN [get_{pin_or_port} {clock_dict[name]['root']}]"
                cons += f"\nset_clock_latency -source -max $CLK_SRC_LATENCY [get_{pin_or_port} {clock_dict[name]['root']}]"
                cons += f"\nset_clock_latency -max $CLK_LATENCY [get_{pin_or_port} {clock_dict[name]['root']}]"
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
    
    return cons


def gen_cms_cons_rst(rst_dict,clock_dict):
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
    
    return cons

def gen_cms_cons_io(io_dict,clock_dict):
    cons = "\n#========================================\n#IO Constraint"
    if not io_dict:
        print("No IO data found.")
        return
    
    print(f"Starting to generate CMS IO constraints for {len(io_dict)} pins.")
    print("-"*20)
    #for row in enumerate(clock_list,start=1):
    for pin,row_data in io_dict.items():
        if io_dict[pin]['direction'] in ("input","in"):
            if io_dict[pin]['delay_min'] is not None:
                delay = clock_dict[io_dict[pin]['clock']]['period'] * io_dict[pin]['delay_min']
                cons += f"\nset_input_delay -clock {io_dict[pin]['clock']} -min {delay} [get_ports {pin}]"
            if io_dict[pin]['delay_max'] is not None:
                delay = clock_dict[io_dict[pin]['clock']]['period'] * io_dict[pin]['delay_max']
                cons += f"\nset_input_delay -clock {io_dict[pin]['clock']} -max {delay} [get_ports {pin}]"
        elif io_dict[pin]['direction'] in ("output","out"):
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
    return cons

def main(filename):
    cons = ""
    wb = openpyxl.load_workbook(filename)

    if 'design' in wb.sheetnames:
        design = parse_design(wb['design'])
    if 'pt' in wb.sheetnames:
        pt_config = parse_config(wb['pt'])
        #cons_pt = gen_cms_cons_pt(pt_config,design)
    if 'synth' in wb.sheetnames:
        synth_config = parse_config(wb['synth'])
        cons_synth = gen_cms_cons_synth(synth_config,design)

    if 'clock' in wb.sheetnames:
        clock_dict = parse_clock(wb['clock'])
        #print (clock_list)
        cons_clk = gen_cms_cons_clk(clock_dict)
    if 'reset' in wb.sheetnames:
        rst_dict = parse_rst(wb['reset'])
        cons_rst = gen_cms_cons_rst(rst_dict,clock_dict)
    if 'io' in wb.sheetnames:
        io_dict = parse_io(wb['io'])
        #print (io_list)
        cons_io = gen_cms_cons_io(io_dict,clock_dict)
    #print(pt_config)
    #print(synth_config)
    #print(clock_list)
    

    cons += cons_clk
    cons += cons_rst
    cons += cons_io
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
import sys
import re
import openpyxl
from dataclasses import dataclass,field

@dataclass
class ClockAttr:
    level:str="None"
    group:str="None"
    type:str="None"
    period:str="None"
    name:str="None"
    master:str="None"
    jsrc:float=0
    jmn:float=0
    jdc:float=0
    root:str="None"
    comment:str="None"


@dataclass
class DrivingCell:
    name:str="None"
    input:str="None"
    output:str="None"
    lib:str="None"

@dataclass
class Range:
    min:str="None"
    max:str="None"

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

def find_cell(sheet, target):
    for row in sheet.iter_rows():
        for cell in row:
            if cell.value == target:
                return cell
    return None

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
    clock_list = []
    row_index  = 4
    while True:
        if sheet.cell(row=row_index,column=1).value in (None, ""):
            break

        row_data = []
        for col_index in range(1, sheet.max_column + 1):
            cell_value = sheet.cell(row=row_index, column=col_index).value
            row_data.append(cell_value)
        
        clock_list.append(row_data)
        row_index += 1
    return clock_list
def parse_io(sheet):
    io_list = []
    row_index  = 4
    while True:
        if sheet.cell(row=row_index,column=1).value in (None, ""):
            print("xxxyyy")
            break

        row_data = []
        for col_index in range(1, sheet.max_column + 1):
            cell_value = sheet.cell(row=row_index, column=col_index).value
            row_data.append(cell_value)
        
        io_list.append(row_data)
        row_index += 1
    return io_list
def gen_cms_cons_clk(clock_list):
    cons = "\n#========================================\n#Clock Constraint"
    if not clock_list:
        print("No clock data found.")
        return
    
    print(f"Starting to generate CMS clock constraints for {len(clock_list)} clocks.")
    print("-"*20)
    #print(clock_list)

    #for row in enumerate(clock_list,start=1):
    for row in clock_list:
        if not len(row) == 11:
            print(f"Data for clock {row} is incomplete, skipping.")
            continue
        ClockAttr.level,ClockAttr.group,ClockAttr.type,ClockAttr.period,ClockAttr.name,ClockAttr.master,ClockAttr.jsrc,ClockAttr.jmn,ClockAttr.jdc,ClockAttr.root,ClockAttr.comment=row
        #print(ClockAttr.level,ClockAttr.group,ClockAttr.type,ClockAttr.period,ClockAttr.name,ClockAttr.master,ClockAttr.jsrc,ClockAttr.jmn,ClockAttr.jdc,ClockAttr.root,ClockAttr.comment)
        
        #print (ClockAttr.master,ClockAttr.root)
        if ClockAttr.root is None:
            cons += f"\ncreate_clock -name {ClockAttr.name} -period {ClockAttr.period}"
        else:
            if "/" in ClockAttr.root:
                pin_or_port = "pins"
            else:
                pin_or_port = "ports"
            
            if ClockAttr.master is None:
                cons += f"\ncreate_clock -name {ClockAttr.name} -period {ClockAttr.period} [get_{pin_or_port} {ClockAttr.root}]"
                cons += f"\nset_ideal_network [get_{pin_or_port} {ClockAttr.root}]"
                cons += f"\nset_dont_touch_network [get_{pin_or_port} {ClockAttr.root}]"
                cons += f"\nset_drive [get_{pin_or_port} {ClockAttr.root}]"
                cons += f"\nset_clock_uncertaity  -setup $CLK_SKEW [get_{pin_or_port} {ClockAttr.root}]"
                cons += f"\nset_clock_transition  -max $CLK_TRAN [get_{pin_or_port} {ClockAttr.root}]"
                cons += f"\nset_clock_latency -source -max $CLK_SRC_LATENCY [get_{pin_or_port} {ClockAttr.root}]"
                cons += f"\nset_clock_latency -max $CLK_LATENCY [get_{pin_or_port} {ClockAttr.root}]"
            else:
                mst_source = next((item[9] for item in clock_list if item[4] == ClockAttr.master),None)
                if not "/" in mst_source:
                    mst_source = f"[get_port {mst_source}]"
                if match := re.match(r"-div\s+(\d+)$",ClockAttr.period):
                    ClockAttr.period = f"-divide_by {match.group(1)}"
                elif match := re.match(r"-multi\s+(\d+)$",ClockAttr.period):
                    ClockAttr.period = f"-multiply_by {match.group(1)}"
                elif match := re.match(r"-edges\s+\{\s*\d+\s+\d+\s+\d+\s*\}$",ClockAttr.period):
                    ClockAttr.period = f"{ClockAttr.period}"
                    
                cons += f"\ncreate_generated_clock -name {ClockAttr.name} {ClockAttr.period} -source {mst_source} [get_{pin_or_port} {ClockAttr.root}]" 
    
    return cons

def main(filename):
    cons = ""
    wb = openpyxl.load_workbook(filename)

    if 'clock' in wb.sheetnames:
        clock_list = parse_clock(wb['clock'])
        #print (clock_list)
        cons_clk = gen_cms_cons_clk(clock_list)
    if 'pt' in wb.sheetnames:
        pt_config = parse_config(wb['pt'])
    if 'sync' in wb.sheetnames:
        sync_config = parse_config(wb['sync'])
    if 'io' in wb.sheetnames:
        io_list = parse_io(wb['io'])
        print (io_list)
        #cons_io = gen_cms_cons_io(io_list)
    #print(pt_config)
    #print(sync_config)
    #print(clock_list)
    

    cons += cons_clk
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
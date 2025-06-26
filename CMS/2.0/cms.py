import sys
import openpyxl
from dataclasses import dataclass,field

@dataclass
class DrivingCell:
    name:str="NA"
    input:str="NA"
    output:str="NA"
    lib:str="NA"

@dataclass
class Range:
    min:str="NA"
    max:str="NA"

@dataclass
class ClockTree:
    source_latency:Range=field(default_factory=Range)
    network_latency:Range=field(default_factory=Range)
    trans:Range=field(default_factory=Range)
    skew:str="NA"
    noise:str="NA"


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
    setup_margin:str="NA"
    hold_margin:str="NA"
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

def main(filename):
    wb = openpyxl.load_workbook(filename)

    if 'pt' in wb.sheetnames:
        pt_config = parse_config(wb['pt'])
    
    print(pt_config)
    

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python cms.py <excel_file>")
        sys.exit(1)
    
    table_path = sys.argv[1]
    try:
        result = main(table_path)
    except Exception as e:
        print("Error:", e)
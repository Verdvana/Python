#===================================================================================
# Project Name:				__TOP__
# Department:				Qualcomm (Shanghai) Co., Ltd.
# Function Description:		__TOP__ top level constraint file
#------------------------------------------------------------------------------
# Version 	Design		Coding		Simulate	  Review		Rel date
# V1.0		Verdvana	Verdvana	Verdvana		  			__DATE__
#-----------------------------------------------------------------------------------
# Version	Modified History
# V1.0		
#===================================================================================

#===================================================
# 添加库文件
#=================================================== 
read_db				[list   __TARGET_LIB__]		;#不加这句list_lib后显示不出来
# 查看库文件
#list_libs

#===================================================
# 添加设计文件
#=================================================== 

# 宏定义
set TOP_MODULE		__TOP_NETLIST_MODULE__			;# 定义顶层文件名
# 读文件
read_verilog	[list	__NETLIST__    ]

#analyze		-f	sverilog	[list	__RTL_LIST__  ]
#elaborate	$TOP_MODULE	-parameter	" __PARAMETER__  "

#设置顶层文件
current_design	$TOP_MODULE

# 检查link
if {[link] == 0} {
	echo "Link Error!";
	exit;
}
# 检查库
list_libs	
# 检查design
list_designs

# 检查语法
#if {[check_design] == 0} {
##	echo "Check Design Error!";
#	exit;
#}

#===================================================
# 复位全部约束
#===================================================
reset_design


#===================================================
# Budget of clock tree
#===================================================
__CLOCK_TREE__BUDGET__

#===================================================
# 约束设置
#===================================================
# 宏定义
set     CLOCK_LIB_NAME      __CLOCK_LIB_NAME__
set     CLOCK_DRIVE_CELL    __CLOCK_DRIVE_CELL__
set     CLOCK_DRIVE_PIN     __CLOCK_DRIVE_PIN__
set     SIGNAL_LIB_NAME     __SIGNAL_LIB_NAME__
set     SIGNAL_DRIVE_CELL   __SIGNAL_DRIVE_CELL__
set     SIGNAL_DRIVE_PIN    __SIGNAL_DRIVE_PIN__
#set     WIRE_LOAD_MODEL     smic18_wl10
set     WIRE_LOAD_MODEL     __WIRE_LOAD_MODEL__
set     OPERA_CONDITION     __OPERA_CONDITION__
#set     ALL_IN_EXCEPT_CLK   [remove_from_collection [all_inputs] [get_ports $CLK_NAME]]
#set     INPUT_DELAY         [expr   $CLK_PERIOD*0.6]
#set     INPUT_TRANSITION    [expr   0.12]

#===================================================
# 时钟约束
#===================================================
source __CLOCKS_CONSTRAINT__

#===================================================
# 复位约束
#===================================================
source __RESET_CONSTRAINT__

#===================================================
# IO约束
#===================================================
source __IO_CONSTRAINT__


#===================================================
# 设置组合电路最大延迟
#===================================================

#set_input_delay     [expr   $CLK_PERIOD*0.1]    -clock  $CLK_NAME   -add_delay  [get_ports a_i]
#set_output_delay    [expr   $CLK_PERIOD*0.1]    -clock  $CLK_NAME   -add_delay  [get_ports y_o]


#===================================================
# 操作条件和线负载模型
#===================================================

# 設置操作条件
set_operating_condition -max            $OPERA_CONDITION    \
                        -max_library    $SIGNAL_LIB_NAME
# 关闭自动选择线负载模型
set     auto_wire_load_selection        false
# 设置线负载模式
set_wire_load_mode      top 
# 设置线负载模型
set_wire_load_model     -name           $WIRE_LOAD_MODEL \
                        -library        $SIGNAL_LIB_NAME


#===================================================
# DRC約束
#===================================================

# 宏定義
#set     MAX_CAPACITANCE     [expr [load_of $LIB_NAME/NAND4X2/Y] *5]
#set_max_capacitance         $MAX_CAPACITANCE    $ALL_IN_EXCEPT_CLK

#===================================================
# 設置分組
#===================================================

# 設置critical_range，通常不能超過時鐘週期的10%
#set     CRITICAL_RANGE      [expr   $CLK_PERIOD*0.1]
# 設置權重，默认为1
#set     WEIGHT              5

# 時鐘分組（reg2reg）
#group_path      -name       $CLK_NAME   -weight	$WEIGHT               			 -critical_range $CRITICAL_RANGE
# 輸入路徑（包含輸入路徑中的組合電路）分組
#group_path      -name       INPUTS      -from	[all_inputs]    			         -critical_range $CRITICAL_RANGE
# 輸出路徑（包含輸出路徑中的組合電路）分組
#group_path      -name       OUTPUTS     -to	[all_outputs]   			         -critical_range $CRITICAL_RANGE
# 輸入與輸出路徑上的組合電路分組
#group_path      -name       COMB        -from	[all_inputs]    -to	[all_outputs]    -critical_range $CRITICAL_RANGE
# 報告分組情況
#report_path_group

group_path  -name   reg2reg     -from   [all_registers] -to [all_registers] -weight 20
group_path  -name   in2reg      -from   [all_inputs]    -to [all_registers]   
group_path  -name   reg2out     -from   [all_registers] -to [all_outputs]
group_path  -name   in2out      -from   [all_inputs]    -to [all_outputs]


#===================================================
# 异常时序定义
#===================================================

# 不约束的时序路径
#set_clock_groups    -asynchronous -group $CLK1_NAME  -group $CLK2_NAME
# 或
#set_false_path -from [get_clocks $CLK1_NAME]    -to [get_clocks $CLK2_NAME]
#set_false_path -from [get_clocks $CLK2_NAME]    -to [get_clocks $CLK1_NAME]

#set_disable_timing      TOP/U1  -from   a   -to     y 
#set_case_analysis       0       [get_ports  sel_i]

# 多周期路径
#set_multicycle_path     -setup  6   -from   FFA/CP  -through    ADD/out     -to     FFB/D
#set_multicycle_path     -hold   5   -from   FFA/CP  -through    ADD/out     -to     FFB/D
#set_multicycle_path     -to     [get_pins q_lac*/D]



# 设置DC多核
#set_host_option		-max_cores      8


update_timing


#===================================================
# 生成報告文件
#===================================================

# report_constraint		-all_violators

# report_timing			-delay_type			max

redirect	-tee	-file	${REPORT_PATH}/report_qor.rpt			{report_qor}

redirect	-tee	-file	${REPORT_PATH}/clock_skew.rpt			{report_clock_timing -type skew}
redirect	-tee	-file	${REPORT_PATH}/clock_attr.rpt			{report_clocks -attributes}

foreach view {VIEW_FUNC_MAX VIEW_FUNC_MIN VIEW_SCAN_MAX VIEW_SCAN_MIN} {
	set_active_analysis_view $view
	redirect	-tee	-file	${REPORT_PATH}/${view}_paths.rpt	{report_timing -transition_time -nets -capacitance -crpr - input_pins}
}


redirect	-tee	-file	${REPORT_PATH}/check_timing.rpt			{check_timing -verbose}
redirect	-tee	-file	${REPORT_PATH}/report_constraint.rpt	{report_constraint	-all_violators}
redirect	-tee	-file	${REPORT_PATH}/check_setup.rpt			{report_timing		-delay_type		max}
redirect	-tee	-file	${REPORT_PATH}/check_hold.rpt			{report_timing		-delay_type		min}
redirect	-tee	-file	${REPORT_PATH}/report_group.rpt			{report_path_group}

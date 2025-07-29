#===================================================================================
# Project Name:				sta_lab
# Department:				Qualcomm (Shanghai) Co., Ltd.
# Function Description:		sta_lab top level constraint file
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
set TOP_MODULE		sta_lab			;# 定义顶层文件名
# 读文件
#read_sverilog	-rtl	[list	__RTL_LIST__    ]

# 检查link
#if {[link] == 0} {
#	echo "Link Error!";
#	exit;
#}

analyze		-f	sverilog	[list	__RTL_LIST__  ]
elaborate	$TOP_MODULE	-parameter	" __PARAMETER__  "

#设置顶层文件
current_design	$TOP_MODULE


# 检查语法
if {[check_design] == 0} {
	echo "Check Design Error!";
	exit;
}

#===================================================
# 复位全部约束
#===================================================
reset_design


#===================================================
# 写入未映射（GTECH）的ddc文件
#===================================================
uniquify;			#把例化的多个模块转化成唯一的模块名字       
set		uniquify_naming_style   “%s_%d”
write	-f  ddc -hierarchy  -output ${UNMAPPED_PATH}/${TOP_MODULE}.ddc

#===================================================
# 输入延迟设置
#===================================================

# 宏定义
set     LIB_NAME            __LIB_NAME__
#set     WIRE_LOAD_MODEL     smic18_wl10
set     WIRE_LOAD_MODEL     __WIRE_LOAD_MODEL__
set     DRIVE_CELL          __DRIVE_CELL__
set     DRIVE_PIN           __DRIVE_PIN__
set     OPERA_CONDITION     typical
set     ALL_IN_EXCEPT_CLK   [remove_from_collection [all_inputs] [get_ports $CLK_NAME]]
set     INPUT_DELAY         [expr   $CLK_PERIOD*0.6]
set     INPUT_TRANSITION    [expr   0.12]

#===================================================
# 运行约束
#===================================================
source	__CONSTRAINT__

# 输出端口插入隔离单元，这里是插入缓存单
set_isolate_ports   -type   buffer                      [all_outputs]


#===================================================
# 操作条件和线负载模型
#===================================================

# 設置操作条件
set_operating_condition -max            $OPERA_CONDITION    \
                        -max_library    $LIB_NAME
# 关闭自动选择线负载模型
set     auto_wire_load_selection        false
# 设置线负载模式
set_wire_load_mode      top 
# 设置线负载模型
set_wire_load_model     -name           $WIRE_LOAD_MODEL \
                        -library        $LIB_NAME

#===================================================
# 面積約束
#===================================================

set_max_area            650000


#===================================================
# 消除多端口互联
#===================================================

set_app_var     verilogout_no_tri                       ture        ;# 三态不要出现assign
set_app_var     verilogout_show_unconnected_pins        ture        ;# 显示寄存器未用到的Q非端口
set_app_var     bus_naming_style                        {%s[%d]}

simplify_constants          -boundary_optimization                  ;# 边界优化
# 相同net插buffer，防 止出现assign
set_fix_multiple_port_nets  -all                        -buffer_constants

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

#===================================================
# 检查时序
#===================================================
check_timing


#===================================================
# 綜合
#===================================================
#ungroup			-flatten	-all

# 设置DC多核
set_host_option		-max_cores      8


# 一次综合
#compile
#compile_ultra
compile		-map_effort high 
#compile	-map_effort high	-retime
#compile	-map_effort high	-area_effort	high 
#compile	-map_effort high	-area_effort	medium
#compile	-map_effort hign	-area_effort	high	-boundary_optimization
#compile	-map_effort hign	-area_effort	high	-scan 

# 二次综合

# 将一次综合中的最差路径单独分组
#group_path		-name		...		-from	...		-to	...	-critical_range	...
#compile		-map_effort hign	-area_effort	high	-boundary_optimization	\
															-incremental_mapping
#compile_ultra						-incr

#===================================================
# 生成后处理文件
#===================================================

change_names			-rules			verilog			-hierarchy
#remove_unconnected_ports		[get_cells -hier *]		.blast_buses
# 生成网表文件
write	-f	ddc			-hierarchy		-output			$MAPPED_PATH/${TOP_MODULE}.ddc
write	-f	verilog		-hierarchy		-output			$MAPPED_PATH/${TOP_MODULE}.v
write_sdc				-version 1.7					$MAPPED_PATH/${TOP_MODULE}.sdc
write_sdf				-version 2.1					$MAPPED_PATH/${TOP_MODULE}.sdf


#===================================================
# 生成報告文件
#===================================================

# report_constraint		-all_violators

# report_timing			-delay_type			max

redirect	-tee	-file	${REPORT_PATH}/check_design.rpt			{check_design}
redirect	-tee	-file	${REPORT_PATH}/check_timing.rpt			{check_timing}
redirect	-tee	-file	${REPORT_PATH}/report_constraint.rpt	{report_constraint	-all_violators}
redirect	-tee	-file	${REPORT_PATH}/check_setup.rpt			{report_timing		-delay_type		max}
redirect	-tee	-file	${REPORT_PATH}/check_hold.rpt			{report_timing		-delay_type		min}
redirect	-tee	-file	${REPORT_PATH}/report_area.rpt			{report_area}
redirect	-tee	-file	${REPORT_PATH}/report_group.rpt			{report_path_group}

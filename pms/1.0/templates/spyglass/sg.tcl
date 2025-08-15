#===================================================================================
# Project Name:				DCD_Top
# Department:				Qualcomm (Shanghai) Co., Ltd.
# Function Description:		DCD_Top top level constraint file
#------------------------------------------------------------------------------
# Version 	Design		Coding		Simulate	  Review		Rel date
# V1.0		Verdvana	Verdvana	Verdvana		  			2023-10-27
#-----------------------------------------------------------------------------------
# Version	Modified History
# V1.0		
#===================================================================================

#===================================================
# 添加库文件
#=================================================== 
# 宏定义
set	TOP_MODULE			__TOP__

set ROOT_DIR			__ROOT_PATH__

new_project		${TOP_MODULE}	-projectwdir	${ROOT_DIR}/work -force
set_option		top	${TOP_MODULE}

read_file	-type	sourcelist	${ROOT_DIR}/work/filelist.f
#read_file	-type	verilog	{lib_xxx}			;#读取memory,std_cell等库文件
read_file   -type   sgdc    ${ROOT_DIR}/cn/${TOP_MODULE}.sgdc	;#读取sgdc文件
read_file	-type	awl		${ROOT_DIR}/cn/${TOP_MODULE}.awl

#set_option	default_waiver_file	${TOP_MODULE}.awl

#===================================================
# Spyglass setup
#=================================================== 

#set_option sdc2sgdc yes
set_option enable_precompile_vlog yes
set_option sort yes
#set_option 87 yes
set_option language_mode mixed
set_option designread_disable_flatten yes
set_option enableSV yes
set_parameter enable_generated_clocks yes
#set_parameter enable_glitchfreecell_detection yes
set_parameter pt no 
set_option sgsyn_clock_gating 1
set_option allow_module_override yes
set_option vlog2001_generate_name yes
set_option handlememory yes
set_option define_cell_sim_depth 11
set_option mthresh 400000
#set_option incdir {}

#current_methodology $SPYGLASS_HOME/GuideWare/latest/block/rtl_handoff

##lint rtl
current_goal lint/lint_rtl -top ${TOP_MODULE}
set_goal_option ignorerules RegInputOutput-ML
run_goal
write_report moresimple > ${ROOT_DIR}/reports/${TOP_MODULE}_lint.rpt

##cdc setup
current_goal cdc/cdc_setup_check -top ${TOP_MODULE}
run_goal
write_report moresimple > ${ROOT_DIR}/reports/${TOP_MODULE}_cdc_setup.rpt

#cdc verify struct
current_goal cdc/cdc_verify_struct -top ${TOP_MODULE}
run_goal
write_report moresimple > ${ROOT_DIR}/reports/${TOP_MODULE}_cdc_verify_struct.rpt

#cdc verify
current_goal cdc/cdc_verify -top ${TOP_MODULE}
run_goal
write_report moresimple > ${ROOT_DIR}/reports/${TOP_MODULE}_cdc_verify.rpt

#cdc abstract
current_goal cdc/cdc_abstract -top ${TOP_MODULE}
run_goal
write_report moresimple > ${ROOT_DIR}/reports/${TOP_MODULE}_cdc_abstract.rpt

##rdc verify struct
#current_goal cdc/cdc_verify_struct -top ${TOP_MODULE}
#run_goal
#write_report moresimple > ${TOP_MODULE}_rdc_verify_struct.rpt

save_project -force ${TOP_MODULE}.prj

exit -force

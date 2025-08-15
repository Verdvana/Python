#===================================================================================
# Project Name:			    __TOP__
# Department:		        Qualcomm (Shanghai) Co., Ltd. 
# Function Description:	    __TOP__ Makefile
#------------------------------------------------------------------------------
# Version 	Design		Coding		Simulate	  Review		Rel date
# V1.0	    Verdvana	Verdvana	Verdvana                    __DATE__
#-----------------------------------------------------------------------------------
# Version	  Modified History
# V1.0		
#===================================================================================

.PHONY: sg gui clean all

#===================================================
# 定义
#=================================================== 

# 指定可执行文件名称
TOP = __TOP__
ROOT_DIR = __ROOT_PATH__

# 宏定义

# 编译命令
# SG
sg_shell		=	sg_shell -tcl ${ROOT_DIR}/scripts/${TOP}.tcl 
sg_gui			=	spyglass -project ${TOP}.prj			

#===================================================
# 执行
#=================================================== 

# RUN
sg:		
			make clean
			cd ./work && ${sg_shell}
gui:
			cd ./work && ${sg_gui}
clean:
			rm -rf ./work/${TOP}* ./reports/*	./work/gui_command.log

all:
			make sg
			make gui

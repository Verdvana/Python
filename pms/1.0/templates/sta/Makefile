.PHONY:	sta  clean

CURRENT_TIME := `date  "+%Y-%m-%d_%H:%M:%S"`

sta:
		make clean
		cd ./work && pt_shell -f __SCRIPT__ | tee  pt_shell_${CURRENT_TIME}.log

clean:
		rm -rf  ./reports/*
		cd ./work/ && rm -rf [^.]*

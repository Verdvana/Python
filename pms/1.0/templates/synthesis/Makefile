.PHONY:	syn  clean

CURRENT_TIME := `date  "+%Y-%m-%d_%H:%M:%S"`

syn:
		make clean
		cd ./work && dc_shell -f __SCRIPT__ | tee  dc_shell_${CURRENT_TIME}.log

clean:
		rm -rf 	./unmapped/* ./mapped/* ./reports/*
		cd ./work/ && rm -rf [^.]*

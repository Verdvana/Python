#打印
print (52.0)
print("*845cc%")
print('"*845cc%"')
print('\'*845cc%\'')
print(r'\n*845cc%\n')

print(3+1)
print("3+1")

print("hello","xscc")

fp=open("D:/X.TXT","a+")
print("hello world",file=fp)
fp.close()


print("hello","xscc")
print(chr(0b100111001011000))
print(ord("乘"))

print("======")



array = [1,2,3,4]
array = array[-1::-1]                     #[4,3,2,1]
print (array)
for cell in array:
    print (f"xxx:{cell}")
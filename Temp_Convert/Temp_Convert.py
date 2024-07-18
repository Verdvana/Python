#华氏度-摄氏度 转换
print("华氏度-摄氏度 转换")
temp = input("请输入单位（‘C’or‘F’）的温度值：")

if temp[-1] in ['F','f']:
    c = (eval(temp[0:-1])-32)/1.8
    print("转换后的温度是{:.2f}C".format(c))
elif temp[-1] in ['C','c']:
    f = 1.8*eval(temp[0:-1])+32
    print("转换后的温度是{:.2f}F".format(f))
else:
    print("输入格式错误")



print('Hello World')
name = input('please enter your name: ')
print('hello,', name)
number = input ('pleasr enter a number(0<number<1000) :')
if int(number) > 100 :
    print('number>100')
else:
    print('number<100')

for number in range(1, 6):
    if number > 3:
        break
    else:
        print(number)
else:
    print("结束")

i = 1

while 1:
    x = i*i
    i = i+15
    print (x)

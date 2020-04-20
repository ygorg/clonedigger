class MyClass:
    def __init__(self):
        self.a = 1
        self.a += 4


def f(a, b):
    global c
    return a + b + c


def pp(a, i):
    x = a
    y = f(x, i)
    print(y)


def gg(a, b, j):
    x = a + b
    y = f(x, j)
    print(y)


if __name__ == '__main__':
    g = lambda i: i + 5
    pp(3, i=3)
    gg(3, 4, 8)

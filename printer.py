import math
import serial
import numpy as np
import matplotlib.pyplot as plt

class Printer:
    CHARACTER_SET_8x16 = 0x00
    CHARACTER_SET_12x20 = 0x01
    CHARACTER_SET_7x16 = 0x02
    PRINT_HEAD_DOTS = 384

    def __init__(self, port='/dev/ttyUSB0', baudrate=9600, **kwargs):
        self.ser = serial.Serial(port, baudrate, **kwargs)
        self.ser.close()
        self.ser.open()

    def set_print_speed(self, speed):
        assert(speed <= 100 and speed >= 0)
        T = round(speed / 100 * (1<<16))
        hi = T >> 8
        lo = T & 255
        print(hi, lo, T)
        self.ser.write(bytes.fromhex('1d73')+bytes([hi, lo]))


    def select_font(self, charset):
        assert(charset in list([Printer.CHARACTER_SET_8x16,
            Printer.CHARACTER_SET_12x20,
            Printer.CHARACTER_SET_7x16]))
        self.ser.write(bytes.fromhex('1b25')+bytes([charset]))

    def print_text(self, text):
        self.ser.write(bytes(text, 'ascii'))

    def print_graphics(self, image, expand=0):
        width = image.shape[1]
        print(width)
        height = image.shape[0]

        assert(image.ndim == 2)
        assert(expand <= 3)
        assert(image.shape[1] <= Printer.PRINT_HEAD_DOTS)
        databuf = bytes()

        iterator = np.nditer(image, flags=['multi_index'])
        curbyte = 0x00
        curbytepos = 0x00
        while not iterator.finished:
            y,x = iterator.multi_index
            #print("({}, {}) {}     ".format(x,y,iterator[0]))

            if image[y,x] == 0:
                curbyte &= 255 - (1<<(7-curbytepos))
            else:
                curbyte ^= (1<<(7-curbytepos))

            iterator.iternext()
            curbytepos+=1
            if(curbytepos == 8):
                databuf += bytes([curbyte])
                curbytepos = 0
                curbyte = 0x00
        if curbytepos != 0:
            databuf += bytes([curbyte])


        n4 = expand
        bytelen = len(databuf)
        n3 = bytelen >> 16
        n2 = (bytelen & 65535) >> 8
        n1 = bytelen & 255

        n5 = 0x00
        n6 = math.ceil(width/8)

        params = bytes.fromhex('1b2a') + bytes([n1, n2, n3, n4, n5, n6])
        self.ser.write(params)
        self.ser.write(databuf)


    def get_status(self):
        self.ser.write(bytes.fromhex('1b76')) # Request status
        return int(self.ser.read(1).hex(), 16)

    def is_power_supply_ok(self):
        return not bool(self.get_status() & (1<<3))

    def is_online(self):
        return bool(self.get_status() & (1<<5))

    def close(self):
        self.ser.close()

    def __del__(self):
        self.close()

if __name__ == '__main__':
    p = Printer(dsrdtr=True)
    print("Online: ", p.is_online())
    print("Power supply:", p.is_power_supply_ok())
    p.select_font(p.CHARACTER_SET_12x20)
    p.set_print_speed(0)
    p.print_text('Hello World!\n\n\n\n')
    """image = np.ones([10,16])
    image[8] = np.zeros([16])
    image[1] = np.concatenate((np.zeros([14]), np.ones([2])))
    image[4] = np.zeros([16])
    image[2] = np.zeros([16])
    print(image)"""
    image = plt.imread("tux.jpg")
    print(image.shape)
    p.print_graphics(image, expand=0)
    p.close()

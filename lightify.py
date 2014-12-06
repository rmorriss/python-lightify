#!/usr/bin/python
#
# Copyright 2014 Mikael Magnusson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

#
# WIP Python module for Osram lightify
# Communicates with a gateway connected to the same LAN via TCP port 4000
# using a binary protocol
#

import binascii
import socket
import sys
import struct
import time

PORT = 4000

# Commands
# 13 all light status (returns list of light address, light status, light name)
# 1e group list (returns list of group id, and group name)
# 26 group status (returns group id, group name, and list of light addresses)
# 31 set group luminance
# 32 set group onoff
# 33 set group temp
# 36 set group colour
# 68 light status (returns light address and light status (?))

class Light:
    def __init__(self, addr, name):
        self.__addr = addr
        self.__name = name

    def name(self):
        return self.__name

    def addr(self):
        return self.__addr

    def __str__(self):
        return "<light: %s>" % self.name()

    def on(self):
        return self.__on

    def set_on(self, on):
        self.__on = on

    def lum(self):
        return self.__lum

    def set_lum(self, lum):
        self.__lum = lum

    def temp(self):
        return self.__temp

    def set_temp(self, temp):
        self.__temp = temp

    def rgb(self):
        return (self.red(), self.green(), self.blue())

    def set_rgb(self, r, g, b):
        self.__r = r
        self.__g = g
        self.__b = b

    def red(self):
        return self.__r

    def green(self):
        return self.__g

    def blue(self):
        return self.__b

class Group:
    def __init__(self):
        pass

    def name(self):
        return self.__name

    def id(self):
        return self.__id

    def __str__(self):
        return "<group: %s>" % self.name()


class Lightify:
    def __init__(self, host):
        self.__seq = 1
        self.__groups = {}
        self.__lights = {}

        try:
            self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error, msg:
            sys.stderr.write("[ERROR] %s\n" % msg[1])
            sys.exit(1)
 
        try:
            self.__sock.connect((host, PORT))
        except socket.error, msg:
            sys.stderr.write("[ERROR] %s\n" % msg[1])
            sys.exit(2)

    def groups(self):
        return self.__groups

    def lights(self):
        return self.__lights

    def next_seq(self):
        self.__seq = self.__seq + 1
        return self.__seq

    def build_global_command(self, command, data):
        length = 6 + len(data)

        return struct.pack("<H6B", length, 0x02, command, 0, 0, 0x7, self.next_seq()) + data

    def build_command(self, command, group, data):
        length = 14 + len(data)

        return struct.pack("<H14B", length, 0x02, command, 0, 0, 0x7, self.next_seq(), group, 0, 0, 0, 0, 0, 0, 0) + data

    def onoff(self, group, on):
        command = 0x32
        return self.build_command(command, group, struct.pack("<B", on))


    def build_temp(self, group, temp):
        command = 0x33
        return self.build_command(command, group, struct.pack("<HH", temp, 10))


    def build_luminance(self, group, luminance, time):
        command = 0x31
        return self.build_command(command, group, struct.pack("<BH", luminance, time))

    def colour(self, group, red, green, blue, time):
        command = 0x36
        return self.build_command(command, group, struct.pack("<BBBBH", red, green, blue, 0xff, time))

    def build_group_info(self, group):
        command = 0x26
        return self.build_command(command, group, "")

    def build_all_light_status(self, flag):
        command = 0x13
        return self.build_global_command(command, struct.pack("<B", flag))

    def build_light_status(self, light):
        command = 0x68
        return self.build_global_command(command, struct.pack("<Q", light))


    def build_group_list(self):
        return self.build_global_command(0x1e, "")

# WIP
    def group_list(self):
        groups = {}
        data = self.build_group_list()
        print 'sending "%s"' % binascii.hexlify(data)
        self.__sock.sendall(data)
        data = self.recv()
        (num,) = struct.unpack("<H", data[7:9])
        print 'Num %d' % num
        for i in range(0, num):
            pos = 9+i*18
            payload = data[pos:pos+18]

            (idx, name) = struct.unpack("<H16s", payload)

            groups[idx] = name
            print "Idx %d: '%s'" % (idx, name)

        return groups

    def group_info(self, group):
        lights = []
        data = self.build_group_info(group)
        print 'sending "%s"' % binascii.hexlify(data)
        self.__sock.sendall(data)
        data = self.recv()
        payload = data[7:]
        (idx, name, num) = struct.unpack("<H16sB", payload[:19])
        print "Idx %d: '%s' %d" % (idx, name, num)
        for i in range(0,num):
            pos = 7 + 19 + i * 8
            payload = data[pos:pos+8]
            (addr,) = struct.unpack("<Q", payload[:8])
            print "%d: %x" % (i, addr)
            lights.append(addr)

        #self.read_light_status(addr)
        return lights


    def recv(self):
        lengthsize = 2
        data = self.__sock.recv(lengthsize)
        (length,) = struct.unpack("<H", data[:lengthsize])

        print(len(data))
        string = ""
        expected = length + 2 - len(data)
        print "Length %d" % length
        print "Expected %d" % expected

        while expected > 0:
            print 'received "%d %s"' % (length, binascii.hexlify(data))
            data = self.__sock.recv(expected)
            expected = expected - len(data)
            string = string + data
        print 'received "%s"' % binascii.hexlify(string)
        return data

    def read_light_status(self, light):
        data = self.build_light_status(light)
        print 'sending "%s"' % binascii.hexlify(data)
        self.__sock.sendall(data)
        data = self.recv()
        return


        (on,lum,temp,red,green,blue,h) = struct.unpack("<27x2BH4B16x", data)
        print 'status: %0x %0x %d %0x %0x %0x %0x' % (on,lum,temp,red,green,blue,h)

        print 'onoff: %d' % on
        print 'temp:  %d' % temp
        print 'lum:   %d' % lum
        print 'red:   %d' % red
        print 'green: %d' % green
        print 'blue:  %d' % blue
        return (on, lum, temp, red, green, blue)

    def update_all_light_status(self):
        data = self.build_all_light_status(1)
        print 'sending %d "%s"' % (len(data), binascii.hexlify(data))
        self.__sock.sendall(data)
        data = self.recv()
        (num,) = struct.unpack("<H", data[7:9])

        print 'num: %d' % num

        old_lights = self.__lights
        new_lights = {}

        for i in range(0, num):
            pos = 9 + i * 42
            payload = data[pos:pos+42]

            print i, pos, len(payload)

            (a,addr,status,name) = struct.unpack("<HQ16s16s", payload)

            print 'light: %x %x %s' % (a,addr,name)
            if addr in old_lights:
                light = old_lights[addr]
            else:
                light = Light(addr, name)

            (b,on,lum,temp,red,green,blue,h) = struct.unpack("<Q2BH4B", status)
            print 'status: %x %0x' % (b, h)

            print 'onoff: %d' % on
            print 'temp:  %d' % temp
            print 'lum:   %d' % lum
            print 'red:   %d' % red
            print 'green: %d' % green
            print 'blue:  %d' % blue

            light.set_on(on)
            light.set_lum(lum)
            light.set_temp(temp)
            light.set_rgb(red, green, blue)
            new_lights[addr] = light
        #return (on, lum, temp, red, green, blue)

        self.__lights = new_lights


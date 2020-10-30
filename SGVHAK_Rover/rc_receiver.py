import datetime
import logging
import re
import serial
import sys
import termios
import threading
import time
import tty

import configuration

class RCReader(threading.Thread):
    sp = None
    start_called = False
    chassis = None

    def __init__(self, group = None, target = None, name = None,
                 args = (), kwargs = None, verbose = None):
        threading.Thread.__init__(self, group=group, target = target, name = name,
                                  verbose = verbose)
        self.args = args
        self.kwargs = kwargs
        self.chassis = args[0]
        self.on = False
        self.is_sbus = False
        self.app = None

        return

    def setApp(self, app):
        self.app = app

    def start(self):
        if self.start_called:
            raise RunTimeError

        self.start_called = True

        # Read parameter file
        config = configuration.configuration("rc_receiver")
        connectparams = config.load()['connect']
        
        # Open serial port with parameters
        s = serial.Serial()
        if 'baudrate' in connectparams:
            s.baudrate = connectparams['baudrate']

        if 'parity' in connectparams:
            if connectparams['parity'] == 'E':
                s.parity = serial.PARITY_EVEN
            elif connectparams['parity'] == 'O':
                s.parity = serial.PARITY_ODD
            else:
                s.parity = serial.PARITY_NONE

        s.port = connectparams['port']

        if 'stopbits' in connectparams:
            s.stopbits = connectparams['stopbits']

        if 'timeout' in connectparams:
            s.timeout = connectparams['timeout']
        try:
            s.open()
        except serial.SerialException as e:
            self.app.logger.error("RCReader.start failed: %s" % str(e))
            self.chassis.use_rc_input = False
        
        if s.is_open:
            self.sp = s
            self.on = True
            self.is_sbus = re.match('.*sbus-rc', connectparams['port']) != None

            super(RCReader, self).start()

    def cancel(self):
        self.on = False

    def drainInput(self):
        if not self.on:
            return None

        if self.is_sbus:
            p = self.sp.read(size = 128)
            while len(p) > 0:
                p = self.sp.read(size = 128)

            self.end_seen = True
        else:
            i = 0                              # Just read some lines
            line = self.sp.readline()
            while line and i < 10:
                line = self.sp.readline()
                i += 1

    def readSentence(self):
        if not self.on:
            return (None, None)

        if self.is_sbus:
            if not self.end_seen:
                p = self.sp.read()
                b = bytearray()
                b.extend(p)
                while len(p) == 0 or b[0] != 0:
                    p = self.sp.read()
                    b = bytearray()
                    b.extend(p)

            p = self.sp.read()
            b = bytearray()
            b.extend(p)
            while len(p) == 0 or b[0] != 0x0f:
                p = self.sp.read()
                b = bytearray()
                b.extend(p)

            self.end_seen = False
            p = self.sp.read(size = 24)
            b = bytearray()
            b.extend(p)
            self.end_seen = b[len(b) - 1] == 0

            if len(b) == 24:
                channels = [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ]
                chanCals = [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ]
                # 16 channels of 11 bit data
                # min: 172, max: 1811
                # --> scale = 2.0 / (max - min)  --> 0.00122025625381
                # --> bias  = -1.0 * (min + (max - min) / 2.0) * scale  --> -1.20988407566
                # scale = 1000 / (max - min) --> 0.610128126907
                # bias  = 1500 - (min + (max - min) / 2.0) * scale --> 895.057962172
                channels[ 0] = (b[ 0]      | b[ 1] << 8)                    & 0x07FF
                channels[ 1] = (b[ 1] >> 3 | b[ 2] << 5)                    & 0x07FF
                channels[ 2] = (b[ 2] >> 6 | b[ 3] << 2 | b[ 4] << 10) & 0x07FF
                channels[ 3] = (b[ 4] >> 1 | b[ 5] << 7)                    & 0x07FF
                channels[ 4] = (b[ 5] >> 4 | b[ 6] << 4)                    & 0x07FF
                channels[ 5] = (b[ 6] >> 7 | b[ 7] << 1 | b[ 8] <<  9) & 0x07FF
                channels[ 6] = (b[ 8] >> 2 | b[ 9] << 6)                    & 0x07FF
                channels[ 7] = (b[ 9] >> 5 | b[10] << 3)                    & 0x07FF
                channels[ 8] = (b[11]      | b[12] << 8)                    & 0x07FF
                channels[ 9] = (b[12] >> 3 | b[13] << 5)                    & 0x07FF
                channels[10] = (b[13] >> 6 | b[14] << 2 | b[15] << 10) & 0x07FF
                channels[11] = (b[15] >> 1 | b[16] << 7)                    & 0x07FF
                channels[12] = (b[16] >> 4 | b[17] << 4)                    & 0x07FF
                channels[13] = (b[17] >> 7 | b[18] << 1 | b[19] <<  9) & 0x07FF
                channels[14] = (b[19] >> 2 | b[20] << 6)                    & 0x07FF
                channels[15] = (b[20] >> 5 | b[21] << 3)                    & 0x07FF

                for i in range(16):
                    chanCals[i] = channels[i] * 0.610128126907 + 895.057962172

                # count lost frames
                lostFrame = b[22] & 0x04 != 0
                # failsafe state
                failsafe  = b[22] & 0x08 != 0

                t = datetime.datetime.utcnow()

                return (t, chanCals)
        else:
            line = self.sp.readline()

            m = re.match('I ([-\d.]+) +([-\d.]+) +([-\d.]+) +([-\d.]+) +([-\d.]+) +([-\d.]+) +([-\d.]+) +([-\d.]+)', line)
            if m != None:
                t = datetime.datetime.utcnow()

                return ( t, [ float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5)), float(m.group(6)), float(m.group(7)), float(m.group(8)) ])

        return (None, None)

    def run(self):
        self.app.logger.error("mw rc_receiver run! sbus= " + str(self.is_sbus) + "  sp= " + str(self.sp))
        last_time = datetime.datetime(1970, 1, 1)
        rc_use_input_time = datetime.datetime(1970, 1, 1)
        send_stop = 0
        last_rc = [ 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 ]

        self.drainInput()

        while self.on:
            (t, rcs) = self.readSentence()
            if t != None and (t - last_time).total_seconds() > 0.05:
                # self.app.logger.error("mw rc_receiver loop t= " + str(t) + ", " + str(rcs))
                last_time = t

                angle = (rcs[0] - 1500.0) / 5.0
                throttle = (rcs[2] - 1500.0) / 5.0
                rc_use = rcs[4] - 1500.0

                if not self.is_sbus and rc_use > -450 and rc_use < 450:
                    self.app.logger.error("%s: rc_receiver.run() messed up last: %f, %f, %f, %f, %f, %f, %f, %f  now %f, %f, %f, %f, %f, %f, %f, %f" %
                        (datetime.datetime.utcnow().strftime("%H%M%S.%f"),
                         last_rc[0], last_rc[1], last_rc[2], last_rc[3], last_rc[4], last_rc[5], last_rc[6], last_rc[7],
                         rcs[0], rcs[1], rcs[2], rcs[3], rcs[4], rcs[5], rcs[6], rcs[7]))

                    last_rc = rcs
                    continue

                last_rc = rcs

                if rc_use < 0.0:
                    self.chassis.use_rc_input = False
                    rc_use_input_time =  datetime.datetime(1970, 1, 1)
                else:
                    rc_use_input_time = datetime.datetime.utcnow()
                    self.chassis.use_rc_input = True

                    if angle > 100.0:
                        angle = 100.0
                    elif angle < - 100.0:
                        angle = -100.0

                    if throttle > 100.0:
                        throttle = 100.0
                    elif throttle < -100.0:
                        throttle = -100.0

                    # print("angle: %f  throttle: %f" % (angle, throttle))
                    radius_inf = False

                    if angle >= -6.0 and angle <= 6.0:
                        radius = float("inf")
                        radius_inf = True
                    elif angle > 1.0:
                        radius = self.chassis.minRadius + (self.chassis.maxRadius - self.chassis.minRadius) * (100.0 - angle) / 100.0
                    else:
                        radius = - self.chassis.minRadius - (self.chassis.maxRadius - self.chassis.minRadius) * (100.0 + angle) / 100.0

                    if throttle >= -5.0 and throttle <= 5.0:
                        throttle = 0.0

                    # self.app.logger.error("run(%f, %f, %d, %d)" % (throttle, radius, int(radius_inf), send_stop))
                    if throttle != 0.0 or radius_inf == False:
                        send_stop = 0

                        self.chassis.ensureready()
                        self.chassis.move_velocity_radius(throttle, radius)
                    elif send_stop < 1:
                        send_stop = 1

                        self.chassis.ensureready()
                        self.chassis.move_velocity_radius(throttle, radius)

            if (datetime.datetime.utcnow() - rc_use_input_time).total_seconds() > 2.0:
                self.chassis.use_rc_input = False

        self.sp.close()


# t = RCReader()
# t.setDaemon(True)
# t.start()

# class Getch:
#     def __call__(self):
#         fd = sys.stdin.fileno()
#         old_settings = termios.tcgetattr(fd)
#         try:
#             tty.setraw(sys.stdin.fileno())
#             ch = sys.stdin.read(1)
#         finally:
#             termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
#         return ch
# 
# 
# getch = Getch()
# c = getch().lower()
# while c != 'q':
#     time.sleep(100)

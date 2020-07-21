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

        return

    def start(self):
        if self.start_called:
            raise RunTimeError

        self.start_called = True

        # Read parameter file
        config = configuration.configuration("rc_receiver")
        connectparams = config.load()['connect']
        
        # Open serial port with parameters
        s = serial.Serial()
        s.baudrate = connectparams['baudrate']
        s.port = connectparams['port']
        s.timeout = connectparams['timeout']
        try:
            s.open()
        except serial.SerialException as e:
            logging.getLogger('werkzeug').error("RCReader.start failed: %s" % str(e))
            self.chassis.use_rc_input = False
        
        if s.is_open:
            self.sp = s
            self.on = True

            i = 0                              # Just read some lines
            line = self.sp.readline()
            while line and i < 10:
                line = self.sp.readline()
                i += 1

            super(RCReader, self).start()

    def cancel(self):
        self.on = False

    def run(self):
        last_time = datetime.datetime(1970, 1, 1)
        rc_use_input_time = datetime.datetime(1970, 1, 1)
        send_stop = 0
        last_rc = [ 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 ]

        while self.on:
            line = self.sp.readline()

            m = re.match('I ([-\d.]+) +([-\d.]+) +([-\d.]+) +([-\d.]+) +([-\d.]+) +([-\d.]+) +([-\d.]+) +([-\d.]+)', line)
            if m != None:
                t = datetime.datetime.utcnow()

                if (t - last_time).total_seconds() > 0.05:
                    last_time = t
                    # logging.getLogger('werkzeug').error("%s: rc_receiver.run(%f, %f, %f)" % (datetime.datetime.utcnow().strftime("%H%M%S.%f"), float(m.group(1)), float(m.group(3)), float(m.group(5))))

                    angle = (float(m.group(1)) - 1500.0) / 5.0
                    throttle = (float(m.group(3)) - 1500.0) / 5.0
                    rc_use = float(m.group(5)) - 1500.0

                    if rc_use > -450 and rc_use < 450:
                        logging.getLogger('werkzeug').error("%s: rc_receiver.run() messed up last: %f, %f, %f, %f, %f, %f, %f, %f  now %f, %f, %f, %f, %f, %f, %f, %f" %
                            (datetime.datetime.utcnow().strftime("%H%M%S.%f"),
                             last_rc[0], last_rc[1], last_rc[2], last_rc[3], last_rc[4], last_rc[5], last_rc[6], last_rc[7],
                             float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5)), float(m.group(6)), float(m.group(7)), float(m.group(8))))

                        last_rc[0] = float(m.group(1))
                        last_rc[1] = float(m.group(2))
                        last_rc[2] = float(m.group(3))
                        last_rc[3] = float(m.group(4))
                        last_rc[4] = float(m.group(5))
                        last_rc[5] = float(m.group(6))
                        last_rc[6] = float(m.group(7))
                        last_rc[7] = float(m.group(8))
                        continue

                    last_rc[0] = float(m.group(1))
                    last_rc[1] = float(m.group(2))
                    last_rc[2] = float(m.group(3))
                    last_rc[3] = float(m.group(4))
                    last_rc[4] = float(m.group(5))
                    last_rc[5] = float(m.group(6))
                    last_rc[6] = float(m.group(7))
                    last_rc[7] = float(m.group(8))

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

                        # logging.getLogger('werkzeug').error("run(%f, %f, %d, %d)" % (throttle, radius, int(radius_inf), send_stop))
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

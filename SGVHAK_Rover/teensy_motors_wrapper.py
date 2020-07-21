import datetime
import logging
import serial
from struct import *

import configuration

class teensy_motors_wrapper:
  """
  Class that implements the rover motor control methods for serial bus
  based on a Teensy 3.5 running a modified ROS Arduino Bridge
  """
  def __init__(self):
    self.sp = None

  def check_sp(self):
    """ Raises error if we haven't opened serial port yet. """
    if self.sp == None:
      raise ValueError("Teensy serial communication is not available.")

  def connect(self):
    """
    Read serial port connection parameters from JSON configuration file
    and open the port.
    """
    
    # Read parameter file
    config = configuration.configuration("teensy_motors")
    connectparams = config.load()['connect']
    
    # Open serial port with parameters
    s = serial.Serial()
    s.baudrate = connectparams['baudrate']
    s.port = connectparams['port']
    s.timeout = connectparams['timeout']

    try:
        s.open()
    except serial.SerialException as e:
        logging.getLogger('werkzeug').error("teensy_motors_wrapper.connect failed: %s" % str(e))

    if s.is_open:
      self.sp = s

  def close(self):
    """
    Closes down the serial port
    """
    if self.sp.is_open:
      self.sp.close()
      self.sp = None

  def version(self, id):
    """ Identifier string for this motor controller """
    return "Teensy Motors"

  @staticmethod
  def check_id(id):
    """ Verifies servo ID is within range and inverted status is boolean"""
    if not isinstance(id, (tuple,list)):
      raise ValueError("Teensy Motors identifier must be a tuple")

    if not isinstance(id[0], int):
      raise ValueError("Teensy Motors address must be an integer")

    if id[0] < 0 or id[0] > 5:
      raise ValueError("Teensy Motors address {} outside of valid range 0-5".format(id[0]))

    if not isinstance(id[1], bool):
      raise ValueError("Inverted status must be a boolean")

    return tuple(id)

  def power_percent(self, id, percentage):
    """ Runs motor at specified +/- percentage """
    mid, inverted = self.check_id(id)
    self.check_sp()

    pct = int(percentage)
    if abs(pct) > 100:
      raise ValueError("Motor power percentage {0} outside valid range from 0 to 100.".format(pct))

    # The Teensy expects +/- 255 
    power = int(percentage * 2.54)

    if inverted:
      power = power * -1

    # logging.getLogger('werkzeug').error("%s: teensy_motors.power_percent(%d, %f)  -> write(%d, %d)" % (datetime.datetime.utcnow().strftime("%H%M%S.%f"), mid, percentage, mid, power))
    self.sp.write("n %d %d\r" % (mid, power))

  def set_max_current(self, id, current):
    sid, center, inverted = self.check_id(id)
    self.check_sp()
    # Does nothing

  def init_velocity(self, id):
    sid, inverted = self.check_id(id)
    self.check_sp()
    # Does nothing

  def velocity(self,id,pct_velocity):
    """
    Runs the specified servo in motor mode at specified velocity
    In case of LewanSoul servos, it is the same as power_percent.
    """
    self.power_percent(id,pct_velocity)

  def init_angle(self, id):
    pass

  def maxangle(self, id):
    return 0

  def angle(self, id, angle):
    pass

  def steer_setzero(self, id):
    pass

  def input_voltage(self, id):
    return 0

if __name__ == "__main__":
  """
  Command line interface to work with teensy serial motor driver.
  Implements a subset of the teensy's functionality
  * Spin at a specified speed.
  * Unload and power down motors

  based on similar interface in lewansoul_wrapper.py
  """
  import argparse

  parser = argparse.ArgumentParser(description="Teensy Serial Motor Driver Command Line Utility")

  parser.add_argument("-id", "--id", help="Motor identifier integer 0-253. ", type=int, default=1)
  parser.add_argument("-t", "--time", help="Time duration for action", type=int, default=0)  #not currently implemented
  parser.add_argument("-i", "--inverted", help="Invert motor direction", action="store_true")
  group = parser.add_mutually_exclusive_group()
  group.add_argument("-s", "--spin", help="Spin the motor at a specified speed from -100 to 100", type=int)
  group.add_argument("-u", "--unload", help="Power down motor", action="store_true")
  group.add_argument("-v", "--voltage", help="Read current input voltage", action="store_true")  #not currently implemented
  args = parser.parse_args()

  c = teensy_motors_wrapper()
  c.connect()

  if args.spin != None: # Zero is a valid parameter.
    if args.spin < -100 or args.spin > 100:
      print("Motor spin speed {} is outside valid range of -100 to 100".format(args.spin))
    else:
      print("Spinning motor with id {} at rate of {}".format(args.id, args.spin))
      c.velocity((args.id, args.inverted), args.spin)
  elif args.unload:
    c.velocity((args.id, args.inverted), 0)
  elif args.voltage:
    #c.send(args.id, 27)
    #(sid, cmd, params) = c.read_parsed(length=8, expectedcmd=27, expectedparams=2)
    #voltage = unpack('h', params)[0]
    #print("Servo {} reports input voltage of {}".format(sid, voltage/1000.0))
    print("teensy voltage check not yet implemented")
  else:
    # None of the actions were specified? Show help screen.
    parser.print_help()

  c.close()


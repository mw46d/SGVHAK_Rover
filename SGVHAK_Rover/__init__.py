"""
MIT License

Copyright (c) 2018 Roger Cheng

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import atexit
import os
from flask import Flask
import SGVHAK_Rover.roverchassis

# Rover chassis geometry, including methods to calculate wheel angle and
# velocity based on chassis geometry.
chassis = roverchassis.chassis()

rcReceiverThread = None

try:
    import rc_receiver

    rcReceiverThread = rc_receiver.RCReader(args = (chassis, ))
    rcReceiverThread.setDaemon(True)
except:
    pass

def create_app():
    app = Flask(__name__)

    def interrupt():
        global rcReceiverThread

        if rcReceiverThread != None:
            rcReceiverThread.cancel()

    # Initiate
    global rcReceiverThread
    app.logger.error("mw rcReceiverThread= " + str(rcReceiverThread));

    # When you kill Flask (SIGTERM), clear the trigger for the next thread
    atexit.register(interrupt)

    if rcReceiverThread != None:
        rcReceiverThread.setApp(app)
        rcReceiverThread.start()

    return app

app = create_app()

# Randomly generated key means session cookies will not be usable across
# instances. This is acceptable for now but may need changing later.
app.secret_key = os.urandom(24)

import SGVHAK_Rover.menu

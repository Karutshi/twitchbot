import sys, time, threading, select, readline
from multiprocessing import Process

from twitchbot import Twitchbot

# Create a twitchbot on its own thread.
twitchbot = Twitchbot()

p = Process(target = twitchbot.read_chat)
p.daemon = True
p.start()

# Check terminal input while twitchbot runs, to allow for commands to be sent through the terminal.
while True:
    time.sleep(1)
    twitchbot.send_welcome_message()
    command = ""
    if select.select([sys.stdin,],[],[],0.0)[0]:
        command = raw_input()
        if command.lower() == "quit" or command.lower() == "q":
            twitchbot.stop()
            p.join(timeout = 1)
            exit(0)
        else:
            twitchbot.send_message(command)
import socket, string, threading, time, re

class Twitchbot:

    class Color:
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKGREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'

    def __init__(self):
        self.HOST = "irc.twitch.tv"
        self.PORT = 6667
        self.NICK = "Karutshi"
        self.PASS = "oauth:20rdhomnsdh47z8loafudeiv1xcxsi"
        self.readbuffer = ""
        self.MODT = False
        self.channel = raw_input(self.Color.FAIL + "Enter the channel name to connect to.\r\n" + self.Color.ENDC)

        self.s = socket.socket()
        self.s.connect((self.HOST, self.PORT))
        self.s.send("PASS " + self.PASS + "\r\n")
        self.s.send("NICK " + self.NICK + "\r\n")
        self.s.send("JOIN #" + self.channel + " \r\n")
        print self.Color.FAIL + "Connecting to http://www.twitch.tv/" + self.channel + self.Color.ENDC
        self.keepReading = True
        self.biglist = []
        self.pause = False

    def Send_message(self, message):
        self.s.send("PRIVMSG #" + self.channel + " :" + message + "\r\n")
        print self.Color.OKBLUE + "karutshi: " + message + self.Color.ENDC
        self.pause = False

    def Change_channel(self, newchannel):
        self.s.send("PART #" + self.channel + " \r\n")
        self.channel = newchannel
        self.s.send("JOIN #" + self.channel + " \r\n")
        print self.Color.FAIL + "Connecting to http://www.twitch.tv/" + self.channel + self.Color.ENDC

        self.pause = False


    def Stop(self):
        self.keepReading = False

    def Pause(self):
        self.pause = True

    def Read_chat(self):
        while self.keepReading:
            self.readbuffer = self.readbuffer + self.s.recv(1024)
            temp = string.split(self.readbuffer, "\n")
            self.readbuffer = temp.pop()

            if self.pause:
                self.biglist.extend(temp)

            if not self.pause:
                if len(self.biglist) > 0:
                    temp.extend(self.biglist)
                    self.biglist = []
                for line in temp:
                    if (line[0] == "PING"):
                        self.s.send("PONG %s\r\n" % line[1])
                    else:

                        parts = string.split(line, ":")
                        try:
                            if "QUIT" not in parts[1] and "JOIN" not in parts[1] and "PART" not in parts[1]:
                                try:
                                    message = ":".join(parts[2:])
                                    message = message[:-1]
                                except:
                                    message = ""

                                usernamesplit = string.split(parts[1], "!")
                                username = usernamesplit[0]

                                if self.MODT:
                                    color = ""
                                    if re.search("bot$", username):
                                        color = self.Color.FAIL
                                    elif username.lower() == "karutshi":
                                        color = self.Color.OKBLUE
                                    elif "karutshi" in message or re.search("[\s:]karu[\s\,\.\!]", username, re.I):
                                        color = self.Color.WARNING 
                                    print color + username + ":" + message + self.Color.ENDC 

                                for l in parts:
                                    if "End of /NAMES list" in l:
                                        self.MODT = True
                            elif "PART" in parts[1]:
                                print self.Color.FAIL + ":".join(parts) + self.Color.ENDC
                        except:
                            for l in parts:
                                print l
        print "Thread stopping"

twitchbot = Twitchbot()
thread = threading.Thread(target = twitchbot.Read_chat)
thread.setDaemon(True)
thread.start()
while True:
    command = raw_input()
    if command.lower() == "quit" or command.lower() == "q":
        twitchbot.Stop()
        break
    elif command.lower() == "p":
        twitchbot.Pause()
    elif command.lower() == "change":
        twitchbot.Pause()
        twitchbot.Change_channel(raw_input(twitchbot.Color.FAIL + "Enter new channel name. \r\n" + twitchbot.Color.ENDC))
    else:
        twitchbot.Send_message(command)
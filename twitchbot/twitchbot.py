import socket, string, threading, time, re, sys, readline
import urllib2, json
import psycopg2

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

        # Read password and nickname from local file.
        with open("pass.pw", 'r') as f:
            self.NICK = ""
            self.PASS = ""
            for line in f:
                username = re.search('^USERNAME = ([A-z0-9:]*)$', line)
                password = re.search('^PASSWORD = ([A-z0-9:]*)$', line)
                if username:
                    self.NICK = username.group(1)
                if password:
                    self.PASS = password.group(1)
        if self.NICK == "" or self.PASS == "":
            print "Username or password wasn't found, make sure file pass.pw is present in current folder."
            exit(1)

        # Setup fields for connecting to twitch.
        self.HOST = "irc.twitch.tv"
        self.PORT = 6667
        self.readbuffer = ""
        self.MODT = False
        self.channel = "supremechancellorlive"
        self.printColor(self.Color.FAIL, "Connecting to http://www.twitch.tv/" + self.channel)
       
        # Attempt to connect to the twitch channel.
        try:
            self.s = socket.socket()
            self.s.connect((self.HOST, self.PORT))
            self.s.send("PASS " + self.PASS + "\r\n")
            self.s.send("NICK " + self.NICK + "\r\n")
            self.s.send("JOIN #" + self.channel + " \r\n")
            self.keepReading = True

            # Get a list of all connected users in chat.
            response = urllib2.urlopen("https://tmi.twitch.tv/group/user/" + self.channel + "/chatters")
            html = response.read()
            parsed_json = json.loads(html)
            self.users = parsed_json.get("chatters")
            self.printColor(self.Color.OKGREEN, "Connected!")
        except Exception as e:
            print "Could not connect to http://www.twitch.tv/" + self.channel
            print e

    # Get a text command from the database
    def get_text_from_db(self, command_name):
        conn = psycopg2.connect(dbname = 'twitchbot_db', user = 'postgres', 
                                password = 'postgres', host = 'localhost')
        cur = conn.cursor()
        cur.execute("SELECT text FROM commands WHERE command_name = (%s) AND last_used < now() - interval '30 seconds'", 
                    (command_name,))
        result = cur.fetchone()
        cur.execute("UPDATE commands SET last_used = now() WHERE command_name = (%s) AND last_used < now() - interval '30 seconds'", (command_name,))
        conn.commit()
        cur.close()
        conn.close()
        return result[0] if result is not None else None

    def checkuser(self, name):
        for key in self.users:
            if name == self.users.get(key):
                self.printColor(self.Color.OKGREEN, "User '" + name + "' is currently watching and is a member of group '" + key + "'.")
                break
        else:
            self.printColor(self.Color.OKGREEN, "User '" + name + "' is not currently watching.")

    def printColor(self, color, message):
        print color + message + self.Color.ENDC

    def printMessage(self, color, username, message):
        print self.Color.HEADER + username + ": " + self.Color.ENDC + color + message + self.Color.ENDC

    def writeColor(self, color, message):
        sys.stdout.write(color + message + self.Color.ENDC)

    def Send_message(self, message):
        if message == "":
            return
        self.s.send("PRIVMSG #" + self.channel + " :" + message + "\r\n")
        self.printColor(self.Color.OKBLUE, self.NICK + ": " + message)



    def Stop(self):
        self.keepReading = False

    def Read_chat(self):
        while self.keepReading:
            self.readbuffer = self.readbuffer + self.s.recv(256)
            temp = string.split(self.readbuffer, "\n")
            self.readbuffer = temp.pop()

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
                                command = re.match(r"^!(\w+)", message)
                                if command:
                                    print "Got here!"
                                    send_message = self.get_text_from_db(command.group(1))
                                    if send_message is not None:
                                        self.Send_message(send_message)
                                    else:
                                        print "Got empty message!"
                                else:
                                    print message
                            for l in parts:
                                if "End of /NAMES list" in l:
                                    self.MODT = True
                        elif "PART" in parts[1]:
                            self.printColor(self.Color.FAIL, ":".join(parts))
                    except Exception as e:
                        print e
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
    elif command.lower() == "checkuser":
        twitchbot.checkuser(raw_input("Enter the username.\n"))
    else:
        twitchbot.Send_message(command)

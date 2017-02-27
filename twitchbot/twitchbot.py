import socket, string, time, re, sys, select, threading, readline, datetime
from multiprocessing import Process, Lock
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

        self.mutex = Lock()

        # Special fields
        self.special_commands = ["commands"]
        self.mod_commands = ["editcmd", "removecmd", "reactto", "removereact"]

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
            self.update_chatters()
            self.printColor(self.Color.OKGREEN, "Connected!")
        except Exception as e:
            print "Could not connect to http://www.twitch.tv/" + self.channel
            print e

    # Execute a query towards the database and disregard the output.
    def execute_query(self, query, query_tuple = None):
        conn = psycopg2.connect(dbname = 'twitchbot_db', user = 'postgres', 
                                password = 'postgres', host = 'localhost')
        cur = conn.cursor()
        if query_tuple is not None:
            cur.execute(query, query_tuple)
        else:
            cur.execute(query)
        conn.commit()
        cur.close()
        conn.close()

    # Execute a query towards the database and expect some output.
    def execute_query_get_result(self, query, query_tuple = None):
        conn = psycopg2.connect(dbname = 'twitchbot_db', user = 'postgres', 
                                password = 'postgres', host = 'localhost')
        cur = conn.cursor()
        if query_tuple is not None:
            cur.execute(query, query_tuple)
        else:
            cur.execute(query)
        conn.commit()
        resultlist = []
        for result in cur:
            resultlist.append(result) if len(result) != 1 else resultlist.append(result[0])
        cur.close()
        conn.close()
        return resultlist

    # Get a text command from the database.
    def get_text_from_db(self, command_name):
        result = self.execute_query_get_result("SELECT text FROM commands WHERE command_name = (%s) AND last_used < now() - interval '30 seconds'", 
                                         (command_name,))[0]
        self.execute_query("UPDATE commands SET last_used = now() WHERE command_name = (%s) AND last_used < now() - interval '30 seconds'", (command_name,))
        return result if result is not None else None

    # Update the internal list of chatters and moderators.
    def update_chatters(self):
        response = urllib2.urlopen("https://tmi.twitch.tv/group/user/" + self.channel + "/chatters")
        html = response.read()
        parsed_json = json.loads(html)
        self.users = parsed_json.get("chatters")
        self.chatters_update = datetime.datetime.now()

    def minutes_since_last_chatters_update(self):
        return (self.chatters_update - datetime.datetime.now()).seconds / 60

    # Checks whether a user is mod, will update modlist if more than 3 minutes has passed since last update.
    def user_is_mod(self, user):
        if user in self.users.get("moderators"):
            return True
        elif user not in self.users.get("") and self.minutes_since_last_chatters_update() > 3:
            self.chatters_update = datetime.datetime.now();
            self.update_chatters()
        return user in self.mods 

    # Update a command in the database, or add it if it doesn't exist.
    def update_command(self, command_name, text):
        update_query = "UPDATE commands SET text = (%s), last_used = now() - interval '30 seconds' WHERE command_name = (%s)"
        insert_query = """  INSERT INTO commands (command_name, text, last_used)
                            SELECT (%s), (%s), now() - interval '30 seconds'
                            WHERE NOT EXISTS (SELECT 1 FROM commands WHERE command_name = (%s))"""
        self.execute_query(update_query, (text, command_name))
        self.execute_query(insert_query, (command_name, text, command_name))
        self.send_message("Command '!" + command_name + "' has been updated to '" + text + "'.")

    # Remove a command from the database.
    def remove_command(self, command_name):
        query = "DELETE FROM commands WHERE command_name = (%s)"
        self.execute_query(query, (command_name,))
        self.send_message("Command '!" + command_name + "' was removed.")

    # Get all commands that are stored in the database.
    def get_commands(self):
        query = "SELECT command_name FROM commands ORDER BY command_name"
        return self.execute_query_get_result(query)

    # Update a reaction in the database, or add it if it doesn't exist.
    def update_reaction(self, trigger, response):
        update_query = "UPDATE reactions SET response = (%s), last_used = now() - interval '30 seconds' WHERE trigger = (%s)"
        insert_query = """  INSERT INTO reactions (trigger, response, last_used)
                            SELECT (%s), (%s), now() - interval '30 seconds'
                            WHERE NOT EXISTS (SELECT 1 FROM reactions WHERE trigger = (%s))"""
        self.execute_query(update_query, (response, trigger))
        self.execute_query(insert_query, (trigger, response, trigger))
        self.send_message("Response for '" + trigger + "' has been updated to '" + response + "'.")

    # Remove a reaction from the database.
    def remove_reaction(self, trigger):
        query = "DELETE FROM reactions WHERE trigger = (%s)"
        self.execute_query(query, (trigger,))
        self.send_message("Reaction for '" + trigger + "' was removed.")

    # Get all react triggers that are stored in the database.
    def get_react_triggers(self):
        query = "SELECT trigger FROM reactions WHERE last_used < now() - interval '30 seconds'"
        return self.execute_query_get_result(query)

    # Send a reaction of the given trigger to twitch chat. 
    def react_to(self, trigger):
        query = "SELECT response FROM reactions WHERE trigger = (%s)"
        update_query = "UPDATE reactions SET last_used = now() WHERE trigger = (%s)"
        response = self.execute_query_get_result(query, (trigger,))[0]
        self.execute_query(update_query, (trigger,))
        self.send_message(response)

    # Scan messages for triggers.
    def look_for_triggers(self, message):
        for trigger in self.get_react_triggers():
            if trigger in message:
                self.react_to(trigger)
                break

    # Parse a command that started with '!'.
    def parse_command(self, command_name, message, user):
        if command_name == "editcmd" and self.user_is_mod(user):
            matchobj = re.match(r"\s*(\w+)\s+(.*)$", message)
            command_to_change = matchobj.group(1)
            command_new_text  = matchobj.group(2)
            self.update_command(command_to_change.lower(), command_new_text)
        elif command_name == "removecmd":
            matchobj = re.match(r"\s*(\w+)", message)
            command_to_remove = matchobj.group(1)
            self.remove_command(command_to_remove)
        elif command_name == "commands":
            commands = self.get_commands()
            self.send_message("Available commands are: !" + ", !".join(commands + self.special_commands))
        elif command_name == "reactto":
            matchobj = re.match(r"\s*'(.*?)'\s*'(.*?)'", message)
            trigger = matchobj.group(1)
            response = matchobj.group(2)
            self.update_reaction(trigger.lower(), response)
        elif command_name == "removereact":
            matchobj = re.match(r"\s(.+)", message)
            reaction_to_remove = matchobj.group(1)
            self.remove_reaction(reaction_to_remove)
        else:
            message_to_send = self.get_text_from_db(command_name)
            if message_to_send is not None:
                self.send_message(message_to_send)

    # Print in a given color in the terminal window.
    def printColor(self, color, message):
        print color + message + self.Color.ENDC
    
    # Print a twitch message.
    def printMessage(self, color, username, message):
        print self.Color.HEADER + username + ": " + self.Color.ENDC + color + message + self.Color.ENDC
    
    # Print a message with a color, but without newline.
    def writeColor(self, color, message):
        sys.stdout.write(color + message + self.Color.ENDC)

    # Send a message to twitch chat.
    def send_message(self, message):
        with self.mutex:
            if message == "":
                return
            self.s.send("PRIVMSG #" + self.channel + " :" + message + "\r\n")
            self.printColor(self.Color.OKBLUE, self.NICK + ": " + message)

    # Send a welcome message every 5 minutes.
    def send_welcome_message(self):
        message = self.execute_query_get_result("SELECT message FROM special_messages WHERE name = 'welcome_message' AND " + 
                                                "last_used < now() - interval '5 minutes'")
        self.execute_query("UPDATE special_messages SET last_used = now() WHERE name = 'welcome_message' AND " + 
                           "last_used < now() - interval '5 minutes'")
        if message:
            self.send_message(message[0])
        

    # Stop reading twitch chat.
    def stop(self):
        self.keepReading = False

    # Read twitch chat.
    def read_chat(self):
        while self.keepReading:
            # Receive 256 bytes at a time.
            self.readbuffer = self.readbuffer + self.s.recv(256)
            temp = string.split(self.readbuffer, "\n")
            self.readbuffer = temp.pop()

            for line in temp:
                # Respond to twitch pings.
                parts = string.split(line, ":")
                if "PING" in parts[0]:
                    self.s.send("PONG %s\r\n" % parts[1])
                else:
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
                                command = re.match(r"!(\w+)(.*)", message)
                                if command:
                                    self.parse_command(command.group(1).lower(), command.group(2), username)
                                else:
                                    self.look_for_triggers(message.lower())
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
        elif command.lower() == "checkuser":
            twitchbot.checkuser(raw_input("Enter the username.\n"))
        else:
            twitchbot.send_message(command)
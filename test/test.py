import urllib2, readline, json

response = urllib2.urlopen("https://tmi.twitch.tv/group/user/imaqtpie/chatters")
html = response.read()
parsed_json = json.loads(html)
def printStuff(i, d):
    for key in d:
        value = d.get(key)
        if isinstance(value, dict):
            print " " * i + key
            printStuff(i + 4, value)
        elif isinstance(value, list):
            print " " * i + key + " " + str(type(value)) + " " + str(len(value))
        else:
            print " " * i + key + " " + str(type(value))
printStuff(0, parsed_json)

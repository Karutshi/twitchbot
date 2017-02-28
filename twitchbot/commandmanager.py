import psycopg2

class CommandManager:

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
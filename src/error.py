
class UnregisteredPlayerError(Exception):
    def __init__(self, conn):
        self.conn = conn
        conn.sendall("Please register yourself with /register <name> before you can join.\n")

class AlreadyRegisteredPlayerError(Exception):
    def __init__(self, conn):
        self.conn = conn
        conn.sendall("You have already registered.\n")

class NotYourTurnError(Exception):
    def __init__(self, conn):
        self.conn = conn
        conn.sendall("It is not your turn to move yet.\n")

class NoSuchPlayerError(Exception):
    def __init__(self, conn, name):
        self.conn = conn
        conn.sendall("Failed to find a player with the name {}.\n".format(name))

class NotEnoughTreasuryCoinsError(Exception):
    def __init__(self, conn):
        self.conn = conn
        conn.sendall("There are not enough coins in the treasury to perform this action.\n")

class InvalidCommandError(Exception):
    def __init__(self, conn, message):
        self.conn = conn
        conn.sendall(message)

class NotEnoughCoinsError(Exception):
    def __init__(self, conn, name):
        self.conn = conn
        if name == "":
            conn.sendall("You do not have enough coins.\n")
        else:
            conn.sendall(name + " does not have enough coins.\n")

class MustCoupError(Exception):
    def __init__(self, conn):
	self.conn = conn
	conn.sendall("You have 10 or more coins, you must Coup.\n")

class CannotRemoveError(Exception):
    def __init__(self, conn):
	self.conn = conn
	conn.sendall("You are not currently using the Ambassador ability.\n")

class AlreadyExchangingError(Exception):
    def __init__(self, conn):
	self.conn = conn
	conn.sendall("You are already exchanging cards.\n")

class NotEnoughArguments(Exception):
    def __init__(self, conn):
	self.conn = conn
	conn.sendall("Not enough arguments.\n")

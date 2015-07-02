#Authors: Joe DiSabito, Ryan Hartman, Alec Benson

import SocketServer
from collections import deque
import sys, os, random, time, threading

class CoupServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

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
    def __init__(self, conn):
        self.conn = conn
        conn.sendall("You do not have enough coins to perform this action.\n")

class CoupRequestHandler(SocketServer.BaseRequestHandler):
        def __init__(self, callback, *args, **keys):
            self.cg = callback
            SocketServer.BaseRequestHandler.__init__(self, *args, **keys)

        '''Broadcasts message to all connected players'''
        def broadcast_message(self, message):
            for player in self.cg.players.list():
                player.conn.sendall(message)

        '''
        When a client connects, a thread is spawned for the client and handle() is called.
        handle() will, as the name suggests, handle the data that the client sends and act accordingly.
        '''
        def handle(self):
            q = self.cg.players
            conn = self.request

            while True:
                try:
                    self.data = conn.recv(1024).strip()
                    player = q.getPlayer(conn)
                    self.parseRequest(player, self.data)
                    #If the player issuing the request is in the game...
                    if not q.isClientRegistered(conn):
                        raise UnregisteredPlayerError(conn)
                except IOError:
                    conn.close()
                    q.removePlayer(conn)
                    return
                except UnregisteredPlayerError:
                    pass

        '''
        Sends a chat message from player to all connected clients. If the user is unregistered, the message is Anonymous
        '''
        def chatMessage(self, player, parts):
            if len(parts) >= 2:
                if player is None:
                    self.broadcast_message("Anonymous: {0}\n".format(parts[1]))
                else:
                    self.broadcast_message("{0}: {1}\n".format(player.name, parts[1]))

        '''Sends a nice message whenever a new client registers
        '''
        def welcome(self, name):
            self.broadcast_message("{} joined the game!\n".format(name))

        '''
        Boots a player from the server
        '''
        def kick(self, player, parts):
            return player.conn.close()

        '''
        Prints the target player's current hand, or display's the current player's hand if no name is provided
        '''
        def showHand(self, player, parts):
            try:
                if player is None:
                    raise UnregisteredPlayerError(self.request)

                if len(parts) >= 2:
                    name = parts[1]
                    #If the player enters their own name
                    if name == player.name:
                        return player.conn.sendall(player.getHand(True))

                    #If the player enters another player's name
                    target = self.cg.players.getPlayerByName(name)
                    if target == None:
                        raise NoSuchPlayerError(self.request, name)
                    return player.conn.sendall(target.getHand(False))
                else:
                    #The player enters no name (default)
                    return player.conn.sendall(player.getHand(True))

            except (UnregisteredPlayerError, NoSuchPlayerError) as e:
                pass

        '''
        Prints the number of coins the player has
        '''
        def showCoins(self, player, parts):
            try:
                if player is None:
                    raise UnregisteredPlayerError(self.request)
                message = "Coins: {}\n".format(player.coins)
                player.conn.sendall(message)
            except UnregisteredPlayerError as e:
                pass

        '''
        Lists all of the players and the number of coins that they have
        '''
        def listplayers(self, parts):
            formatted_list = ""

            for player in self.cg.players.list():
                formatted_list += "{0} ({1} Coins)\n".format(player.name, player.coins)

            if not formatted_list:
                return self.request.sendall("No registered players.\n")

            self.request.sendall(formatted_list)

        '''
        Performs either a Duke tax, Foreign Aid, or Income.
        '''
        def getCoins(self, player, parts, coins):
            try:
                if player is None:
                    raise UnregisteredPlayerError(self.request)

                if not self.cg.players.isPlayersTurn(player):
                    raise NotYourTurnError(self.request)

                if self.cg.treasury < coins:
                    raise NotEnoughTreasuryCoinsError(self.request)

		#TODO: These two lines should only happen if no challenges.
                player.coins += coins
                self.cg.treasury -= coins
                #TODO:Broadcast player's new coin count after turn.
		if coins == 3:
                	self.broadcast_message("{} called a TAX, the Duke ability.\n".format(player.name))
			#TODO: Allow challenge.
		elif coins == 2:
                        self.broadcast_message("{} called FOREIGN AID.\n".format(player.name))
                #TODO:Allow players to claim DUKE to block (and challenge).
		else:
                        self.broadcast_message("{} called INCOME.\n".format(player.name))
                self.broadcast_message(self.cg.players.advanceTurn())
            except (UnregisteredPlayerError, NotYourTurnError, NotEnoughTreasuryCoinsError) as e:
                pass

        '''
        Performs card destruction (coup, assassination, challenge)
        '''
        def destroy(self, player, parts, coins):
            try:
                if player is None:
                    raise UnregisteredPlayerError(self.request)

                if not self.cg.players.isPlayersTurn(player):
                    raise NotYourTurnError(self.request)

                if len(parts) < 2:
                    raise InvalidCommandError(self.request, "You need to specify a player (by name) that you want to coup\n")

                name = parts[1]
                if name == player.name:
                    raise InvalidCommandError(self.request, "You cannot coup yourself. Nice try.\n")

                if player.coins < coins:
                    raise NotEnoughCoinsError(self.request)

                target = self.cg.players.getPlayerByName(name)
                if target == None:
                    raise NoSuchPlayerError(self.request, name)

                player.coins -= coins
                self.cg.treasury += coins
                if coins == 7:
                	self.broadcast_message("{0} called a COUP on {1}.\n".format(player.name, target.name))
                elif coins == 3:
			self.broadcast_message("{0} is attempting to ASSASSINATE {1}.\n".format(player.name, target.name))
                	#TODO: ADD CHALLENGE/PROTECTION CHANCE HERE
                else: #challenge
			self.broadcast_message(".\n".format(player.name, target.name))
		self.broadcast_message(target.killCardInHand())
                self.broadcast_message(self.cg.players.advanceTurn())
            except (UnregisteredPlayerError, NotYourTurnError, InvalidCommandError, NoSuchPlayerError, NotEnoughCoinsError) as e:
                pass


        '''
        Ends the player's turn, or raises a NotYourTurnError if it is not the player's turn to move
        '''
        def endturn(self, player, parts):
            try:
                if player is None:
                    raise UnregisteredPlayerError(self.request)

                if not self.cg.players.isPlayersTurn(player):
                    raise NotYourTurnError(self.request)

                self.broadcast_message("{} ended his turn.\n".format(player.name))
                self.broadcast_message(self.cg.players.advanceTurn())
            except (UnregisteredPlayerError, NotYourTurnError) as e:
                pass

        '''
        A helper to verify that a requested name is valid before it is registered
        '''
        def isValidName(self, name):
            try:
                strname = str(name)
                length = len(strname)
                if length <= 0 or length >= 20:
                    raise InvalidCommandError(self.request, "Name must be between 1 and 20 characters in length.\n")
                if self.cg.players.getPlayerByName(name):
                    raise InvalidCommandError(self.request, "A user with this name is already registered.\n")
                return True
            except (InvalidCommandError) as e:
                return False

        '''
        Registers the client with the name provided
        '''
        def register(self, parts):
            try:
                if len(parts) < 2:
                    raise InvalidCommandError(self.request, "Could not register: please provide a name.")

                name = parts[1]
                if self.cg.players.isClientRegistered(self.request):
                    raise AlreadyRegisteredPlayerError(self.request)

                if self.isValidName(name):
                    newPlayer = Player(self.request, name, self.cg.deck.deal(), self.cg.deck.deal())
                    self.cg.players.addPlayer(newPlayer)
                    self.welcome(name)
            except (InvalidCommandError, AlreadyRegisteredPlayerError) as e:
                pass

        '''Sets a player as ready or unready and announces to all clients'''
        def ready(self, player, parts):
            try:
                if player is None:
                    raise UnregisteredPlayerError(self.request)
                self.broadcast_message(player.toggleReady())
            except UnregisteredPlayerError:
                pass

        '''
        Prints a help message for clients
        '''
        def help(self, player, parts):
            message = "\nCOMMANDS:\n/say\n/exit\n/help\n/hand\n/tax\n/register\n/ready\n/endturn\n"
            player.conn.sendall(message)

        '''
        Parses the client's request and dispatches to the correct function
        '''
        def parseRequest(self, player, message):
                parts = message.split(' ',1)
                command = parts[0]
                COUP = 7
		ASSASSINATE = 3
                TAX = 3
                FOREIGN_AID = 2
                INCOME = 1

                if command == "/say":
                    self.chatMessage(player, parts)
                elif command == "/exit":
                    self.kick(player, parts)
                elif command == "/help":
                    self.help(player,parts)
                elif command == "/hand":
                    self.showHand(player, parts)
                elif command == "/coins":
                    self.showCoins(player, parts)
                elif command == "/tax":
                    self.getCoins(player, parts, TAX)
                elif command == "/income":
                    self.getCoins(player, parts, INCOME)
                elif command == "/aid":
                    self.getCoins(player, parts, FOREIGN_AID)
                elif command == "/coup":
                    self.destroy(player, parts, COUP)
                elif command == "/assasinate":
                    self.destroy(player, parts, ASSASSINATE)
                elif command == "/register":
                    self.register(parts)
                elif command == "/ready":
                    self.ready(player, parts)
                elif command == "/endturn":
                    self.endturn(player, parts)
                elif command == "/players":
                    self.listplayers(parts)
                elif command != "":
                    self.request.sendall("Unrecognized command.\n")

#A data structure containing a list of player objects
#Used to keep track of players and turns
class PlayerQueue():
    def __init__(self):
        #Initialize a queue structure that contains players
        self.players = deque([],maxlen=6)

    '''Add a player to the turn queue'''
    def addPlayer(self, player):
            self.players.append(player)

    '''Remove a player from the turn queue'''
    def removePlayer(self, player):
            self.players.remove(player)

    '''Returns true if the client has registered, false otherwise'''
    def isClientRegistered(self, conn):
        for player in self.players:
            if conn == player.conn:
                return True
        return False

    '''Returns the player at the front of the turn queue. This player will move next'''
    def getCurrentPlayer(self):
        if self.numPlayers > 0:
            return list(self.players)[0]
        else:
            return None

    '''Returns true if it is player's turn to move. False otherwise.'''
    def isPlayersTurn(self, player):
        return player == self.getCurrentPlayer()

    '''Returns the player with the matching connection identifier'''
    def getPlayer(self, conn):
        for player in self.players:
            if conn == player.conn:
                return player
        return None

    '''Returns the player with the matching name'''
    def getPlayerByName(self, name):
        for player in self.players:
            if name == player.name:
                return player
        return None

    '''Returns the queue in list form for easy iteration'''
    def list(self):
        return list(self.players)

    '''Cycle the turn so that the next player in line is now set to move'''
    def advanceTurn(self):
        self.players.rotate(1)
        return "It is now {}'s turn to move.\n".format(self.getCurrentPlayer().name)


    '''Gets the current number of players in the turn queue'''
    def numPlayers(self):
        return len(self.players)

class CoupGame(object):
        def __init__(self):
                self.deck = Deck()
                self.destroyedCards = []
                self.players = PlayerQueue()

                #coins dispersed
                self.treasury = 50 - 2 * self.players.numPlayers() #50 is starting amt

                #deck shuffled
                self.deck.shuffle()

class Player(object):
        def __init__(self, conn, name, card1, card2):
                self.name = name
                self.coins = 2
                self.cards = [card1, card2]
                self.ready = False
                self.conn = conn

        '''Sets the player as "READY or "NOT READY" so that the game can begin'''
        def toggleReady(self):
            self.ready = not self.ready
            if self.ready:
                return "{} is READY!\n".format(self.name)
            else:
                return "{} is NOT READY!\n".format(self.name)

        '''Calls renderCard on each string and returns the result'''
        def getHand(self, reveal):
            hand = "\n{0}'s hand:\n".format(self.name)
            for card in self.cards:
                hand += card.renderCard(reveal)
            return hand

        def killCardInHand(self):
            alivecards = []
            for card in self.cards:
                if card.alive:
                    alivecards.append(card)
            if alivecards == []:
                return "{} has no living cards!\n".format(self.name)
            #TODO: Choice is not random, player chooses
            choice = random.choice(alivecards)
            choice.kill()
            return "{0}'s {1} was just killed!\n".format(self.name, choice.type)

class Card(object):
    def __init__(self, type):
        self.type = type
        self.alive = True

    '''Sets a card as 'flipped' '''
    def kill(self):
        self.alive = False

    '''
    Displays a card in ascii art form
    Reveal is a boolean used to determine if the card should be shown or not
    '''
    def renderCard(self, reveal):
        status = ""
        if self.alive:
            status = "ALIVE"
        else:
            status = "DEAD"

        if not self.alive or reveal:
            return "______\n|     |\n|{0}.| ({1})\n|     |\n|_____|\n".format(self.type[:4], status)

        else:
            return "______\n|     | ({0})\n|     |\n|     |\n|_____|\n".format(status)

class Deck(object):
        def __init__(self):
                self.cards = [
                Card('Contessa'),
                Card('Contessa'),
                Card('Contessa'),
                Card('Duke'),
                Card('Duke'),
                Card('Duke'),
                Card('Captain'),
                Card('Captain'),
                Card('Captain'),
                Card('Assassin'),
                Card('Assassin'),
                Card('Assassin'),
                Card('Ambassador'),
                Card('Ambassador'),
                Card('Ambassador')]
                self.numCards = len(self.cards)

        '''Shuffles all of the cards'''
        def shuffle(self):
                random.seed()
                random.shuffle(self.cards)

        '''Pops a card from the deck'''
        def deal(self):
                self.numCards -= 1
                print "Dealing Card: numCards = ", self.numCards
                return self.cards.pop()

        '''Shows all of the cards in the deck'''
        def fanUp(self):
                for i, card in enumerate(self.cards):
                        print card.renderCard(True)
        '''Adds a card to the deck'''
        def addCard(self, card):
                self.numCards += 1
                self.cards.append(card)

'''
handler_factory() creates a function called create_handler.
The function is handed to the CoupServer.
The function gets invoked when a new handler is created (when a new client connects).
'''
def handler_factory(callback):
    def createHandler(*args, **keys):
        return CoupRequestHandler(callback, *args, **keys)
    return createHandler

if __name__ == "__main__":
    print "Welcome to COUP!\n"
    HOST, PORT = "localhost", int(sys.argv[1])

    cg = CoupGame()
    server = CoupServer((HOST, PORT), handler_factory(cg) )
    ip, port = server.server_address

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    server_thread.join()

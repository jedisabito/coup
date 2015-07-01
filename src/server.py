import SocketServer
from collections import deque
import sys, os, random, time, threading

class CoupServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

class UnregisteredPlayerError(Exception):
    def __init__(self, conn):
        self.conn = conn
        conn.sendall("Please register yourself with /register <name> before you can join.\n")

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
                    if not q.currentlyPlaying(conn):
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
        Prints a help message for clients
        '''
        def help(self, player, parts):
            message = "\nCOMMANDS:\n/say\n/exit\n/help\n"
            player.conn.sendall(message)

        '''
        Prints the player's current hand
        '''
        def showHand(self, player, parts):
            if player is None:
                raise UnregisteredPlayerError(self.request)
            hand = player.getHand()
            player.conn.sendall(hand)

        '''
        Prints the number of coins the player has
        '''
        def showCoins(self, player, parts):
            if player is None:
                raise UnregisteredPlayerError(self.request)
            message = "Coins: {}\n".format(player.coins)
            player.conn.sendall(message)

        '''
        Performs a coup tax
        '''
        def tax(self, player, parts):
            if player is None:
                raise UnregisteredPlayerError(self.request)
            return

        '''
        A helper to verify that a requested name is valid before it is registered
        '''
        def isValidName(self, name):
            try:
                strname = str(name)
                length = len(strname)
                if length <= 0 or length >= 20:
                    self.request.sendall("Name must be between 1 and 20 characters in length.\n")
                    return False
                if self.cg.players.currentlyPlaying(self.request):
                    self.request.sendall("A user with this name is already registered.\n")
                    return False
                return True
            except ValueError:
                self.request.sendall("Something went wrong registering your name.\n")
                return False

        '''
        Registers the client with the name provided
        '''
        def register(self, parts):
                if len(parts) >= 2:
                    name = parts[1]
                    if self.isValidName(name):
                        newPlayer = Player(self.request, name, self.cg.deck.deal(), self.cg.deck.deal())
                        self.cg.players.addPlayer(newPlayer)
                        self.welcome(name)
                else:
                    self.request.sendall("Could not register: Please provide a name.")

        '''
        Parses the client's request and dispatches to the correct function
        '''
        def parseRequest(self, player, message):
                parts = message.split(' ',1)
                command = parts[0]

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
                    self.tax(player, parts)
                elif command == "/register":
                    self.register(parts)
                else:
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

    '''Returns the player at the front of the turn queue. This player will move next'''
    def getCurrentPlayer(self):
        if self.numPlayers > 0:
            return list(self.players)[0]
        else:
            return None

    '''Returns the player with the matching connection identifier'''
    def getPlayer(self, conn):
        for player in self.players:
            if conn == player.conn:
                return player
        return None

    '''Returns the queue in list form for easy iteration'''
    def list(self):
        return list(self.players)

    '''Cycle the turn so that the next player in line is now set to move'''
    def advanceTurn(self):
        return self.players.rotate(1)

    '''Gets the current number of players in the turn queue'''
    def numPlayers(self):
        return len(self.players)

    '''Checks to see if a client connection is a registered player'''
    def currentlyPlaying(self, conn):
        for player in self.players:
            if conn == player.conn:
                return True
        return False


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
                return "{} is READY!".format(self.name)
            else:
                return "{} is NOT READY".format(self.name)

        '''Calls renderCard on each string and returns the result'''
        def getHand(self):
            hand = ""
            for card in self.cards:
                hand += card.renderCard(True)
            return hand

class Card(object):
    def __init__(self, type):
        self.type = type
        self.alive = True

    '''Sets a card as 'flipped' '''
    def kill(self):
        self.alive = False

    '''Displays a card in ascii art form'''
    def renderCard(self, reveal):
        if self.alive and not reveal:
            return "_____\n|    |\n|    |\n|    |\n|____|\n"
        else:
            return "_____\n|    |\n|{}|\n|    |\n|____|\n".format(self.type)

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
                self.numCards = len(cards)

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
    HOST, PORT = "localhost", 7064

    cg = CoupGame()
    server = CoupServer((HOST, PORT), handler_factory(cg) )
    ip, port = server.server_address

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    server_thread.join()

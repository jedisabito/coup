import SocketServer
from collections import deque
import sys, os, random, time, threading

class CoupServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

class CoupRequestHandler(SocketServer.BaseRequestHandler):
        def __init__(self, callback, *args, **keys):
            self.cg = callback
            SocketServer.BaseRequestHandler.__init__(self, *args, **keys)

        '''Broadcasts message to all connected players'''
        def broadcast_message(self, message):
            for player in self.cg.players.list():
                player.conn.sendall(message)

        def handle(self):
            q = self.cg.players
            conn = self.request

            while True:
                try:
                    self.data = conn.recv(1024).strip()
                    #If the player issuing the request is in the game...
                    if q.currentlyPlaying(conn):
                        #If it is the requesting player's turn...
                        player = q.getPlayerTurn()
                        if player.conn == conn:
                            conn.sendall("It's your turn!\n")
                            self.chatMessage(player, self.data)
                        else:
                            conn.sendall("Wait your turn!\n")
                    else:
                        newPlayer = Player(conn, "Alec", self.cg.deck.deal(), self.cg.deck.deal())
                        q.addPlayer(newPlayer)
                        self.welcome("Alec")
                except IOError:
                    conn.close()
                    q.removePlayer(conn)
                    return

        def chatMessage(self, player, message):
            self.broadcast_message("{0}: {1}\n".format(player.name, message))

        def welcome(self, name):
            self.broadcast_message("{} joined the game!\n".format(name))

#A data structure containing a list of player objects
#Used to keep track of players and turns
class PlayerQueue():
    def __init__(self):
        #Initialize a queue structure that contains players
        self.players = deque([],maxlen=6)

    def addPlayer(self, player):
            self.players.append(player)

    def removePlayer(self, player):
            try:
                self.players.remove(player)
            except:
                print "Could not remove player: no matches"

    def getPlayerTurn(self):
        if self.numPlayers > 0:
            return list(self.players)[0]
        else:
            return None

    def list(self):
        return list(self.players)

    def advanceTurn(self):
        return self.players.rotate(1)

    def numPlayers(self):
        return len(self.players)

    def currentlyPlaying(self, conn):
        for player in self.players:
            if conn == player.conn:
                return True
        return False

    def getPlayerByName(self, name):
        for player in self.players:
            if name == player.name:
                return player
        return None

'''The moderator is a class responsible for carrying out actions on behalf of the player.'''
class Moderator():
    def __init__(self, cg):
        self.cg = cg

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
        def aboutMe(self):
                pCards = ""
                for card in self.cards:
                        pCards += card + " "
                return "Coins: " + str(self.coins) + "\nCards: " + pCards

        def draw(self, newCard):
                self.cards.append(newCard)

        def toggleReady(self):
            self.ready = not self.ready
            if self.ready:
                return "{} is READY!".format(self.name)
            else:
                return "{} is NOT READY".format(self.name)

        def lookAtHand(self):
            hand = ""
            for card in self.cards:
                hand += card.renderCard(True)
            return hand

class Card(object):
    def __init__(self, type):
        self.type = type
        self.alive = True

    def kill(self):
        self.alive = False

    def renderCard(self, reveal):
        if self.alive and not reveal:
            return "____\n|    |\n|    |\n|    |\n|____|\n"
        else:
            return "____\n|    |\n|{}|\n|    |\n|____|\n".format(self.type)

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

                self.numCards = 15

        def shuffle(self):
                random.seed()
                random.shuffle(self.cards)

        def deal(self):
                self.numCards -= 1
                print "Dealing Card: numCards = ", self.numCards
                return self.cards.pop()

        def fanUp(self):
                for i, card in enumerate(self.cards):
                        print card.renderCard(True)

        def addCard(self, card):
                self.cards.append(card)

def handler_factory(callback):
    def createHandler(*args, **keys):
        return CoupRequestHandler(callback, *args, **keys)
    return createHandler

if __name__ == "__main__":
    print "Welcome to COUP!\n"
    HOST, PORT = "localhost", 7050

    cg = CoupGame()
    server = CoupServer((HOST, PORT), handler_factory(cg) )
    ip, port = server.server_address

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    server_thread.join()

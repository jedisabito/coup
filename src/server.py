import SocketServer
from collections import deque
import sys, os, random, time, threading

class CoupServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

class CoupRequestHandler(SocketServer.BaseRequestHandler):
        def __init__(self, callback, *args, **keys):
            self.cg = callback
            SocketServer.BaseRequestHandler.__init__(self, *args, **keys)

        def handle(self):
            while True:
                q = self.cg.players
                raddr = self.client_address[0]
                self.data = self.request.recv(1024).strip()

                #If the player issuing the request is in the game...
                if q.currentlyPlaying(raddr):
                    #If it is the requesting player's turn...
                    if q.getPlayerTurn().ipAddr == raddr:
                        self.request.sendall("It's your turn!\n")
                        #Parse request (self.data)
                    else:
                        self.request.sendall("Wait your turn!\n")
                else:
                    newPlayer = Player(raddr, "Alec", self.cg.deck.deal(), self.cg.deck.deal())
                    q.addPlayer(newPlayer)
                    self.welcome("Alec")

        def parseMessage(self):
            return

        def welcome(self, name):
            self.request.sendall("{} joined the game!\n".format(name))

#A data structure containing a list of player objects
#Used to keep track of players and turns
class PlayerQueue():
    def __init__(self):
        #Initialize a queue structure that contains players
        self.players = deque([],maxlen=6)

    def addPlayer(self, player):
            self.players.append(player)
            print "Added player!"

    def getPlayerTurn(self):
        if self.numPlayers > 0:
            return list(self.players)[0]
        else:
            return None

    def advanceTurn(self):
        return self.players.rotate(1)

    def numPlayers(self):
        return len(self.players)

    def currentlyPlaying(self, ipAddr):
        for player in self.players:
            if ipAddr == player.ipAddr:
                return True
        return False

    def getPlayerByName(self, name):
        for player in self.players:
            if name == player.name:
                return player
        return None


'''The moderator is a class responsible for carrying out actions on behalf of the player.'''
class Moderator():
    def __init__(self):
        return

    #Define methods that interact between two players or the player and the deck


class CoupGame(object):
        def __init__(self):
                self.deck = Deck()
                self.destroyedCards = []
                self.players = PlayerQueue()

                #coins dispersed
                self.treasury = 50 - 2 * self.players.numPlayers() #50 is starting amt

                #deck shuffled
                self.deck.shuffle()

        def renderCard(card):
            return

class Player(object):
        def __init__(self, ipAddr, name, card1, card2):
                self.name = name
                self.coins = 2
                self.cards = [card1, card2]
                self.ready = False
                self.ipAddr = ipAddr
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
                print "{} is READY!".format(self.name)
            else:
                print "{} is NOT READY".format(self.name)

        def lookAtHand(self):
            for card in self.cards:
                    print card

class Card(object):
    def __init__(self, type):
        self.type = type
        self.alive = True

    def kill(self):
        self.alive = False

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
                        print i, " ", card

        def addCard(self, card):
                self.cards.append(card)

def handler_factory(callback):
    def createHandler(*args, **keys):
        return CoupRequestHandler(callback, *args, **keys)
    return createHandler

if __name__ == "__main__":
    print "Welcome to COUP!\n"
    HOST, PORT = "130.215.249.79", 5120
    cg = CoupGame()

    server = CoupServer((HOST, PORT), handler_factory(cg) )
    ip, port = server.server_address

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    server_thread.join()

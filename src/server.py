#Authors: Joe DiSabito, Ryan Hartman, Alec Benson
import SocketServer
from collections import deque
import sys, threading, urllib
from deck import Deck
from vote import Vote
from player import Player, PlayerQueue
from error import *

class CoupServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

class CoupRequestHandler(SocketServer.BaseRequestHandler):
    def __init__(self, callback, *args, **keys):
        self.cg = callback
        SocketServer.BaseRequestHandler.__init__(self, *args, **keys)

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

    '''Broadcasts message to all connected players'''
    def broadcast_message(self, message):
        for player in self.cg.players.listPlayers():
            player.conn.sendall(message)

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
            if len(player.cards) > 2:
                raise AlreadyExchangingError(self.request)
            if player.coins >= 10:
                raise MustCoupError(self.request)

            return True
        except (AlreadyExchangingError, UnregisteredPlayerError, NotYourTurnError, NotEnoughTreasuryCoinsError, MustCoupError) as e:
            return False

	'''
	Functions (duke, foreignAid, income) using getCoins as helper function
	'''
    def tax(self, player, parts):
        if self.getCoins(player, parts, 3):
             
            self.broadcast_message("{} called TAX, the Duke ability, and will get 3 coins. Other players type \"/challenge\" or \"/pass\" to continue.\n".format(player.name))
            
            def failFunc(handler, passers, player):
                player.coins += 3
                handler.cg.treasury -= 3
		handler.broadcast_message("No challengers, {} has gained 3 coins.\n".format(player.name))
                handler.broadcast_message(handler.cg.players.advanceTurn())

	    
            def successFunc(handler, challengers, player):

                card = player.checkForCard('Duke')
                if card != -1:
                    #player exchanges Duke with deck
                    handler.cg.deck.swapCard(player, card) 

                    #player gets 3 coins
                    player.coins += 3
                    handler.cg.treasury -= 3

                    #challenger loses a card
                    target = challengers[0]
                    handler.destroy(player, target, 0)
                    handler.broadcast_message("Challenge failed! {0} reveals a Duke from his hand, exchanges it with the deck, and still gains 3 coins. {1} loses a card.\n".format(player.name, target.name)) 
                else:
                    #player loses a card
                    handler.broadcast_message("Challenge succeeded! {0} loses a card.\n".format(player.name))
                    handler.broadcast_message(handler.cg.players.advanceTurn())

            #TODO: Challenge vote given Tax
            voteQueue = PlayerQueue()
            for voter in self.cg.players.listPlayers():
                if not (voter.name == player.name):
                     voteQueue.addPlayer(player)
            passThreshold = (1 - self.cg.players.numPlayers()) * 100
            successArgs = [player]
            failArgs = [player]
            challenge = Vote(self, voteQueue, "challenge", 20, passThreshold, successFunc, successArgs, failFunc, failArgs)
            
 
    def foreignAid(self, player, parts):
        if self.getCoins(player, parts, 2):
            self.broadcast_message("{} receieved FOREIGN AID.\n".format(player.name))

    def income(self, player, parts):
        if self.getCoins(player, parts, 1):
            self.broadcast_message("{} called INCOME.\n".format(player.name))

    '''
    Stealing, CAPTAIN ability
    '''
    def steal(self, player, parts):
        try:
            if player is None:
                raise UnregisteredPlayerError(self.request)

            if not self.cg.players.isPlayersTurn(player):
                raise NotYourTurnError(self.request)

            if player.coins >= 10:
                raise MustCoupError(self.request)

            if len(player.cards) > 2:
                raise AlreadyExchangingError(self.request)

            name = parts[1]
            if name == player.name:
                raise InvalidCommandError(self.request, "You cannot target yourself.\n")

            target = self.cg.players.getPlayerByName(name)
            if target == None:
                raise NoSuchPlayerError(self.request, name)

            if target.coins < 2:
                raise NotEnoughCoinsError(self.request, target.name)

            message = player.name + " is claiming CAPTAIN, stealing from " + target.name + ".\n"
            self.broadcast_message(message)

            #TODO:Challenge and block
            player.coins += 2
            target.coins -= 2
            self.broadcast_message(self.cg.players.advanceTurn())
        except (UnregisteredPlayerError, NotYourTurnError, InvalidCommandError, NoSuchPlayerError, NotEnoughCoinsError, MustCoupError, AlreadyExchangingError) as e:
            pass

    '''
    Exchanging cards with deck, AMBASSADOR ability
    '''
    def exchange(self, player, parts):
        try:
            if player is None:
                raise UnregisteredPlayerError(self.request)

            if not self.cg.players.isPlayersTurn(player):
                raise NotYourTurnError(self.request)

            if len(player.cards) > 2:
                raise AlreadyExchangingError(self.request)

            if player.coins >= 10:
                raise MustCoupError(self.request)

            message = player.name + " is claiming AMBASSADOR, exchanging cards with the deck.\n"
            self.broadcast_message(message)

            player.cards.append(cg.deck.deal())
            player.cards.append(cg.deck.deal())
            self.showHand(player, ["",player.name])

            message = player.name + " has been dealt two cards to exchange.\n"
            self.broadcast_message(message)

            player.conn.sendall("Select cards to remove (1 to {}, where 1 is the top card)" \
                                "from least to greatest without a space. Ex. /remove 23\n".format(str(len(player.cards))))
        except (AlreadyExchangingError, UnregisteredPlayerError, NotYourTurnError,
                InvalidCommandError, NoSuchPlayerError, NotEnoughCoinsError, MustCoupError) as e:
                pass

    '''
    Remove function to carry out the second half of Ambassador ability.
    '''
    def remove(self, player, parts):
        try:
            if player is None:
                raise UnregisteredPlayerError(self.request)

            if not self.cg.players.isPlayersTurn(player):
                raise NotYourTurnError(self.request)

            if len(player.cards) <= 2:
                raise CannotRemoveError(self.request)

            card1 = int(parts[1]) % 10 - 1
            card2 = int(parts[1]) / 10 - 1
            cg.deck.addCard(player.cards[card1])
            cg.deck.addCard(player.cards[card2])
            del player.cards[card1]
            del player.cards[card2]

            self.showHand(player, ["",player.name])

            message = player.name + " has returned 2 cards to the deck.\n"
            self.broadcast_message(message)

            self.broadcast_message(self.cg.players.advanceTurn())
            cg.deck.shuffle()

        except (CannotRemoveError, UnregisteredPlayerError, NotYourTurnError,
            InvalidCommandError, NoSuchPlayerError, NotEnoughCoinsError, MustCoupError, NotEnoughArguments) as e:
            pass

    '''
    Performs card destruction (coup, assassination, challenge)
    '''
    def destroy(self, player, target, coins):
        try:
            if player is None:
                raise UnregisteredPlayerError(self.request)

            if not self.cg.players.isPlayersTurn(player) and coins != 0:
                raise NotYourTurnError(self.request)

            if player.coins >= 10 and coins == 3:
                raise MustCoupError(self.request)

            if len(parts) < 2:
                raise InvalidCommandError(self.request, "You need to specify a player (by name) that you want to target\n")

            name = parts[1]
            if name == player.name:
                raise InvalidCommandError(self.request, "You cannot target yourself. Nice try.\n")

            if player.coins < coins:
                raise NotEnoughCoinsError(self.request, "")

            target = self.cg.players.getPlayerByName(name)
            if target == None:
                raise NoSuchPlayerError(self.request, name)

            player.coins -= coins
            self.cg.treasury += coins

            #TODO: ADD CHALLENGE/PROTECTION CHANCE HERE
            self.broadcast_message(".\n".format(player.name, target.name))
            self.broadcast_message(target.killCardInHand())
            self.broadcast_message(self.cg.players.advanceTurn())
            return target
        except (UnregisteredPlayerError, NotYourTurnError, InvalidCommandError, NoSuchPlayerError, NotEnoughCoinsError, MustCoupError) as e:
            return None

    '''
    Assassination (using destroy as helper function), card destruction with loss of 3 coins
    '''
    def assassinate(self, player, parts):
        target = self.cg.players.getPlayerByName(parts[1])
        target = self.destroy(player, target, 3)
        if target is not None:
            self.broadcast_message("{0} will ASSASSINATE {1}.\n".format(player.name, target.name))

    '''
    Coup (using destroy as helper function), card destruction with loss of 7 coins
        '''
    def coup(self,player,parts):
        target = self.cg.players.getPlayerByName(parts[1])
        target = self.destroy(player, parts, 7)
        if target is not None:
            self.broadcast_message("{0} called a COUP on {1}.\n".format(player.name, target.name))

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
                msg = self.cg.players.addPlayer(newPlayer)
                self.broadcast_message(msg)
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
        message = "\nCOMMANDS:\n/say\n/exit\n/help\n/hand\n/tax\n/register\n/exchange\n/income\n/aid\n/steal\n/assassinate\n/ready\n/endturn\n"
        player.conn.sendall(message)

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
        elif command == "/income":
            self.income(player, parts)
        elif command == "/aid":
            self.foreignAid(player, parts)
        elif command == "/coup":
            self.coup(player, parts)
        elif command == "/assassinate":
            self.assassinate(player, parts)
        elif command == "/exchange":
            self.exchange(player, parts)
        elif command == "/remove":
            self.remove(player, parts)
        elif command == "/steal":
            self.steal(player, parts)
        elif command == "/register":
            self.register(parts)
        elif command == "/ready":
            self.ready(player, parts)
        elif command == "/endturn":
            self.endturn(player, parts)
        elif command == "/players":
            self.listplayers(parts)
        elif command == "/challenge":
            currentVote = self.players.getVote("challenge")
            currentVote.vote(player, True)
                 
        elif command == "/pass":
            currentVote = self.players.getVote("challenge")
            currentVote.vote(player, False)
        elif command != "":
            self.request.sendall("Unrecognized command.\n")

class CoupGame(object):
    def __init__(self):
        self.deck = Deck()
        self.destroyedCards = []
        self.players = PlayerQueue()

        #coins dispersed
        self.treasury = 50 - 2 * self.players.numPlayers() #50 is starting amt

        #deck shuffled
        self.deck.shuffle()

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
    HOST, PORT = sys.argv[1], int(sys.argv[2])

    if sys.argv[1] == "external":
        HOST = urllib.urlopen('http://canihazip.com/s').read()
        print "Network-facing IP:", HOST

    cg = CoupGame()

    try:
        server = CoupServer((HOST, PORT), handler_factory(cg) )
    except Exception as e:
	server = CoupServer(('localhost', PORT), handler_factory(cg) )
        print "External binding FAILED. Running LOCALLY on port", PORT

    ip, port = server.server_address

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    server_thread.join()

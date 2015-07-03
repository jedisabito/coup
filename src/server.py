#Authors: Joe DiSabito, Ryan Hartman, Alec Benson

import SocketServer
from collections import deque
import sys, os, random, time, threading, urllib

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
        for player in self.cg.players.list():
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

		    #TODO: These two lines should only happen if no challenges.
            player.coins += coins
            self.cg.treasury -= coins
            self.broadcast_message(self.cg.players.advanceTurn())
            return True
        except (AlreadyExchangingError, UnregisteredPlayerError, NotYourTurnError, NotEnoughTreasuryCoinsError, MustCoupError) as e:
            return False

	'''
	Functions (duke, foreignAid, income) using getCoins as helper function
	'''
    def tax(self, player, parts):
        if self.getCoins(player, parts, 3):
            self.broadcast_message("{} called a TAX, the Duke ability.\n".format(player.name))

    def foreignAid(self, player, parts):
        if self.getCoins(player, parts, 2):
            self.broadcast_message("{} called FOREIGN AID.\n".format(player.name))

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

            '''
            #Same line twice, not sure if its worth consolidating
            player.draw(cg.deck.deal())
            player.draw(cg.deck.deal())

            cg.players[name].lookAtHand()
            #print cards[numCards - 1], cards[numCards - 2]

            #This will enforce handsizes. This is the only time someone's
            #hand should be bigger than 2

            to_deck = raw_input("which card will you discard first? (0-3): ")
            cg.deck.addCard(cg.players[name].cards[int(to_deck)])
            cg.players[name].cards.remove(cg.players[name].cards[int(to_deck)])

            cg.players[name].lookAtHand()

            to_deck = raw_input("which card will you discard second? (0-2): ")
            cg.deck.addCard(cg.players[name].cards[int(to_deck)])
            cg.players[name].cards.remove(cg.players[name].cards[int(to_deck)])

            self.broadcast_message(self.cg.players.advanceTurn())
            cg.deck.shuffle()
            '''
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
    def destroy(self, player, parts, coins):
        try:
            if player is None:
                raise UnregisteredPlayerError(self.request)

            if not self.cg.players.isPlayersTurn(player):
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
        target = self.destroy(player, parts, 3)
        if target is not None:
            self.broadcast_message("{0} will ASSASSINATE {1}.\n".format(player.name, target.name))

    '''
    Coup (using destroy as helper function), card destruction with loss of 7 coins
        '''
    def coup(self,player,parts):
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
        elif command != "":
            self.request.sendall("Unrecognized command.\n")

'''
timeout - number of seconds the vote lasts for
options - a list of voteOptions that players can vote for
successFunction - the function that runs if the vote passes
failFunction - the function that runs if the vote fails
eligiblePlayers - the players that are able to vote in this vote
'''
class Vote(object):
    def __init__(self, playerQueue, name, timeout, passThreshhold, successFunction, failFunction):
        #Votes is a list of players that have voted in favor
        self.timeout = timeout
        self.name = name
        self.playerQueue = playerQueue
        self.playerList = self.playerQueue.list()

        self.successFunction = successFunction
        self.failFunction = failFunction

        self.yesList = []
        self.noList = []
        self.passThreshhold = passThreshhold

        self.voteThread = threading.Thread( target = self.startVote )
        self.voteThread.start()
        self.concluded = False

    '''
    Initiates a vote that lasts for timeout seconds
    '''
    def startVote(self):
        self.playerQueue.ongoingVotes[self.name] = self
        timer = 0
        while timer <= self.timeout:
            time.sleep(1)
            timer += 1
            print "{} seconds into vote...\n".format(i)
            if self.concluded:
                return
        if not self.concluded:
            return self.voteFail()

    '''
    Checks to see if the vote has reached a conclusion
    '''
    def checkResults(self):
        #Number of people eligible to vote
        eligibleVotes = len(self.playerList)
        #Number of people voting YES
        yesVotes = len(self.yesList)
        #Percentage of eligible voters voting YES
        yesPercent = int((yesVotes/eligibleVotes)*100)
        #Percentage of eligible voters voting NO
        noPercent = 1 - yesPercent

        if yesPercent >= self.passThreshhold:
            self.votePass()
        elif noPercent >= (1 - self.passThreshhold):
            self.voteFail()

    '''
    Allows a player to vote for a particular option
    '''
    def vote(self, player, vote):
        try:
            if player in self.playerList:
                if player not in self.yesList or player not in self.noList:
                    if vote:
                        self.yesList.append(player)
                    else:
                        self.noList.append(player)
                    self.checkResults()
                else:
                    raise InvalidCommandError(player.conn, "You already voted in this poll")
            else:
                raise InvalidCommandError(player.conn, "You are not eligible to vote in this poll")
        except InvalidCommandError:
            pass

    def votePass(self):
        self.successFunction()
        del self.playerQueue.ongoingVotes[self.name]
        self.concluded = True
        self.voteThread.exit()

    def voteFail(self):
        self.failFunction()
        del self.playerQueue.ongoingVotes[self.name]
        self.concluded = True
        self.voteThread.exit()

#A data structure containing a list of player objects
#Used to keep track of players and turns
class PlayerQueue():
    def __init__(self):
        #Initialize a queue structure that contains players
        self.players = deque([],maxlen=6)

    '''Add a player to the turn queue'''
    def addPlayer(self, player):
        self.players.append(player)
        return "{} joined the game!\n".format(player.name)


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
        print "Returning Card: numCards = ", self.numCards

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

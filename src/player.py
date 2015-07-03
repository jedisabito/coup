from collections import deque

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

#A data structure containing a list of player objects
#Used to keep track of players and turns
class PlayerQueue():
    def __init__(self):
        #Initialize a queue structure that contains players
        self.players = deque([],maxlen=6)
        self.ongoingVotes = {}

    def getVote(self, name):
        if name in self.ongoingVotes.keys():
            return self.ongoingVotes[name]
        return None

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

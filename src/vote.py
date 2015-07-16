from error import *
import threading, urllib, time
from deck import Deck
from player import Player, PlayerQueue

'''
timeout - number of seconds the vote lasts for
options - a list of voteOptions that players can vote for
successFunction - the function that runs if the vote passes
failFunction - the function that runs if the vote fails
eligiblePlayers - the players that are able to vote in this vote
'''
class Vote(object):
    def __init__(self, handler, playerQueue, name, timeout, passThreshold, successFunc, successArgs, failFunc, failArgs):
        #Votes is a list of players that have voted in favor
        self.handler = handler
        self.timeout = timeout
        self.name = name
        self.playerQueue = playerQueue
        self.playerList = self.playerQueue.listPlayers()

        self.yesList = []
        self.noList = []
        self.passThreshold = passThreshold

        self.successFunc = successFunc
        self.successArgs = successArgs
        self.failFunc = failFunc
        self.failArgs = failArgs

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
            if timer % 10 == 0:
                 print "{} seconds left...\n".format(self.timeout - timer)
            if self.concluded:
		self.votePass()
                return
        if not self.concluded:
            self.voteFail()
            return

    '''
    Checks to see if the vote has reached a conclusion
    '''
    def checkResults(self):
        #Number of people eligible to vote
        eligibleVotes = float(len(self.playerList))
        #Number of people voting YES
        yesVotes = float(len(self.yesList))
        #Percentage of eligible voters voting YES
        yesPercent = (yesVotes/eligibleVotes)*100
        #Percentage of eligible voters voting NO
        noPercent = 100 - yesPercent
        print "yes percent is {0}, eligible votes is {1}".format(yesPercent, eligibleVotes)

        if yesPercent >= self.passThreshold:
            self.votePass()
        elif noPercent >= (100 - self.passThreshold):
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
        del self.playerQueue.ongoingVotes[self.name]
        self.concluded = True
        self.successFunc(self.handler, self.noList, *self.successArgs)
        print "PASSED"

    def voteFail(self):
        del self.playerQueue.ongoingVotes[self.name]
        self.concluded = True
        self.failFunc(self.handler, self.noList, *self.failArgs)
        print "FAILED"

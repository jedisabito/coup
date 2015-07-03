from error import *
import threading, urllib

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

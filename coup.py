#Author: Joe DiSabito
#Description: Allows automation of Coup game without cards. Requires moderator
#to operate. Python is weird about dictionaries (no list elements allowed),
#which made the Ambassador ability very difficult. Would have liked
#each person's hand to be a list of cards, but that was not possible.
#Anyways, enjoy!
#!/usr/bin/python

import sys, os, random, time

class Player(object):
        def __init__(self, card1, card2):
                self.coins = 2
                self.cards = [card1, card2]
        def aboutMe(self):
                pCards = ""
                for card in self.cards:
                        pCards += card + " "
                return "Coins: " + str(self.coins) + "\nCards: " + pCards
        def draw(self, newCard):
                self.cards.append(newCard)
        def lookAtHand(self):
                for card in self.cards:
                        print card
                
class Deck(object):
        def __init__(self):
                self.cards = self.cards = ['Contessa', 'Contessa', 'Contessa', 'Duke', 'Duke', 'Duke', 'Captain', 'Captain', 'Captain', 'Assassin', 'Assassin', 'Assassin', 'Ambassador' ,'Ambassador' ,'Ambassador']
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

        


        
        

class CoupGame(object):
        def __init__(self):
                #self.cards = ['Contessa', 'Contessa', 'Contessa', 'Duke', 'Duke', 'Duke', 'Captain', 'Captain', 'Captain', 'Assassin', 'Assassin', 'Assassin', 'Ambassador' ,'Ambassador' ,'Ambassador']
                self.deck = Deck()
                #self.numCards = 15
                self.destroyedCards = []
                self.players = {}
                self.numPlayers = input("Number of players (2-6): ")

                if self.numPlayers >= 2 and self.numPlayers <= 6:
	                #coins dispersed
	                self.treasury = 50 - 2 * self.numPlayers #50 is starting amt

	                #deck shuffled
	                self.deck.shuffle()

	                #cards dealt
	                for i in range(self.numPlayers):
		                name = raw_input("Player name: ")
                                newPlayer = Player(self.deck.deal(), self.deck.deal())
		                #players.append((name,cards[numCards - 1], cards[numCards - 2], 2))
	                        self.players[name] = newPlayer
	                        print self.players[name].aboutMe()
                                

        
                

#initialized deck of cards, numCards used as an "index pointer", tells us 
#where the last card of the deck is (numCards - 1)



#after cards are lost, they are added to this list


#starting treasury


#will become a dictionary with each player's name as keys, each entry
#provides information on that player (cards held, number of coins) 


print "Welcome to COUP!\n"
cg = CoupGame()





	#waits for moderator's input, acts accordingly
response = 's'
while response != 'q':
        response = raw_input("(s)tatus\ncoun(t)s\n(e)xchange\ns(h)uffle\n(c)oins\n(d)estroy\nta(x)\nstea(l)\n(i)ncome\n(f)oreign aid\n(q)uit:")
        #Prints out raw statistics of the current game
        if response == 's':
                for player in cg.players.iterkeys():
                        print player, cg.players[player].aboutMe()
                cg.deck.fanUp() #Print all cards in deck
                print "Cards in deck:", cg.deck.numCards
                print "Treasury: ", cg.treasury

        #Allows for Ambassador ability
        elif response == 'e':
                name = raw_input("Player name: ")
                print cg.players[name].aboutMe()
                print "2 cards dealt to", name

                #Same line twice, not sure if its worth consolidating
                cg.players[name].draw(cg.deck.deal())
                cg.players[name].draw(cg.deck.deal())

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
                        
                # if not (players[name][1] == "GONE" or players[name][2] == "GONE"):
                #         exchange = input("Exchange 0 (neither)\n" +
                #                          "Exchange 1 (first with first)\n" +
                #                          "Exchange 2 (first with second)\n" +
                #                          "Exchange 3 (second with first)\n" +
                #                          "Exchange 4 (second with second)\n" +
                #                          "Exchange 5 (both):")
                #         if exchange == 5:
                #                 temp = [players[name][1], players[name][2]]
                #                 players[name][0] = cards[numCards - 1]
                #                 players[name][1] = cards[numCards - 2]
                #                 cards[numCards - 1] = temp[0]
                #                 cards[numCards - 2] = temp[1]
                #         elif exchange == 4:
                #                 temp = players[name][1]
                #                 players[name][1] = cards[numCards - 2]
                #                 cards[numCards - 2] = temp
                #         elif exchange == 3:
                #                 temp = players[name][1]
                #                 players[name][1] = cards[numCards - 1]
                #                 cards[numCards - 1] = temp
                #         elif exchange == 2:
                #                 temp = players[name][0]
                #                 players[name][0] = cards[numCards - 2]
                #                 cards[numCards - 2] = temp
                #         elif exchange == 1:
                #                 temp = players[name][0]
                #                 players[name][0] = cards[numCards - 1]
                #                 cards[numCards - 1] = temp
                # else:
                #         exchange = input("Exchange 0 (neither)\n" +
                #                          "Exchange 1 (with first)\n" +
                #                          "Exchange 2 (with second):")
                #         card = 0
                #         temp = players[name][card]
                #         if temp == "GONE":
                #                 card = card + 1
                #                 temp = players[name][card]

                #         if exchange == 2:
                #                 players[name][card] = cards[numCards - 2]
                #                 cards[numCards - 2] = temp
                #         elif exchange == 1:	
                #                 players[name][card] = cards[numCards - 1]
                #                 cards[numCards - 1] = temp

                cg.deck.shuffle()

        #Coin counts (without held cards)
        elif response == 't':
                for player in cg.players.iterkeys():
                        print player, ":", cg.players[player].coins
                print "Treasury:", treasury

        #Shuffle option
        elif response == 'h':
                cg.deck.shuffle()

        #Adjust coin amount of one player
        elif response == 'c':
                name = raw_input("Player name:")
                print name, "current coins:", cg.players[name].coins
                newVal = input("New coin count:")
                cg.players[name].coins = newVal

        #Duke ability - Tax
        elif response == 'x':
                name = raw_input("Player name:")
                cg.players[name].coins += 3
                cg.treasury -= 3

        #Income
        elif response == 'i':
                name = raw_input("Player name:")
                cg.players[name].coins += 1
                cg.treasury -= 1

        #Foreign Aid
        elif response == 'f':
                name = raw_input("Player name:")
                cg.players[name].coins += 2
                cg.treasury -= 2

        #Captain Ability - Steal
        elif response == 'l':
                name1 = raw_input("Captain claimer:")
                name2 = raw_input("Target:")
                cg.players[name1].coins += 2
                cg.players[name2].coins -= 2

        #Destruction of a card (Coup or Assassination or failed bluff/challenge)
        elif response == 'd':
                name = raw_input("Player name:")
                print cg.players[name].aboutMe()
                
                remove = input("Which to remove(0-1):")
                cg.destroyedCards.append(cg.players[name].cards[int(remove)]) 
                cg.players[name].cards.remove(cg.players[name].cards[int(remove)])
                print cg.players[name].aboutMe()

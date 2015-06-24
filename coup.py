#Author: Joe DiSabito
#Description: Allows automation of Coup game without cards. Requires moderator
#to operate. Python is weird about dictionaries (no list elements allowed),
#which made the Ambassador ability very difficult. Would have liked
#each person's hand to be a list of cards, but that was not possible.
#Anyways, enjoy!
#!/usr/bin/python

import sys, os, random, time


#shuffles the deck
def shuffle(cards):
	random.seed()
	for i in range(numCards):
		r = random.randrange(numCards)
		temp = cards[i]
		cards[i] = cards[r]
		cards[r] = temp
	return cards

#initialized deck of cards, numCards used as an "index pointer", tells us 
#where the last card of the deck is (numCards - 1)
cards = ['Contessa', 'Contessa', 'Contessa', 'Duke', 'Duke', 'Duke', 'Captain', 'Captain', 'Captain', 'Assassin', 'Assassin', 'Assassin', 'Ambassador' ,'Ambassador' ,'Ambassador']
numCards = 15

#after cards are lost, they are added to this list
destroyedCards = []

#starting treasury
treasury = 50

#will become a dictionary with each player's name as keys, each entry
#provides information on that player (cards held, number of coins) 
players = []

print "Welcome to COUP!\n"
numPlayers = input("Number of players (2-6): ")

if numPlayers >= 2 and numPlayers <= 6:
	#coins dispersed
	treasury = treasury - 2 * numPlayers

	#deck shuffled
	cards = shuffle(cards)

	#cards dealt
	for i in range(numPlayers):
		name = raw_input("Player name: ")
		players.append((name,cards[numCards - 1], cards[numCards - 2], 2))
		numCards = numCards - 2
	players = {a:[b,c,d] for a,b,c,d in players}
	print players

	#waits for moderator's input, acts accordingly
        response = 's'
	while response != 'q':
		response = raw_input("(s)tatus\ncoun(t)s\n(e)xchange\ns(h)uffle\n(c)oins\n(d)estroy\nta(x)\nstea(l)\n(i)ncome\n(f)oreign aid\n(q)uit:")
		#Prints out raw statistics of the current game
		if response == 's':
			for player in players:
				print player, players[player]
			for i in range(numCards):
				print cards[i]
			print "Cards in deck:", numCards
			print "Treasury: ", treasury

		#Allows for Ambassador ability
		elif response == 'e':
			name = raw_input("Player name: ")
			print players[name]
			print "2 cards dealt to", name
			print cards[numCards - 1], cards[numCards - 2]
			if not (players[name][1] == "GONE" or players[name][2] == "GONE"):
				exchange = input("Exchange 0 (neither)\n" +
                                                 "Exchange 1 (first with first)\n" +
                                                 "Exchange 2 (first with second)\n" +
                                                 "Exchange 3 (second with first)\n" +
                                                 "Exchange 4 (second with second)\n" +
                                                 "Exchange 5 (both):")
				if exchange == 5:
					temp = [players[name][1], players[name][2]]
                                        players[name][0] = cards[numCards - 1]
                                        players[name][1] = cards[numCards - 2]
                                        cards[numCards - 1] = temp[0]
                                        cards[numCards - 2] = temp[1]
				elif exchange == 4:
					temp = players[name][1]
					players[name][1] = cards[numCards - 2]
					cards[numCards - 2] = temp
				elif exchange == 3:
					temp = players[name][1]
                                        players[name][1] = cards[numCards - 1]
                                        cards[numCards - 1] = temp
				elif exchange == 2:
					temp = players[name][0]
                                        players[name][0] = cards[numCards - 2]
                                        cards[numCards - 2] = temp
				elif exchange == 1:
					temp = players[name][0]
                                        players[name][0] = cards[numCards - 1]
                                        cards[numCards - 1] = temp
			else:
				exchange = input("Exchange 0 (neither)\n" +
                                                 "Exchange 1 (with first)\n" +
                                                 "Exchange 2 (with second):")
			        card = 0
				temp = players[name][card]
				if temp == "GONE":
					card = card + 1
					temp = players[name][card]

				if exchange == 2:
					players[name][card] = cards[numCards - 2]
					cards[numCards - 2] = temp
				elif exchange == 1:	
					players[name][card] = cards[numCards - 1]
					cards[numCards - 1] = temp
		
			cards = shuffle(cards)

		#Coin counts (without held cards)
		elif response == 't':
			for player in players:
				print player, ":", players[player][2]
			print "Treasury:", treasury
		
		#Shuffle option
		elif response == 'h':
			cards = shuffle(cards)
		
		#Adjust coin amount of one player
		elif response == 'c':
			name = raw_input("Player name:")
			print name, "current coins:", players[name][2]
			newVal = input("New coin count:")
			players[name][2] = newVal
		
		#Duke ability - Tax
		elif response == 'x':
			name = raw_input("Player name:")
			players[name][2] = players[name][2] + 3
			treasury = treasury - 3

		#Income
		elif response == 'i':
			name = raw_input("Player name:")
                        players[name][2] = players[name][2] + 1
			treasury = treasury - 1

		#Foreign Aid
		elif response == 'f':
			name = raw_input("Player name:")
                        players[name][2] = players[name][2] + 2
			treasury = treasury - 2

		#Captain Ability - Steal
		elif response == 'l':
			name1 = raw_input("Captain claimer:")
			name2 = raw_input("Target:")
			players[name1][2] = players[name1][2] + 2
			players[name2][2] = players[name2][2] - 2

		#Destruction of a card (Coup or Assassination or failed bluff/challenge)
		elif response == 'd':
			name = raw_input("Player name:")
			print players[name][0], players[name][1]
			remove = input("Which to remove(1 or 2):")
			destroyedCards.append(players[name][remove - 1]) 
                        players[name][remove - 1] = "GONE"
			print players[name]

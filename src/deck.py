import random

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

    def swapCard(self, player, card):
        self.addCard(player.cards[card])
        self.shuffle()
        player.cards[card] = self.deal()


from pywikibot import family

class Family(family.Family):
    name = 'wot'
    langs = {
        'en': 'wot.fandom.com'
    }

    def scriptpath(self, code):
        return '/'

    def apipath(self, code):
        return '/api.php'

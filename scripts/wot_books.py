import json
from log_utils import logger as log

class Bookset():

    def __init__(self):
        self.books = None
        self.books_by_str = {}

    def setup(self, path, force_reload):
        if self.books == None or force_reload:
            with open(path, "r") as f:
                data = json.load(f)
            for book in data:
                for k in [ book["title"], book.get("abbrev", None), book.get("template", None), book.get("key", None) ] + book.get("templates", []) + book.get("other_aliases", []):
                    if k == None:
                        continue
                    for k_str in [ k, k.lower(), k.upper() ]:
                        if k_str in self.books_by_str:
                            log.warning(f"Duplicate book key {k_str} for book {book['title']} (already mapped to {self.books_by_str[k_str]['title']})")
                        else:
                            self.books_by_str[k_str] = book
            self.books = data
        return self.books

books = Bookset()

def setup(path = "../wotwiki-snapshot/Module:Books/Data/data.json", force_reload = False):
    global books
    if books.books == None or force_reload:
        books.setup(path, force_reload)
    return books
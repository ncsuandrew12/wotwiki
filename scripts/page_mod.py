import inspect
import json
import re
# import log_utils

# log = log_utils.get_logger(f"{os.path.basename(__file__)}")

class PageMod():
    def __init__(self, id, page=None, title=None, summary=None):
        self.id = id
        self.page = page
        self.title = title
        self.summary = summary or []
    
    def to_dict(self):
        """Convert PageMod object to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title': self.get_title() or None,
            'summary': self.summary
        }

    def get_title(self):
        return self.page and self.page.title() or self.title

    @classmethod
    def from_dict(cls, data):
        """Create PageMod object from dictionary (for JSON deserialization)."""
        return cls(data['id'], None, data['title'], data['summary'])
    
    def to_json(self):
        """Convert PageMod object to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str):
        """Create PageMod object from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

class PageModifier():

    def __init__(self, summary):
        self.summary = summary

    def process_page(self, page):
        pre_text = page.text
        self.process_page_logic(page)
        return pre_text != page.text

    def process_page_logic(self, page):
        raise Exception("Unimplemented function! Implement {}.{} ({}).".format(
            self.__class__.__name__,
            self.process_page.__name__,
            inspect.getfile(self.__class__)))


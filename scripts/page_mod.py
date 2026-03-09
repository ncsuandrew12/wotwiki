import json
# import log_utils

# log = log_utils.get_logger(f"{os.path.basename(__file__)}")

class PageMod():
    def __init__(self, id, title):
        self.id = id
        self.title = title
    
    def to_dict(self):
        """Convert PageMod object to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title': self.title
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create PageMod object from dictionary (for JSON deserialization)."""
        return cls(data['id'], data['title'])
    
    def to_json(self):
        """Convert PageMod object to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str):
        """Create PageMod object from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

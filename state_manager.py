import json
import os

class StateManager:
    def __init__(self, filename='persistence.json'):
        self.filename = filename
        self.state = self._load()

    def _load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save(self):
        with open(self.filename, 'w') as f:
            json.dump(self.state, f, indent=4)

    def get_last_id(self, chat_id):
        return self.state.get(str(chat_id), 0)

    def update_last_id(self, chat_id, last_id):
        # Only overwrite if the new ID is higher (ensure no regression)
        current_id = self.get_last_id(chat_id)
        if last_id > current_id:
            self.state[str(chat_id)] = last_id
            self.save()

    def get_staged_cards(self):
        return self.state.get('staged_cards', [])

    def stage_cards(self, cards):
        current_staged = set(self.get_staged_cards())
        current_staged.update(cards)
        self.state['staged_cards'] = list(current_staged)
        self.save()

    def clear_staged_cards(self):
        self.state['staged_cards'] = []
        self.save()

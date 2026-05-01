import json
import os
from supabase import create_client, Client

class StateManager:
    def __init__(self, filename='persistence.json'):
        self.filename = filename
        self.state = self._load()
        
        # Supabase Init for Cloud Persistence
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SECRET_KEY')
        self.supabase: Client = None
        if self.supabase_url and self.supabase_key:
            try:
                self.supabase = create_client(self.supabase_url, self.supabase_key)
            except: pass

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
        if self.supabase:
            try:
                res = self.supabase.table("system_settings").select("value").eq("key", f"last_id_{chat_id}").single().execute()
                if res.data: return int(res.data['value'])
            except: pass
        return self.state.get(str(chat_id), 0)

    def update_last_id(self, chat_id, last_id):
        current_id = self.get_last_id(chat_id)
        if last_id > current_id:
            if self.supabase:
                try:
                    self.supabase.table("system_settings").upsert({"key": f"last_id_{chat_id}", "value": str(last_id)}).execute()
                except: pass
            self.state[str(chat_id)] = last_id
            self.save()

    def get_staged_cards(self):
        if self.supabase:
            try:
                res = self.supabase.table("system_settings").select("value").eq("key", "staged_vectors").single().execute()
                if res.data: return json.loads(res.data['value'])
            except: pass
        return self.state.get('staged_cards', [])

    def stage_cards(self, cards):
        """
        Stores cards while ensuring only ONE card per BIN (first 6 digits) exists 
        in the staged collection.
        """
        current_staged = self.get_staged_cards()
        
        # Use a dictionary to track cards by BIN
        # bin_map: BIN (6 digits) -> Full Card String
        bin_map = {}
        
        # First, populate with existing cards to maintain them
        for card in current_staged:
            if '|' in card:
                bin_prefix = card.split('|')[0][:6]
                if bin_prefix not in bin_map:
                    bin_map[bin_prefix] = card
        
        # Then, add new cards only if their BIN is not already present
        for card in cards:
            if '|' in card:
                bin_prefix = card.split('|')[0][:6]
                if bin_prefix not in bin_map:
                    bin_map[bin_prefix] = card
        
        new_list = list(bin_map.values())
        
        if self.supabase:
            try:
                self.supabase.table("system_settings").upsert({"key": "staged_vectors", "value": json.dumps(new_list)}).execute()
            except: pass
        self.state['staged_cards'] = new_list
        self.save()

    def clear_staged_cards(self):
        if self.supabase:
            try:
                self.supabase.table("system_settings").upsert({"key": "staged_vectors", "value": "[]"}).execute()
            except: pass
        self.state['staged_cards'] = []
        self.save()

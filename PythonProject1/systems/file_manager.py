# systems/file_manager.py
import os
import json
import pickle
import time
import shutil
from datetime import datetime
from typing import Optional
from models.game_state import GameState


class RobustFileManager:
    def __init__(self):
        self._ensure_directory_structure()

    def _ensure_directory_structure(self):
        directories = ['data', 'saves', 'api_cache', 'backups']
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    def save_game_with_validation(self, game_state: GameState, slot: int = 1) -> bool:
        try:
            save_file = f"saves/slot{slot}.sav"
            save_data = {
                'version': '3.1_map_fixed',
                'timestamp': time.time(),
                'game_state': game_state,
                'metadata': {
                    'saved_at': datetime.now().isoformat(),
                    'game_time': game_state.game_time,
                    'player_position': (game_state.player_pos.x, game_state.player_pos.y),
                    'completion_percentage': (game_state.money / game_state.goal) * 100,
                    'city_info': f"{game_state.city_name} ({game_state.city_width}x{game_state.city_height})"
                }
            }

            with open(save_file, 'wb') as f:
                pickle.dump(save_data, f, protocol=pickle.HIGHEST_PROTOCOL)

            print(f"💾 Juego guardado en slot {slot}")
            return True
        except Exception as e:
            print(f"❌ Error saving: {e}")
            return False

    def load_game_with_validation(self, slot: int = 1) -> Optional[GameState]:
        save_file = f"saves/slot{slot}.sav"
        if not os.path.exists(save_file):
            return None

        try:
            with open(save_file, 'rb') as f:
                save_data = pickle.load(f)

            if not isinstance(save_data, dict):
                return None

            game_state = save_data['game_state']
            if not hasattr(game_state, 'city_width'):
                return None

            print(f"📂 Juego cargado desde slot {slot}")
            return game_state
        except Exception as e:
            print(f"❌ Error loading: {e}")
            return None

    def load_scores(self) -> list:
        scores_file = "data/puntajes.json"
        try:
            os.makedirs("data", exist_ok=True)
            if not os.path.exists(scores_file):
                with open(scores_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, indent=2, ensure_ascii=False)
                return []

            with open(scores_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return []
                scores = json.loads(content)

            if not isinstance(scores, list):
                return []

            scores.sort(key=lambda x: x.get('score', 0), reverse=True)
            return scores[:10]
        except Exception:
            return []

    def get_save_info(self, slot: int) -> Optional[dict]:
        save_file = f"saves/slot{slot}.sav"
        if not os.path.exists(save_file):
            return None

        try:
            with open(save_file, 'rb') as f:
                save_data = pickle.load(f)
            if 'metadata' in save_data:
                return save_data['metadata']
        except:
            return None
        return None
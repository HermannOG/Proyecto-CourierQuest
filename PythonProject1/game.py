# game.py
"""
Courier Quest - Proyecto EIF-207 Estructuras de Datos
Clase principal del juego con toda la lógica integrada.
"""

import pygame
import json
import os
import time
import random
import math
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import deque

# Imports de módulos propios
from config.constants import *
from models.order import Order, Position
from models.game_state import GameState
from systems.api_manager import TigerAPIManager
from systems.weather import EnhancedWeatherSystem
from systems.file_manager import RobustFileManager
from systems.sorting import SortingAlgorithms
from utils.data_structures import OptimizedPriorityQueue, MemoryEfficientHistory
from ui.menu import GameMenu
from ui.tutorial import TutorialSystem

pygame.init()


class CourierQuest:
    """Clase principal del juego Courier Quest - VERSIÓN CON IMÁGENES COMPLETA."""

    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Courier Quest - Versión con Imágenes")
        self.clock = pygame.time.Clock()

        # Fuentes optimizadas
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 20)
        self.large_font = pygame.font.Font(None, 32)
        self.title_font = pygame.font.Font(None, 38)
        self.header_font = pygame.font.Font(None, 28)

        # Sistema de imágenes para tiles, clima Y JUGADOR
        self.tile_images = {}
        self.weather_images = {}
        self.player_image = None

        # Sistemas del juego
        self.api_manager = TigerAPIManager()
        self.weather_system = EnhancedWeatherSystem()
        self.history = MemoryEfficientHistory()
        self.file_manager = RobustFileManager()
        self.sorting_algorithms = SortingAlgorithms()
        self.menu_system = GameMenu()
        self.tutorial_system = TutorialSystem()

        # Estados del juego
        self.game_state = "menu"
        self.running = True
        self.paused = False
        self.game_over = False
        self.victory = False

        # Datos del mundo
        self.map_data = {}
        self.city_width = 30
        self.city_height = 25
        self.tiles = []
        self.legend = {}
        self.goal = 3000
        self.city_name = "TigerCity"
        self.max_game_time = 600.0

        # POSICIÓN DEL MAPA CORREGIDA
        self.map_offset_x = 20
        self.map_offset_y = 35
        self.map_pixel_width = self.city_width * TILE_SIZE
        self.map_pixel_height = self.city_height * TILE_SIZE

        # Estado del jugador
        self.player_pos = Position(2, 2)
        self.stamina = 100.0
        self.max_stamina = 100.0
        self.reputation = 70
        self.money = 0
        self.max_weight = 10
        self.base_speed = 3.0

        # Tiempo del juego
        self.game_time = 0.0

        # Gestión de pedidos
        self.pending_orders = deque()
        self.available_orders = OptimizedPriorityQueue()
        self.inventory = deque()
        self.completed_orders = []

        # Estadísticas
        self.delivery_streak = 0
        self.last_delivery_was_clean = True

        # Interfaz de usuario
        self.show_inventory = False
        self.show_orders = False
        self.selected_order_index = 0
        self.selected_inventory_index = 0

        # Control de movimiento
        self.move_cooldown = 0.08
        self.last_move_time = 0
        self.time_since_last_move = 0

        # Mensajes del juego
        self.game_messages = []
        self.message_timer = 0

        # Métricas de rendimiento
        self.fps_counter = 0
        self.fps_timer = 0
        self.current_fps = 60

        # Cargar imágenes de tiles, clima Y JUGADOR
        self._load_tile_images()
        self._load_weather_images()
        self._load_player_image()

        self._ensure_data_files()
        print("✅ Courier Quest inicializado - VERSIÓN CON IMÁGENES COMPLETAS + JUGADOR")

    def _load_player_image(self):
        """Carga la imagen del jugador/repartidor."""
        try:
            player_image = pygame.image.load("assets/Repartidor.png")
            player_size = TILE_SIZE - 4
            self.player_image = pygame.transform.scale(player_image, (player_size, player_size))
            print("✅ Imagen del repartidor cargada correctamente desde Repartidor.png")

        except FileNotFoundError as e:
            print(f"⚠️ No se pudo cargar imagen del repartidor: {e}")
            print("⚠️ Asegúrate de que exista 'Repartidor.png' en la carpeta del juego")
            self._create_fallback_player_image()
        except Exception as e:
            print(f"⚠️ Error cargando imagen del repartidor: {e}")
            self._create_fallback_player_image()

    def _create_fallback_player_image(self):
        """Crea una imagen de respaldo para el jugador."""
        player_size = TILE_SIZE - 4
        fallback_surface = pygame.Surface((player_size, player_size), pygame.SRCALPHA)

        center_x = player_size // 2
        center_y = player_size // 2

        pygame.draw.circle(fallback_surface, BLUE, (center_x, center_y), player_size // 3)
        head_color = (255, 220, 177)
        pygame.draw.circle(fallback_surface, head_color, (center_x, center_y - player_size // 4), player_size // 6)
        helmet_color = (255, 255, 0)
        helmet_rect = pygame.Rect(center_x - player_size // 8, center_y - player_size // 3, player_size // 4,
                                  player_size // 6)
        pygame.draw.ellipse(fallback_surface, helmet_color, helmet_rect)
        pygame.draw.circle(fallback_surface, BLACK, (center_x, center_y), player_size // 3, 2)

        self.player_image = fallback_surface

    def _load_weather_images(self):
        """Carga las imágenes para los diferentes estados del clima."""
        weather_files = {
            'clear': 'assets/Despejado.png',
            'clouds': 'assets/Nublado.png',
            'rain_light': 'assets/Llovizna.png',
            'rain': 'assets/Lluvioso.png',
            'storm': 'assets/Tormenta.png',
            'fog': 'assets/Nublado.png',
            'wind': 'assets/Ventoso.png',
            'heat': 'assets/Despejado.png',
            'cold': 'assets/Ventoso.png'
        }

        weather_loaded = 0
        weather_size = 60

        for weather_state, filename in weather_files.items():
            try:
                weather_image = pygame.image.load(filename)
                self.weather_images[weather_state] = pygame.transform.scale(weather_image, (weather_size, weather_size))
                weather_loaded += 1
            except Exception:
                pass

        self._create_weather_fallbacks()

    def _create_weather_fallbacks(self):
        """Crea íconos de respaldo para climas sin imagen."""
        weather_size = 75
        weather_colors = {
            'clear': (200, 150, 100),
            'clouds': (180, 180, 180),
            'rain_light': (100, 150, 200),
            'rain': (70, 120, 180),
            'storm': (50, 50, 100),
            'fog': (200, 200, 200),
            'wind': (150, 200, 150),
            'heat': (255, 100, 100),
            'cold': (150, 200, 255)
        }

        for weather_state, color in weather_colors.items():
            if weather_state not in self.weather_images:
                fallback_surface = pygame.Surface((weather_size, weather_size), pygame.SRCALPHA)
                pygame.draw.circle(fallback_surface, color, (weather_size // 2, weather_size // 2),
                                   weather_size // 2 - 2)
                pygame.draw.circle(fallback_surface, (100, 100, 100), (weather_size // 2, weather_size // 2),
                                   weather_size // 2 - 2, 2)
                self.weather_images[weather_state] = fallback_surface

    def _load_tile_images(self):
        """Carga las imágenes para todos los tipos de tiles."""
        images_loaded = 0

        try:
            park_image = pygame.image.load("assets/pixilart-drawing.png")
            self.tile_images["P"] = pygame.transform.scale(park_image, (TILE_SIZE, TILE_SIZE))
            print("✅ Imagen de parque cargada desde pixilart-drawing.png")
            images_loaded += 1
        except Exception:
            pass

        try:
            street_image = pygame.image.load("assets/pixil-frame-0 (1).png")
            self.tile_images["C"] = pygame.transform.scale(street_image, (TILE_SIZE, TILE_SIZE))
            print("✅ Imagen de calle cargada desde pixil-frame-0 (1).png")
            images_loaded += 1
        except Exception:
            pass

        try:
            building_image = pygame.image.load("assets/pixil-frame-0 (2).png")
            self.tile_images["B"] = pygame.transform.scale(building_image, (TILE_SIZE, TILE_SIZE))
            print("✅ Imagen de edificio cargada desde pixil-frame-0 (2).png")
            images_loaded += 1
        except Exception:
            pass

        self._create_fallback_images()

    def get_complete_image_status(self):
        """Obtiene el estado completo de todas las imágenes cargadas."""
        tile_count = len(self.tile_images)
        unique_weather_files = set()
        weather_files = {
            'clear': 'Despejado.png',
            'clouds': 'Nublado.png',
            'rain_light': 'Llovizna.png',
            'rain': 'Lluvioso.png',
            'storm': 'Tormenta.png',
            'wind': 'Ventoso.png',
        }

        for state in self.weather_images:
            if state in weather_files:
                unique_weather_files.add(weather_files[state])

        weather_count = len(unique_weather_files)
        has_player_image = self.player_image is not None

        if tile_count == 3 and weather_count >= 5 and has_player_image:
            return "✅ Imágenes completas: 3 tiles + clima + jugador"
        elif tile_count == 3 and has_player_image:
            return f"✅ 3 tiles PNG + {weather_count} clima + jugador"
        elif weather_count >= 5 and has_player_image:
            return f"✅ {tile_count} tiles + clima completo + jugador"
        elif has_player_image:
            return f"✅ {tile_count} tiles + {weather_count} clima + jugador + respaldo"
        else:
            return f"✅ {tile_count} tiles + {weather_count} clima + jugador respaldo"

    def _create_fallback_images(self):
        """Crea imágenes de respaldo para los tiles que no tienen imagen PNG."""

        if "P" not in self.tile_images:
            park_surface = pygame.Surface((TILE_SIZE, TILE_SIZE))
            park_surface.fill(GREEN)
            tree_color = (0, 100, 0)
            for i in range(3):
                for j in range(3):
                    if (i + j) % 2 == 0:
                        tree_rect = pygame.Rect(
                            i * (TILE_SIZE // 3) + 2,
                            j * (TILE_SIZE // 3) + 2,
                            TILE_SIZE // 3 - 4,
                            TILE_SIZE // 3 - 4
                        )
                        pygame.draw.ellipse(park_surface, tree_color, tree_rect)
            self.tile_images["P"] = park_surface

        if "C" not in self.tile_images:
            street_surface = pygame.Surface((TILE_SIZE, TILE_SIZE))
            street_surface.fill(LIGHT_GRAY)
            line_color = (180, 180, 180)
            pygame.draw.line(street_surface, line_color,
                             (0, TILE_SIZE // 2), (TILE_SIZE, TILE_SIZE // 2), 2)
            pygame.draw.line(street_surface, line_color,
                             (TILE_SIZE // 2, 0), (TILE_SIZE // 2, TILE_SIZE), 2)
            self.tile_images["C"] = street_surface

        if "B" not in self.tile_images:
            building_surface = pygame.Surface((TILE_SIZE, TILE_SIZE))
            building_surface.fill(DARK_GRAY)
            window_color = (100, 100, 100)
            for i in range(2):
                for j in range(2):
                    window_rect = pygame.Rect(
                        4 + i * (TILE_SIZE // 2 - 2),
                        4 + j * (TILE_SIZE // 2 - 2),
                        TILE_SIZE // 2 - 8,
                        TILE_SIZE // 2 - 8
                    )
                    pygame.draw.rect(building_surface, window_color, window_rect)
            self.tile_images["B"] = building_surface

    def _get_tile_base_color(self, tile_type):
        """Obtiene el color base para un tipo de tile."""
        if tile_type == "C":
            return LIGHT_GRAY
        elif tile_type == "B":
            return DARK_GRAY
        elif tile_type == "P":
            return GREEN
        elif tile_type == "R":
            return PURPLE
        else:
            return WHITE

    def _ensure_data_files(self):
        os.makedirs("data", exist_ok=True)
        os.makedirs("saves", exist_ok=True)
        os.makedirs("api_cache", exist_ok=True)

        if not os.path.exists("data/puntajes.json"):
            with open("data/puntajes.json", 'w') as f:
                json.dump([], f)

    def initialize_game_data(self):
        """Inicializa los datos del juego desde la API."""
        try:
            print("🎮 Inicializando datos del juego...")

            self.map_data = self.api_manager.get_city_map()
            self.city_width = self.map_data.get('width', 30)
            self.city_height = self.map_data.get('height', 25)
            self.tiles = self.map_data.get('tiles', [])
            self.legend = self.map_data.get('legend', {})
            self.goal = self.map_data.get('goal', 3000)
            self.city_name = self.map_data.get('city_name', 'TigerCity')
            self.max_game_time = self.map_data.get('max_time', 600.0)

            self.map_pixel_width = self.city_width * TILE_SIZE
            self.map_pixel_height = self.city_height * TILE_SIZE

            self.player_pos = self._find_valid_starting_position()

            orders_data = self.api_manager.get_city_jobs()

            for order_data in orders_data:
                try:
                    if not self._validate_order_positions(order_data):
                        order_data = self._fix_order_positions(order_data)

                    self.pending_orders.append(order_data)
                except (KeyError, ValueError) as e:
                    print(f"⚠️ Error cargando pedido: {e}")
                    continue

            self.pending_orders = deque(sorted(self.pending_orders, key=lambda x: x.release_time))

            print(f"✅ {self.city_name} cargada: {self.city_width}x{self.city_height}")
            print(f"✅ {len(self.pending_orders)} pedidos validados cargados")
            print(f"✅ Meta: ${self.goal} | Tiempo: {self.max_game_time}s")

            self.add_game_message(f"¡Bienvenido a {self.city_name}! Meta: ${self.goal}", 4.0, GREEN)

        except Exception as e:
            print(f"❌ Error cargando datos del mundo: {e}")
            self._create_fallback_data()

    def _find_valid_starting_position(self) -> Position:
        """Encuentra una posición inicial válida para el jugador."""
        common_positions = [
            (2, 2), (3, 3), (1, 1), (4, 4), (5, 5),
            (2, 3), (3, 2), (1, 2), (2, 1)
        ]

        for x, y in common_positions:
            if self._is_position_walkable(x, y):
                return Position(x, y)

        for y in range(min(10, self.city_height)):
            for x in range(min(10, self.city_width)):
                if self._is_position_walkable(x, y):
                    return Position(x, y)

        return Position(1, 1)

    def _is_position_walkable(self, x: int, y: int) -> bool:
        """Verifica si una posición es caminable según las reglas del juego"""
        if not (0 <= x < self.city_width and 0 <= y < self.city_height):
            return False

        if y < len(self.tiles) and x < len(self.tiles[y]):
            tile_type = self.tiles[y][x]
            tile_info = self.legend.get(tile_type, {})
            return not tile_info.get("blocked", False)

        return True

    def _validate_order_positions(self, order: Order) -> bool:
        """Valida que las posiciones del pedido sean válidas."""
        pickup_valid = self._is_position_walkable(order.pickup.x, order.pickup.y)
        dropoff_valid = self._is_position_walkable(order.dropoff.x, order.dropoff.y)
        return pickup_valid and dropoff_valid

    def _fix_order_positions(self, order: Order) -> Order:
        """Corrige las posiciones de un pedido para que sean válidas"""
        if not self._is_position_walkable(order.pickup.x, order.pickup.y):
            order.pickup = self._find_nearest_walkable_position(order.pickup.x, order.pickup.y)

        if not self._is_position_walkable(order.dropoff.x, order.dropoff.y):
            order.dropoff = self._find_nearest_walkable_position(order.dropoff.x, order.dropoff.y)

        return order

    def _find_nearest_walkable_position(self, x: int, y: int) -> Position:
        """Encuentra la posición caminable más cercana"""
        for radius in range(1, min(self.city_width, self.city_height) // 2):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) == radius or abs(dy) == radius:
                        nx, ny = x + dx, y + dy
                        if self._is_position_walkable(nx, ny):
                            return Position(nx, ny)

        return Position(1, 1)

    def _create_fallback_data(self):
        """Crea datos por defecto si falla la carga de la API."""
        self.city_width = 20
        self.city_height = 15
        self.tiles = [["C"] * 20 for _ in range(15)]
        self.legend = {"C": {"name": "calle", "surface_weight": 1.00}}
        self.goal = 2000
        self.city_name = "Ciudad de Respaldo"
        self.max_game_time = 600.0

    def add_game_message(self, message: str, duration: float = 3.0, color: tuple = WHITE):
        """Añade un mensaje temporal al juego."""
        self.game_messages.append((message, duration, color))

    def get_order_time_remaining(self, order: Order) -> float:
        """Calcula el tiempo restante de un pedido."""
        if order.status == "waiting_release":
            return order.duration_minutes * 60

        elapsed_since_created = self.game_time - order.created_at
        total_duration_seconds = order.duration_minutes * 60
        return max(0, total_duration_seconds - elapsed_since_created)

    def get_order_urgency_color(self, order: Order) -> tuple:
        """Determina el color basado en urgencia del pedido."""
        time_remaining = self.get_order_time_remaining(order)
        total_duration = order.duration_minutes * 60

        if time_remaining <= 0:
            return DARK_RED

        progress = time_remaining / total_duration

        if progress > 0.66:
            return DARK_GREEN
        elif progress > 0.33:
            return YELLOW
        else:
            return RED

    def get_order_status_text(self, order: Order) -> str:
        time_remaining = self.get_order_time_remaining(order)

        if time_remaining <= 0:
            return "EXPIRADO"

        minutes = int(time_remaining // 60)
        seconds = int(time_remaining % 60)

        if minutes > 0:
            return f"{minutes}:{seconds:02d}"
        else:
            return f"0:{seconds:02d}"

    def _get_district_name(self, x: int, y: int) -> str:
        """Sistema de distritos para mejor organización"""
        if y < self.city_height // 3:
            return "Norte"
        elif y < 2 * self.city_height // 3:
            return "Centro"
        else:
            return "Sur"

    def handle_events(self, events):
        """Maneja eventos de pygame."""
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if self.game_state == "playing":
                    self._handle_game_events(event)
                elif self.game_state == "menu":
                    self._handle_menu_events(event)
                elif self.game_state == "tutorial":
                    self._handle_tutorial_events(event)
                elif self.game_state == "game_over":
                    self._handle_game_over_events(event)

    def _handle_game_over_events(self, event):
        """Maneja eventos durante el game over."""
        if event.key == pygame.K_ESCAPE:
            print("\nVolviendo al menú principal...")

            self.game_state = "menu"
            self.game_over = False
            self.victory = False

            if hasattr(self, '_score_saved'):
                delattr(self, '_score_saved')
            if hasattr(self, '_final_score_display'):
                delattr(self, '_final_score_display')

            self.game_messages = []
            self.message_timer = 0

            self.pending_orders = deque()
            self.available_orders = OptimizedPriorityQueue()
            self.inventory = deque()
            self.completed_orders = []
            self.money = 0
            self.reputation = 70
            self.stamina = 100.0
            self.game_time = 0.0

    def _handle_game_events(self, event):
        """Maneja eventos durante el juego."""
        if event.key == pygame.K_SPACE:
            self.paused = not self.paused
        elif event.key == pygame.K_i:
            self.show_inventory = not self.show_inventory
            if self.show_inventory:
                self.selected_inventory_index = 0
        elif event.key == pygame.K_o:
            self.show_orders = not self.show_orders
            if self.show_orders:
                self.selected_order_index = 0
        elif event.key == pygame.K_ESCAPE:
            if self.game_over:
                self.game_state = "menu"
                self.game_over = False
                self.victory = False
            else:
                self.paused = not self.paused
        elif event.key == pygame.K_e:
            self.interact_at_position()
        elif event.key == pygame.K_F5:
            self.save_game(slot=1)
        elif event.key == pygame.K_F9:
            if self.load_game(slot=1):
                self.game_state = "playing"
        elif event.key == pygame.K_z and pygame.key.get_pressed()[pygame.K_LCTRL]:
            self.undo_move()
        elif event.key == pygame.K_p:
            self._sort_inventory_by_priority()
        elif event.key == pygame.K_t:
            self._sort_inventory_by_deadline()
        elif event.key == pygame.K_d:
            self._sort_orders_by_distance()

        # Navegación en menús
        elif self.show_inventory:
            if event.key == pygame.K_UP:
                self.selected_inventory_index = max(0, self.selected_inventory_index - 1)
            elif event.key == pygame.K_DOWN:
                max_index = len(self.inventory) - 1
                self.selected_inventory_index = min(max_index, self.selected_inventory_index + 1)
            elif event.key == pygame.K_RETURN:
                self.deliver_selected_order()

        elif self.show_orders:
            if event.key == pygame.K_UP:
                self.selected_order_index = max(0, self.selected_order_index - 1)
            elif event.key == pygame.K_DOWN:
                max_index = min(len(self.available_orders.items) - 1, 6)
                self.selected_order_index = min(max_index, self.selected_order_index + 1)
            elif event.key == pygame.K_RETURN:
                self.accept_selected_order()

    def _handle_menu_events(self, event):
        """Maneja eventos del menú principal."""
        action = self.menu_system.handle_menu_input(event)
        if action == "start_new_game":
            self.initialize_game_data()
            self.game_state = "playing"
        elif action == "start_tutorial":
            self.tutorial_system = TutorialSystem()
            self.game_state = "tutorial"
        elif action == "exit":
            self.running = False
        elif action and action.startswith("load_slot_"):
            slot = int(action.split("_")[-1])
            if self._load_game(slot):
                self.game_state = "playing"

    def _handle_tutorial_events(self, event):
        """Maneja eventos durante el tutorial."""
        if not self.tutorial_system.handle_input(event):
            self.initialize_game_data()
            self.game_state = "playing"

    def _sort_inventory_by_priority(self):
        """Ordena el inventario por prioridad usando QuickSort."""
        if not self.inventory:
            self.add_game_message("Inventario vacío", 2.0, YELLOW)
            return

        inventory_list = list(self.inventory)
        sorted_list = self.sorting_algorithms.quicksort_by_priority(inventory_list)
        self.inventory = deque(sorted_list)
        self.add_game_message("Inventario ordenado por PRIORIDAD (QuickSort)", 3.0, GREEN)

    def _sort_inventory_by_deadline(self):
        """Ordena el inventario por tiempo restante usando MergeSort."""
        if not self.inventory:
            self.add_game_message("Inventario vacío", 2.0, YELLOW)
            return

        inventory_list = list(self.inventory)
        sorted_list = self.sorting_algorithms.mergesort_by_deadline(inventory_list, self.game_time)
        self.inventory = deque(sorted_list)
        self.add_game_message("Inventario ordenado por TIEMPO RESTANTE (MergeSort)", 3.0, GREEN)

    def _sort_orders_by_distance(self):
        """Ordena pedidos disponibles por distancia usando Insertion Sort."""
        if not self.available_orders.items:
            self.add_game_message("No hay pedidos disponibles", 2.0, YELLOW)
            return

        orders_list = self.available_orders.items.copy()
        sorted_list = self.sorting_algorithms.insertion_sort_by_distance(orders_list, self.player_pos)
        self.available_orders.items = sorted_list
        self.add_game_message("Pedidos ordenados por DISTANCIA (Insertion Sort)", 3.0, GREEN)

    def handle_input(self, keys, dt):
        """Maneja entrada del teclado durante el juego."""
        if self.paused or self.game_over:
            return

        # ✅ BLOQUEO: Si está exhausto (≤0), no procesar ningún movimiento
        if self.stamina <= 0:
            current_time = time.time()
            if not hasattr(self, '_last_exhausted_message') or current_time - self._last_exhausted_message > 3.0:
                self.add_game_message("¡EXHAUSTO! Espera a recuperar resistencia hasta 30", 3.0, RED)
                self._last_exhausted_message = current_time
            return

        actual_speed = self.calculate_actual_speed()
        adjusted_cooldown = self.move_cooldown / max(0.1, actual_speed / self.base_speed)

        self.last_move_time += dt
        if self.last_move_time < adjusted_cooldown:
            return

        direction = (0, 0)

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            direction = (-1, 0)
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            direction = (1, 0)
        elif keys[pygame.K_UP] or keys[pygame.K_w]:
            direction = (0, -1)
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            direction = (0, 1)

        if direction != (0, 0):
            new_pos = Position(
                self.player_pos.x + direction[0],
                self.player_pos.y + direction[1]
            )
            if self.is_valid_move(new_pos):
                self.move_player(new_pos)
                self.last_move_time = 0
            else:
                # ✅ Mensaje cuando el movimiento no es válido
                if self.stamina <= 0:
                    self.add_game_message("No te puedes mover - ¡Estás exhausto!", 1.5, RED)

    def is_valid_move(self, pos: Position) -> bool:
        """Verifica si un movimiento es válido con regla de exhausto."""
        if not (0 <= pos.x < self.city_width and 0 <= pos.y < self.city_height):
            return False

        # REGLA: No se puede caminar en edificios bloqueados
        if pos.y < len(self.tiles) and pos.x < len(self.tiles[pos.y]):
            tile_type = self.tiles[pos.y][pos.x]
            tile_info = self.legend.get(tile_type, {})
            if tile_info.get("blocked", False):
                return False

        # Si está exhausto, no puede moverse
        if self.stamina <= 0:
            return False

        # REGLA: Necesita resistencia mínima para moverse
        stamina_cost = self.calculate_stamina_cost()
        return self.stamina >= stamina_cost

    def move_player(self, new_pos: Position):
        """Mueve el jugador con regla de exhausto."""

        if self.stamina <= 0:
            self.add_game_message("¡Exhausto! Recupera hasta 30 de resistencia para moverte", 2.0, RED)
            return

        stamina_cost = self.calculate_stamina_cost()

        if self.stamina < stamina_cost:
            self.add_game_message("¡Resistencia insuficiente para moverse!", 2.0, RED)
            return

        if self.weather_system.current_condition in ['rain', 'storm']:
            if random.random() < 0.1:
                self.add_game_message(
                    f"El {self.weather_system._get_condition_name(self.weather_system.current_condition).lower()} dificulta el movimiento",
                    2.0, CYAN)

        self.player_pos = new_pos
        self.stamina = max(0, self.stamina - stamina_cost)
        self.time_since_last_move = 0

        if self.stamina <= 0:
            self.add_game_message("¡Exhausto! No puedes moverte hasta recuperar 30 de resistencia", 3.0, RED)
        elif self.stamina <= 30:
            self.add_game_message(f"Cansado ({self.stamina:.0f}/30) - velocidad reducida", 2.0, YELLOW)

    def calculate_stamina_cost(self) -> float:
        """Calcula el costo de resistencia por movimiento."""
        base_cost = 2.0

        weather_penalty = self.weather_system.get_stamina_penalty()

        current_weight = sum(order.weight for order in self.inventory)
        weight_penalty = 0.0
        if current_weight > self.max_weight * 0.7:
            weight_penalty = 0.5
        elif current_weight > self.max_weight * 0.5:
            weight_penalty = 0.2

        total_cost = base_cost * (1 + weather_penalty + weight_penalty)
        return total_cost

    def calculate_actual_speed(self) -> float:
        """Calcula la velocidad real del jugador."""
        base_speed = self.base_speed

        weather_multiplier = self.weather_system.get_speed_multiplier()

        stamina_multiplier = 1.0
        if self.stamina < 30:
            stamina_multiplier = 0.5
        elif self.stamina < 50:
            stamina_multiplier = 0.8

        current_weight = sum(order.weight for order in self.inventory)
        weight_multiplier = 1.0
        if current_weight > self.max_weight * 0.7:
            weight_multiplier = 0.6
        elif current_weight > self.max_weight * 0.5:
            weight_multiplier = 0.8

        actual_speed = base_speed * weather_multiplier * stamina_multiplier * weight_multiplier
        return actual_speed

    def interact_at_position(self):
        """Interactúa con pedidos en la posición actual."""
        current_pos = self.player_pos

        for order in self.available_orders.items[:]:
            if (order.pickup.x == current_pos.x and order.pickup.y == current_pos.y and
                    order.status == "available"):

                current_weight = sum(o.weight for o in self.inventory)
                if current_weight + order.weight <= self.max_weight:
                    order.status = "picked_up"
                    self.inventory.append(order)
                    self.available_orders.remove(order)

                    district = self._get_district_name(order.dropoff.x, order.dropoff.y)
                    self.add_game_message(
                        f"📦 Recogido {order.id} → Entregar en {district} (P{order.priority})",
                        3.0, GREEN
                    )
                    return
                else:
                    self.add_game_message("❌ Inventario lleno, no puedes llevar más pedidos", 3.0, RED)
                    return

        for order in list(self.inventory):
            if (order.dropoff.x == current_pos.x and order.dropoff.y == current_pos.y and
                    order.status == "picked_up"):

                time_remaining = self.get_order_time_remaining(order)
                bonus_multiplier = 1.0

                if time_remaining > order.duration_minutes * 60 * 0.66:
                    bonus_multiplier = 1.1
                    bonus_text = " (+10% bonus rápido)"
                elif time_remaining <= 0:
                    bonus_multiplier = 0.5
                    bonus_text = " (-50% penalización tardío)"
                    self.reputation -= 3
                    self.delivery_streak = 0
                    self.last_delivery_was_clean = False
                else:
                    bonus_text = ""
                    self.delivery_streak += 1
                    self.last_delivery_was_clean = True

                if self.delivery_streak >= 3:
                    streak_bonus = 0.05 * min(self.delivery_streak // 3, 4)
                    bonus_multiplier += streak_bonus
                    bonus_text += f" (+{streak_bonus * 100:.0f}% racha x{self.delivery_streak})"

                payout = int(order.payout * bonus_multiplier)
                self.money += payout

                if time_remaining > 0 and bonus_multiplier >= 1.0:
                    self.reputation = min(100, self.reputation + 2)

                self.inventory.remove(order)
                self.completed_orders.append(order)

                district = self._get_district_name(order.dropoff.x, order.dropoff.y)
                self.add_game_message(
                    f"✅ Entregado {order.id} en {district} → ${payout}{bonus_text}",
                    4.0, GREEN
                )

                if self.money >= self.goal and not self.victory:
                    self.victory = True
                    self.game_over = True
                    self.add_game_message("🎉 ¡VICTORIA! Meta alcanzada", 5.0, (255, 215, 0))

                return

        self.add_game_message("No hay pedidos para interactuar aquí", 2.0, YELLOW)

    def accept_selected_order(self):
        """Acepta el pedido seleccionado en el overlay de pedidos."""
        if not self.available_orders.items or self.selected_order_index >= len(self.available_orders.items):
            return

        order = self.available_orders.items[self.selected_order_index]

        current_weight = sum(o.weight for o in self.inventory)
        if current_weight + order.weight > self.max_weight:
            self.add_game_message("❌ Inventario lleno, no puedes llevar más pedidos", 3.0, RED)
            return

        order.status = "accepted"
        self.inventory.append(order)
        self.available_orders.remove(order)

        district = self._get_district_name(order.pickup.x, order.pickup.y)
        self.add_game_message(f"✅ Aceptado {order.id} - Recoger en {district}", 3.0, GREEN)

    def deliver_selected_order(self):
        """Entrega el pedido seleccionado del inventario."""
        if not self.inventory or self.selected_inventory_index >= len(self.inventory):
            return

        order = list(self.inventory)[self.selected_inventory_index]

        if (order.dropoff.x == self.player_pos.x and order.dropoff.y == self.player_pos.y):
            self.interact_at_position()
        else:
            distance = abs(order.dropoff.x - self.player_pos.x) + abs(order.dropoff.y - self.player_pos.y)
            self.add_game_message(f"❌ No estás en el destino del pedido ({distance} celdas de distancia)", 3.0, RED)

    def calculate_efficiency(self) -> float:
        """Calcula la eficiencia del jugador."""
        if not self.completed_orders:
            return 0.0

        total_orders = len(self.completed_orders) + len(self.inventory)
        if total_orders == 0:
            return 0.0

        efficiency = (len(self.completed_orders) / total_orders) * 100
        return efficiency

    def format_time(self, seconds: float) -> str:
        """Formatea el tiempo en minutos:segundos."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"

    def save_game(self, slot: int = 1):
        """Guarda el juego en un slot específico usando RobustFileManager."""
        try:
            current_state = GameState(
                player_pos=Position(self.player_pos.x, self.player_pos.y),
                stamina=self.stamina,
                reputation=self.reputation,
                money=self.money,
                game_time=self.game_time,
                weather_time=self.weather_system.time_in_current,
                current_weather=self.weather_system.current_condition,
                weather_intensity=self.weather_system.current_intensity,
                inventory=list(self.inventory),
                available_orders=self.available_orders.items,
                completed_orders=self.completed_orders,
                goal=self.goal,
                delivery_streak=self.delivery_streak,
                pending_orders=list(self.pending_orders),
                city_width=self.city_width,
                city_height=self.city_height,
                tiles=self.tiles,
                legend=self.legend,
                city_name=self.city_name,
                max_game_time=self.max_game_time
            )

            success = self.file_manager.save_game_with_validation(current_state, slot)

            if success:
                self.add_game_message(f"Juego guardado en slot {slot}", 3.0, GREEN)
            else:
                self.add_game_message(f"Error guardando en slot {slot}", 3.0, RED)

            return success

        except Exception as e:
            print(f"Error en save_game: {e}")
            import traceback
            traceback.print_exc()
            self.add_game_message("Error guardando el juego", 3.0, RED)
            return False

    def load_game(self):
        """Carga un juego guardado."""
        try:
            save_files = self.file_manager.get_save_files()
            if not save_files:
                self.add_game_message("No hay partidas guardadas", 3.0, RED)
                return False

            latest_save = save_files[0]
            save_data = self.file_manager.load_game_data(latest_save)

            if not save_data:
                self.add_game_message("Error cargando partida", 3.0, RED)
                return False

            self.player_pos = Position(save_data['player_pos']['x'], save_data['player_pos']['y'])
            self.stamina = save_data['stamina']
            self.reputation = save_data['reputation']
            self.money = save_data['money']
            self.game_time = save_data['game_time']

            self.inventory = deque([Order.from_dict(order_data) for order_data in save_data['inventory']])
            self.available_orders.items = [Order.from_dict(order_data) for order_data in save_data['available_orders']]
            self.completed_orders = [Order.from_dict(order_data) for order_data in save_data['completed_orders']]
            self.pending_orders = deque([Order.from_dict(order_data) for order_data in save_data['pending_orders']])

            weather_state = save_data['weather_state']
            self.weather_system.current_condition = weather_state['current_condition']
            self.weather_system.current_intensity = weather_state['current_intensity']
            self.weather_system.time_in_current = weather_state['time_in_current']

            city_data = save_data['city_data']
            self.city_width = city_data['width']
            self.city_height = city_data['height']
            self.tiles = city_data['tiles']
            self.legend = city_data['legend']
            self.city_name = city_data['city_name']
            self.goal = city_data['goal']
            self.max_game_time = city_data['max_game_time']

            self.map_pixel_width = self.city_width * TILE_SIZE
            self.map_pixel_height = self.city_height * TILE_SIZE

            self.add_game_message(f"✅ Partida cargada: {latest_save}", 3.0, GREEN)
            return True

        except Exception as e:
            print(f"Error cargando juego: {e}")
            self.add_game_message("❌ Error cargando partida", 3.0, RED)
            return False

    def load_game(self, slot: int = 1) -> bool:
        """Carga un juego desde un slot específico."""
        try:
            # ✅ Usar el file_manager
            game_state = self.file_manager.load_game_with_validation(slot)

            if not game_state:
                self.add_game_message(f"❌ No hay partida en slot {slot}", 3.0, RED)
                return False

            # Restaurar estado
            self.player_pos = game_state.player_pos
            self.stamina = game_state.stamina
            self.reputation = game_state.reputation
            self.money = game_state.money
            self.game_time = game_state.game_time

            self.inventory = deque(game_state.inventory)
            self.available_orders.items = game_state.available_orders
            self.completed_orders = game_state.completed_orders
            self.pending_orders = deque(game_state.pending_orders)

            # Restaurar clima
            self.weather_system.current_condition = game_state.current_weather
            self.weather_system.current_intensity = game_state.weather_intensity
            self.weather_system.time_in_current = game_state.weather_time

            # Restaurar mapa
            self.city_width = game_state.city_width
            self.city_height = game_state.city_height
            self.tiles = game_state.tiles
            self.legend = game_state.legend
            self.city_name = game_state.city_name
            self.goal = game_state.goal
            self.max_game_time = game_state.max_game_time

            self.map_pixel_width = self.city_width * TILE_SIZE
            self.map_pixel_height = self.city_height * TILE_SIZE

            self.add_game_message(f"✅ Partida cargada desde slot {slot}", 3.0, GREEN)
            return True

        except Exception as e:
            print(f"❌ Error cargando juego: {e}")
            import traceback
            traceback.print_exc()
            self.add_game_message("❌ Error cargando partida", 3.0, RED)
            return False

    def undo_move(self):
        """Deshace el último movimiento usando el historial."""
        if self.history.size() > 1:
            previous_state = self.history.pop()
            current_state = self.history.peek()

            self.player_pos = current_state.player_pos
            self.stamina = current_state.stamina
            self.reputation = current_state.reputation
            self.money = current_state.money
            self.game_time = current_state.game_time

            self.add_game_message("↩️ Movimiento deshecho", 2.0, YELLOW)
        else:
            self.add_game_message("❌ No hay movimientos para deshacer", 2.0, RED)

    def _process_order_releases(self, dt: float):
        """Liberación de pedidos con límite reducido para mayor enfoque."""
        MAX_ACTIVE_ORDERS = 10
        current_active_orders = len(self.available_orders.items)

        released_count = 0
        orders_to_release = 0
        if current_active_orders < MAX_ACTIVE_ORDERS // 3:
            orders_to_release = 3
        elif current_active_orders < MAX_ACTIVE_ORDERS // 2:
            orders_to_release = 2
        elif current_active_orders < MAX_ACTIVE_ORDERS:
            orders_to_release = 1

        while (self.pending_orders and
               released_count < orders_to_release and
               self.pending_orders[0].release_time <= self.game_time and
               current_active_orders < MAX_ACTIVE_ORDERS):

            order = self.pending_orders.popleft()

            if not self._validate_order_positions(order):
                order = self._fix_order_positions(order)

            order.status = "available"
            order.created_at = self.game_time
            self.available_orders.enqueue(order)
            released_count += 1
            current_active_orders += 1

            if released_count <= 3:
                priority_text = f"P{order.priority}" if order.priority > 0 else "Normal"
                duration_text = f"{order.duration_minutes * 60:.0f}s"
                district = getattr(order, 'district', self._get_district_name(order.pickup.x, order.pickup.y))

                if order.priority >= 2:
                    urgency_indicator = "RAPIDORAPIDORAPIDO!!!!!!!!"
                elif order.priority == 1:
                    urgency_indicator = "RapidoRapido"
                else:
                    urgency_indicator = "Rapido"
                self.add_game_message(
                    f"📋 {urgency_indicator}{order.id} ({priority_text}) ${order.payout} ({duration_text}) [{district}]",
                    2.0, YELLOW)

        if released_count > 2:
            self.add_game_message(f"📋 {released_count} pedidos ULTRA URGENTES (8-22s) disponibles", 2.0, BRIGHT_RED)

    def _check_expired_orders(self, dt: float):
        """Verifica y maneja pedidos expirados."""
        expired_orders = []

        for order in self.available_orders.items[:]:
            time_remaining = self.get_order_time_remaining(order)
            if time_remaining <= 0:
                expired_orders.append(order)
                self.available_orders.remove(order)

        for order in list(self.inventory):
            time_remaining = self.get_order_time_remaining(order)
            if time_remaining <= 0:
                expired_orders.append(order)
                self.inventory.remove(order)

        for order in expired_orders:
            self.reputation -= 6
            self.delivery_streak = 0
            self.last_delivery_was_clean = False
            self.add_game_message(f"❌ {order.id} expiró! (-6 reputación)", 4.0, RED)

    def _get_stamina_recovery_rate(self) -> float:
        """Calcula la tasa de recuperación de resistencia."""
        base_recovery = 5.0  # Recuperación base: +5 por segundo

        # Verificar si está en un tile válido
        if (0 <= self.player_pos.y < len(self.tiles) and
                0 <= self.player_pos.x < len(self.tiles[self.player_pos.y])):

            tile_type = self.tiles[self.player_pos.y][self.player_pos.x]
            tile_info = self.legend.get(tile_type, {})

            # ✅ CORRECCIÓN: Verificar si es un parque (tile tipo "P")
            if tile_type == "P" or tile_info.get("rest_bonus", 0) > 0:
                bonus_recovery = 15.0  # Bonificación en parques
                total_recovery = base_recovery + bonus_recovery  # Total: +20/seg

                # Mensaje visual solo cuando realmente lo necesita
                current_time = time.time()
                if not hasattr(self, '_last_park_message'):
                    self._last_park_message = 0

                # Mostrar mensaje si:
                # 1. Está exhausto (<=0) o muy cansado (<=30)
                # 2. No se ha mostrado mensaje en los últimos 5 segundos
                if (self.stamina <= 30 and
                        current_time - self._last_park_message > 5.0):

                    if self.stamina <= 0:
                        self.add_game_message(
                            " ¡En un PARQUE! Recuperando +20/seg (Base +5 + Bonus +15)",
                            3.0,
                            BRIGHT_GREEN
                        )
                    else:
                        self.add_game_message(
                            f" Parque: Recuperación rápida +20/seg ({self.stamina:.0f}/100)",
                            2.5,
                            GREEN
                        )

                    self._last_park_message = current_time

                return total_recovery

        # Si no está en un parque, recuperación normal
        return base_recovery

    def update(self, dt: float):
        """Actualiza la lógica del juego SIN guardados múltiples."""

        if hasattr(self, '_score_saved') and self._score_saved:
            return

        if self.game_state != "playing" or self.paused:
            return

        self.fps_counter += 1
        self.fps_timer += dt
        if self.fps_timer >= 1.0:
            self.current_fps = self.fps_counter
            self.fps_counter = 0
            self.fps_timer = 0

        if self.history.size() == 0 or self.game_time - getattr(self, '_last_history_save', 0) > 8.0:
            current_state = GameState(
                player_pos=Position(self.player_pos.x, self.player_pos.y),
                stamina=self.stamina,
                reputation=self.reputation,
                money=self.money,
                game_time=self.game_time,
                weather_time=self.weather_system.time_in_current,
                current_weather=self.weather_system.current_condition,
                weather_intensity=self.weather_system.current_intensity,
                inventory=list(self.inventory),
                available_orders=self.available_orders.items,
                completed_orders=self.completed_orders,
                goal=self.goal,
                delivery_streak=self.delivery_streak,
                pending_orders=list(self.pending_orders),
                city_width=self.city_width,
                city_height=self.city_height,
                tiles=self.tiles,
                legend=self.legend,
                city_name=self.city_name,
                max_game_time=self.max_game_time
            )
            self.history.push(current_state)
            self._last_history_save = self.game_time

        self.game_time += dt
        self.weather_system.update(dt)

        self._process_order_releases(dt)
        self._check_expired_orders(dt)

        self.message_timer += dt
        self.game_messages = [
            (msg, time_left - dt, color) for msg, time_left, color in self.game_messages
            if time_left - dt > 0
        ]

        self.time_since_last_move += dt

        # ✅ CORRECCIÓN: Sistema de recuperación mejorado
        previous_stamina = getattr(self, '_previous_stamina', self.stamina)

        # Solo recupera si no está al máximo Y ha pasado >1seg sin moverse
        if self.stamina < self.max_stamina and self.time_since_last_move > 1.0:
            recovery_rate = self._get_stamina_recovery_rate()
            new_stamina = min(self.max_stamina, self.stamina + recovery_rate * dt)

            # ✅ Mensajes de estado cuando cruza umbrales importantes
            if previous_stamina <= 0 and new_stamina > 0:
                if new_stamina >= 30:
                    self.add_game_message("✅ ¡Recuperado! Ya puedes moverte", 2.0, BRIGHT_GREEN)
                else:
                    remaining = 30 - new_stamina
                    self.add_game_message(
                        f"⚡ Recuperando... Faltan {remaining:.0f} pts para moverte (30 mínimo)",
                        2.0,
                        YELLOW
                    )
            elif previous_stamina < 30 and new_stamina >= 30 and previous_stamina > 0:
                self.add_game_message("✅ Resistencia suficiente para moverse", 1.5, GREEN)

            self.stamina = new_stamina
            self._previous_stamina = self.stamina

        if self.reputation < 20:
            if not self.game_over:
                print("\n GAME OVER: Reputación baja")
                self.game_over = True
                self.victory = False
                self.game_state = "game_over"
                self.add_game_message("¡Juego terminado! Reputación muy baja.", 5.0, RED)

                print("Guardando puntaje por reputación baja...")
                success = self.save_score()
                if success:
                    print("Puntaje guardado exitosamente")
                    self._score_saved = True
                else:
                    print("Error guardando puntaje")

        elif self.money >= self.goal:
            if not self.game_over:
                print("\nVICTORIA: Meta alcanzada")
                self.victory = True
                self.game_over = True

                self.add_game_message("¡Victoria! Meta de ingresos alcanzada.", 5.0, GREEN)

                print("Guardando puntaje por victoria...")
                success = self.save_score()
                if success:
                    print("Puntaje guardado exitosamente")
                    self._score_saved = True
                    self.game_state = "game_over"
                else:
                    print("Error guardando puntaje")

        elif self.game_time >= self.max_game_time:
            if not self.game_over:
                print("\n⏰ GAME OVER: Tiempo agotado")
                self.game_over = True
                self.game_state = "game_over"
                if self.money >= self.goal:
                    self.victory = True
                    self.add_game_message("¡Victoria! Tiempo agotado pero meta cumplida.", 5.0, GREEN)
                else:
                    self.victory = False
                    self.add_game_message("¡Tiempo agotado! No se cumplió la meta.", 5.0, RED)

                print("💾 Guardando puntaje por tiempo agotado...")
                success = self.save_score()
                if success:
                    print("✅ Puntaje guardado exitosamente")
                    self._score_saved = True
                else:
                    print("❌ Error guardando puntaje")

    def save_score(self, score: int = None):
        """Guarda el puntaje UNA SOLA VEZ con protección adicional."""

        if hasattr(self, '_score_saved') and self._score_saved:
            print("⚠️ Puntaje ya guardado previamente, ignorando llamada duplicada")
            return True

        try:
            final_score = self._calculate_final_score()

            scores_file = "data/puntajes.json"
            os.makedirs("data", exist_ok=True)

            if os.path.exists(scores_file):
                try:
                    with open(scores_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        scores = json.loads(content) if content else []
                        if not isinstance(scores, list):
                            scores = []
                except:
                    scores = []
            else:
                scores = []

            new_score = {
                "score": final_score,
                "money": self.money,
                "reputation": self.reputation,
                "completed_orders": len(self.completed_orders),
                "game_time": round(self.game_time, 1),
                "date": datetime.now().isoformat(),
                "victory": self.victory,
                "delivery_streak_record": getattr(self, 'delivery_streak', 0),
                "city_name": self.city_name,
                "city_size": f"{self.city_width}x{self.city_height}",
                "api_source": "TigerCity_Real"
            }

            scores.append(new_score)
            scores.sort(key=lambda x: x.get('score', 0), reverse=True)
            scores = scores[:10]

            with open(scores_file, 'w', encoding='utf-8') as f:
                json.dump(scores, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"\n❌ ERROR guardando puntaje: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _calculate_final_score(self) -> int:
        """Calcula el puntaje final según las reglas del documento."""
        try:
            pay_mult = 1.05 if self.reputation >= 90 else 1.0
            score_base = self.money * pay_mult

            bonus_tiempo = 0
            if self.victory and self.game_time < self.max_game_time * 0.8:
                time_bonus_factor = (self.max_game_time * 0.8 - self.game_time) / (self.max_game_time * 0.8)
                bonus_tiempo = int(500 * time_bonus_factor)

            delivery_bonus = len(self.completed_orders) * 10
            reputation_bonus = max(0, (self.reputation - 70) * 5)
            defeat_penalty = 0 if self.victory else -500

            final_score = int(score_base + bonus_tiempo + delivery_bonus + reputation_bonus + defeat_penalty)
            return max(0, final_score)

        except Exception as e:
            print(f"❌ Error calculando puntaje: {e}")
            return 0

    def draw(self):
        """Dibuja toda la interfaz del juego."""
        if self.game_state == "menu":
            self.menu_system.draw(self.screen)
        elif self.game_state == "tutorial":
            self.screen.fill((20, 25, 40))
            self.tutorial_system.draw(self.screen)
        elif self.game_state == "playing":
            self._draw_game()
        elif self.game_state == "game_over":
            self._draw_game()
            self.draw_game_over_overlay()

        pygame.display.flip()

    def _draw_game(self):
        """Dibuja la pantalla principal del juego."""
        self.screen.fill(UI_BACKGROUND)

        self.draw_weather_background()
        self.draw_full_map()
        self.draw_orders()
        self.draw_player()
        self.draw_ui()

        if self.show_inventory:
            self.draw_inventory_overlay()

        if self.show_orders:
            self.draw_orders_overlay()

        self.draw_game_messages()
        self.draw_weather_notifications()

        if self.paused:
            self.draw_pause_overlay()

        if self.game_over:
            self.draw_game_over_overlay()

    def draw_weather_background(self):
        weather_color = self.weather_system.get_weather_color()
        alpha = int(25 * self.weather_system.current_intensity)

        if alpha > 5:
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
            overlay.set_alpha(alpha)
            overlay.fill(weather_color)
            self.screen.blit(overlay, (0, 0))

    def draw_game_messages(self):
        """Mensajes en esquina inferior derecha."""
        base_x = WINDOW_WIDTH - 450
        base_y = WINDOW_HEIGHT - 200

        for i, (message, time_left, color) in enumerate(self.game_messages[-5:]):
            alpha = min(255, int(255 * (time_left / 3.0)))

            text_surface = self.small_font.render(message, True, color)
            y_offset = base_y + i * 22

            bg_rect = pygame.Rect(base_x - 10, y_offset - 2, text_surface.get_width() + 20, 20)
            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
            bg_surface.set_alpha(120)
            bg_surface.fill((0, 0, 0))
            self.screen.blit(bg_surface, bg_rect)

            pygame.draw.rect(self.screen, (255, 255, 255, 50), bg_rect, 1)

            text_surface.set_alpha(alpha)
            self.screen.blit(text_surface, (base_x, y_offset))

    def draw_weather_notifications(self):
        """Notificaciones del clima en esquina inferior derecha."""
        base_x = WINDOW_WIDTH - 500
        base_y = WINDOW_HEIGHT - 120

        for i, (notification, time_left) in enumerate(self.weather_system.weather_notifications):
            alpha = min(255, int(255 * (time_left / 4.0)))

            text_surface = self.font.render(notification, True, self.weather_system.get_weather_color())
            y_offset = base_y + i * 28

            bg_rect = pygame.Rect(base_x - 10, y_offset - 2, text_surface.get_width() + 20, 24)
            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
            bg_surface.set_alpha(120)
            bg_surface.fill((0, 0, 0))
            self.screen.blit(bg_surface, bg_rect)

            pygame.draw.rect(self.screen, (255, 255, 255, 50), bg_rect, 1)

            text_surface.set_alpha(alpha)
            self.screen.blit(text_surface, (base_x, y_offset))

    def draw_full_map(self):
        """Dibuja el mapa completo con imágenes para tiles especiales."""
        for y in range(self.city_height):
            for x in range(self.city_width):
                if y < len(self.tiles) and x < len(self.tiles[y]):
                    tile_type = self.tiles[y][x]
                    screen_x = x * TILE_SIZE + self.map_offset_x
                    screen_y = y * TILE_SIZE + self.map_offset_y

                    rect = pygame.Rect(screen_x, screen_y, TILE_SIZE, TILE_SIZE)

                    if tile_type in self.tile_images:
                        base_color = self._get_tile_base_color(tile_type)
                        pygame.draw.rect(self.screen, base_color, rect)

                        self.screen.blit(self.tile_images[tile_type], (screen_x, screen_y))

                        if tile_type == "P":
                            player_screen_x = self.player_pos.x * TILE_SIZE + self.map_offset_x
                            player_screen_y = self.player_pos.y * TILE_SIZE + self.map_offset_y
                            distance = abs(player_screen_x - screen_x) + abs(player_screen_y - screen_y)

                            if distance < TILE_SIZE:
                                bonus_text = self.small_font.render("+15/s", True, (255, 255, 255))
                                text_rect = bonus_text.get_rect(
                                    center=(screen_x + TILE_SIZE // 2, screen_y + TILE_SIZE // 2))

                                text_bg = pygame.Rect(text_rect.x - 2, text_rect.y - 1, text_rect.width + 4,
                                                      text_rect.height + 2)
                                text_bg_surface = pygame.Surface((text_bg.width, text_bg.height))
                                text_bg_surface.set_alpha(150)
                                text_bg_surface.fill((0, 100, 0))
                                self.screen.blit(text_bg_surface, text_bg)

                                self.screen.blit(bonus_text, text_rect)
                    else:
                        color = self._get_tile_base_color(tile_type)
                        pygame.draw.rect(self.screen, color, rect)

                    pygame.draw.rect(self.screen, (100, 100, 100), rect, 1)

        self.draw_map_info()

    def draw_map_info(self):
        """Información del mapa con datos reales de la API."""
        map_rect = pygame.Rect(
            self.map_offset_x - 3,
            self.map_offset_y - 3,
            self.map_pixel_width + 6,
            self.map_pixel_height + 6
        )
        pygame.draw.rect(self.screen, UI_BORDER, map_rect, 3)

        title_text = self.title_font.render(f"{self.city_name.upper()} {self.city_width}x{self.city_height}", True,
                                            UI_TEXT_HEADER)
        title_bg = pygame.Rect(
            self.map_offset_x + self.map_pixel_width // 2 - title_text.get_width() // 2 - 10,
            2,
            title_text.get_width() + 20,
            22
        )
        pygame.draw.rect(self.screen, UI_HIGHLIGHT, title_bg, border_radius=5)
        pygame.draw.rect(self.screen, UI_BORDER, title_bg, 2, border_radius=5)
        title_rect = title_text.get_rect(center=(
            self.map_offset_x + self.map_pixel_width // 2,
            13
        ))
        self.screen.blit(title_text, title_rect)

        size_text = self.font.render(f"Tiles: {TILE_SIZE}px | {self.city_width * self.city_height} celdas totales",
                                     True, UI_TEXT_SECONDARY)
        self.screen.blit(size_text, (self.map_offset_x, self.map_offset_y - 12))

        tile_count = len(self.tile_images)
        weather_count = len(self.weather_images)

        if tile_count == 3 and weather_count >= 9:
            api_text = self.small_font.render("✅ API TigerCity + Imágenes completas (Tiles + Clima)", True, UI_SUCCESS)
        elif tile_count > 0 or weather_count > 0:
            status_parts = []
            if tile_count > 0:
                tile_types = []
                if "P" in self.tile_images: tile_types.append("Parques")
                if "C" in self.tile_images: tile_types.append("Calles")
                if "B" in self.tile_images: tile_types.append("Edificios")
                status_parts.append(f"Tiles: {', '.join(tile_types)}")
            if weather_count > 0:
                status_parts.append(f"Clima: {weather_count} estados")

            api_text = self.small_font.render(f"✅ API + PNG: {' | '.join(status_parts)}", True, UI_WARNING)
        else:
            api_text = self.small_font.render("✅ API TigerCity REAL + Gráficos de respaldo completos", True, UI_WARNING)
        self.screen.blit(api_text, (self.map_offset_x, self.map_offset_y - 24))

    def draw_orders(self):
        """Dibuja todos los marcadores de pedidos."""
        for order in self.available_orders.items:
            if order.status in ["available", "accepted"]:
                self.draw_order_marker(order, order.pickup, "P")

        for order in self.available_orders.items:
            if order.status == "accepted":
                self.draw_order_marker(order, order.dropoff, "D", is_dropoff=True)

        for order in self.inventory:
            if order.status == "picked_up":
                self.draw_order_marker(order, order.dropoff, order.id[-2:], in_inventory=True)

    def draw_player(self):
        """Dibuja el jugador con imagen PNG o indicadores de estado."""
        screen_x = self.player_pos.x * TILE_SIZE + self.map_offset_x + 2
        screen_y = self.player_pos.y * TILE_SIZE + self.map_offset_y + 2

        if self.player_image is not None:
            image_rect = self.player_image.get_rect()
            image_rect.center = (screen_x + (TILE_SIZE - 4) // 2, screen_y + (TILE_SIZE - 4) // 2)
            self.screen.blit(self.player_image, image_rect.topleft)

            border_rect = pygame.Rect(
                screen_x - 1, screen_y - 1,
                TILE_SIZE - 2, TILE_SIZE - 2
            )

            if self.stamina > 30:
                border_color = (0, 255, 0)
                border_width = 2
            elif self.stamina > 0:
                border_color = (255, 255, 0)
                border_width = 3
            else:
                border_color = (255, 0, 0)
                border_width = 4

            pygame.draw.rect(self.screen, border_color, border_rect, border_width)

            if self.stamina <= 30:
                alert_rect = pygame.Rect(screen_x - 2, screen_y - 8, TILE_SIZE, 4)
                alert_color = BRIGHT_RED if self.stamina <= 0 else (255, 200, 0)
                pygame.draw.rect(self.screen, alert_color, alert_rect)

                if self.stamina <= 0:
                    status_text = self.small_font.render("EXHAUSTO!", True, WHITE)
                    status_rect = status_text.get_rect(center=(screen_x + TILE_SIZE // 2, screen_y - 12))

                    text_bg = pygame.Rect(status_rect.x - 2, status_rect.y - 1, status_rect.width + 4,
                                          status_rect.height + 2)
                    text_bg_surface = pygame.Surface((text_bg.width, text_bg.height))
                    text_bg_surface.set_alpha(200)
                    text_bg_surface.fill((200, 0, 0))
                    self.screen.blit(text_bg_surface, text_bg)

                    self.screen.blit(status_text, status_rect)

        else:
            player_rect = pygame.Rect(
                screen_x, screen_y,
                TILE_SIZE - 4, TILE_SIZE - 4
            )

            if self.stamina > 30:
                color = BLUE
            elif self.stamina > 0:
                color = YELLOW
            else:
                color = RED

            pygame.draw.ellipse(self.screen, color, player_rect)
            pygame.draw.ellipse(self.screen, BLACK, player_rect, 2)

            if self.stamina <= 30:
                alert_rect = pygame.Rect(screen_x - 2, screen_y - 8, TILE_SIZE, 4)
                pygame.draw.rect(self.screen, BRIGHT_RED, alert_rect)

                if self.stamina <= 0:
                    status_text = self.small_font.render("EXHAUSTO!", True, WHITE)
                    status_rect = status_text.get_rect(center=(screen_x + TILE_SIZE // 2, screen_y - 12))

                    text_bg = pygame.Rect(status_rect.x - 2, status_rect.y - 1, status_rect.width + 4,
                                          status_rect.height + 2)
                    text_bg_surface = pygame.Surface((text_bg.width, text_bg.height))
                    text_bg_surface.set_alpha(200)
                    text_bg_surface.fill((200, 0, 0))
                    self.screen.blit(text_bg_surface, text_bg)

                    self.screen.blit(status_text, status_rect)

    def draw_order_marker(self, order, position, label, is_dropoff=False, in_inventory=False):
        """Dibuja un marcador individual de pedido."""
        screen_x = position.x * TILE_SIZE + self.map_offset_x + 1
        screen_y = position.y * TILE_SIZE + self.map_offset_y + 1

        marker_rect = pygame.Rect(screen_x, screen_y, TILE_SIZE - 2, TILE_SIZE - 2)

        urgency_color = self.get_order_urgency_color(order)
        time_remaining = self.get_order_time_remaining(order)

        if in_inventory:
            if time_remaining <= 0:
                fill_color = (80, 40, 40)
                border_color = (120, 0, 0)
            elif urgency_color == DARK_GREEN:
                fill_color = (255, 200, 150)
                border_color = (255, 140, 0)
            elif urgency_color == YELLOW:
                fill_color = (255, 180, 255)
                border_color = (255, 100, 255)
            else:
                fill_color = (255, 100, 150)
                border_color = (255, 0, 100)
        elif is_dropoff:
            if urgency_color == DARK_GREEN:
                fill_color = (150, 200, 255)
                border_color = (0, 100, 255)
            elif urgency_color == YELLOW:
                fill_color = (180, 180, 255)
                border_color = (100, 100, 255)
            else:
                fill_color = (200, 150, 255)
                border_color = (150, 0, 255)
        else:
            if time_remaining <= 0:
                fill_color = (100, 50, 50)
                border_color = DARK_RED
            elif urgency_color == DARK_GREEN:
                fill_color = (200, 255, 200)
                border_color = DARK_GREEN
            elif urgency_color == YELLOW:
                fill_color = (255, 255, 200)
                border_color = ORANGE
            else:
                fill_color = (255, 200, 200)
                border_color = RED

        pygame.draw.rect(self.screen, fill_color, marker_rect)
        border_width = 3 if time_remaining <= 0 or urgency_color == RED else 2
        pygame.draw.rect(self.screen, border_color, marker_rect, border_width)

        text = self.font.render(label, True, BLACK)
        text_rect = text.get_rect(center=(screen_x + TILE_SIZE // 2, screen_y + TILE_SIZE // 2))
        self.screen.blit(text, text_rect)

        if TILE_SIZE >= 28:
            time_text = self.get_order_status_text(order)
            time_surface = self.small_font.render(time_text[:6], True, BLACK)
            time_rect = time_surface.get_rect(center=(screen_x + TILE_SIZE // 2, screen_y + TILE_SIZE // 2 + 12))
            self.screen.blit(time_surface, time_rect)

    def draw_ui(self):
        """Dibuja la interfaz con controles restaurados."""
        sidebar_x = self.map_offset_x + self.map_pixel_width + 25
        sidebar_width = WINDOW_WIDTH - sidebar_x - 25
        panel_spacing = 15

        col_width = (sidebar_width - panel_spacing) // 2
        col1_x = sidebar_x
        col2_x = sidebar_x + col_width + panel_spacing

        y1 = 30
        self.draw_compact_header(col1_x, y1, col_width)
        y1 += 85
        self.draw_compact_stats(col1_x, y1, col_width)
        y1 += 140
        self.draw_compact_player_status(col1_x, y1, col_width)
        y1 += 140
        self.draw_compact_reputation(col1_x, y1, col_width)
        y1 += 120
        self.draw_compact_weather(col1_x, y1, col_width)

        y2 = 30
        self.draw_compact_legend(col2_x, y2, col_width)
        y2 += 85
        self.draw_compact_tips(col2_x, y2, col_width)
        y2 += 100
        self.draw_compact_progress(col2_x, y2, col_width)
        y2 += 90
        self.draw_compact_controls(col2_x, y2, col_width)

    def draw_compact_header(self, x: int, y: int, width: int):
        """Encabezado compacto con información de la API."""
        header_bg = pygame.Rect(x - 8, y - 5, width + 16, 75)
        pygame.draw.rect(self.screen, UI_HIGHLIGHT, header_bg, border_radius=6)
        pygame.draw.rect(self.screen, UI_BORDER, header_bg, 2, border_radius=6)

        title = self.large_font.render(f"COURIER QUEST - {self.city_name.upper()}", True, UI_TEXT_HEADER)
        title_rect = title.get_rect(center=(x + width // 2, y + 12))
        self.screen.blit(title, title_rect)

        tile_count = len(self.tile_images)
        weather_count = len(self.weather_images)
        has_player_image = self.player_image is not None

        if tile_count == 3 and weather_count >= 9 and has_player_image:
            subtitle = self.font.render("API REAL + IMÁGENES COMPLETAS + JUGADOR ✅", True, UI_SUCCESS)
        elif tile_count > 0 or weather_count > 0 or has_player_image:
            components = []
            if tile_count > 0:
                components.append(f"{tile_count} TILES")
            if weather_count > 0:
                components.append(f"{weather_count} CLIMA")
            if has_player_image:
                components.append("JUGADOR")
            subtitle = self.font.render(f"API + {' + '.join(components)} ✅", True, UI_SUCCESS)
        else:
            subtitle = self.font.render("API REAL + GRÁFICOS DE RESPALDO ⚠️", True, UI_WARNING)
        subtitle_rect = subtitle.get_rect(center=(x + width // 2, y + 32))
        self.screen.blit(subtitle, subtitle_rect)

        progress = (self.money / self.goal) * 100
        meta_color = UI_SUCCESS if progress >= 100 else UI_WARNING if progress >= 80 else UI_CRITICAL
        meta_text = f"Meta: ${self.money}/${self.goal} ({progress:.1f}%)"
        meta = self.small_font.render(meta_text, True, meta_color)
        meta_rect = meta.get_rect(center=(x + width // 2, y + 52))
        self.screen.blit(meta, meta_rect)

    def draw_compact_stats(self, x: int, y: int, width: int):
        """Estadísticas principales con reglas exactas."""
        stats_bg = pygame.Rect(x - 8, y - 5, width + 16, 130)
        pygame.draw.rect(self.screen, (250, 250, 255), stats_bg, border_radius=6)
        pygame.draw.rect(self.screen, UI_BORDER, stats_bg, 2, border_radius=6)

        title = self.header_font.render("ESTADÍSTICAS", True, UI_TEXT_HEADER)
        self.screen.blit(title, (x + 5, y))

        stats_y = y + 25
        col_left = x + 5
        col_right = x + width // 2 + 5

        rep_color = UI_SUCCESS if self.reputation >= 80 else UI_WARNING if self.reputation >= 50 else UI_CRITICAL
        self.draw_compact_stat(col_left, stats_y, f"Reputación: {self.reputation}/100", rep_color)

        time_left = self.max_game_time - self.game_time
        time_color = UI_SUCCESS if time_left > 300 else UI_WARNING if time_left > 120 else UI_CRITICAL
        self.draw_compact_stat(col_left, stats_y + 20, f"Tiempo: {self.format_time(time_left)}", time_color)

        district = self._get_district_name(self.player_pos.x, self.player_pos.y)
        self.draw_compact_stat(col_left, stats_y + 40, f"Distrito: {district}", BLUE)

        speed = self.calculate_actual_speed()
        speed_color = UI_SUCCESS if speed >= 2.5 else UI_WARNING if speed >= 2.0 else UI_CRITICAL
        self.draw_compact_stat(col_left, stats_y + 60, f"Velocidad: {speed:.1f} c/s", speed_color)

        inv_weight = sum(order.weight for order in self.inventory)
        inv_color = UI_WARNING if inv_weight >= self.max_weight * 0.8 else UI_TEXT_NORMAL
        self.draw_compact_stat(col_right, stats_y, f"Inventario: {inv_weight}/{self.max_weight}kg", inv_color)

        active_orders = self.available_orders.size()
        orders_color = UI_SUCCESS if active_orders > 0 else UI_TEXT_SECONDARY
        self.draw_compact_stat(col_right, stats_y + 20, f"Activos: {active_orders}/10", orders_color)

        self.draw_compact_stat(col_right, stats_y + 40, f"Pendientes: {len(self.pending_orders)}", UI_TEXT_NORMAL)
        self.draw_compact_stat(col_right, stats_y + 60, f"Completados: {len(self.completed_orders)}", UI_SUCCESS)

    def draw_compact_player_status(self, x: int, y: int, width: int):
        """Estado del jugador con reglas exactas."""
        status_bg = pygame.Rect(x - 8, y - 5, width + 16, 110)
        pygame.draw.rect(self.screen, (255, 250, 240), status_bg, border_radius=6)
        pygame.draw.rect(self.screen, UI_BORDER, status_bg, 2, border_radius=6)

        title = self.header_font.render("ESTADO JUGADOR", True, UI_TEXT_HEADER)
        self.screen.blit(title, (x + 5, y))

        bar_y = y + 25
        bar_width = width - 20
        bar_height = 20

        label = self.font.render("RESISTENCIA:", True, UI_TEXT_NORMAL)
        self.screen.blit(label, (x + 5, bar_y))

        bar_bg = pygame.Rect(x + 10, bar_y + 20, bar_width - 10, bar_height)
        pygame.draw.rect(self.screen, DARK_GRAY, bar_bg, border_radius=3)

        stamina_progress = self.stamina / self.max_stamina
        fill_width = max(3, int((bar_width - 10) * stamina_progress))

        if self.stamina > 30:
            fill_color = UI_SUCCESS
        elif self.stamina > 0:
            fill_color = UI_WARNING
        else:
            fill_color = UI_CRITICAL

        if fill_width > 0:
            fill_rect = pygame.Rect(x + 12, bar_y + 22, fill_width - 4, bar_height - 4)
            pygame.draw.rect(self.screen, fill_color, fill_rect, border_radius=2)

        threshold_x = x + 10 + int((30 / self.max_stamina) * (bar_width - 10))
        pygame.draw.line(self.screen, (255, 100, 100),
                         (threshold_x, bar_y + 20),
                         (threshold_x, bar_y + 20 + bar_height), 2)

        pygame.draw.rect(self.screen, UI_BORDER, bar_bg, 2, border_radius=3)

        stamina_text = f"{self.stamina:.0f}/{self.max_stamina}"
        text_surface = self.small_font.render(stamina_text, True, BLACK)
        text_rect = text_surface.get_rect(center=(x + bar_width // 2, bar_y + 30))
        self.screen.blit(text_surface, text_rect)

        status_y = bar_y + 45
        if self.stamina <= 0:
            status_text = "EXHAUSTO (¡BLOQUEADO!)"
            status_color = UI_CRITICAL
        elif self.stamina <= 30:
            status_text = f"CANSADO ({self.stamina:.0f}/30)"
            status_color = UI_WARNING
        else:
            status_text = "NORMAL"
            status_color = UI_SUCCESS

        status_surface = self.font.render(status_text, True, status_color)
        self.screen.blit(status_surface, (x + 5, status_y))

    def draw_compact_reputation(self, x: int, y: int, width: int):
        """Barra de reputación."""
        reputation_bg = pygame.Rect(x - 8, y - 5, width + 16, 110)
        pygame.draw.rect(self.screen, (240, 255, 240), reputation_bg, border_radius=6)
        pygame.draw.rect(self.screen, UI_BORDER, reputation_bg, 2, border_radius=6)

        title = self.header_font.render("REPUTACIÓN", True, UI_TEXT_HEADER)
        self.screen.blit(title, (x + 5, y))

        bar_y = y + 25
        bar_width = width - 20
        bar_height = 20

        label = self.font.render("REPUTACIÓN:", True, UI_TEXT_NORMAL)
        self.screen.blit(label, (x + 5, bar_y))

        bar_bg = pygame.Rect(x + 10, bar_y + 20, bar_width - 10, bar_height)
        pygame.draw.rect(self.screen, DARK_GRAY, bar_bg, border_radius=3)

        reputation_progress = self.reputation / 100.0
        fill_width = max(3, int((bar_width - 10) * reputation_progress))

        if self.reputation >= 90:
            fill_color = BRIGHT_GREEN
        elif self.reputation >= 80:
            fill_color = GREEN
        elif self.reputation >= 70:
            fill_color = YELLOW
        elif self.reputation >= 50:
            fill_color = ORANGE
        elif self.reputation >= 20:
            fill_color = RED
        else:
            fill_color = DARK_RED

        if fill_width > 0:
            fill_rect = pygame.Rect(x + 12, bar_y + 22, fill_width - 4, bar_height - 4)
            pygame.draw.rect(self.screen, fill_color, fill_rect, border_radius=2)

        pygame.draw.rect(self.screen, UI_BORDER, bar_bg, 2, border_radius=3)

        reputation_text = f"{self.reputation}/100"
        text_surface = self.small_font.render(reputation_text, True, BLACK)
        text_rect = text_surface.get_rect(center=(x + bar_width // 2, bar_y + 30))
        self.screen.blit(text_surface, text_rect)

        status_y = bar_y + 45
        if self.reputation < 20:
            status_text = "CRÍTICA (¡Perderás!)"
            status_color = UI_CRITICAL
        elif self.reputation >= 90:
            status_text = "EXCELENTE (+5%)"
            status_color = UI_SUCCESS
        elif self.reputation >= 80:
            status_text = "MUY BUENA"
            status_color = UI_SUCCESS
        elif self.reputation >= 70:
            status_text = "BUENA"
            status_color = UI_WARNING
        else:
            status_text = "REGULAR"
            status_color = UI_WARNING

        status_surface = self.font.render(status_text, True, status_color)
        self.screen.blit(status_surface, (x + 5, status_y))

    def draw_compact_weather(self, x: int, y: int, width: int):
        """Indicador del clima con imagen."""
        weather_bg = pygame.Rect(x - 8, y - 5, width + 16, 110)
        pygame.draw.rect(self.screen, UI_HIGHLIGHT, weather_bg, border_radius=6)
        pygame.draw.rect(self.screen, UI_BORDER, weather_bg, 2, border_radius=6)

        title = self.header_font.render("CLIMA DINÁMICO", True, UI_TEXT_HEADER)
        self.screen.blit(title, (x + 5, y))

        current_weather = self.weather_system.current_condition
        image_size = 75
        weather_image_pos = (x + 12, y + 27)

        if current_weather in self.weather_images:
            scaled_image = pygame.transform.scale(self.weather_images[current_weather], (image_size, image_size))
            self.screen.blit(scaled_image, weather_image_pos)

            image_rect = pygame.Rect(weather_image_pos[0], weather_image_pos[1], image_size, image_size)
            pygame.draw.rect(self.screen, UI_BORDER, image_rect, 2, border_radius=5)
        else:
            weather_color = self.weather_system.get_weather_color()
            circle_rect = pygame.Rect(weather_image_pos[0], weather_image_pos[1], image_size, image_size)
            pygame.draw.ellipse(self.screen, weather_color, circle_rect)
            pygame.draw.ellipse(self.screen, UI_BORDER, circle_rect, 2)

        weather_name = self.weather_system.get_weather_description()
        name_text = self.font.render(weather_name, True, UI_TEXT_NORMAL)
        self.screen.blit(name_text, (x + image_size + 25, y + 27))

        speed_mult = self.weather_system.get_speed_multiplier()
        stamina_penalty = self.weather_system.get_stamina_penalty()

        speed_color = UI_SUCCESS if speed_mult >= 0.9 else UI_WARNING if speed_mult >= 0.8 else UI_CRITICAL
        stamina_color = UI_SUCCESS if stamina_penalty <= 0.05 else UI_WARNING if stamina_penalty <= 0.1 else UI_CRITICAL

        speed_text = f"Velocidad: {speed_mult:.0%}"
        stamina_text = f"Resistencia: -{stamina_penalty * 100:.0f}%"

        speed_surface = self.small_font.render(speed_text, True, speed_color)
        stamina_surface = self.small_font.render(stamina_text, True, stamina_color)

        self.screen.blit(speed_surface, (x + image_size + 25, y + 50))
        self.screen.blit(stamina_surface, (x + image_size + 25, y + 70))

    def draw_compact_legend(self, x: int, y: int, width: int):
        """Leyenda del mapa."""
        legend_bg = pygame.Rect(x - 8, y - 5, width + 16, 75)
        pygame.draw.rect(self.screen, (255, 255, 240), legend_bg, border_radius=6)
        pygame.draw.rect(self.screen, UI_BORDER, legend_bg, 2, border_radius=6)

        title = self.header_font.render("LEYENDA DEL MAPA", True, UI_TEXT_HEADER)
        self.screen.blit(title, (x + 5, y))

        items = [
            ("Calles", LIGHT_GRAY, "PNG" if "C" in self.tile_images else "Caminable"),
            ("Parques", GREEN, "PNG +15/s" if "P" in self.tile_images else "Recupera +15/s"),
            ("Edificios", DARK_GRAY, "PNG" if "B" in self.tile_images else "BLOQUEADO"),
        ]

        for i, (name, color, desc) in enumerate(items):
            row = i % 2
            col = i // 2
            item_x = x + 5 + col * (width // 2)
            item_y = y + 20 + row * 18

            color_rect = pygame.Rect(item_x, item_y, 10, 10)
            pygame.draw.rect(self.screen, color, color_rect)
            pygame.draw.rect(self.screen, UI_BORDER, color_rect, 1)

            if "PNG" in desc:
                text = self.small_font.render(f"{name}", True, UI_SUCCESS)
            else:
                text = self.small_font.render(f"{name}", True, UI_TEXT_NORMAL)
            self.screen.blit(text, (item_x + 15, item_y - 2))

    def draw_compact_tips(self, x: int, y: int, width: int):
        """Consejos basados en reglas."""
        tips_bg = pygame.Rect(x - 8, y - 5, width + 16, 90)
        pygame.draw.rect(self.screen, (240, 255, 240), tips_bg, border_radius=6)
        pygame.draw.rect(self.screen, UI_BORDER, tips_bg, 2, border_radius=6)

        title = self.header_font.render("REGLAS DEL JUEGO", True, UI_TEXT_HEADER)
        self.screen.blit(title, (x + 5, y))

        tips = [
            "• Resistencia >30 para moverse",
            "• META: $3000 (Mayor desafío)",
            "• P2: 4min | P1: 7min | P0: 9min",
            "• Mayor prioridad = Mayor pago"
        ]

        for i, tip in enumerate(tips):
            text = self.small_font.render(tip, True, UI_TEXT_NORMAL)
            self.screen.blit(text, (x + 5, y + 20 + i * 15))

    def draw_compact_progress(self, x: int, y: int, width: int):
        """Progreso del juego."""
        progress_bg = pygame.Rect(x - 8, y - 5, width + 16, 80)
        pygame.draw.rect(self.screen, (255, 255, 240), progress_bg, border_radius=6)
        pygame.draw.rect(self.screen, UI_BORDER, progress_bg, 2, border_radius=6)

        title = self.header_font.render("PROGRESO", True, UI_TEXT_HEADER)
        self.screen.blit(title, (x + 5, y))

        efficiency = self.calculate_efficiency()

        progress_info = [
            f"Completados: {len(self.completed_orders)}",
            f"Tiempo jugado: {self.format_time(self.game_time)}",
            f"Eficiencia: {efficiency:.1f}%"
        ]

        for i, info in enumerate(progress_info):
            color = UI_SUCCESS if "Completados" in info else UI_TEXT_NORMAL
            text = self.small_font.render(info, True, color)
            self.screen.blit(text, (x + 5, y + 20 + i * 16))

    def draw_compact_stat(self, x: int, y: int, text: str, color: tuple):
        """Dibuja una estadística de forma compacta."""
        text_surface = self.small_font.render(text, True, color)
        self.screen.blit(text_surface, (x, y))

    def draw_compact_controls(self, x: int, y: int, width: int):
        """Controles del juego."""
        controls_bg = pygame.Rect(x - 8, y - 5, width + 16, 230)
        pygame.draw.rect(self.screen, (240, 245, 255), controls_bg, border_radius=6)
        pygame.draw.rect(self.screen, UI_BORDER, controls_bg, 2, border_radius=6)

        title = self.header_font.render("CONTROLES & ALGORITMOS", True, UI_TEXT_HEADER)
        self.screen.blit(title, (x + 5, y))

        algo_title = self.font.render("Algoritmos:", True, UI_SUCCESS)
        self.screen.blit(algo_title, (x + 5, y + 25))

        algorithms = [
            "P: Prioridad (QuickSort)",
            "T: Tiempo (MergeSort)",
            "D: Distancia (InsertionSort)"
        ]

        for i, algo in enumerate(algorithms):
            text = self.small_font.render(algo, True, UI_TEXT_NORMAL)
            self.screen.blit(text, (x + 5, y + 45 + i * 16))

        control_title = self.font.render("Controles:", True, UI_TEXT_HEADER)
        self.screen.blit(control_title, (x + 5, y + 105))

        controls = [
            "WASD/Flechas: Moverse | E: Interactuar",
            "I: Inventario | O: Pedidos",
            "F5: Guardar | F9: Cargar",
            "B: Volver (menú cargar)",
            "P/T/D: Algoritmos de ordenamiento"
        ]

        for i, control in enumerate(controls):
            text = self.small_font.render(control, True, UI_TEXT_NORMAL)
            self.screen.blit(text, (x + 5, y + 125 + i * 16))

    def draw_inventory_overlay(self):
        """Overlay del inventario."""
        overlay_x = self.map_offset_x + self.map_pixel_width + 40
        overlay_y = 400
        overlay_width = 650
        overlay_height = 520

        overlay_rect = pygame.Rect(overlay_x, overlay_y, overlay_width, overlay_height)
        pygame.draw.rect(self.screen, UI_BACKGROUND, overlay_rect, border_radius=12)
        pygame.draw.rect(self.screen, UI_BORDER, overlay_rect, 3, border_radius=12)

        title_bg = pygame.Rect(overlay_x, overlay_y, overlay_width, 45)
        pygame.draw.rect(self.screen, UI_HIGHLIGHT, title_bg, border_radius=12)
        title = self.large_font.render("INVENTARIO ACTUAL", True, UI_TEXT_HEADER)
        title_rect = title.get_rect(center=(overlay_x + overlay_width // 2, overlay_y + 22))
        self.screen.blit(title, title_rect)

        if not self.inventory:
            no_items_text = self.font.render("No hay pedidos en inventario", True, UI_TEXT_SECONDARY)
            text_rect = no_items_text.get_rect(center=(overlay_rect.centerx, overlay_rect.centery))
            self.screen.blit(no_items_text, text_rect)
        else:
            inventory_list = list(self.inventory)

            for i, order in enumerate(inventory_list[:7]):
                y_pos = overlay_rect.y + 55 + i * 65

                if i == self.selected_inventory_index:
                    selection_rect = pygame.Rect(overlay_rect.x + 8, y_pos - 3, overlay_width - 16, 60)
                    pygame.draw.rect(self.screen, UI_HIGHLIGHT, selection_rect, border_radius=5)
                    pygame.draw.rect(self.screen, UI_BORDER, selection_rect, 2, border_radius=5)

                urgency_color = self.get_order_urgency_color(order)
                time_text = self.get_order_status_text(order)
                district = self._get_district_name(order.dropoff.x, order.dropoff.y)

                priority_text = f"P{order.priority}" if order.priority > 0 else "Normal"

                text1 = self.font.render(f"{order.id} ({priority_text}) - {time_text}", True, urgency_color)
                self.screen.blit(text1, (overlay_rect.x + 15, y_pos))

                text2 = self.small_font.render(f"Peso: {order.weight}kg - Pago: ${order.payout} - {district}", True,
                                               UI_TEXT_NORMAL)
                self.screen.blit(text2, (overlay_rect.x + 15, y_pos + 20))

                distance = abs(order.dropoff.x - self.player_pos.x) + abs(order.dropoff.y - self.player_pos.y)
                text3 = self.small_font.render(
                    f"Destino: ({order.dropoff.x}, {order.dropoff.y}) - Distancia: {distance} celdas", True,
                    UI_TEXT_SECONDARY)
                self.screen.blit(text3, (overlay_rect.x + 15, y_pos + 40))

        instructions_bg = pygame.Rect(overlay_x, overlay_y + overlay_height - 50, overlay_width, 45)
        pygame.draw.rect(self.screen, (240, 240, 245), instructions_bg, border_radius=12)

        instructions = [
            "↑/↓: Navegar | ENTER: Entregar (si estás en destino) | I: Cerrar",
            "P/T: Ordenar con QuickSort/MergeSort según algoritmos implementados"
        ]

        for i, instruction in enumerate(instructions):
            color = UI_SUCCESS if "algoritmos" in instruction else UI_TEXT_NORMAL
            text = self.small_font.render(instruction, True, color)
            self.screen.blit(text, (overlay_rect.x + 15, overlay_rect.y + overlay_height - 42 + i * 14))

    def draw_orders_overlay(self):
        """Overlay de pedidos."""
        overlay_x = self.map_offset_x + self.map_pixel_width + 40
        overlay_y = 50
        overlay_width = 750
        overlay_height = 650

        overlay_rect = pygame.Rect(overlay_x, overlay_y, overlay_width, overlay_height)
        pygame.draw.rect(self.screen, UI_BACKGROUND, overlay_rect, border_radius=12)
        pygame.draw.rect(self.screen, UI_BORDER, overlay_rect, 3, border_radius=12)

        title_bg = pygame.Rect(overlay_x, overlay_y, overlay_width, 50)
        pygame.draw.rect(self.screen, UI_HIGHLIGHT, title_bg, border_radius=12)
        title = self.large_font.render("PEDIDOS - ALGORITMOS IMPLEMENTADOS", True, UI_TEXT_HEADER)
        title_rect = title.get_rect(center=(overlay_x + overlay_width // 2, overlay_y + 25))
        self.screen.blit(title, title_rect)

        if not self.available_orders.items:
            no_orders_text = self.font.render("No hay pedidos disponibles", True, UI_TEXT_SECONDARY)
            text_rect = no_orders_text.get_rect(center=(overlay_rect.centerx, overlay_rect.centery))
            self.screen.blit(no_orders_text, text_rect)
        else:
            for i, order in enumerate(self.available_orders.items[:7]):
                y_pos = overlay_rect.y + 60 + i * 80

                if i == self.selected_order_index:
                    selection_rect = pygame.Rect(overlay_rect.x + 8, y_pos - 3, overlay_width - 16, 75)
                    pygame.draw.rect(self.screen, UI_HIGHLIGHT, selection_rect, border_radius=5)
                    pygame.draw.rect(self.screen, UI_BORDER, selection_rect, 2, border_radius=5)

                urgency_color = self.get_order_urgency_color(order)
                time_text = self.get_order_status_text(order)

                pickup_district = self._get_district_name(order.pickup.x, order.pickup.y)
                dropoff_district = self._get_district_name(order.dropoff.x, order.dropoff.y)

                priority_text = f"P{order.priority}" if order.priority > 0 else "Normal"

                text1 = self.font.render(f"{order.id} ({priority_text}) - ${order.payout} | {time_text}", True,
                                         urgency_color)
                self.screen.blit(text1, (overlay_rect.x + 15, y_pos))

                text2 = self.small_font.render(
                    f"Peso: {order.weight}kg | Duración: {order.duration_minutes:.1f}min",
                    True, UI_TEXT_NORMAL)
                self.screen.blit(text2, (overlay_rect.x + 15, y_pos + 20))

                pickup_distance = abs(order.pickup.x - self.player_pos.x) + abs(order.pickup.y - self.player_pos.y)
                text3 = self.small_font.render(
                    f"Recoger: ({order.pickup.x}, {order.pickup.y}) [{pickup_district}] - {pickup_distance} celdas",
                    True, UI_TEXT_NORMAL)
                self.screen.blit(text3, (overlay_rect.x + 15, y_pos + 40))

                total_route_distance = abs(order.dropoff.x - order.pickup.x) + abs(order.dropoff.y - order.pickup.y)
                text4 = self.small_font.render(
                    f"Entregar: ({order.dropoff.x}, {order.dropoff.y}) [{dropoff_district}] - Ruta: {total_route_distance} celdas",
                    True, UI_TEXT_SECONDARY)
                self.screen.blit(text4, (overlay_rect.x + 15, y_pos + 60))

        instructions_bg = pygame.Rect(overlay_x, overlay_y + overlay_height - 80, overlay_width, 75)
        pygame.draw.rect(self.screen, (240, 240, 245), instructions_bg, border_radius=12)

        instructions = [
            "↑/↓: Navegar | ENTER: Aceptar pedido | O: Cerrar",
            "",
            "ALGORITMOS DE ORDENAMIENTO IMPLEMENTADOS:",
            "D: Ordenar por DISTANCIA (Insertion Sort O(n²))",
            "Usa P/T en inventario para QuickSort/MergeSort"
        ]

        for i, instruction in enumerate(instructions):
            if not instruction:
                continue
            if "ALGORITMOS" in instruction:
                color = UI_SUCCESS
            else:
                color = UI_TEXT_NORMAL

            text = self.small_font.render(instruction, True, color)
            self.screen.blit(text, (overlay_rect.x + 15, overlay_rect.y + overlay_height - 70 + i * 14))

    def draw_pause_overlay(self):
        """Overlay de pausa."""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 50))
        self.screen.blit(overlay, (0, 0))

        pause_rect = pygame.Rect(WINDOW_WIDTH // 2 - 250, WINDOW_HEIGHT // 2 - 120, 500, 240)
        pygame.draw.rect(self.screen, UI_BACKGROUND, pause_rect, border_radius=15)
        pygame.draw.rect(self.screen, UI_BORDER, pause_rect, 4, border_radius=15)

        pause_text = self.title_font.render("JUEGO PAUSADO", True, UI_TEXT_HEADER)
        text_rect = pause_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 40))
        self.screen.blit(pause_text, text_rect)

        instruction_text = self.large_font.render("Presiona ESPACIO para continuar", True, UI_TEXT_NORMAL)
        text_rect = instruction_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 10))
        self.screen.blit(instruction_text, text_rect)

        state_info = [
            f"Dinero: ${self.money}/${self.goal}",
            f"Tiempo restante: {self.format_time(self.max_game_time - self.game_time)}",
            f"Reputación: {self.reputation}/100"
        ]

        for i, info in enumerate(state_info):
            text = self.font.render(info, True, UI_TEXT_SECONDARY)
            text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 40 + i * 25))
            self.screen.blit(text, text_rect)

    def draw_game_over_overlay(self):
        """Overlay de fin de juego."""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(220)
        overlay.fill((20, 20, 40))
        self.screen.blit(overlay, (0, 0))

        game_over_rect = pygame.Rect(WINDOW_WIDTH // 2 - 350, WINDOW_HEIGHT // 2 - 280, 700, 560)
        pygame.draw.rect(self.screen, UI_BACKGROUND, game_over_rect, border_radius=20)
        pygame.draw.rect(self.screen, UI_BORDER, game_over_rect, 5, border_radius=20)

        if self.victory:
            title_text = self.title_font.render("¡VICTORIA!", True, UI_SUCCESS)
            message = f"¡Felicidades! Alcanzaste la meta de ${self.goal}"
        else:
            title_text = self.title_font.render("JUEGO TERMINADO", True, UI_CRITICAL)
            if self.reputation < 20:
                message = "Reputación demasiado baja"
            else:
                message = f"Tiempo agotado. Necesitabas ${self.goal - self.money} más"

        title_rect = title_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 240))
        self.screen.blit(title_text, title_rect)

        final_score = self._calculate_final_score()
        final_district = self._get_district_name(self.player_pos.x, self.player_pos.y)
        efficiency = self.calculate_efficiency()

        stats = [
            message,
            "",
            f"PUNTAJE FINAL: {final_score}",
            f"Dinero obtenido: ${self.money} / ${self.goal}",
            f"Reputación final: {self.reputation}/100",
            f"Pedidos completados: {len(self.completed_orders)}",
            f"Eficiencia: {efficiency:.1f}%",
            f"Ciudad: {self.city_name} ({self.city_width}x{self.city_height})",
            f"Posición final: ({self.player_pos.x}, {self.player_pos.y}) - Distrito {final_district}",
            f"Mejor racha consecutiva: {getattr(self, 'delivery_streak', 0)}",
            f"Tiempo total jugado: {self.format_time(self.game_time)}"
        ]

        for i, stat in enumerate(stats):
            if not stat:
                continue

            if "PUNTAJE FINAL" in stat:
                color = UI_SUCCESS if self.victory else UI_CRITICAL
                font = self.large_font
            elif "Dinero obtenido" in stat:
                progress = (self.money / self.goal) * 100
                color = UI_SUCCESS if progress >= 100 else UI_WARNING if progress >= 80 else UI_CRITICAL
                font = self.font
            elif "Reputación" in stat:
                color = UI_SUCCESS if self.reputation >= 80 else UI_WARNING if self.reputation >= 50 else UI_CRITICAL
                font = self.font
            else:
                color = UI_TEXT_NORMAL
                font = self.small_font

            text_surface = font.render(stat, True, color)
            text_rect = text_surface.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 200 + i * 25))
            self.screen.blit(text_surface, text_rect)

        instruction_text = self.font.render("Presiona ESC para volver al menú principal", True, UI_TEXT_SECONDARY)
        instruction_rect = instruction_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 220))
        self.screen.blit(instruction_text, instruction_rect)

    def run(self):
        """Bucle principal del juego."""
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            events = pygame.event.get()

            self.handle_events(events)

            if self.game_state == "playing" and not self.paused and not self.game_over:
                keys = pygame.key.get_pressed()
                self.handle_input(keys, dt)
                self.update(dt)

            self.draw()

        pygame.quit()
# ui/menu.py
import pygame
from typing import Optional
from systems.file_manager import RobustFileManager
from config.constants import WINDOW_WIDTH, WINDOW_HEIGHT, UI_HIGHLIGHT, UI_BORDER


class GameMenu:
    def __init__(self):
        self.state = "main_menu"
        self.main_options = ["Nuevo Juego", "Cargar Partida", "Tutorial", "Ver Puntajes", "Salir"]
        self.selected = 0
        self.file_manager = RobustFileManager()

        # Fuentes para el menú principal (más grandes)
        self.title_font = pygame.font.Font(None, 72)
        self.menu_font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 32)

        # Fuentes para submenús (tamaño original)
        self.submenu_title_font = pygame.font.Font(None, 48)
        self.submenu_font = pygame.font.Font(None, 32)
        self.submenu_small_font = pygame.font.Font(None, 24)

        # Cargar imágenes de los repartidores
        self.courier_left = None
        self.courier_right = None
        self._load_courier_images()

    def _load_courier_images(self):
        """Carga las imágenes de los repartidores para el menú."""
        try:
            # Cargar imagen izquierda
            left_img = pygame.image.load("assets/RepartidorIzq.png")
            # Escalar a un tamaño apropiado para el menú
            self.courier_left = pygame.transform.scale(left_img, (400, 500))
            print("✅ Imagen RepartidorIzq.png cargada para el menú")
        except Exception as e:
            print(f"⚠️ No se pudo cargar RepartidorIzq.png: {e}")
            self.courier_left = None

        try:
            # Cargar imagen derecha
            right_img = pygame.image.load("assets/RepartidorDer.png")
            # Escalar a un tamaño apropiado para el menú
            self.courier_right = pygame.transform.scale(right_img, (400, 500))
            print("✅ Imagen RepartidorDer.png cargada para el menú")
        except Exception as e:
            print(f"⚠️ No se pudo cargar RepartidorDer.png: {e}")
            self.courier_right = None

    def handle_menu_input(self, event) -> Optional[str]:
        if event.type == pygame.KEYDOWN:
            if self.state == "main_menu":
                return self._handle_main_menu_input(event)
            elif self.state == "load_menu":
                return self._handle_load_menu_input(event)
            elif self.state == "scores_menu":
                return self._handle_scores_menu_input(event)
        return None

    def _handle_scores_menu_input(self, event) -> Optional[str]:
        if event.key in (pygame.K_b, pygame.K_ESCAPE, pygame.K_RETURN):
            self.state = "main_menu"
            self.selected = 3
            if hasattr(self, '_cached_scores'):
                self._cached_scores = None
        return None

    def _handle_main_menu_input(self, event) -> Optional[str]:
        if event.key == pygame.K_UP:
            self.selected = (self.selected - 1) % len(self.main_options)
            if hasattr(self, '_cached_scores'):
                self._cached_scores = None
        elif event.key == pygame.K_DOWN:
            self.selected = (self.selected + 1) % len(self.main_options)
            if hasattr(self, '_cached_scores'):
                self._cached_scores = None
        elif event.key == pygame.K_RETURN:
            option = self.main_options[self.selected]
            if option == "Nuevo Juego":
                return "start_new_game"
            elif option == "Cargar Partida":
                self.state = "load_menu"
                self.selected = 0
                if hasattr(self, '_cached_scores'):
                    self._cached_scores = None
            elif option == "Tutorial":
                return "start_tutorial"
            elif option == "Ver Puntajes":
                self.state = "scores_menu"
                self.selected = 0
            elif option == "Salir":
                return "exit"
        elif event.key == pygame.K_ESCAPE:
            return "exit"
        return None

    def _handle_load_menu_input(self, event) -> Optional[str]:
        if event.key == pygame.K_UP:
            self.selected = max(0, self.selected - 1)
        elif event.key == pygame.K_DOWN:
            self.selected = min(1, self.selected + 1)
        elif event.key == pygame.K_RETURN:
            if self.selected == 1:
                self.state = "main_menu"
                self.selected = 1
            else:
                return "load_slot_1"
        elif event.key in (pygame.K_b, pygame.K_ESCAPE):
            self.state = "main_menu"
            self.selected = 1
        return None

    def draw(self, screen):
        screen.fill((20, 25, 40))

        if self.state == "main_menu":
            self._draw_main_menu(screen)
        elif self.state == "load_menu":
            self._draw_load_menu(screen)
        elif self.state == "scores_menu":
            self._draw_scores_menu(screen)

    def _draw_scores_menu(self, screen):
        title = self.submenu_title_font.render("TABLA DE PUNTAJES", True, (255, 255, 255))
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 80))
        screen.blit(title, title_rect)

        if not hasattr(self, '_cached_scores') or self._cached_scores is None:
            self._cached_scores = self.file_manager.load_scores()

        scores = self._cached_scores

        if not scores:
            no_scores_text = self.submenu_font.render("No hay puntajes registrados", True, (150, 150, 150))
            text_rect = no_scores_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
            screen.blit(no_scores_text, text_rect)
        else:
            start_y = 150
            headers = ["#", "Puntaje", "Dinero", "Rep.", "Pedidos", "Fecha", "Estado"]
            header_positions = [100, 200, 320, 420, 520, 650, 850]

            for i, header in enumerate(headers):
                header_text = self.submenu_font.render(header, True, (200, 200, 255))
                screen.blit(header_text, (header_positions[i], start_y))

            pygame.draw.line(screen, (100, 100, 150), (80, start_y + 35), (WINDOW_WIDTH - 80, start_y + 35), 2)

            for i, score in enumerate(scores[:10]):
                y_pos = start_y + 50 + i * 35
                rank_color = (255, 215, 0) if i == 0 else (192, 192, 192) if i == 1 else (205, 127, 50) if i == 2 else (
                    255, 255, 255)

                rank_text = self.submenu_small_font.render(f"{i + 1}", True, rank_color)
                screen.blit(rank_text, (header_positions[0], y_pos))

                score_text = self.submenu_small_font.render(f"{score.get('score', 0)}", True, rank_color)
                screen.blit(score_text, (header_positions[1], y_pos))

                money_text = self.submenu_small_font.render(f"${score.get('money', 0)}", True, (100, 255, 100))
                screen.blit(money_text, (header_positions[2], y_pos))

                rep = score.get('reputation', 0)
                rep_color = (100, 255, 100) if rep >= 80 else (255, 255, 100) if rep >= 50 else (255, 100, 100)
                rep_text = self.submenu_small_font.render(f"{rep}", True, rep_color)
                screen.blit(rep_text, (header_positions[3], y_pos))

                orders_text = self.submenu_small_font.render(f"{score.get('completed_orders', 0)}", True,
                                                             (150, 200, 255))
                screen.blit(orders_text, (header_positions[4], y_pos))

                date_str = score.get('date', '')[:16].replace('T', ' ')
                date_text = self.submenu_small_font.render(date_str, True, (150, 150, 150))
                screen.blit(date_text, (header_positions[5], y_pos))

                victory = score.get('victory', False)
                status_text = "VICTORIA" if victory else "DERROTA"
                status_color = (100, 255, 100) if victory else (255, 100, 100)
                status_surface = self.submenu_small_font.render(status_text, True, status_color)
                screen.blit(status_surface, (header_positions[6], y_pos))

        back_text = self.submenu_small_font.render("Presiona B, ESC o ENTER para volver", True, (150, 150, 150))
        back_rect = back_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50))
        screen.blit(back_text, back_rect)

    def _draw_main_menu(self, screen):
        # Posiciones para las imágenes (sin cuadros blancos)
        left_x = 80
        right_x = WINDOW_WIDTH - 80 - 400  # 400 es el ancho de la imagen
        center_y = WINDOW_HEIGHT // 2

        # Dibujar imágenes de repartidores si están cargadas
        if self.courier_left:
            # Centrar imagen verticalmente en el lado izquierdo
            img_y = center_y - self.courier_left.get_height() // 2
            screen.blit(self.courier_left, (left_x, img_y))

        if self.courier_right:
            # Centrar imagen verticalmente en el lado derecho
            img_y = center_y - self.courier_right.get_height() // 2
            screen.blit(self.courier_right, (right_x, img_y))

        # Título
        title = self.title_font.render("COURIER QUEST", True, (255, 255, 255))
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 150))
        screen.blit(title, title_rect)

        subtitle = self.menu_font.render("API REAL INTEGRADA - EIF-207", True, (100, 255, 100))
        subtitle_rect = subtitle.get_rect(center=(WINDOW_WIDTH // 2, 220))
        screen.blit(subtitle, subtitle_rect)

        # Opciones del menú (más espaciadas por el tamaño mayor)
        start_y = 320
        for i, option in enumerate(self.main_options):
            color = (255, 255, 100) if i == self.selected else (255, 255, 255)
            text = self.menu_font.render(option, True, color)
            text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, start_y + i * 65))

            if i == self.selected:
                pygame.draw.rect(screen, (50, 50, 100),
                                 (text_rect.x - 20, text_rect.y - 5, text_rect.width + 40, text_rect.height + 10))

            screen.blit(text, text_rect)

        instructions = self.small_font.render("Usa ↑↓ para navegar, ENTER para seleccionar", True, (150, 150, 150))
        instructions_rect = instructions.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50))
        screen.blit(instructions, instructions_rect)

    def _draw_load_menu(self, screen):
        title = self.submenu_title_font.render("CARGAR PARTIDA", True, (255, 255, 255))
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 100))
        screen.blit(title, title_rect)

        start_y = 250
        slot_info = self.file_manager.get_save_info(1)

        if self.selected == 0:
            color = (255, 255, 100)
            bg_color = (50, 50, 100)
        elif slot_info:
            color = (255, 255, 255)
            bg_color = (30, 30, 50)
        else:
            color = (100, 100, 100)
            bg_color = (20, 20, 30)

        slot_rect = pygame.Rect(WINDOW_WIDTH // 2 - 300, start_y - 5, 600, 70)
        pygame.draw.rect(screen, bg_color, slot_rect)
        pygame.draw.rect(screen, color, slot_rect, 2)

        if slot_info:
            slot_text = f"Slot 1 - {slot_info.get('saved_at', 'Desconocido')[:19]}"
            progress_text = f"Progreso: {slot_info.get('completion_percentage', 0):.1f}%"
            city_text = slot_info.get('city_info', 'Ciudad desconocida')

            slot_label = self.submenu_font.render(slot_text, True, color)
            progress_label = self.submenu_small_font.render(progress_text, True, color)
            city_label = self.submenu_small_font.render(city_text, True, color)

            screen.blit(slot_label, (WINDOW_WIDTH // 2 - 280, start_y))
            screen.blit(progress_label, (WINDOW_WIDTH // 2 - 280, start_y + 25))
            screen.blit(city_label, (WINDOW_WIDTH // 2 - 280, start_y + 45))
        else:
            empty_text = "Slot 1 - Vacío"
            empty_label = self.submenu_font.render(empty_text, True, color)
            screen.blit(empty_label, (WINDOW_WIDTH // 2 - 280, start_y + 20))

        volver_color = (255, 255, 100) if self.selected == 1 else (255, 255, 255)
        volver_text = self.submenu_font.render("← Volver al menú principal (B)", True, volver_color)
        volver_rect = volver_text.get_rect(center=(WINDOW_WIDTH // 2, start_y + 120))

        if self.selected == 1:
            pygame.draw.rect(screen, (50, 50, 100),
                             (volver_rect.x - 20, volver_rect.y - 5, volver_rect.width + 40, volver_rect.height + 10))

        screen.blit(volver_text, volver_rect)
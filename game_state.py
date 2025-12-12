import pygame
import random
import math
from enum import Enum
from config import *
from entities import CelestialBody, BlackHole, PlayerCursor, FloatingText, Shockwave, Debris

class GameState(Enum):
    MENU = 0
    PLAYING = 1
    PAUSED = 2
    SUMMARY = 3
    PROGRESSION = 4
    TRANSITION_TO_SUMMARY = 5 # Nuevo estado de transición
    TRANSITION_TO_PLAY = 6    # Nuevo estado de transición
    TRANSITION_TO_SHOP = 7    # Transición a tienda
    TRANSITION_FROM_SHOP = 8  # Transición desde tienda

class GameManager:
    def __init__(self):
        self.state = GameState.PLAYING  # Empezamos directo en juego por ahora
        self.black_hole = BlackHole()
        self.cursor = PlayerCursor()
        self.bodies = []
        self.floating_texts = []
        self.shockwaves = []
        self.debris_list = []
        
        # Stats de la Run
        self.time_remaining = GAME_DURATION
        self.money_earned = 0 # Dinero acumulado en la run actual
        self.total_money = 0  # Dinero total (banco) para comprar mejoras
        self.bodies_destroyed = {level: 0 for level in MASS_COLORS.keys()}
        
        # Progreso del Agujero Negro
        self.current_xp = 0
        self.xp_to_next_level = XP_BASE_REQUIREMENT
        
        # Lógica de Spawn
        self.spawn_timer = 0
        self.bodies_per_level = 10 # Cantidad fija de cuerpos por nivel
        self.spawned_count = 0
        
        # Lógica de Daño
        self.damage_tick_timer = 0
        
        # Estado de Mejoras (Nivel actual de cada mejora)
        self.upgrades = {key: 0 for key in UPGRADES.keys()}
        
        # Valores actuales (cacheados para rendimiento)
        self.current_damage = BASE_DAMAGE
        self.current_cursor_radius = CURSOR_RADIUS
        self.time_refund_chance = 0.0 # Probabilidad de recuperar tiempo
        self.current_spawn_limit = self.bodies_per_level
        
        # Nuevas Stats
        self.mass_bonus = 0
        self.resonance_pct = 0.0
        self.fission_chance = 0.0
        
        # Variables de Transición
        self.shop_transition_radius = 0
        self.max_transition_radius = int((SCREEN_WIDTH**2 + SCREEN_HEIGHT**2)**0.5 / 2) + 50
        self.transition_speed = self.max_transition_radius / (FPS * 0.5) # 0.5 segundos
        
        # Zoom
        self.current_zoom = 1.0

    def get_upgrade_cost(self, key):
        """Calcula el coste del siguiente nivel de una mejora"""
        data = UPGRADES[key]
        level = self.upgrades[key]
        return int(data["base_cost"] * (data["cost_multiplier"] ** level))

    def buy_upgrade(self, key):
        """Intenta comprar una mejora"""
        data = UPGRADES[key]
        current_level = self.upgrades[key]
        
        # Verificar nivel máximo si existe
        if "max_level" in data and current_level >= data["max_level"]:
            return False
            
        cost = self.get_upgrade_cost(key)
        if self.total_money >= cost:
            self.total_money -= cost
            self.upgrades[key] += 1
            self._recalculate_stats()
            return True
        return False

    def _recalculate_stats(self):
        """Actualiza los valores del juego basados en las mejoras"""
        # Daño
        dmg_data = UPGRADES["damage"]
        self.current_damage = dmg_data["base_value"] + (self.upgrades["damage"] * dmg_data["increment"])
        
        # Radio
        rad_data = UPGRADES["radius"]
        self.current_cursor_radius = rad_data["base_value"] + (self.upgrades["radius"] * rad_data["increment"])
        self.cursor.radius = self.current_cursor_radius # Actualizar cursor visual
        
        # Duración (Probabilidad de reembolso)
        dur_data = UPGRADES["duration"]
        self.time_refund_chance = dur_data["base_value"] + (self.upgrades["duration"] * dur_data["increment"])
        
        # Spawn
        spw_data = UPGRADES["spawn_rate"]
        self.current_spawn_limit = spw_data["base_value"] + (self.upgrades["spawn_rate"] * spw_data["increment"])
        self.bodies_per_level = self.current_spawn_limit
        
        # Masa (Nivel extra)
        mass_data = UPGRADES["mass"]
        self.mass_bonus = mass_data["base_value"] + (self.upgrades["mass"] * mass_data["increment"])
        
        # Resonancia (Recuperar oleada)
        res_data = UPGRADES["resonance"]
        self.resonance_pct = res_data["base_value"] + (self.upgrades["resonance"] * res_data["increment"])
        
        # Fisión (Dividir)
        fis_data = UPGRADES["fission"]
        self.fission_chance = fis_data["base_value"] + (self.upgrades["fission"] * fis_data["increment"])

    def update(self):
        if self.state == GameState.PLAYING:
            self._update_playing()
        elif self.state == GameState.TRANSITION_TO_SUMMARY:
            self._update_transition_summary()
        elif self.state == GameState.TRANSITION_TO_PLAY:
            self._update_transition_play()
        elif self.state == GameState.PROGRESSION:
            self._update_progression()
        elif self.state == GameState.TRANSITION_TO_SHOP:
            self._update_transition_to_shop()
        elif self.state == GameState.TRANSITION_FROM_SHOP:
            self._update_transition_from_shop()
        elif self.state == GameState.PAUSED:
            pass # No actualizamos posiciones
        
        # El cursor siempre se actualiza para poder navegar menús
        self.cursor.update()

    def _update_transition_to_shop(self):
        self.shop_transition_radius += self.transition_speed
        if self.shop_transition_radius >= self.max_transition_radius:
            self.shop_transition_radius = self.max_transition_radius
            self.state = GameState.PROGRESSION

    def _update_transition_from_shop(self):
        self.shop_transition_radius -= self.transition_speed
        if self.shop_transition_radius <= 0:
            self.shop_transition_radius = 0
            self.state = GameState.SUMMARY

    def _update_progression(self):
        # Aquí gestionaremos los clicks en el menú radial
        # Por ahora solo necesitamos que el cursor se mueva
        pass

    def _get_visible_nodes_positions(self):
        """Calcula las posiciones de todos los nodos visibles en el árbol de mejoras"""
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        
        branches = {
            "asteroid": {"angle": math.pi},
            "blackhole": {"angle": 0},
            "unique": {"angle": -math.pi/2}
        }
        
        grouped_upgrades = {"asteroid": [], "blackhole": [], "unique": []}
        for key, data in UPGRADES.items():
            cat = data.get("category", "asteroid")
            if cat in grouped_upgrades:
                grouped_upgrades[cat].append(key)
                
        node_positions = {}
        spacing = 80
        branch_start_dist = 100
        
        for cat, keys in grouped_upgrades.items():
            branch_angle = branches[cat]["angle"]
            start_x = center_x + branch_start_dist * math.cos(branch_angle)
            start_y = center_y + branch_start_dist * math.sin(branch_angle)
            
            u_x = math.cos(branch_angle)
            u_y = math.sin(branch_angle)
            v_x = math.cos(branch_angle + math.pi/2)
            v_y = math.sin(branch_angle + math.pi/2)
            
            for key in keys:
                data = UPGRADES[key]
                parent_key = data.get("parent")
                
                # Visibilidad
                is_visible = True
                if parent_key:
                    # Si tiene padre, solo es visible si el padre está comprado (nivel > 0)
                    if self.upgrades.get(parent_key, 0) == 0:
                        is_visible = False
                
                if not is_visible:
                    continue
                    
                col, row = data.get("tree_pos", (0, 0))
                spacing_y = spacing * 0.8
                
                x = int(start_x + (col * spacing * u_x) + (row * spacing_y * v_x))
                y = int(start_y + (col * spacing * u_y) + (row * spacing_y * v_y))
                
                node_positions[key] = (x, y)
                
        return node_positions

    def handle_input(self, event):
        """Maneja inputs específicos que no son continuos (como clicks)"""
        if self.state == GameState.SUMMARY and event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Click izquierdo
                restart_rect, shop_rect = self._get_summary_buttons_rects()
                if restart_rect.collidepoint(event.pos):
                    self.reset_run()
                elif shop_rect.collidepoint(event.pos):
                    self.state = GameState.TRANSITION_TO_SHOP

        if self.state == GameState.PROGRESSION and event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Click izquierdo
                mx, my = event.pos
                
                # Usar la misma lógica de posicionamiento que el dibujado
                node_positions = self._get_visible_nodes_positions()
                
                # Verificar clicks en nodos
                for key, (x, y) in node_positions.items():
                    # Radio de click un poco más generoso que el visual (15 -> 25)
                    if math.sqrt((mx - x)**2 + (my - y)**2) < 25:
                        if self.buy_upgrade(key):
                            # Feedback sonoro o visual podría ir aquí
                            pass
                            
                # Botón Volver (Centro)
                center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
                if math.sqrt((mx - center_x)**2 + (my - center_y)**2) < 40:
                    self.state = GameState.TRANSITION_FROM_SHOP

    def _update_transition_summary(self):
        # El agujero negro crece
        self.black_hole.update()
        
        # Seguir actualizando textos flotantes para que terminen su animación
        for text in self.floating_texts:
            text.update()
        self.floating_texts = [t for t in self.floating_texts if t.life > 0]
        
        # Si ya cubre la pantalla (radio > diagonal/2 aprox + margen)
        diagonal = (SCREEN_WIDTH**2 + SCREEN_HEIGHT**2)**0.5
        if self.black_hole.radius >= diagonal:
            self.state = GameState.SUMMARY
            self.floating_texts = [] # Limpiar textos restantes al llegar al resumen
            self.bodies = []         # Limpiar cuerpos
            self.debris_list = []    # Limpiar debris
            self.shockwaves = []     # Limpiar ondas

    def _update_transition_play(self):
        # El agujero negro decrece
        self.black_hole.update()
        
        # Si ya llegó al tamaño base
        if abs(self.black_hole.radius - self.black_hole.target_radius) < 1:
            self.state = GameState.PLAYING

    def _update_playing(self):
        # 1. Timer de la Run
        self.time_remaining -= 1 / FPS
        if self.time_remaining <= 0:
            # Iniciar transición a Summary
            self.state = GameState.TRANSITION_TO_SUMMARY
            self.black_hole.expand_to_screen()
            return

        # 2. Spawner (Por oleadas/Nivel)
        # Si hay menos cuerpos de los que debería haber para este nivel, spawneamos
        # MODIFICADO: Solo spawneamos si NO hemos alcanzado el límite total de spawns de esta oleada/run
        # Por ahora, el límite es bodies_per_level. Si los matas todos, se acabó hasta reiniciar.
        
        if self.spawned_count < self.bodies_per_level:
            self.spawn_timer += 1
            if self.spawn_timer >= 2: # Spawn MUY rápido (cada 2 frames)
                self.spawn_timer = 0
                
                # Lógica de nivel de cuerpo
                # El nivel máximo está determinado por la mejora de Masa (Nucleosíntesis)
                # Nivel base 1 + bonus de masa
                max_unlocked_level = min(6, 1 + int(self.mass_bonus))
                
                # Spawneamos un nivel aleatorio entre 1 y el máximo desbloqueado
                level = random.randint(1, max_unlocked_level)
                
                self.bodies.append(CelestialBody(level=level))
                self.spawned_count += 1

        # 3. Actualizar Entidades
        self.black_hole.update()
        
        # Actualizar Zoom Suave
        target_zoom = 1.0 / (1.0 + (self.black_hole.level - 1) * 0.1)
        if abs(self.current_zoom - target_zoom) > 0.001:
            # Lerp suave (5% por frame para que sea muy fluido)
            self.current_zoom += (target_zoom - self.current_zoom) * 0.05
        else:
            self.current_zoom = target_zoom
            
        for body in self.bodies:
            body.update()
            
        # Actualizar efectos visuales
        for text in self.floating_texts:
            text.update()
        self.floating_texts = [t for t in self.floating_texts if t.life > 0]
        
        for wave in self.shockwaves:
            wave.update()
        self.shockwaves = [w for w in self.shockwaves if w.active]

        # Actualizar Debris
        for debris in self.debris_list:
            debris.update()
        # Eliminar debris que ha llegado al centro (radio < radio agujero negro)
        self.debris_list = [d for d in self.debris_list if d.orbit_radius > self.black_hole.radius]

        # 4. Lógica de Daño (Optimización Distancia Cuadrada)
        self.damage_tick_timer += 1
        if self.damage_tick_timer >= DAMAGE_TICK_RATE:
            self.damage_tick_timer = 0
            self._apply_damage()

    def _apply_damage(self):
        bodies_to_remove = []
        
        # Transformar coordenadas del mouse (pantalla) a mundo para la colisión
        # Si hay zoom out (zoom < 1), el mundo es más grande que la pantalla
        zoom = self.get_zoom()
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        
        # mouse_world = center + (mouse_screen - center) / zoom
        mouse_world_x = center_x + (self.cursor.x - center_x) / zoom
        mouse_world_y = center_y + (self.cursor.y - center_y) / zoom

        for body in self.bodies:
            # Distancia al cuadrado entre cursor (en mundo) y cuerpo (en mundo)
            dx = body.x - mouse_world_x
            dy = body.y - mouse_world_y
            dist_sq = dx*dx + dy*dy
            
            # Colisión Círculo-Círculo: Detectar si se tocan
            # Sumamos el radio del cursor y el radio aproximado del cuerpo
            # Esto permite dañar al cuerpo con solo tocar su borde
            collision_radius = self.cursor.radius + body.current_size
            
            if dist_sq < collision_radius * collision_radius:
                # Está dentro del área (o tocándola)
                destroyed, actual_damage = body.take_damage(self.current_damage)
                
                # Feedback visual de daño (mostramos el daño real, redondeado a 1 decimal si es pequeño)
                # Eliminamos la probabilidad para mostrar TODOS los ticks de daño
                dmg_str = f"{actual_damage:.1f}" if actual_damage < 10 else str(int(actual_damage))
                self.floating_texts.append(FloatingText(body.x, body.y, dmg_str))
                
                if destroyed:
                    bodies_to_remove.append(body)
                    self.money_earned += body.value
                    self.total_money += body.value # Sumar al banco global
                    self.bodies_destroyed[body.level] += 1
                    self._add_xp(body.mass * 10)
                    
                    # Feedback visual de dinero (Verde)
                    # Offset vertical para que no se solape con el daño
                    self.floating_texts.append(FloatingText(body.x, body.y - 30, f"+${body.value}", COLOR_MONEY_TEXT))
                    
                    # Probabilidad de Reembolso de Tiempo
                    if random.random() < self.time_refund_chance:
                        self.time_remaining += 1.0
                        # Feedback visual de tiempo (Azul)
                        self.floating_texts.append(FloatingText(body.x, body.y - 50, "+1s", COLOR_TIME_TEXT))
                    
                    # Probabilidad de Fisión (Dividir)
                    if random.random() < self.fission_chance:
                        # Generar nuevo cuerpo del mismo nivel o superior (+1)
                        # Pero limitado por el nivel máximo desbloqueado
                        max_unlocked_level = min(6, 1 + int(self.mass_bonus))
                        new_level = min(max_unlocked_level, body.level + random.randint(0, 1))
                        
                        # Crear nuevo cuerpo (ya se inicializa con posición aleatoria válida)
                        new_body = CelestialBody(level=new_level)
                        new_body.update() # Para setear x,y iniciales
                        
                        self.bodies.append(new_body)
                        # No incrementamos spawned_count para que sea un "bonus" real
                        
                        # El texto aparece donde murió el padre
                        self.floating_texts.append(FloatingText(body.x, body.y - 70, "SPLIT!", COLOR_XP_BAR_FILL))

                    # Generar Debris (Escalado con tamaño)
                    # Más debris para cuerpos más grandes
                    num_debris = int(random.randint(3, 6) * body.size_multiplier)
                    for _ in range(num_debris):
                        self.debris_list.append(Debris(body.x, body.y, body.color, body.orbit_radius, body.angle))

        # Eliminar cuerpos destruidos
        for body in bodies_to_remove:
            if body in self.bodies:
                self.bodies.remove(body)
            # Aquí podríamos generar Debris en el futuro

    def _add_xp(self, amount):
        self.current_xp += amount
        if self.current_xp >= self.xp_to_next_level:
            self.current_xp -= self.xp_to_next_level
            self.xp_to_next_level = int(self.xp_to_next_level * XP_SCALING_FACTOR)
            self.black_hole.level_up()
            # Crear onda expansiva
            self.shockwaves.append(Shockwave(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            
            # REFILL AUTOMÁTICO AL SUBIR DE NIVEL
            # Solo si se tiene la mejora de Resonancia
            if self.resonance_pct > 0:
                # Reiniciamos el contador de spawns para que salga una nueva oleada completa
                self.spawned_count = 0
                self.floating_texts.append(FloatingText(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 100, "RESONANCE!", COLOR_XP_BAR_FILL))

    def get_zoom(self):
        """Devuelve el nivel de zoom actual (suavizado)"""
        return self.current_zoom

    def draw(self, surface):
        # Fondo
        surface.fill(COLOR_BACKGROUND)
        
        # Calcular Zoom
        zoom = self.get_zoom()
        
        # Determinar orden de dibujado
        # Si el agujero negro se está expandiendo o ya cubrió la pantalla, 
        # debe dibujarse ENCIMA de los cuerpos para "tragárselos" visualmente.
        # También en las transiciones de tienda, el agujero negro (Summary) está debajo
        draw_black_hole_on_top = self.state in [GameState.TRANSITION_TO_SUMMARY, GameState.SUMMARY, GameState.TRANSITION_TO_SHOP, GameState.TRANSITION_FROM_SHOP]
        
        if not draw_black_hole_on_top:
            self.black_hole.draw(surface, zoom)
        
        # Dibujar Debris (detrás de los cuerpos pero delante del agujero si es normal)
        for debris in self.debris_list:
            debris.draw(surface, zoom)
        
        for body in self.bodies:
            body.draw(surface, zoom)
            
        if draw_black_hole_on_top:
            # En transiciones a pantalla completa, ignoramos el zoom para que cubra todo bien
            if self.state == GameState.TRANSITION_TO_SUMMARY:
                self.black_hole.draw(surface, 1.0)
            else:
                self.black_hole.draw(surface, zoom)
            
        # Efectos visuales (detrás del cursor)
        for wave in self.shockwaves:
            wave.draw(surface, zoom)
            
        for text in self.floating_texts:
            text.draw(surface, zoom)
            
        # UI Básica
        self._draw_ui(surface)
        
        # Pantallas especiales
        if self.state == GameState.SUMMARY:
            self._draw_summary(surface)
        elif self.state == GameState.PROGRESSION:
            self._draw_progression(surface)
        elif self.state == GameState.TRANSITION_TO_SHOP or self.state == GameState.TRANSITION_FROM_SHOP:
            # Dibujar Summary debajo
            self._draw_summary(surface)
            # Dibujar círculo de transición
            pygame.draw.circle(surface, COLOR_BACKGROUND, (SCREEN_WIDTH//2, SCREEN_HEIGHT//2), int(self.shop_transition_radius))
        
        if self.state == GameState.PAUSED:
            self._draw_pause_overlay(surface)
            
        # Dibujar Cursor (siempre encima de todo, incluso UI)
        # El cursor recibe el zoom para escalar su radio visualmente
        self.cursor.draw(surface, zoom)

    def end_run_from_pause(self):
        """Termina la run desde el menú de pausa"""
        self.state = GameState.TRANSITION_TO_SUMMARY
        self.black_hole.expand_to_screen()

    def _draw_pause_overlay(self, surface):
        # Efecto VHS: Scanlines y Ruido
        # Usamos una superficie temporal con alpha
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        
        # 1. Oscurecer fondo
        overlay.fill((0, 0, 0, 100))
        
        # 2. Scanlines (Líneas horizontales)
        for y in range(0, SCREEN_HEIGHT, 4):
            pygame.draw.line(overlay, (0, 0, 0, 50), (0, y), (SCREEN_WIDTH, y))
            
        # 3. Ruido estático (Puntos aleatorios)
        for _ in range(500):
            x = random.randint(0, SCREEN_WIDTH - 1)
            y = random.randint(0, SCREEN_HEIGHT - 1)
            # Ruido blanco/gris con transparencia
            overlay.set_at((x, y), (200, 200, 200, 50))
            
        surface.blit(overlay, (0, 0))
        
        # Texto "PAUSA" parpadeante
        if (pygame.time.get_ticks() // 500) % 2 == 0:
            font_large = pygame.font.SysFont("Arial", 60, bold=True)
            text = font_large.render("PAUSA", True, COLOR_TEXT)
            # Efecto de sombra/glitch simple
            surface.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2 + 2, SCREEN_HEIGHT//2 - 100 + 2))
            surface.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, SCREEN_HEIGHT//2 - 100))
            
        # Opciones del menú
        font_small = pygame.font.SysFont("Arial", 30)
        
        resume_text = font_small.render("ESC - Reanudar", True, COLOR_TEXT)
        end_text = font_small.render("Q - Terminar Run", True, COLOR_TEXT)
        
        # Centrar textos
        surface.blit(resume_text, (SCREEN_WIDTH//2 - resume_text.get_width()//2, SCREEN_HEIGHT//2))
        surface.blit(end_text, (SCREEN_WIDTH//2 - end_text.get_width()//2, SCREEN_HEIGHT//2 + 50))

    def _draw_ui(self, surface):
        font = pygame.font.SysFont("Arial", 24)
        
        if self.state == GameState.PLAYING:
            # Barra de XP (Arriba Centro)
            bar_width = 400
            bar_height = 20
            bar_x = (SCREEN_WIDTH - bar_width) // 2
            bar_y = 10
            
            # Fondo barra
            pygame.draw.rect(surface, COLOR_XP_BAR_BG, (bar_x, bar_y, bar_width, bar_height), border_radius=10)
            
            # Relleno barra
            fill_pct = min(1, self.current_xp / self.xp_to_next_level)
            fill_width = int(bar_width * fill_pct)
            if fill_width > 0:
                pygame.draw.rect(surface, COLOR_XP_BAR_FILL, (bar_x, bar_y, fill_width, bar_height), border_radius=10)
            
            # Texto Nivel
            level_text = font.render(f"Nivel {self.black_hole.level}", True, COLOR_TEXT)
            surface.blit(level_text, (bar_x + bar_width + 10, bar_y - 2))

            # Tiempo
            time_text = font.render(f"Tiempo: {int(self.time_remaining)}s", True, COLOR_TEXT)
            surface.blit(time_text, (20, 20))
            
            # Dinero
            money_text = font.render(f"Dinero: ${self.money_earned}", True, COLOR_TEXT)
            surface.blit(money_text, (20, 50))

    def _get_summary_buttons_rects(self):
        """Calcula los rectángulos de los botones de la pantalla de resumen"""
        button_width = 220
        button_height = 50
        center_x = SCREEN_WIDTH // 2
        center_y = SCREEN_HEIGHT // 2
        
        # Bajamos los botones para dejar espacio a las estadísticas
        restart_rect = pygame.Rect(center_x - button_width // 2, center_y + 160, button_width, button_height)
        shop_rect = pygame.Rect(center_x - button_width // 2, center_y + 230, button_width, button_height)
        
        return restart_rect, shop_rect

    def _draw_summary(self, surface):
        font = pygame.font.SysFont("Arial", 24)
        font_btn = pygame.font.SysFont("Arial", 24, bold=True)
        font_stats = pygame.font.SysFont("Arial", 20)
        
        # Pantalla de Resumen (Fondo Negro = Agujero Negro Gigante)
        # No necesitamos overlay porque el agujero negro ya cubre todo
        
        # Usamos color invertido (claro)
        # Subimos el título y los dineros
        title = font.render("¡RUN TERMINADA!", True, COLOR_TEXT_INVERTED)
        score = font.render(f"Ganancias: ${self.money_earned}", True, COLOR_TEXT_INVERTED)
        total = font.render(f"Banco Total: ${self.total_money}", True, COLOR_MONEY_TEXT)
        
        surface.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, SCREEN_HEIGHT//2 - 200))
        surface.blit(score, (SCREEN_WIDTH//2 - score.get_width()//2, SCREEN_HEIGHT//2 - 160))
        surface.blit(total, (SCREEN_WIDTH//2 - total.get_width()//2, SCREEN_HEIGHT//2 - 120))
        
        # --- Estadísticas de Cuerpos Destruidos ---
        stats_start_y = SCREEN_HEIGHT // 2 - 70
        line_height = 25
        
        # Título de sección
        stats_title = font_stats.render("Cuerpos Absorbidos:", True, (200, 200, 200))
        surface.blit(stats_title, (SCREEN_WIDTH//2 - stats_title.get_width()//2, stats_start_y))
        
        current_y = stats_start_y + 30
        
        # Iterar sobre los niveles (ordenados)
        for level in sorted(self.bodies_destroyed.keys()):
            count = self.bodies_destroyed[level]
            if count > 0:
                # Usar el color del nivel para el texto
                color = MASS_COLORS.get(level, COLOR_TEXT_INVERTED)
                
                # Texto: "Asteroides Nivel X: Y"
                text_str = f"Asteroides Nivel {level}: {count}"
                text_surf = font_stats.render(text_str, True, color)
                
                surface.blit(text_surf, (SCREEN_WIDTH//2 - text_surf.get_width()//2, current_y))
                current_y += line_height
        
        # Botones
        restart_rect, shop_rect = self._get_summary_buttons_rects()
        mx, my = pygame.mouse.get_pos()
        
        # Botón Reiniciar
        is_hover_restart = restart_rect.collidepoint(mx, my)
        color_restart_bg = (60, 60, 60) if not is_hover_restart else (90, 90, 90)
        pygame.draw.rect(surface, color_restart_bg, restart_rect, border_radius=12)
        pygame.draw.rect(surface, COLOR_TEXT_INVERTED, restart_rect, width=2, border_radius=12)
        
        restart_text = font_btn.render("Repetir (R)", True, COLOR_TEXT_INVERTED)
        surface.blit(restart_text, (restart_rect.centerx - restart_text.get_width()//2, restart_rect.centery - restart_text.get_height()//2))
        
        # Botón Tienda
        is_hover_shop = shop_rect.collidepoint(mx, my)
        color_shop_bg = (40, 20, 60) if not is_hover_shop else (70, 40, 100) # Morado oscuro
        pygame.draw.rect(surface, color_shop_bg, shop_rect, border_radius=12)
        pygame.draw.rect(surface, COLOR_XP_BAR_FILL, shop_rect, width=2, border_radius=12)
        
        shop_text = font_btn.render("Mejoras (M)", True, COLOR_XP_BAR_FILL)
        surface.blit(shop_text, (shop_rect.centerx - shop_text.get_width()//2, shop_rect.centery - shop_text.get_height()//2))

    def _draw_progression(self, surface):
        # Fondo Beige (cubriendo el agujero negro gigante)
        surface.fill(COLOR_BACKGROUND)
        
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        
        font_title = pygame.font.SysFont("Arial", 20, bold=True)
        font_desc = pygame.font.SysFont("Arial", 14)
        font_cost = pygame.font.SysFont("Arial", 16, bold=True)
        
        node_radius = 15
        
        mx, my = pygame.mouse.get_pos()
        
        hovered_node = None
        
        # Obtener posiciones de nodos visibles
        node_positions = self._get_visible_nodes_positions()
        
        # Dibujar conexiones (Líneas)
        # Necesitamos saber dónde empieza cada rama para conectar los nodos raíz
        branches = {
            "asteroid": {"angle": math.pi},
            "blackhole": {"angle": 0},
            "unique": {"angle": -math.pi/2}
        }
        branch_start_dist = 100
        
        for key, (x, y) in node_positions.items():
            data = UPGRADES[key]
            parent_key = data.get("parent")
            
            if parent_key and parent_key in node_positions:
                # Conectar con padre
                parent_pos = node_positions[parent_key]
                pygame.draw.line(surface, (100, 100, 100), parent_pos, (x, y), 2)
            elif not parent_key:
                # Es nodo raíz, conectar con el inicio de su rama
                cat = data.get("category", "asteroid")
                angle = branches[cat]["angle"]
                start_x = center_x + branch_start_dist * math.cos(angle)
                start_y = center_y + branch_start_dist * math.sin(angle)
                pygame.draw.line(surface, (100, 100, 100), (start_x, start_y), (x, y), 2)

        # Dibujar nodos (en segunda pasada para que queden encima de las líneas)
        for key, pos in node_positions.items():
            x, y = pos
            data = UPGRADES[key]
            
            # Estado
            level = self.upgrades[key]
            cost = self.get_upgrade_cost(key)
            can_buy = self.total_money >= cost
            is_maxed = "max_level" in data and level >= data["max_level"]
            
            # Interacción Mouse
            hover = math.sqrt((mx - x)**2 + (my - y)**2) < node_radius + 5
            
            if hover:
                hovered_node = {
                    "key": key, "data": data, "level": level, 
                    "cost": cost, "can_buy": can_buy, "is_maxed": is_maxed,
                    "x": x, "y": y
                }
            
            # Color del nodo
            if is_maxed:
                color = (100, 200, 100) # Verde
            elif can_buy:
                color = COLOR_XP_BAR_FILL # Azul
            else:
                color = (100, 100, 100) # Gris
            
            if hover: color = (min(255, color[0]+50), min(255, color[1]+50), min(255, color[2]+50))
            
            # Dibujar círculo
            pygame.draw.circle(surface, color, (x, y), node_radius)
            pygame.draw.circle(surface, COLOR_TEXT, (x, y), node_radius, 1) # Borde oscuro
            
            # Nivel dentro
            if node_radius > 10:
                icon_text = font_desc.render(str(level), True, COLOR_TEXT)
                surface.blit(icon_text, (x - icon_text.get_width()//2, y - icon_text.get_height()//2))

        # Botón Central (Volver)
        center_radius = 40 # Aumentado de 30
        hover_center = math.sqrt((mx - center_x)**2 + (my - center_y)**2) < center_radius
        center_color = (200, 200, 200) if hover_center else (150, 150, 150)
        pygame.draw.circle(surface, center_color, (center_x, center_y), center_radius)
        pygame.draw.circle(surface, COLOR_TEXT, (center_x, center_y), center_radius, 2)
        
        back_text = font_desc.render("BACK", True, COLOR_TEXT)
        surface.blit(back_text, (center_x - back_text.get_width()//2, center_y - back_text.get_height()//2))
        
        # Mostrar Dinero Total arriba
        money_surf = font_title.render(f"BANCO: ${self.total_money}", True, COLOR_MONEY_TEXT) # Verde oscuro se ve bien
        surface.blit(money_surf, (center_x - money_surf.get_width()//2, 50))
        
        # Etiquetas de Ramas (Colores más oscuros para contraste)
        # Ajustadas posiciones para el nuevo espaciado
        lbl_ast = font_desc.render("ASTEROIDES", True, (50, 100, 150))
        surface.blit(lbl_ast, (center_x - 250, center_y - 30))
        
        lbl_bh = font_desc.render("AGUJERO NEGRO", True, (100, 50, 150))
        surface.blit(lbl_bh, (center_x + 150, center_y - 30))
        
        lbl_uniq = font_desc.render("ÚNICAS", True, (150, 150, 50))
        surface.blit(lbl_uniq, (center_x - lbl_uniq.get_width()//2, center_y - 150))

        # DIBUJAR TOOLTIP AL FINAL (ENCIMA DE TODO)
        if hovered_node:
            data = hovered_node["data"]
            
            # Contenido del tooltip
            lines = [
                (data["name"], font_title, COLOR_TEXT_INVERTED),
                (data["description"], font_desc, (200, 200, 200)),
            ]
            
            if hovered_node["is_maxed"]:
                lines.append(("MAX LEVEL", font_cost, (100, 255, 100)))
            else:
                cost_color = COLOR_MONEY_TEXT if hovered_node["can_buy"] else (255, 100, 100)
                lines.append((f"Cost: ${hovered_node['cost']}", font_cost, cost_color))
                
                # Mostrar incremento
                current_val = data["base_value"] + (hovered_node["level"] * data["increment"])
                next_val = current_val + data["increment"]
                if isinstance(current_val, float):
                    val_str = f"{current_val:.2f} -> {next_val:.2f}"
                else:
                    val_str = f"{current_val} -> {next_val}"
                lines.append((f"Effect: {val_str}", font_desc, (150, 150, 255)))

            # Calcular dimensiones
            box_width = 220
            box_height = 10 + len(lines) * 25
            
            # Posición
            bx = mx + 15
            by = my + 15
            
            if bx + box_width > SCREEN_WIDTH: bx = mx - box_width - 15
            if by + box_height > SCREEN_HEIGHT: by = my - box_height - 15
            
            # Fondo oscuro para el tooltip (para que el texto claro se lea)
            s = pygame.Surface((box_width, box_height))
            s.set_alpha(230)
            s.fill((20, 20, 30))
            surface.blit(s, (bx, by))
            
            pygame.draw.rect(surface, (100, 100, 150), (bx, by, box_width, box_height), 1)
            
            curr_y = by + 10
            for text, font_obj, color in lines:
                surf = font_obj.render(text, True, color)
                surface.blit(surf, (bx + 10, curr_y))
                curr_y += 25

    def reset_run(self):
        self.time_remaining = GAME_DURATION
        self.money_earned = 0 # Resetear dinero de la run (el total se mantiene)
        
        self.bodies = []
        self.bodies_destroyed = {level: 0 for level in MASS_COLORS.keys()}
        
        # Iniciar transición de vuelta al juego
        self.state = GameState.TRANSITION_TO_PLAY
        
        # Resetear progreso del agujero negro (pero manteniendo tamaño gigante para la animación)
        self.black_hole.shrink_to_game() 
        
        self.current_xp = 0
        self.xp_to_next_level = XP_BASE_REQUIREMENT
        self.shockwaves = []
        self.floating_texts = []
        self.debris_list = []
        
        # Resetear spawns
        self.spawned_count = 0

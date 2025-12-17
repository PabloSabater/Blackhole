import pygame
import random
import math
from enum import Enum
from config import *
from entities import CelestialBody, Asteroid, Planet, BlackHole, PlayerCursor, FloatingText, Shockwave, Debris, Starfield

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
    TRANSITION_FROM_MENU = 9  # Transición desde menú
    TRANSITION_TO_MENU = 10   # Transición hacia menú

class GameManager:
    def __init__(self):
        self.state = GameState.MENU  # Empezamos en el Menú Principal
        self.black_hole = BlackHole()
        self.cursor = PlayerCursor()
        self.bodies = []
        self.floating_texts = []
        self.shockwaves = []
        self.debris_list = []
        self.starfield = Starfield() # Fondo dinámico para el menú de mejoras
        
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
        
        # Nuevas Stats (Asteroides)
        self.asteroid_mass_bonus = 0
        self.asteroid_fission_chance = 0.0
        
        # Nuevas Stats (Globales)
        self.resonance_pct = 0.0
        self.critical_chance = 0.0
        self.critical_damage_multiplier = 1.5
        
        # Nuevas Stats (Planetas)
        self.planets_unlocked = False
        self.planet_mass_bonus = 0
        self.planet_spawn_rate = 0.0
        self.planet_defense_reduction = 0.0
        
        # Variables de Transición
        self.shop_transition_radius = 0
        self.max_transition_radius = int((SCREEN_WIDTH**2 + SCREEN_HEIGHT**2)**0.5 / 2) + 50
        self.transition_speed = self.max_transition_radius / (FPS * 0.5) # 0.5 segundos
        self.menu_anim_offset = 0 # Animación de salida del menú
        self.menu_time = 0 # Timer para animaciones del menú
        self.nodes_anim_progress = 0.0 # 0.0 (Invisible) -> 1.0 (Visible)
        
        # Zoom
        self.current_zoom = 1.0

        # --- Optimización: Fuentes Precargadas ---
        self.font_ui = pygame.font.SysFont("Arial", 24)
        self.font_ui_large = pygame.font.SysFont("Arial", 60, bold=True)
        self.font_ui_small = pygame.font.SysFont("Arial", 30)
        self.font_btn = pygame.font.SysFont("Arial", 24, bold=True)
        self.font_stats = pygame.font.SysFont("Arial", 20)
        self.font_title = pygame.font.SysFont("Arial", 20, bold=True)
        self.font_desc = pygame.font.SysFont("Arial", 14)
        self.font_cost = pygame.font.SysFont("Arial", 16, bold=True)

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
        self.asteroid_mass_bonus = mass_data["base_value"] + (self.upgrades["mass"] * mass_data["increment"])
        
        # Resonancia (Recuperar oleada)
        res_data = UPGRADES["resonance"]
        self.resonance_pct = res_data["base_value"] + (self.upgrades["resonance"] * res_data["increment"])
        
        # Fisión (Dividir)
        fis_data = UPGRADES["fission"]
        # Críticos
        crit_chance_data = UPGRADES["critical_chance"]
        self.critical_chance = crit_chance_data["base_value"] + (self.upgrades["critical_chance"] * crit_chance_data["increment"])
        
        crit_dmg_data = UPGRADES["critical_damage"]
        self.critical_damage_multiplier = crit_dmg_data["base_value"] + (self.upgrades["critical_damage"] * crit_dmg_data["increment"])

        # Asteroid Stats
        fis_data = UPGRADES["fission"]
        self.asteroid_fission_chance = fis_data["base_value"] + (self.upgrades["fission"] * fis_data["increment"])
        
        # Planet Stats
        self.planets_unlocked = self.upgrades.get("planet_unlock", 0) > 0
        
        pmass_data = UPGRADES["planet_mass"]
        self.planet_mass_bonus = pmass_data["base_value"] + (self.upgrades["planet_mass"] * pmass_data["increment"])
        # self.planets_unlocked = self.upgrades.get("planet_unlock", 0) > 0
        # ...

    def update(self):
        if self.state == GameState.MENU:
            self._update_menu()
        elif self.state == GameState.TRANSITION_FROM_MENU:
            self._update_transition_from_menu()
        elif self.state == GameState.TRANSITION_TO_MENU:
            self._update_transition_to_menu()
        elif self.state == GameState.PLAYING:
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

    def _update_menu(self):
        # Solo actualizamos el agujero negro para que pulse
        self.black_hole.update()

    def _update_transition_from_menu(self):
        self.black_hole.update()
        # Animación: Aumentar offset
        self.menu_anim_offset += 15 # Velocidad de animación
        
        # Si ya salieron de pantalla (aprox 400px)
        if self.menu_anim_offset > 400:
            self.state = GameState.PLAYING
            self.menu_anim_offset = 0

    def _update_transition_to_menu(self):
        self.black_hole.update()
        # Animación: Disminuir offset
        self.menu_anim_offset -= 15
        
        if self.menu_anim_offset <= 0:
            self.menu_anim_offset = 0
            self.state = GameState.MENU

    def _update_transition_to_shop(self):
        # El agujero negro se encoge hasta el tamaño del botón central
        self.black_hole.target_radius = 25 # Tamaño del botón central (Reducido de 40)
        self.black_hole.anim_speed = 15.0 # Velocidad rápida
        self.black_hole.update()
        
        # Actualizar implosión de estrellas
        self.starfield.update()
        
        # Si ya llegó al tamaño objetivo
        if abs(self.black_hole.radius - self.black_hole.target_radius) < 1:
            self.black_hole.radius = self.black_hole.target_radius
            self.state = GameState.PROGRESSION

    def _update_transition_from_shop(self):
        # Esta transición ya no se usa para volver al Summary, 
        # sino que el botón central inicia el juego (TRANSITION_TO_PLAY)
        pass

    def _update_progression(self):
        # El agujero negro sigue pulsando en el centro
        self.black_hole.update()
        # Actualizar fondo de estrellas
        self.starfield.update()

    def _get_visible_nodes_positions(self):
        """Calcula las posiciones de todos los nodos visibles en el árbol de mejoras"""
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        
        branches = {
            "asteroid": {"angle": math.pi},
            "blackhole": {"angle": 0},
            "unique": {"angle": -math.pi/2},
            "planet": {"angle": math.pi/2}
        }
        
        grouped_upgrades = {"asteroid": [], "blackhole": [], "unique": [], "planet": []}
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
        if self.state == GameState.MENU and event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Click izquierdo
                # Botón más abajo (+150)
                play_rect = pygame.Rect(SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT//2 + 150, 200, 60)
                if play_rect.collidepoint(event.pos):
                    self.state = GameState.TRANSITION_FROM_MENU

        if self.state == GameState.SUMMARY and event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Click izquierdo
                restart_rect, shop_rect, menu_rect = self._get_summary_buttons_rects()
                if restart_rect.collidepoint(event.pos):
                    self.reset_run()
                elif shop_rect.collidepoint(event.pos):
                    self.starfield.trigger_implosion() # Activar efecto Warp Inverso
                    self.state = GameState.TRANSITION_TO_SHOP
                    self.nodes_anim_progress = 0.0 # Resetear animación de nodos
                elif menu_rect.collidepoint(event.pos):
                    self.return_to_menu()

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
                            
                # Botón Volver (Centro) -> AHORA ES JUGAR
                center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
                if math.sqrt((mx - center_x)**2 + (my - center_y)**2) < 25: # Radio ajustado a 25
                    self.starfield.trigger_explosion() # Activar efecto Warp
                    self.reset_run()
                    # La animación de salida de los nodos se maneja en _draw_progression o _update_transition_play
                    # Pero como cambiamos de estado inmediatamente, necesitamos que la transición visual lo maneje.
                    # En este caso, el efecto Warp y el cambio de fondo ya son bastante fuertes.
                    # Podríamos hacer que los nodos se alejen rápidamente hacia afuera.

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
        # El agujero negro decrece (o crece si viene de la tienda)
        self.black_hole.update()
        
        # Actualizar explosión de estrellas si está activa
        self.starfield.update()
        
        # Si ya llegó al tamaño base
        if abs(self.black_hole.radius - self.black_hole.target_radius) < 1:
            self.state = GameState.PLAYING
            self.starfield.reset() # Resetear estrellas para la próxima vez

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
                
                # Lógica de Spawning (Asteroides vs Planetas)
                should_spawn_planet = False
                # Solo spawnean si están desbloqueados Y el agujero negro es nivel 5 o superior
                if self.planets_unlocked and self.black_hole.level >= 5:
                    # 20% de probabilidad de spawnear un planeta
                    if random.random() < 0.2:
                        should_spawn_planet = True
                
                if should_spawn_planet:
                    # Lógica de nivel de Planeta
                    # Nivel máximo determinado por mejoras
                    max_planet_level = min(6, 1 + int(self.planet_mass_bonus))
                    
                    # Nivel mínimo determinado por el nivel del agujero negro
                    # Los planetas empiezan en nivel 5. Mantenemos los niveles bajos durante 3 niveles (5, 6, 7).
                    # A partir del nivel 8, el mínimo sube a 2.
                    min_planet_level = max(1, self.black_hole.level - 6)
                    
                    # Asegurar rango válido
                    real_min_level = min(min_planet_level, max_planet_level)
                    
                    level = random.randint(real_min_level, max_planet_level)
                    new_body = Planet(level=level)
                else:
                    # Lógica de nivel de Asteroide
                    # El nivel máximo está determinado por la mejora de Masa (Nucleosíntesis)
                    # Nivel base 1 + bonus de masa
                    max_unlocked_level = min(6, 1 + int(self.asteroid_mass_bonus))
                    
                    # Spawneamos un nivel aleatorio entre el mínimo (basado en agujero) y el máximo desbloqueado
                    # Mínimo: Nivel del agujero - 3
                    min_level = max(1, self.black_hole.level - 3)
                    
                    # Aseguramos que min_level no supere a max_unlocked_level
                    real_min_level = min(min_level, max_unlocked_level)
                    
                    level = random.randint(real_min_level, max_unlocked_level)
                    new_body = Asteroid(level=level)
                
                # Calcular distancia de spawn dinámica
                
                # Calcular distancia de spawn dinámica
                # Mínimo: Radio del agujero negro + margen (para no nacer dentro)
                # Máximo: Escalado con el nivel del agujero negro para llenar más pantalla al hacer zoom out
                # AUMENTADO: El rango máximo crece más rápido para compensar el crecimiento del agujero
                min_spawn = max(SPAWN_DISTANCE_MIN, self.black_hole.radius + 80) # Margen aumentado a 80
                max_spawn = SPAWN_DISTANCE_MAX + (self.black_hole.level * 100)   # Crecimiento duplicado (50 -> 100)
                
                new_body.set_spawn_position(min_spawn, max_spawn)
                
                self.bodies.append(new_body)
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
            
            # Lógica de Empuje de Onda de Choque
            # Si la onda alcanza a un cuerpo, lo empuja hacia afuera
            for body in self.bodies:
                if wave.id not in body.hit_shockwaves:
                    # Si la onda ha alcanzado o superado el radio orbital del cuerpo
                    # Usamos un margen para que no empuje cosas que ya están muy lejos si la onda nace lejos (aunque siempre nace en el centro)
                    if wave.radius >= body.orbit_radius - body.current_size:
                        # ¡IMPACTO!
                        body.hit_shockwaves.add(wave.id)
                        
                        # Calcular fuerza de empuje
                        # Queremos que los aleje lo suficiente para compensar el crecimiento del agujero
                        # Y un poco más para dar sensación de impacto
                        # REDUCIDO: Antes era 15 + level*2, ahora es mucho más suave
                        base_force = 5.0 + (self.black_hole.level * 1.5)
                        
                        # Atenuación por distancia: Cuanto más lejos, menos empuje
                        # Usamos 800 como distancia de referencia donde el empuje es mínimo
                        distance_factor = max(0.1, 1.0 - (body.orbit_radius / 800))
                        
                        body.push_velocity = base_force * distance_factor
                        
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
                
                # Cálculo de Daño (Crítico)
                damage_to_deal = self.current_damage
                is_crit = False
                if random.random() < self.critical_chance:
                    damage_to_deal *= self.critical_damage_multiplier
                    is_crit = True
                
                destroyed, actual_damage = body.take_damage(damage_to_deal)
                
                # Feedback visual de daño
                dmg_str = f"{actual_damage:.1f}" if actual_damage < 10 else str(int(actual_damage))
                if is_crit:
                    dmg_str += "!"
                    self.floating_texts.append(FloatingText(body.x, body.y, dmg_str, COLOR_CRIT_TEXT, size=28))
                else:
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
                    
                    # Probabilidad de Fisión (Dividir) - SOLO ASTEROIDES
                    # Verificamos si es instancia de Asteroid (aunque por ahora todos lo son)
                    if isinstance(body, Asteroid) and random.random() < self.asteroid_fission_chance:
                        # Generar nuevo cuerpo del mismo nivel o superior (+1)
                        # Pero limitado por el nivel máximo desbloqueado
                        max_unlocked_level = min(6, 1 + int(self.asteroid_mass_bonus))
                        new_level = min(max_unlocked_level, body.level + random.randint(0, 1))
                        
                        # Crear nuevo cuerpo
                        new_body = Asteroid(level=new_level)
                        
                        # Heredar posición aproximada del padre pero con variación
                        # Usamos el radio actual del padre +/- un poco
                        min_spawn = max(SPAWN_DISTANCE_MIN, body.orbit_radius - 30)
                        max_spawn = body.orbit_radius + 30
                        new_body.set_spawn_position(min_spawn, max_spawn)
                        new_body.angle = body.angle + random.uniform(-0.2, 0.2) # Cerca angularmente
                        
                        new_body.update() # Para setear x,y iniciales
                        
                        self.bodies.append(new_body)
                        # No incrementamos spawned_count para que sea un "bonus" real
                        
                        # El texto aparece donde murió el padre
                        self.floating_texts.append(FloatingText(body.x, body.y - 70, "SPLIT!", COLOR_XP_BAR_FILL))

                    # Generar Debris (Escalado con tamaño)
                    # Más debris para cuerpos más grandes
                    if isinstance(body, Planet):
                        # Planetas: Mucho más debris y más grande
                        num_debris = int(random.randint(15, 25) * body.size_multiplier)
                        debris_size_mult = 2.5
                    else:
                        # Asteroides: Debris normal
                        num_debris = int(random.randint(3, 6) * body.size_multiplier)
                        debris_size_mult = 1.0
                        
                    for _ in range(num_debris):
                        self.debris_list.append(Debris(body.x, body.y, body.dark_color, body.orbit_radius, body.angle, size_multiplier=debris_size_mult))

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
        # Factor de energía para el aura (0.0 = Gravedad/Juego, 1.0 = Energía/Tienda)
        energy_factor = 0.0
        
        # Fondo Dinámico
        if self.state == GameState.PROGRESSION:
            surface.fill(COLOR_BACKGROUND_SHOP)
            energy_factor = 1.0
            
        elif self.state == GameState.TRANSITION_TO_PLAY:
            # Interpolación de Oscuro a Beige
            # Usamos el radio del agujero negro como proxy del progreso
            # Radio va de 25 (Shop) a 50 (Base)
            denom = (BLACK_HOLE_RADIUS_BASE - 25)
            if denom == 0: denom = 1 # Evitar división por cero
            progress = (self.black_hole.radius - 25) / denom
            progress = max(0, min(1, progress))
            
            # Detectar si venimos de Summary (Radio gigante) o Shop (Radio pequeño)
            # Si el radio es muy grande, estamos encogiendo desde Summary
            if self.black_hole.radius > BLACK_HOLE_RADIUS_BASE + 10:
                # Venimos de Summary: Fondo de juego normal
                surface.fill(COLOR_BACKGROUND)
                energy_factor = 0.0
            else:
                # Venimos de Shop: Interpolación y Starfield
                # Lerp color
                r = int(COLOR_BACKGROUND_SHOP[0] + (COLOR_BACKGROUND[0] - COLOR_BACKGROUND_SHOP[0]) * progress)
                g = int(COLOR_BACKGROUND_SHOP[1] + (COLOR_BACKGROUND[1] - COLOR_BACKGROUND_SHOP[1]) * progress)
                b = int(COLOR_BACKGROUND_SHOP[2] + (COLOR_BACKGROUND[2] - COLOR_BACKGROUND_SHOP[2]) * progress)
                surface.fill((r, g, b))
                
                # Dibujar Starfield explotando
                self.starfield.draw(surface, black_hole_radius=self.black_hole.radius)
                
                # Interpolación del aura (Inverso al progreso: 1.0 -> 0.0)
                energy_factor = 1.0 - progress
                
                # ANIMACIÓN DE SALIDA DE NODOS (Efecto Warp hacia afuera)
                # Reutilizamos la lógica de _draw_progression pero con un "zoom" exagerado
                # basado en el progreso de la transición
                
                # Solo dibujamos si estamos al principio de la transición para que no moleste
                if progress < 0.8:
                    # Factor de expansión exponencial
                    expansion = 1.0 + (progress * 5.0) # 1.0 -> 6.0
                    alpha = int(255 * (1.0 - progress * 1.5)) # Desvanecimiento rápido
                    if alpha > 0:
                        # Dibujar nodos expandiéndose
                        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
                        node_positions = self._get_visible_nodes_positions()
                        
                        # Superficie temporal para transparencia
                        nodes_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                        
                        for key, (x, y) in node_positions.items():
                            # Expandir desde el centro
                            dx = x - center_x
                            dy = y - center_y
                            ex = center_x + dx * expansion
                            ey = center_y + dy * expansion
                            
                            # Solo dibujar si está en pantalla
                            if 0 <= ex <= SCREEN_WIDTH and 0 <= ey <= SCREEN_HEIGHT:
                                # Dibujar nodo simplificado (solo círculo)
                                pygame.draw.circle(nodes_surf, (100, 200, 255, alpha), (int(ex), int(ey)), 10)
                                # Línea de velocidad (Trail) hacia el centro
                                start_trail = (int(ex - dx*0.1), int(ey - dy*0.1))
                                pygame.draw.line(nodes_surf, (100, 200, 255, alpha//2), start_trail, (int(ex), int(ey)), 2)
                        
                        surface.blit(nodes_surf, (0, 0))
            
        elif self.state == GameState.TRANSITION_TO_SHOP:
             # Aquí el agujero negro cubre casi todo al principio
             surface.fill(COLOR_BACKGROUND_SHOP)
             # Al ir entrando a la tienda, activamos el modo energía
             # Podríamos interpolar, pero como viene de pantalla completa negra, 
             # el cambio de color del aura (que está fuera de pantalla al inicio) no se nota tanto.
             energy_factor = 1.0
             
        else:
            surface.fill(COLOR_BACKGROUND)
            energy_factor = 0.0
        
        # Calcular Zoom
        zoom = self.get_zoom()
        
        # Determinar orden de dibujado
        draw_black_hole_on_top = self.state in [GameState.TRANSITION_TO_SUMMARY, GameState.SUMMARY, GameState.TRANSITION_TO_SHOP, GameState.TRANSITION_FROM_SHOP, GameState.PROGRESSION]
        
        if not draw_black_hole_on_top:
            # Dibujado normal (Juego y Transición a Juego)
            # Pasamos el energy_factor calculado
            self.black_hole.draw(surface, zoom, energy_factor=energy_factor)
        
        # Dibujar Debris (detrás de los cuerpos pero delante del agujero si es normal)
        for debris in self.debris_list:
            debris.draw(surface, zoom)
        
        for body in self.bodies:
            body.draw(surface, zoom)
            
        if draw_black_hole_on_top:
            # En transiciones a pantalla completa, ignoramos el zoom para que cubra todo bien
            if self.state == GameState.TRANSITION_TO_SUMMARY:
                self.black_hole.draw(surface, 1.0)
            elif self.state == GameState.PROGRESSION:
                # En el menú de mejoras, el agujero negro está en el centro
                self.black_hole.draw(surface, 1.0, energy_factor=1.0)
            elif self.state == GameState.TRANSITION_TO_SHOP:
                self.black_hole.draw(surface, 1.0, energy_factor=1.0)
            else:
                self.black_hole.draw(surface, zoom, energy_factor=energy_factor)
            
        # Efectos visuales (detrás del cursor)
        for wave in self.shockwaves:
            wave.draw(surface, zoom)
            
        for text in self.floating_texts:
            text.draw(surface, zoom)
            
                # UI Básica
        self._draw_ui(surface)
        
        # Pantallas especiales
        if self.state == GameState.MENU or self.state == GameState.TRANSITION_FROM_MENU or self.state == GameState.TRANSITION_TO_MENU:
            self._draw_menu(surface)
        elif self.state == GameState.SUMMARY:
            self._draw_summary(surface)
        elif self.state == GameState.PROGRESSION:
            self._draw_progression(surface)
        elif self.state == GameState.TRANSITION_TO_SHOP or self.state == GameState.TRANSITION_FROM_SHOP:
            # Dibujar Summary debajo
            # self._draw_summary(surface) # Ya no dibujamos summary debajo, queremos ver el fondo
            
            # Fondo oscuro
            surface.fill(COLOR_BACKGROUND_SHOP)
            
            # Dibujar Starfield implosionando
            self.starfield.draw(surface, black_hole_radius=self.black_hole.radius)
            
            # Dibujar círculo de transición (Agujero negro encogiéndose)
            # Ya se dibuja en draw() principal, pero queremos forzar el modo energía si estamos cerca del final
            # O simplemente dejar que el draw principal lo maneje (usará modo normal por defecto)
            # Para suavidad, podríamos interpolar, pero por ahora dejemos que cambie al llegar a PROGRESSION
        
        if self.state == GameState.PAUSED:
            self._draw_pause_overlay(surface)
            
        # Dibujar Cursor (siempre encima de todo, incluso UI)
        # El cursor recibe el zoom para escalar su radio visualmente
        self.cursor.draw(surface, zoom)

    def _draw_menu(self, surface):
        offset = self.menu_anim_offset
        
        # Título Grande (Más arriba: -250) - Se mueve hacia ARRIBA (-offset)
        title_text = self.font_ui_large.render(TITLE, True, COLOR_TEXT)
        surface.blit(title_text, (SCREEN_WIDTH//2 - title_text.get_width()//2, SCREEN_HEIGHT//2 - 250 - offset))
        
        # Botón Jugar (Más abajo: +150) - Se mueve hacia ABAJO (+offset)
        play_rect = pygame.Rect(SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT//2 + 150 + offset, 200, 60)
        
        mx, my = pygame.mouse.get_pos()
        is_hover = play_rect.collidepoint(mx, my)
        
        color_bg = (60, 60, 60) if not is_hover else (90, 90, 90)
        pygame.draw.rect(surface, color_bg, play_rect, border_radius=15)
        pygame.draw.rect(surface, COLOR_TEXT, play_rect, width=2, border_radius=15)
        
        play_text = self.font_btn.render("JUGAR", True, COLOR_TEXT_INVERTED)
        surface.blit(play_text, (play_rect.centerx - play_text.get_width()//2, play_rect.centery - play_text.get_height()//2))
        
        # Instrucciones (También se mueven hacia abajo)
        instr_text = self.font_desc.render("Usa el mouse para mover el agujero negro", True, COLOR_TEXT)
        surface.blit(instr_text, (SCREEN_WIDTH//2 - instr_text.get_width()//2, SCREEN_HEIGHT - 50 + offset))

    def end_run_from_pause(self):
        """Termina la run desde el menú de pausa"""
        self.state = GameState.TRANSITION_TO_SUMMARY
        self.black_hole.expand_to_screen()

    def return_to_menu(self):
        """Vuelve al menú principal desde pausa"""
        self.state = GameState.TRANSITION_TO_MENU
        self.menu_anim_offset = 400 # Empezar fuera de pantalla
        
        # Resetear estado de juego
        self.time_remaining = GAME_DURATION
        self.money_earned = 0
        self.bodies = []
        self.bodies_destroyed = {level: 0 for level in MASS_COLORS.keys()}
        self.current_xp = 0
        self.xp_to_next_level = XP_BASE_REQUIREMENT
        self.shockwaves = []
        self.floating_texts = []
        self.debris_list = []
        self.spawned_count = 0
        
        # Resetear agujero negro
        self.black_hole.shrink_to_game()
        # Eliminamos la linea que forzaba el radio para permitir la animación

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
            text = self.font_ui_large.render("PAUSA", True, COLOR_TEXT)
            # Efecto de sombra/glitch simple
            surface.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2 + 2, SCREEN_HEIGHT//2 - 100 + 2))
            surface.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, SCREEN_HEIGHT//2 - 100))
            
        # Opciones del menú
        resume_text = self.font_ui_small.render("ESC - Reanudar", True, COLOR_TEXT)
        end_text = self.font_ui_small.render("Q - Terminar Run", True, COLOR_TEXT)
        
        # Centrar textos
        surface.blit(resume_text, (SCREEN_WIDTH//2 - resume_text.get_width()//2, SCREEN_HEIGHT//2))
        surface.blit(end_text, (SCREEN_WIDTH//2 - end_text.get_width()//2, SCREEN_HEIGHT//2 + 50))

    def _draw_ui(self, surface):
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
            level_text = self.font_ui.render(f"Nivel {self.black_hole.level}", True, COLOR_TEXT)
            surface.blit(level_text, (bar_x + bar_width + 10, bar_y - 2))

            # Tiempo
            time_text = self.font_ui.render(f"Tiempo: {int(self.time_remaining)}s", True, COLOR_TEXT)
            surface.blit(time_text, (20, 20))
            
            # Dinero
            money_text = self.font_ui.render(f"Dinero: ${self.money_earned}", True, COLOR_TEXT)
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
        menu_rect = pygame.Rect(center_x - button_width // 2, center_y + 300, button_width, button_height)
        
        return restart_rect, shop_rect, menu_rect

    def _draw_summary(self, surface):
        # Pantalla de Resumen (Fondo Negro = Agujero Negro Gigante)
        # No necesitamos overlay porque el agujero negro ya cubre todo
        
        # Usamos color invertido (claro)
        # Subimos el título y los dineros
        title = self.font_ui.render("¡RUN TERMINADA!", True, COLOR_TEXT_INVERTED)
        score = self.font_ui.render(f"Ganancias: ${self.money_earned}", True, COLOR_TEXT_INVERTED)
        total = self.font_ui.render(f"Banco Total: ${self.total_money}", True, COLOR_MONEY_TEXT)
        
        surface.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, SCREEN_HEIGHT//2 - 200))
        surface.blit(score, (SCREEN_WIDTH//2 - score.get_width()//2, SCREEN_HEIGHT//2 - 160))
        surface.blit(total, (SCREEN_WIDTH//2 - total.get_width()//2, SCREEN_HEIGHT//2 - 120))
        
        # --- Estadísticas de Cuerpos Destruidos ---
        stats_start_y = SCREEN_HEIGHT // 2 - 70
        line_height = 25
        
        # Título de sección
        stats_title = self.font_stats.render("Cuerpos Absorbidos:", True, (200, 200, 200))
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
                text_surf = self.font_stats.render(text_str, True, color)
                
                surface.blit(text_surf, (SCREEN_WIDTH//2 - text_surf.get_width()//2, current_y))
                current_y += line_height
        
        # Botones
        restart_rect, shop_rect, menu_rect = self._get_summary_buttons_rects()
        mx, my = pygame.mouse.get_pos()
        
        # Botón Reiniciar
        is_hover_restart = restart_rect.collidepoint(mx, my)
        color_restart_bg = (60, 60, 60) if not is_hover_restart else (90, 90, 90)
        pygame.draw.rect(surface, color_restart_bg, restart_rect, border_radius=12)
        pygame.draw.rect(surface, COLOR_TEXT_INVERTED, restart_rect, width=2, border_radius=12)
        
        restart_text = self.font_btn.render("Repetir (R)", True, COLOR_TEXT_INVERTED)
        surface.blit(restart_text, (restart_rect.centerx - restart_text.get_width()//2, restart_rect.centery - restart_text.get_height()//2))
        
        # Botón Tienda
        is_hover_shop = shop_rect.collidepoint(mx, my)
        color_shop_bg = (40, 20, 60) if not is_hover_shop else (70, 40, 100) # Morado oscuro
        pygame.draw.rect(surface, color_shop_bg, shop_rect, border_radius=12)
        pygame.draw.rect(surface, COLOR_XP_BAR_FILL, shop_rect, width=2, border_radius=12)
        
        shop_text = self.font_btn.render("Mejoras (M)", True, COLOR_XP_BAR_FILL)
        surface.blit(shop_text, (shop_rect.centerx - shop_text.get_width()//2, shop_rect.centery - shop_text.get_height()//2))

        # Botón Menu Principal
        is_hover_menu = menu_rect.collidepoint(mx, my)
        color_menu_bg = (60, 20, 20) if not is_hover_menu else (100, 40, 40) # Rojo oscuro
        pygame.draw.rect(surface, color_menu_bg, menu_rect, border_radius=12)
        pygame.draw.rect(surface, (200, 100, 100), menu_rect, width=2, border_radius=12)
        
        menu_text = self.font_btn.render("Menu Principal", True, (200, 100, 100))
        surface.blit(menu_text, (menu_rect.centerx - menu_text.get_width()//2, menu_rect.centery - menu_text.get_height()//2))

    def _draw_progression(self, surface):
        # Actualizar timer de animación
        self.menu_time += 0.05
        
        # Animación de entrada de nodos
        if self.nodes_anim_progress < 1.0:
            self.nodes_anim_progress += 0.05
            if self.nodes_anim_progress > 1.0: self.nodes_anim_progress = 1.0
            
        # Easing para la animación (EaseOutBack para un efecto de rebote suave)
        t = self.nodes_anim_progress
        c1 = 1.70158
        c3 = c1 + 1
        ease_val = 1 + c3 * math.pow(t - 1, 3) + c1 * math.pow(t - 1, 2)
        
        # Fondo Espacial (Ya no beige)
        # El agujero negro central se dibuja en el método draw() principal
        
        # Dibujar Starfield (con culling del agujero negro)
        self.starfield.draw(surface, black_hole_radius=self.black_hole.radius)
        
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        
        node_radius = 15
        
        mx, my = pygame.mouse.get_pos()
        
        hovered_node = None
        
        # Obtener posiciones de nodos visibles
        node_positions = self._get_visible_nodes_positions()
        
        # Aplicar flotación y ANIMACIÓN DE ENTRADA a las posiciones
        floating_positions = {}
        for key, (x, y) in node_positions.items():
            # Usamos hash de la key para desincronizar las ondas
            offset = hash(key) % 100
            float_y = math.sin(self.menu_time + offset) * 5 # Amplitud 5px
            
            # Animación de entrada: Los nodos vienen desde el centro
            # Interpolamos entre el centro y la posición final
            final_x = x
            final_y = y + float_y
            
            curr_x = center_x + (final_x - center_x) * ease_val
            curr_y = center_y + (final_y - center_y) * ease_val
            
            floating_positions[key] = (curr_x, curr_y)
        
        # Dibujar conexiones (Líneas de Energía)
        # Necesitamos saber dónde empieza cada rama para conectar los nodos raíz
        branches = {
            "asteroid": {"angle": math.pi},
            "blackhole": {"angle": 0},
            "unique": {"angle": -math.pi/2},
            "planet": {"angle": math.pi/2}
        }
        branch_start_dist = 100
        
        for key, (x, y) in floating_positions.items():
            data = UPGRADES[key]
            parent_key = data.get("parent")
            
            start_pos = None
            is_active = False # Si la conexión está "viva" (padre comprado)
            
            if parent_key and parent_key in floating_positions:
                start_pos = floating_positions[parent_key]
                # La conexión está activa si el nodo destino (hijo) ha sido comprado
                # Esto significa que la conexión está "establecida"
                if self.upgrades.get(key, 0) > 0:
                    is_active = True
            elif not parent_key:
                # Es nodo raíz
                cat = data.get("category", "asteroid")
                angle = branches[cat]["angle"]
                sx = center_x + branch_start_dist * math.cos(angle)
                sy = center_y + branch_start_dist * math.sin(angle)
                start_pos = (sx, sy)
                # Las conexiones al núcleo están activas si el nodo raíz está comprado
                if self.upgrades.get(key, 0) > 0:
                    is_active = True
            
            if start_pos:
                # Dibujar línea base oscura (siempre presente como "cable apagado")
                pygame.draw.line(surface, (30, 30, 40), start_pos, (x, y), 5)
                
                if is_active:
                    # Efecto Neón: La línea completa brilla
                    # Pulsación suave del brillo para que parezca electricidad viva
                    pulse = (math.sin(self.menu_time * 4 + hash(key)) + 1) / 2 # 0.0 a 1.0
                    
                    # 1. Glow externo (Simulado con líneas más anchas y oscuras)
                    # Azul eléctrico oscuro
                    glow_color = (0, 100, 180) 
                    pygame.draw.line(surface, glow_color, start_pos, (x, y), 5)
                    
                    # 2. Línea media (Color principal pulsante)
                    # Cian brillante
                    mid_val = 150 + int(105 * pulse)
                    mid_color = (0, mid_val, mid_val)
                    pygame.draw.line(surface, mid_color, start_pos, (x, y), 3)
                    
                    # 3. Núcleo (Blanco/Cian muy claro)
                    pygame.draw.line(surface, (200, 255, 255), start_pos, (x, y), 1)

        # Dibujar nodos (en segunda pasada para que queden encima de las líneas)
        for key, pos in floating_positions.items():
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
            
            # --- Estilos de Nodo ---
            
            # 1. Relleno (Fondo)
            if is_maxed:
                fill_color = (20, 50, 20) # Verde oscuro
            elif can_buy:
                fill_color = (20, 20, 40) # Azul oscuro
            elif level > 0:
                # Comprado pero no alcanza para mejorar (Stalled) -> GRIS
                fill_color = (20, 20, 25) # Gris oscuro
            else:
                # No comprado y no alcanza (Locked/Dormant) -> ROJO
                fill_color = (30, 10, 10) # Rojo oscuro suave
            
            pygame.draw.circle(surface, fill_color, (x, y), node_radius)
            
            # 2. Borde y Efectos
            if is_maxed:
                # Dorado / Verde Brillante
                border_color = (255, 215, 0) # Gold
                pygame.draw.circle(surface, border_color, (x, y), node_radius, 2)
                # Brillo interno
                pygame.draw.circle(surface, (100, 255, 100), (x, y), node_radius - 4, 1)
                
            elif can_buy:
                # Cian Neón Pulsante
                pulse = (math.sin(self.menu_time * 5) + 1) / 2 # 0.0 a 1.0 rápido
                base_val = 150
                bright_val = 255
                c_val = int(base_val + (bright_val - base_val) * pulse)
                border_color = (0, c_val, c_val) # Cian variable
                
                # Glow externo si es comprable
                glow_surf = pygame.Surface((node_radius*4, node_radius*4), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (0, 200, 255, 50), (node_radius*2, node_radius*2), node_radius + 5 + 2*pulse)
                surface.blit(glow_surf, (x - node_radius*2, y - node_radius*2))
                
                pygame.draw.circle(surface, border_color, (x, y), node_radius, 2)
                
            elif level > 0:
                # Gris (Bloqueado por dinero pero ya poseído) -> GRIS
                border_color = (80, 80, 100) # Gris metal
                pygame.draw.circle(surface, border_color, (x, y), node_radius, 1)
                
            else:
                # Rojo (Bloqueado y nunca comprado) -> ROJO
                border_color = (150, 50, 50) # Rojo óxido
                pygame.draw.circle(surface, border_color, (x, y), node_radius, 1)
            
            # Highlight al hacer hover
            if hover:
                pygame.draw.circle(surface, (255, 255, 255), (x, y), node_radius + 2, 1)
            
            # Nivel dentro
            if node_radius > 10:
                if is_maxed:
                    txt_col = (255, 215, 0)
                    txt_str = "M" # Max
                elif can_buy:
                    txt_col = (200, 255, 255)
                    txt_str = str(level)
                elif level > 0:
                    txt_col = (150, 150, 170) # Gris claro
                    txt_str = str(level)
                else:
                    txt_col = (150, 100, 100) # Rojo claro
                    txt_str = "0"
                    
                icon_text = self.font_desc.render(txt_str, True, txt_col)
                surface.blit(icon_text, (x - icon_text.get_width()//2, y - icon_text.get_height()//2))

        # Botón Central (Volver/Jugar)
        # Ya no dibujamos un círculo, el agujero negro está ahí.
        # Solo dibujamos el texto "PLAY" o "EVOLVE" encima si queremos, o un anillo indicador
        center_radius = 25 # Reducido de 40
        hover_center = math.sqrt((mx - center_x)**2 + (my - center_y)**2) < center_radius
        
        if hover_center:
            # Indicador sutil de que es interactivo
            pygame.draw.circle(surface, (255, 255, 255), (center_x, center_y), center_radius + 5, 1)
            # Texto más pequeño o icono de Play
            play_text = self.font_btn.render("PLAY", True, (255, 255, 255))
            surface.blit(play_text, (center_x - play_text.get_width()//2, center_y - play_text.get_height()//2))
        
        # Mostrar Dinero Total arriba
        money_surf = self.font_title.render(f"BANCO: ${self.total_money}", True, COLOR_MONEY_TEXT) # Verde oscuro se ve bien
        surface.blit(money_surf, (center_x - money_surf.get_width()//2, 50))
        
        # Etiquetas de Ramas (Colores más oscuros para contraste)
        # Ajustadas posiciones para el nuevo espaciado
        lbl_ast = self.font_desc.render("ASTEROIDES", True, COLOR_TEXT_LIGHT)
        surface.blit(lbl_ast, (center_x - 250, center_y - 30))
        
        lbl_bh = self.font_desc.render("AGUJERO NEGRO", True, COLOR_TEXT_LIGHT)
        surface.blit(lbl_bh, (center_x + 150, center_y - 30))
        
        lbl_uniq = self.font_desc.render("ÚNICAS", True, COLOR_TEXT_LIGHT)
        surface.blit(lbl_uniq, (center_x - lbl_uniq.get_width()//2, center_y - 150))
        
        # Etiqueta Planetas (Abajo)
        if self.planets_unlocked:
            lbl_planet = self.font_desc.render("PLANETAS", True, COLOR_TEXT_LIGHT)
            surface.blit(lbl_planet, (center_x - lbl_planet.get_width()//2, center_y + 150))

        # DIBUJAR TOOLTIP AL FINAL (ENCIMA DE TODO)
        if hovered_node:
            data = hovered_node["data"]
            
            # Contenido del tooltip
            lines = [
                (data["name"], self.font_title, COLOR_TEXT_INVERTED),
                (data["description"], self.font_desc, (200, 200, 200)),
            ]
            
            if hovered_node["is_maxed"]:
                lines.append(("MAX LEVEL", self.font_cost, (100, 255, 100)))
            else:
                cost_color = COLOR_MONEY_TEXT if hovered_node["can_buy"] else (255, 100, 100)
                lines.append((f"Cost: ${hovered_node['cost']}", self.font_cost, cost_color))
                
                # Mostrar incremento
                current_val = data["base_value"] + (hovered_node["level"] * data["increment"])
                next_val = current_val + data["increment"]
                if isinstance(current_val, float):
                    val_str = f"{current_val:.2f} -> {next_val:.2f}"
                else:
                    val_str = f"{current_val} -> {next_val}"
                lines.append((f"Effect: {val_str}", self.font_desc, (150, 150, 255)))

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
        
        # Si venimos de la tienda (radio 25), queremos que crezca suavemente
        # Si venimos de Summary (radio gigante), shrink_to_game ya lo maneja
        if self.black_hole.radius < BLACK_HOLE_RADIUS_BASE:
             self.black_hole.anim_speed = 0.5 # Velocidad lenta para ver el gradiente
        
        self.current_xp = 0
        self.xp_to_next_level = XP_BASE_REQUIREMENT
        self.shockwaves = []
        self.floating_texts = []
        self.debris_list = []
        
        # Resetear spawns
        self.spawned_count = 0

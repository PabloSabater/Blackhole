import pygame
import math
import random
from config import *

class CelestialBody:
    def __init__(self, level):
        self.level = level
        self.x = 0
        self.y = 0
        self.orbit_radius = 0
        self.angle = random.uniform(0, 2 * math.pi)
        self.angular_speed = 0
        self.push_velocity = 0
        self.hit_shockwaves = set()
        
        # Default values (to be overridden by subclasses)
        self.color = (100, 100, 100)
        self.dark_color = (50, 50, 50)
        self.size_multiplier = 1.0
        self.defense_factor = 1.0
        self.mass = 10
        self.max_health = 10
        self.current_health = 10
        self.value = 1
        self.angular_speed_base = 0.005
        self.target_size = 10
        self.current_size = 0
        self.base_size = 10
        self.spawn_anim_timer = 0
        self.spawn_anim_duration = 30
        self.points = []

        self._init_stats()
        self.points = self._generate_shape()

    def _init_stats(self):
        """Inicializa las estadísticas específicas del cuerpo celeste"""
        pass

    def _generate_shape(self):
        """Genera la forma del cuerpo celeste"""
        return []

    def set_spawn_position(self, min_dist, max_dist):
        """Asigna una posición orbital válida basada en el radio del agujero negro"""
        self.orbit_radius = random.randint(int(min_dist), int(max_dist))
        # Recalcular velocidad angular basada en el nuevo radio
        self.angular_speed = (100 / self.orbit_radius) * self.angular_speed_base

    def update(self):
        """Actualiza la posición basada en coordenadas polares"""
        # Aplicar empuje radial (si lo hay)
        if abs(self.push_velocity) > 0.1:
            self.orbit_radius += self.push_velocity
            self.push_velocity *= 0.9 # Fricción fuerte para que se detenga rápido
        else:
            self.push_velocity = 0
            
        self.angle += self.angular_speed
        
        # Animación de entrada (Pop-in con rebote EXAGERADO)
        if self.spawn_anim_timer < self.spawn_anim_duration:
            self.spawn_anim_timer += 1
            t = self.spawn_anim_timer / self.spawn_anim_duration
            
            # Usamos una función elástica más pronunciada
            # Elastic Out
            c4 = (2 * math.pi) / 3
            if t == 0: scale = 0
            elif t == 1: scale = 1
            else:
                # Elastic Out: Comienza en 0 y termina en 1 con rebote
                scale = math.pow(2, -10 * t) * math.sin((t * 10 - 0.75) * c4) + 1
            
            self.current_size = self.target_size * scale
        else:
            self.current_size = self.target_size

        # Convertir a cartesianas para renderizado y colisiones
        # El centro de la pantalla se pasará o calculará fuera, 
        # pero asumimos que orbitan el centro de la pantalla.
        center_x = SCREEN_WIDTH // 2
        center_y = SCREEN_HEIGHT // 2
        
        self.x = center_x + self.orbit_radius * math.cos(self.angle)
        self.y = center_y + self.orbit_radius * math.sin(self.angle)

    def draw(self, surface, zoom=1.0):
        """Dibuja el cuerpo en la superficie dada con zoom"""
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        
        # Transformar posición de mundo a pantalla
        screen_x = center_x + (self.x - center_x) * zoom
        screen_y = center_y + (self.y - center_y) * zoom
        
        # Escalar tamaño visual
        screen_size = self.current_size * zoom
        
        # Transformar los puntos locales a coordenadas de pantalla
        screen_points = []
        for px_norm, py_norm in self.points:
            # Escalamos los puntos normalizados por el tamaño actual escalado
            px = px_norm * screen_size
            py = py_norm * screen_size
            screen_points.append((screen_x + px, screen_y + py))
        
        if len(screen_points) < 3: return

        # Culling simple: Si el bounding box está fuera de pantalla, no dibujar
        # Margen de seguridad de 10px
        min_x = min(p[0] for p in screen_points)
        max_x = max(p[0] for p in screen_points)
        min_y = min(p[1] for p in screen_points)
        max_y = max(p[1] for p in screen_points)
        
        if (max_x < -10 or min_x > SCREEN_WIDTH + 10 or 
            max_y < -10 or min_y > SCREEN_HEIGHT + 10):
            return

        # 1. Dibujar fondo oscuro (parte dañada)
        dark_color = [max(0, c - 100) for c in self.color]
        pygame.draw.polygon(surface, dark_color, screen_points)
        
        # 2. Dibujar parte viva (recortada verticalmente)
        # Optimizacion: Usar set_clip en lugar de crear superficies temporales
        # min_y y max_y ya calculados arriba para el culling
        height = max_y - min_y
        
        if height > 0:
            health_pct = max(0, self.current_health / self.max_health)
            # La parte "viva" está abajo. Calculamos Y donde empieza.
            clip_top = min_y + (height * (1 - health_pct))
            
            # Guardar clip actual
            old_clip = surface.get_clip()
            
            # Definir zona de dibujo (desde clip_top hacia abajo)
            # Usamos coordenadas de pantalla completas para el ancho
            clip_rect = pygame.Rect(0, int(clip_top), SCREEN_WIDTH, int(SCREEN_HEIGHT - clip_top + 100))
            
            # Respetar clip existente si lo hubiera
            if old_clip:
                clip_rect = clip_rect.clip(old_clip)
            
            surface.set_clip(clip_rect)
            
            # Dibujar polígono vivo
            pygame.draw.polygon(surface, self.color, screen_points)
            # Brillo interno
            pygame.draw.aalines(surface, (255, 255, 255), True, screen_points)
            
            # Restaurar clip
            surface.set_clip(old_clip)

        # 3. Dibujar borde (Nuevo)
        # Usamos el color oscuro para el borde, para definir bien la forma
        # pygame.draw.polygon(surface, dark_color, screen_points, 2) # Redundante con aalines
        # Añadimos suavizado al borde
        pygame.draw.aalines(surface, dark_color, True, screen_points)

    def take_damage(self, amount):
        # Aplicar defensa (reducción de daño)
        effective_damage = amount / self.defense_factor
        # Asegurar daño mínimo
        effective_damage = max(0.1, effective_damage)
        
        self.current_health -= effective_damage
        return self.current_health <= 0, effective_damage

class Asteroid(CelestialBody):
    def _init_stats(self):
        self.color = MASS_COLORS.get(self.level, (100, 100, 100))
        
        # Variación de Tamaño (Size Variance)
        # El tamaño influye en la vida total
        # AUMENTADO: Rango mucho más amplio para que se note la diferencia visual
        self.size_multiplier = random.uniform(0.6, 2.2)
        
        # Defensa basada en Nivel (Mitigación de daño)
        # Nivel 1: 1.0 (Sin reducción), Nivel 2: 1.5, etc.
        self.defense_factor = 1.0 + (self.level - 1) * 0.5
        
        # Propiedades físicas
        self.mass = self.level * 10 * self.size_multiplier
        
        # Vida: Base por nivel * Multiplicador de tamaño
        # Escalado exponencial (x^1.5) para que los grandes se sientan mucho más "tanques"
        base_hp = 30 * self.level 
        self.max_health = base_hp * (self.size_multiplier ** 1.5)
        self.current_health = self.max_health
        
        # Valor: Escalado exponencial por nivel y tamaño
        # Aseguramos que el nivel tenga mucho peso
        # Nivel 1: ~5, Nivel 2: ~15, Nivel 3: ~30...
        self.value = int((self.level ** 1.8) * (self.size_multiplier ** 1.2) * 5)
        self.value = max(1, self.value)
        
        # Velocidad angular: Más lejos = más lento (Kepler simplificado)
        # Ajustamos la velocidad para que sea jugable
        # REDUCIDO: Multiplicador bajado de 0.02 a 0.005 para movimiento mucho más lento y relajante
        self.angular_speed_base = 0.005 * random.choice([-1, 1])
        
        # Generación Procedural de Forma (Polígono)
        # El tamaño visual también se ve afectado por el multiplicador
        self.target_size = (10 + (self.level * 5)) * self.size_multiplier
        self.base_size = self.target_size # Referencia
        # Duración de animación escalada con el tamaño (más grande = más lento/pesado)
        self.spawn_anim_duration = int(30 + 20 * self.size_multiplier)
        
        # Color oscuro pre-calculado para debris y bordes
        self.dark_color = tuple(max(0, c - 100) for c in self.color)

    def _generate_shape(self):
        """Genera un polígono irregular suavizado para parecer un asteroide"""
        # 1. Generar vértices base (picos)
        num_points = random.randint(5, 9)
        base_points = []
        for i in range(num_points):
            theta = (i / num_points) * 2 * math.pi
            r = random.uniform(0.8, 1.2)
            px = r * math.cos(theta)
            py = r * math.sin(theta)
            base_points.append((px, py))
            
        # 2. Suavizar usando el algoritmo de Chaikin (Corner Cutting)
        # Esto redondea las esquinas iterativamente
        points = base_points
        iterations = 2 # 2 iteraciones es suficiente para que se vea suave pero irregular
        
        for _ in range(iterations):
            new_points = []
            for i in range(len(points)):
                p0 = points[i]
                p1 = points[(i + 1) % len(points)]
                
                # Crear dos nuevos puntos entre p0 y p1 (al 25% y 75%)
                # Q = 0.75*P0 + 0.25*P1
                # R = 0.25*P0 + 0.75*P1
                
                qx = 0.75 * p0[0] + 0.25 * p1[0]
                qy = 0.75 * p0[1] + 0.25 * p1[1]
                
                rx = 0.25 * p0[0] + 0.75 * p1[0]
                ry = 0.25 * p0[1] + 0.75 * p1[1]
                
                new_points.append((qx, qy))
                new_points.append((rx, ry))
            points = new_points
            
        return points

class Planet(CelestialBody):
    def _init_stats(self):
        # Usamos los mismos colores que los asteroides para mantener consistencia
        self.color = MASS_COLORS.get(self.level, (255, 255, 255))
        
        # Los planetas son mucho más grandes y pesados
        self.size_multiplier = random.uniform(1.5, 3.0)
        
        # Defensa muy alta (Son duros de roer)
        self.defense_factor = 2.0 + (self.level * 1.0)
        
        # Masa masiva
        self.mass = self.level * 50 * self.size_multiplier
        
        # Vida masiva (x5 respecto a asteroides)
        base_hp = 150 * self.level 
        self.max_health = base_hp * (self.size_multiplier ** 1.2)
        self.current_health = self.max_health
        
        # Valor muy alto
        self.value = int((self.level ** 2) * (self.size_multiplier ** 1.5) * 50)
        
        # Movimiento lento y majestuoso
        self.angular_speed_base = 0.002 * random.choice([-1, 1])
        
        # Tamaño visual
        self.target_size = (20 + (self.level * 8)) * self.size_multiplier
        self.base_size = self.target_size
        self.spawn_anim_duration = 60 # Animación lenta
        
        self.dark_color = tuple(max(0, c - 80) for c in self.color)
        
        # Atmósfera (Color secundario)
        self.atmosphere_color = tuple(min(255, c + 50) for c in self.color)
        self.atmosphere_pulse = random.uniform(0, 6.28)
        
        self._generate_texture()

    def _generate_texture(self):
        # Resolución alta para evitar pixelado al hacer zoom
        res = int(self.target_size * 4)
        if res < 100: res = 100
        
        # 1. Fondo Base (Color Principal)
        rect_surf = pygame.Surface((res, res), pygame.SRCALPHA)
        rect_surf.fill(self.color)
        
        # 2. Bandas Sinoidales (Júpiter Style)
        num_bands = random.randint(5, 10)
        
        # Colores para las bandas (Oscuro y Claro)
        c_dark = self.dark_color
        c_light = tuple(min(255, c + 40) for c in self.color)
        
        for i in range(num_bands):
            # Alternar entre oscuro y claro
            band_color = c_dark if i % 2 == 0 else c_light
            
            # Propiedades de la banda
            y_center = (i / num_bands) * res
            thickness = random.randint(res//20, res//8)
            amplitude = random.randint(res//50, res//20)
            freq = random.uniform(0.02, 0.06)
            phase = random.uniform(0, 6.28)
            
            # Dibujar polígono para la banda
            points = []
            # Borde superior
            for x in range(0, res, 4):
                y = y_center + math.sin(x * freq + phase) * amplitude
                points.append((x, y))
            
            # Borde inferior
            for x in range(res, -1, -4):
                y = y_center + thickness + math.sin(x * freq + phase) * amplitude
                points.append((x, y))
                
            pygame.draw.polygon(rect_surf, band_color, points)
            
        # 3. Aplicar Máscara Circular
        mask = pygame.Surface((res, res), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (res//2, res//2), res//2)
        
        # Multiplicar para recortar (Mantiene lo que está dentro del círculo blanco)
        rect_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        
        self.texture = rect_surf
        
        # 4. Generar versión "Muerta" (Oscura)
        self.dead_texture = self.texture.copy()
        # Oscurecer: Multiplicar por gris oscuro
        dark_overlay = pygame.Surface((res, res), pygame.SRCALPHA)
        dark_overlay.fill((80, 80, 80, 255))
        self.dead_texture.blit(dark_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    def _generate_shape(self):
        # Los planetas son círculos perfectos, no necesitamos puntos irregulares
        # Pero generamos un círculo de alta resolución para mantener compatibilidad con el draw() base si fuera necesario
        # Aunque sobreescribiremos draw() para hacerlo más bonito
        num_points = 32
        points = []
        for i in range(num_points):
            theta = (i / num_points) * 2 * math.pi
            px = math.cos(theta)
            py = math.sin(theta)
            points.append((px, py))
        return points

    def update(self):
        super().update()
        self.atmosphere_pulse += 0.05

    def draw(self, surface, zoom=1.0):
        # Sobreescribimos draw para hacer un círculo perfecto con atmósfera
        
        # Posición en pantalla
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        screen_x = center_x + (self.x - center_x) * zoom
        screen_y = center_y + (self.y - center_y) * zoom
        
        # Tamaño actual (con animación de spawn)
        screen_size = self.current_size * zoom
        
        if screen_size < 1: return
        
        # Culling simple
        if (screen_x + screen_size < 0 or screen_x - screen_size > SCREEN_WIDTH or
            screen_y + screen_size < 0 or screen_y - screen_size > SCREEN_HEIGHT):
            return

        # 1. Atmósfera (Glow externo)
        pulse = (math.sin(self.atmosphere_pulse) + 1) / 2 # 0.0 a 1.0
        atmo_size = screen_size + (5 + 5 * pulse) * zoom
        
        # Superficie temporal para transparencia
        atmo_surf_size = int(atmo_size * 2)
        atmo_surf = pygame.Surface((atmo_surf_size, atmo_surf_size), pygame.SRCALPHA)
        
        pygame.draw.circle(atmo_surf, (*self.atmosphere_color, 50), (atmo_surf_size//2, atmo_surf_size//2), int(atmo_size))
        surface.blit(atmo_surf, (screen_x - atmo_surf_size//2, screen_y - atmo_surf_size//2))
        
        # 2. Planeta Base (Círculo)
        # Usamos la misma técnica de clipping que los asteroides para la vida
        
        # Texture Size (Diameter)
        tex_size = int(screen_size * 2)
        
        # Primero dibujamos la versión "muerta" (oscura) completa
        if tex_size > 0:
            scaled_dead = pygame.transform.smoothscale(self.dead_texture, (tex_size, tex_size))
            surface.blit(scaled_dead, (screen_x - tex_size//2, screen_y - tex_size//2))
        
        # Luego dibujamos la versión "viva" recortada según la vida restante
        if self.current_health > 0:
            health_pct = max(0, self.current_health / self.max_health)
            
            # Calcular rectángulo de recorte
            # La parte viva está abajo, así que recortamos desde arriba
            # Altura total del círculo es 2 * screen_size
            diameter = screen_size * 2
            clip_top = (screen_y - screen_size) + (diameter * (1 - health_pct))
            
            # Guardar clip actual
            old_clip = surface.get_clip()
            
            # Definir zona de dibujo (desde clip_top hacia abajo)
            clip_rect = pygame.Rect(0, int(clip_top), SCREEN_WIDTH, int(SCREEN_HEIGHT - clip_top + 100))
            
            # Respetar clip existente
            if old_clip:
                clip_rect = clip_rect.clip(old_clip)
            
            surface.set_clip(clip_rect)
            
            # Dibujar planeta vivo (Textura original)
            if tex_size > 0:
                scaled_live = pygame.transform.smoothscale(self.texture, (tex_size, tex_size))
                surface.blit(scaled_live, (screen_x - tex_size//2, screen_y - tex_size//2))
            
            # Restaurar clip
            surface.set_clip(old_clip)
        
        # 3. Sombra (Efecto 3D simple)
        # Sombra en la parte inferior derecha (lejos de la "luz" del centro/agujero negro?)
        # Asumimos luz ambiental o desde el centro
        # Vamos a hacer un "crescent" de sombra
        shadow_offset = screen_size * 0.3
        # Dibujamos un círculo oscuro desplazado y recortamos (simulado con superposición)
        # Simplificación: Arco de sombra
        
        # 4. Borde (Opcional, para definir mejor)
        pygame.draw.circle(surface, self.dark_color, (screen_x, screen_y), int(screen_size), 2)

class BlackHole:
    def __init__(self):
        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_HEIGHT // 2
        self.level = 1
        self.radius = BLACK_HOLE_RADIUS_BASE
        self.pulse_timer = 0
        self.target_radius = self.radius
        self.anim_speed = 0.5 # Velocidad normal de crecimiento

    def update(self):
        self.pulse_timer += 0.1
        
        # Crecimiento/Decrecimiento suave hacia target_radius
        diff = self.target_radius - self.radius
        
        if abs(diff) > 0.1:
            # Movimiento proporcional a la distancia (Easing exponencial simple)
            change = diff * 0.05
            
            # Aplicar velocidad mínima para asegurar que termine la animación
            if abs(change) < self.anim_speed:
                # Si la distancia restante es menor que la velocidad mínima, llegamos directamente
                if abs(diff) < self.anim_speed:
                    self.radius = self.target_radius
                    return
                
                change = math.copysign(self.anim_speed, diff)
            
            self.radius += change
        else:
            self.radius = self.target_radius

    def level_up(self):
        self.level += 1
        # Aumentamos el crecimiento para compensar el zoom out
        # Antes era +5 (GROWTH_FACTOR), ahora +15 para que se note más
        self.target_radius = BLACK_HOLE_RADIUS_BASE + (self.level * (BLACK_HOLE_GROWTH_FACTOR + 10))
        self.anim_speed = 0.5

    def expand_to_screen(self):
        # Calcular radio necesario para cubrir la pantalla (diagonal)
        diagonal = math.sqrt(SCREEN_WIDTH**2 + SCREEN_HEIGHT**2)
        self.target_radius = diagonal
        self.anim_speed = 15.0 # Expansión rápida y dramática

    def shrink_to_game(self):
        self.level = 1
        self.target_radius = BLACK_HOLE_RADIUS_BASE
        self.anim_speed = 10.0 # Contracción rápida

    def draw(self, surface, zoom=1.0, energy_factor=0.0):
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        
        # Posición en pantalla
        screen_x = center_x + (self.x - center_x) * zoom
        screen_y = center_y + (self.y - center_y) * zoom
        
        # Radio escalado
        screen_radius = self.radius * zoom
        
        # --- Efecto de Aura / Respiración ---
        
        # Interpolación de parámetros entre Modo Gravedad (0.0) y Modo Energía (1.0)
        
        # 1. Calcular distancias base para cada capa
        # Modo Energía: Escala con el radio visual
        scale_factor = max(0.5, screen_radius / 50.0)
        dists_energy = [10 * scale_factor, 25 * scale_factor, 50 * scale_factor]
        
        # Modo Gravedad: Escala con el zoom
        dists_gravity = [25 * zoom, 80 * zoom, 180 * zoom]
        
        # 2. Calcular colores base
        colors_energy = [(100, 200, 255), (50, 100, 200), (20, 20, 100)]
        colors_gravity = [(40, 40, 40), (55, 55, 55), (70, 70, 70)]
        
        # 3. Calcular Alphas base
        alphas_energy = [80, 60, 40]
        alphas_gravity = [65, 50, 35]
        
        # 4. Calcular Offset Máximo (para el tamaño de la superficie)
        offset_energy = 60 * scale_factor
        offset_gravity = 250 * zoom
        max_aura_offset = offset_gravity * (1 - energy_factor) + offset_energy * energy_factor

        aura_surface_size = int((screen_radius + max_aura_offset) * 2)
        # Asegurar tamaño mínimo
        if aura_surface_size < 1: aura_surface_size = 1
        
        aura_surface = pygame.Surface((aura_surface_size, aura_surface_size), pygame.SRCALPHA)
        aura_center = (aura_surface_size // 2, aura_surface_size // 2)
        
        # Factor de respiración
        breath = (math.sin(self.pulse_timer * 0.2) + 1) / 2 
        
        # 3 Capas de aura
        for i in range(2, -1, -1): # 2, 1, 0 (Indices de listas)
            # Interpolación Lineal (Lerp) de distancia
            dist = dists_gravity[i] * (1 - energy_factor) + dists_energy[i] * energy_factor
            
            # La respiración escala con la distancia
            breath_dist = (dist * 0.25) * breath 
            current_radius = screen_radius + dist + breath_dist
            
            # Lerp Color
            c_g = colors_gravity[i]
            c_e = colors_energy[i]
            r = int(c_g[0] + (c_e[0] - c_g[0]) * energy_factor)
            g = int(c_g[1] + (c_e[1] - c_g[1]) * energy_factor)
            b = int(c_g[2] + (c_e[2] - c_g[2]) * energy_factor)
            
            # Lerp Alpha
            a_g = alphas_gravity[i]
            a_e = alphas_energy[i]
            base_alpha = a_g * (1 - energy_factor) + a_e * energy_factor
            
            # Modulamos alpha con la respiración
            current_alpha = int(base_alpha * (0.7 + 0.3 * breath))
            
            color = (r, g, b, current_alpha)
            
            pygame.draw.circle(aura_surface, color, aura_center, int(current_radius))
            
        # Dibujar el aura en la pantalla principal
        surface.blit(aura_surface, (screen_x - aura_center[0], screen_y - aura_center[1]))
        
        # Cuerpo principal (Agujero Negro)
        pygame.draw.circle(surface, COLOR_BLACK_HOLE, (screen_x, screen_y), int(screen_radius))

class Shockwave:
    def __init__(self, x, y):
        self.id = random.randint(0, 1000000) # ID único para evitar golpes múltiples
        self.x = x
        self.y = y
        self.radius = 10
        self.max_radius = SCREEN_WIDTH  # Cubrir pantalla
        self.alpha = 255
        self.speed = 25 # Más rápida para que el golpe se sienta potente
        self.active = True

    def update(self):
        self.radius += self.speed
        self.alpha -= 5
        if self.alpha <= 0:
            self.active = False

    def draw(self, surface, zoom=1.0):
        if not self.active: return
        
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        screen_x = center_x + (self.x - center_x) * zoom
        screen_y = center_y + (self.y - center_y) * zoom
        screen_radius = self.radius * zoom
        
        s = pygame.Surface((int(screen_radius*2), int(screen_radius*2)), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 255, 255, max(0, self.alpha)), (int(screen_radius), int(screen_radius)), int(screen_radius), int(5 * zoom))
        surface.blit(s, (screen_x - screen_radius, screen_y - screen_radius))

class Debris:
    def __init__(self, x, y, color, radius, angle, size_multiplier=1.0):
        self.x = x
        self.y = y
        self.color = color
        self.orbit_radius = radius
        self.angle = angle
        self.size = random.randint(3, 6) * size_multiplier # Tamaño escalable
        self.speed = random.uniform(0.02, 0.05) # Velocidad angular rápida
        self.decay_speed = random.uniform(1.0, 2.0) # Velocidad de caída al centro

    def update(self):
        # Movimiento espiral hacia el centro
        self.angle += self.speed
        self.orbit_radius -= self.decay_speed
        
        center_x = SCREEN_WIDTH // 2
        center_y = SCREEN_HEIGHT // 2
        
        self.x = center_x + self.orbit_radius * math.cos(self.angle)
        self.y = center_y + self.orbit_radius * math.sin(self.angle)

    def draw(self, surface, zoom=1.0):
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        screen_x = center_x + (self.x - center_x) * zoom
        screen_y = center_y + (self.y - center_y) * zoom
        screen_size = max(1, int(self.size * zoom))
        
        pygame.draw.circle(surface, self.color, (int(screen_x), int(screen_y)), screen_size)

class FloatingText:
    def __init__(self, x, y, text, color=COLOR_DAMAGE_TEXT, size=16):
        self.x = x
        self.y = y
        self.text = str(text)
        self.color = color
        self.life = 60 # frames
        self.alpha = 255
        self.font = pygame.font.SysFont("Arial", size, bold=True)

    def update(self):
        self.y -= 1 # Subir
        self.life -= 1
        self.alpha = max(0, int((self.life / 60) * 255))

    def draw(self, surface, zoom=1.0):
        if self.life <= 0: return
        
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        screen_x = center_x + (self.x - center_x) * zoom
        screen_y = center_y + (self.y - center_y) * zoom
        
        text_surf = self.font.render(self.text, True, self.color)
        text_surf.set_alpha(self.alpha)
        surface.blit(text_surf, (screen_x, screen_y))

class PlayerCursor:
    def __init__(self):
        self.radius = CURSOR_RADIUS
        self.x = 0
        self.y = 0
        self.angle_offset = 0 # Para rotar el borde discontinuo

    def update(self):
        self.x, self.y = pygame.mouse.get_pos()
        self.angle_offset += 0.02

    def draw(self, surface, zoom=1.0):
        # El cursor se dibuja en coordenadas de pantalla (mouse), pero su radio visual debe escalar
        # para representar el área de efecto en el mundo "zoomeado"
        visual_radius = self.radius * zoom
        
        # Dibujar línea discontinua real
        num_segments = 20
        segment_angle = (2 * math.pi) / num_segments
        gap_ratio = 0.6 # 60% línea, 40% hueco
        
        for i in range(num_segments):
            start_angle = (i * segment_angle) + self.angle_offset
            end_angle = start_angle + (segment_angle * gap_ratio)
            
            # Calcular puntos del arco (aproximado con línea recta para rendimiento)
            start_pos = (
                self.x + visual_radius * math.cos(start_angle),
                self.y + visual_radius * math.sin(start_angle)
            )
            end_pos = (
                self.x + visual_radius * math.cos(end_angle),
                self.y + visual_radius * math.sin(end_angle)
            )
            
            # Dibujar línea del cursor
            # Usamos un solo color oscuro y sólido para mejor visibilidad en fondo claro
            pygame.draw.line(surface, COLOR_CURSOR, start_pos, end_pos, 3)
            
        # Punto central para precisión (Opcional, comentado por ahora)
        # pygame.draw.circle(surface, (0, 0, 0), (self.x, self.y), 4)
        # pygame.draw.circle(surface, (255, 255, 255), (self.x, self.y), 2)

class Starfield:
    def __init__(self):
        self.stars = []
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        
        # Crear 3 capas de estrellas
        # Capa 0: Fondo (Lentas, pequeñas, muchas)
        # Capa 1: Medio (Velocidad media)
        # Capa 2: Frente (Rápidas, menos cantidad)
        
        counts = [200, 100, 50]
        speeds = [0.0002, 0.0005, 0.001] # Velocidad angular
        colors = [(100, 100, 120), (150, 150, 180), (200, 200, 255)]
        sizes = [1, 2, 2]
        
        for layer in range(3):
            for _ in range(counts[layer]):
                # Generar en coordenadas polares para facilitar rotación
                angle = random.uniform(0, 2 * math.pi)
                # Radio hasta la esquina para cubrir todo al rotar
                max_radius = math.sqrt(center_x**2 + center_y**2) + 50
                radius = random.uniform(0, max_radius)
                
                self.stars.append({
                    'layer': layer,
                    'angle': angle,
                    'base_radius': radius, # Guardar radio original
                    'radius': radius,
                    'speed': speeds[layer],
                    'color': colors[layer],
                    'size': sizes[layer],
                    'twinkle_offset': random.uniform(0, 2*math.pi),
                    'radial_speed': 0 # Velocidad de expansión
                })
        
        self.exploding = False
        self.imploding = False

    def trigger_explosion(self):
        """Inicia el efecto de warp/explosión (Salida)"""
        self.exploding = True
        self.imploding = False
        for star in self.stars:
            # Velocidad basada en la capa (más cerca = más rápido)
            # REDUCIDO: Velocidad inicial mucho más baja para que se vea la aceleración
            star['radial_speed'] = 2 + (star['layer'] * 2)

    def trigger_implosion(self):
        """Inicia el efecto de warp inverso (Entrada)"""
        self.imploding = True
        self.exploding = False
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        max_dist = math.sqrt(center_x**2 + center_y**2) + 200
        
        for star in self.stars:
            # Empezar lejos
            star['radius'] = star['base_radius'] + max_dist
            # Velocidad negativa (hacia adentro)
            # Más rápido cuanto más lejos para que lleguen a la vez aprox
            star['radial_speed'] = -20 - (star['layer'] * 10)

    def reset(self):
        """Reinicia las estrellas a su estado normal"""
        self.exploding = False
        self.imploding = False
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        max_radius = math.sqrt(center_x**2 + center_y**2) + 50
        
        for star in self.stars:
            star['radial_speed'] = 0
            star['radius'] = star['base_radius'] # Volver a posición base

    def update(self):
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        max_radius = math.sqrt(center_x**2 + center_y**2) + 100
        
        for star in self.stars:
            if self.exploding:
                # Movimiento radial explosivo (Hacia afuera)
                star['radius'] += star['radial_speed']
                star['radial_speed'] *= 1.02 # Aceleración suave (antes 1.05)
                
            elif self.imploding:
                # Movimiento radial implosivo (Hacia adentro)
                star['radius'] += star['radial_speed']
                
                # Frenado suave al llegar
                if star['radius'] <= star['base_radius']:
                    star['radius'] = star['base_radius']
                    # No paramos la velocidad aquí, simplemente clampamos el radio
                    # para que se queden en su órbita
                else:
                    # Aceleración inversa (frenado) o velocidad constante?
                    # Vamos a hacer que aceleren hacia adentro para efecto "succión"
                    pass 
                    
            else:
                # Movimiento rotacional normal
                star['angle'] += star['speed']
                
            # Si se salen del rango máximo en modo normal, reaparecen (loop)
            # En modo explosión dejamos que se vayan
            if not self.exploding and not self.imploding and star['radius'] > max_radius:
                star['radius'] = random.uniform(0, max_radius)

    def draw(self, surface, black_hole_radius=0):
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        
        for star in self.stars:
            # No dibujar si está dentro del agujero negro
            if star['radius'] < black_hole_radius:
                continue
                
            # Convertir a cartesianas
            x = center_x + star['radius'] * math.cos(star['angle'])
            y = center_y + star['radius'] * math.sin(star['angle'])
            
            # Solo dibujar si está en pantalla
            if 0 <= x <= SCREEN_WIDTH and 0 <= y <= SCREEN_HEIGHT:
                # Efecto de parpadeo (Twinkle)
                # Usamos el tiempo para variar el alpha o el color
                time = pygame.time.get_ticks() * 0.005
                twinkle = (math.sin(time + star['twinkle_offset']) + 1) / 2 # 0.0 a 1.0
                
                # Modificar alpha (simulado con color porque draw.circle no usa alpha por defecto sin surface)
                # O podemos dibujar rects pequeños o circulos.
                # Para optimizar, usamos el color base y lo oscurecemos un poco según el twinkle
                base_c = star['color']
                factor = 0.7 + 0.3 * twinkle # Brillo entre 70% y 100%
                color = (int(base_c[0]*factor), int(base_c[1]*factor), int(base_c[2]*factor))
                
                if star['size'] == 1:
                    surface.set_at((int(x), int(y)), color)
                else:
                    pygame.draw.circle(surface, color, (int(x), int(y)), star['size'])



import pygame
import math
import random
from config import *

class CelestialBody:
    def __init__(self, level):
        self.level = level
        self.color = MASS_COLORS.get(level, (100, 100, 100))
        
        # Variación de Tamaño (Size Variance)
        # El tamaño influye en la vida total
        # AUMENTADO: Rango mucho más amplio para que se note la diferencia visual
        self.size_multiplier = random.uniform(0.6, 2.2)
        
        # Defensa basada en Nivel (Mitigación de daño)
        # Nivel 1: 1.0 (Sin reducción), Nivel 2: 1.5, etc.
        self.defense_factor = 1.0 + (level - 1) * 0.5
        
        # Propiedades físicas
        self.mass = level * 10 * self.size_multiplier
        
        # Vida: Base por nivel * Multiplicador de tamaño
        # Escalado exponencial (x^1.5) para que los grandes se sientan mucho más "tanques"
        base_hp = 30 * level 
        self.max_health = base_hp * (self.size_multiplier ** 1.5)
        self.current_health = self.max_health
        
        # Valor: Escalado exponencial por nivel y tamaño
        # Aseguramos que el nivel tenga mucho peso
        # Nivel 1: ~5, Nivel 2: ~15, Nivel 3: ~30...
        self.value = int((level ** 1.8) * (self.size_multiplier ** 1.2) * 5)
        self.value = max(1, self.value)
        
        # Posición Polar (Optimización)
        self.orbit_radius = random.randint(SPAWN_DISTANCE_MIN, SPAWN_DISTANCE_MAX)
        self.angle = random.uniform(0, 2 * math.pi)
        
        # Velocidad angular: Más lejos = más lento (Kepler simplificado)
        # Ajustamos la velocidad para que sea jugable
        # REDUCIDO: Multiplicador bajado de 0.02 a 0.005 para movimiento mucho más lento y relajante
        self.angular_speed = (100 / self.orbit_radius) * 0.005 * random.choice([-1, 1])
        
        # Generación Procedural de Forma (Polígono)
        # El tamaño visual también se ve afectado por el multiplicador
        self.target_size = (10 + (level * 5)) * self.size_multiplier
        self.current_size = 0 # Para animación de entrada
        self.base_size = self.target_size # Referencia
        self.spawn_anim_timer = 0
        # Duración de animación escalada con el tamaño (más grande = más lento/pesado)
        self.spawn_anim_duration = int(30 + 20 * self.size_multiplier)
        
        self.points = self._generate_shape()
        
        # Coordenadas cartesianas para colisiones (se actualizan en update)
        self.x = 0
        self.y = 0

    def _generate_shape(self):
        """Genera un polígono irregular para parecer un asteroide"""
        num_points = random.randint(5, 9)
        points = []
        for i in range(num_points):
            # Ángulo para este vértice
            theta = (i / num_points) * 2 * math.pi
            # Variación aleatoria en el radio para que sea irregular
            # Usamos 1.0 como base, escalaremos al dibujar
            r = random.uniform(0.8, 1.2)
            px = r * math.cos(theta)
            py = r * math.sin(theta)
            points.append((px, py))
        return points

    def update(self):
        """Actualiza la posición basada en coordenadas polares"""
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
        
        # 1. Dibujar fondo oscuro (parte dañada)
        dark_color = [max(0, c - 100) for c in self.color]
        if len(screen_points) > 2:
            pygame.draw.polygon(surface, dark_color, screen_points)
        
        # 2. Dibujar parte viva (recortada verticalmente)
        # Creamos una superficie temporal para hacer el recorte
        # Calculamos el bounding box del polígono
        if not screen_points: return
        
        min_x = min(p[0] for p in screen_points)
        max_x = max(p[0] for p in screen_points)
        min_y = min(p[1] for p in screen_points)
        max_y = max(p[1] for p in screen_points)
        
        width = int(max_x - min_x) + 2
        height = int(max_y - min_y) + 2
        
        if width > 0 and height > 0:
            # Superficie temporal con canal alfa
            temp_surf = pygame.Surface((width, height), pygame.SRCALPHA)
            
            # Puntos relativos a la superficie temporal
            local_points = [(p[0] - min_x, p[1] - min_y) for p in screen_points]
            
            # Dibujar el polígono lleno en la temp surf
            if len(local_points) > 2:
                pygame.draw.polygon(temp_surf, self.color, local_points)
            
            # Calcular altura de recorte basada en salud
            health_pct = max(0, self.current_health / self.max_health)
            clip_height = int(height * (1 - health_pct))
            
            # "Borrar" la parte superior (daño) usando un rect con modo BLEND_RGBA_MULT (o simplemente fill transparente)
            # En pygame simple, podemos dibujar un rect transparente encima con flag especial, 
            # o más fácil: rellenar la parte superior con transparente.
            # Usaremos un rect para borrar la parte superior
            erase_rect = pygame.Rect(0, 0, width, clip_height)
            temp_surf.fill((0,0,0,0), erase_rect, special_flags=pygame.BLEND_RGBA_MULT)

            # Dibujar borde suavizado (Antialiasing)
            if len(local_points) > 2:
                pygame.draw.aalines(temp_surf, (255,255,255), True, local_points)

            # Blit al main surface
            surface.blit(temp_surf, (min_x, min_y))

        # 3. Dibujar borde (Nuevo)
        # Usamos el color oscuro para el borde, para definir bien la forma
        pygame.draw.polygon(surface, dark_color, screen_points, 2)
        # Añadimos suavizado al borde
        pygame.draw.aalines(surface, dark_color, True, screen_points)

    def take_damage(self, amount):
        # Aplicar defensa (reducción de daño)
        effective_damage = amount / self.defense_factor
        # Asegurar daño mínimo
        effective_damage = max(0.1, effective_damage)
        
        self.current_health -= effective_damage
        return self.current_health <= 0, effective_damage

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

    def draw(self, surface, zoom=1.0):
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        
        # Posición en pantalla (aunque el agujero suele estar en el centro, aplicamos zoom por si acaso se mueve)
        screen_x = center_x + (self.x - center_x) * zoom
        screen_y = center_y + (self.y - center_y) * zoom
        
        # Radio escalado
        screen_radius = self.radius * zoom
        
        # Efecto de pulsación suave
        pulse = math.sin(self.pulse_timer) * 2 * zoom
        
        # Anillo de acreción (decorativo)
        pygame.draw.circle(surface, (50, 50, 50), (screen_x, screen_y), int(screen_radius + (5 * zoom) + pulse), 2)
        
        # Cuerpo principal
        pygame.draw.circle(surface, COLOR_BLACK_HOLE, (screen_x, screen_y), int(screen_radius))

class Shockwave:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 10
        self.max_radius = SCREEN_WIDTH  # Cubrir pantalla
        self.alpha = 255
        self.speed = 20
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
    def __init__(self, x, y, color, radius, angle):
        self.x = x
        self.y = y
        self.color = color
        self.orbit_radius = radius
        self.angle = angle
        self.size = random.randint(3, 6) # Aumentado tamaño del debris
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
    def __init__(self, x, y, text, color=COLOR_DAMAGE_TEXT):
        self.x = x
        self.y = y
        self.text = str(text)
        self.color = color
        self.life = 60 # frames
        self.alpha = 255
        self.font = pygame.font.SysFont("Arial", 16, bold=True)

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
            
            # Sombra/Borde negro para contraste
            pygame.draw.line(surface, (0, 0, 0), start_pos, end_pos, 4)
            # Línea de color (Blanco para máximo contraste con el borde negro)
            pygame.draw.line(surface, (255, 255, 255), start_pos, end_pos, 2)
            
        # Punto central para precisión (Opcional, comentado por ahora)
        # pygame.draw.circle(surface, (0, 0, 0), (self.x, self.y), 4)
        # pygame.draw.circle(surface, (255, 255, 255), (self.x, self.y), 2)



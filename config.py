import pygame

# --- Configuración de Pantalla ---
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FPS = 60
TITLE = "Project Blackhole"

# --- Paleta de Colores (Cozy & Pastel) ---
# Fondo Beige Claro (Juego)
COLOR_BACKGROUND = (250, 243, 224)  # Un beige muy suave y cálido
# Fondo Espacio Profundo (Tienda/Mejoras)
COLOR_BACKGROUND_SHOP = (15, 15, 25)  # Azul muy oscuro / Negro espacial

# Elementos UI
COLOR_TEXT = (89, 69, 69)           # Marrón oscuro suave para texto (Juego)
COLOR_TEXT_LIGHT = (220, 220, 230)  # Texto claro para fondos oscuros (Tienda)
COLOR_TEXT_INVERTED = (250, 243, 224) # Beige claro para texto sobre negro
COLOR_CURSOR = (115, 95, 95)        # Marrón pastel suave para el cursor
COLOR_BLACK_HOLE = (25, 25, 25)     # Negro casi puro
COLOR_XP_BAR_BG = (230, 230, 230)   # Fondo barra XP
COLOR_XP_BAR_FILL = (100, 200, 200) # Relleno barra XP (Cyan pastel)
COLOR_DAMAGE_TEXT = (255, 100, 100) # Rojo pastel para daño
COLOR_MONEY_TEXT = (100, 200, 100)  # Verde pastel para dinero
COLOR_TIME_TEXT = (100, 200, 255)   # Azul pastel para tiempo extra
COLOR_CRIT_TEXT = (255, 200, 100)   # Naranja/Amarillo para críticos
COLOR_SHOCKWAVE = (255, 255, 255)   # Blanco para onda expansiva

# Jerarquía de Masas (Niveles)
# Cada nivel tiene un color pastel asociado.
# Formato: Nivel: (R, G, B)
MASS_COLORS = {
    1: (168, 216, 234),  # Pastel Blue (Nivel más bajo)
    2: (170, 214, 160),  # Pastel Green
    3: (255, 223, 186),  # Pastel Peach
    4: (255, 179, 186),  # Pastel Pink
    5: (255, 255, 186),  # Pastel Yellow
    6: (224, 187, 228),  # Pastel Purple (Nivel alto)
}

# --- Configuración de Juego ---
GAME_DURATION = 20      # Duración de la run en segundos (Reducido para partidas rápidas e intensas)
BASE_DAMAGE = 8         # Daño base por tick del jugador (Aumentado de 5 a 8)
DAMAGE_TICK_RATE = 30   # Cada cuántos frames se aplica daño (60 FPS / 30 = 2 veces por seg)

# --- Configuración del Jugador ---
CURSOR_RADIUS = 35      # Radio del área de efecto (Reducido de 80 para permitir mejoras)

# --- Configuración del Agujero Negro ---
BLACK_HOLE_RADIUS_BASE = 50

# --- Configuración de Desarrollo ---
DEBUG_MODE = True # Set to False for release
SAVE_FILE = "savefile.json"
BLACK_HOLE_GROWTH_FACTOR = 5 # Cuánto crece por nivel
XP_BASE_REQUIREMENT = 300    # XP necesaria para nivel 1->2 (Reducido de 500 para feedback más rápido)
XP_SCALING_FACTOR = 1.5      # Multiplicador de XP por nivel

# --- Configuración de Spawns ---
# Distancia desde el centro donde aparecen los cuerpos
SPAWN_DISTANCE_MIN = 150
SPAWN_DISTANCE_MAX = 400

# --- Sistema de Mejoras (Tienda) ---
# Balanceo de Economía:
# - Costes iniciales ajustados para ser alcanzables en 1-2 runs.
# - Multiplicadores ajustados para que no se vuelva imposible demasiado rápido.
UPGRADES = {
    "damage": {
        "name": "Fuerza de Marea",
        "category": "asteroid",
        "parent": None,
        "tree_pos": (0, 0),
        "base_cost": 40,       # Coste inicial accesible
        "cost_multiplier": 1.4, # Escalado moderado
        "description": "Aumenta el daño por tick",
        "base_value": BASE_DAMAGE,
        "increment": 3.0       # +3 daño (Impacto notable)
    },
    "radius": {
        "name": "Horizonte",
        "category": "blackhole",
        "parent": None,
        "tree_pos": (0, 0),
        "base_cost": 60,
        "cost_multiplier": 1.5,
        "description": "Aumenta el radio de acción",
        "base_value": CURSOR_RADIUS,
        "increment": 5 # +5 pixels
    },
    "duration": {
        "name": "Dilatación Temporal",
        "category": "blackhole",
        "parent": "radius",
        "tree_pos": (1, 0),
        "base_cost": 150,      # Caro pero valioso
        "cost_multiplier": 1.5,
        "description": "Probabilidad de +1s al destruir",
        "base_value": 0.0, # 0% probabilidad base
        "increment": 0.05, # +5% probabilidad por nivel
        "max_level": 5
    },
    "spawn_rate": {
        "name": "Atracción",
        "category": "asteroid",
        "parent": "damage",
        "tree_pos": (1, 0.8), # Un poco hacia abajo
        "base_cost": 80,       # Inversión media
        "cost_multiplier": 1.6,
        "description": "Más cuerpos celestes",
        "base_value": 12,      # Empezamos con 12 cuerpos (antes 10)
        "increment": 2         # +2 cuerpos (antes +1, para que se note más)
    },
    "mass": {
        "name": "Nucleosíntesis",
        "category": "asteroid",
        "parent": "damage",
        "tree_pos": (1, -0.8), # Un poco hacia arriba
        "base_cost": 250,      # Gatekeeper de contenido (Nuevos niveles)
        "cost_multiplier": 2.0, # Escala rápido
        "description": "Desbloquea cuerpos de mayor nivel",
        "base_value": 0,
        "increment": 1 # +1 nivel
    },
    "resonance": {
        "name": "Resonancia",
        "category": "unique",
        "parent": None,
        "tree_pos": (0, 0),
        "base_cost": 500, # Meta a largo plazo
        "cost_multiplier": 1.0,
        "description": "Recupera oleada al subir nivel",
        "base_value": 0.0,
        "increment": 1.0,
        "max_level": 1
    },
    "fission": {
        "name": "Fisión",
        "category": "asteroid",
        "parent": "spawn_rate",
        "tree_pos": (2, 0.8),
        "base_cost": 200,
        "cost_multiplier": 1.5,
        "description": "Probabilidad de dividir al destruir",
        "base_value": 0.0,
        "increment": 0.1, # +10% probabilidad
        "max_level": 5
    },
    "critical_chance": {
        "name": "Singularidad Crítica",
        "category": "asteroid",
        "parent": "mass",
        "tree_pos": (2, -0.8),
        "base_cost": 150,
        "cost_multiplier": 1.5,
        "description": "Probabilidad de daño crítico",
        "base_value": 0.0,
        "increment": 0.05 # +5% probabilidad
    },
    "critical_damage": {
        "name": "Colapso Gravitacional",
        "category": "asteroid",
        "parent": "critical_chance",
        "tree_pos": (3, -0.8),
        "base_cost": 200,
        "cost_multiplier": 1.5,
        "description": "Aumenta el daño crítico",
        "base_value": 1.5, # 150% base
        "increment": 0.5 # +50% daño
    },
    "planet_unlock": {
        "name": "Formación Planetaria",
        "category": "planet",
        "parent": "mass",
        "tree_pos": (1, -1.6), # Debajo de masa
        "base_cost": 1000,     # Coste alto, late game
        "cost_multiplier": 2.0,
        "description": "Permite la formación de Planetas",
        "base_value": 0,
        "increment": 1,
        "max_level": 1
    },
    "planet_mass": {
        "name": "Acreción Planetaria",
        "category": "planet",
        "parent": "planet_unlock",
        "tree_pos": (2, -1.6),
        "base_cost": 1500,
        "cost_multiplier": 2.0,
        "description": "Aumenta el nivel de los Planetas",
        "base_value": 0,
        "increment": 1
    },
    "moon_unlock": {
        "name": "Captura Lunar",
        "category": "planet",
        "parent": "planet_unlock",
        "tree_pos": (1, -2.4), # Debajo de planet unlock
        "base_cost": 2000,
        "cost_multiplier": 2.0,
        "description": "Planetas pueden tener lunas",
        "base_value": 0,
        "increment": 1,
        "max_level": 1
    },
    "moon_chance": {
        "name": "Estabilidad Orbital",
        "category": "planet",
        "parent": "moon_unlock",
        "tree_pos": (2, -2.4),
        "base_cost": 1000,
        "cost_multiplier": 1.5,
        "description": "Probabilidad de lunas",
        "base_value": 0.05, # 5% base
        "increment": 0.05, # +5% por nivel
        "max_level": 5
    },
    "planet_fission": {
        "name": "Fragmentación Planetaria",
        "category": "planet",
        "parent": "planet_mass",
        "tree_pos": (3, -1.6),
        "base_cost": 2000,
        "cost_multiplier": 1.8,
        "description": "Probabilidad de dividir planetas",
        "base_value": 0.0,
        "increment": 0.1, # +10% probabilidad
        "max_level": 5
    }
}

# --- Configuración de Lunas ---
MOON_ORBIT_DURATION = 5.0 # Segundos que dura la luna orbitando el cursor
MOON_SPEED_BOOST = 0.05   # 5% de velocidad extra por luna
MOON_SIZE = 14            # Tamaño visual de la luna en planeta (Aumentado para visibilidad)
MOON_SIZE_CURSOR = 9      # Tamaño visual de la luna en cursor (Aumentado de 6)
MOON_ORBIT_RADIUS = 25    # Distancia de órbita relativa al planeta
MOON_CURSOR_ORBIT_RADIUS = 50 # Distancia de órbita en el cursor
MAX_CURSOR_MOONS = 8      # Máximo de lunas orbitando el cursor

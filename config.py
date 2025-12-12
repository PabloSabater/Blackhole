import pygame

# --- Configuración de Pantalla ---
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FPS = 60
TITLE = "Cosmic Incremental"

# --- Paleta de Colores (Cozy & Pastel) ---
# Fondo Beige Claro
COLOR_BACKGROUND = (250, 243, 224)  # Un beige muy suave y cálido

# Elementos UI
COLOR_TEXT = (89, 69, 69)           # Marrón oscuro suave para texto
COLOR_TEXT_INVERTED = (250, 243, 224) # Beige claro (igual al fondo original) para texto sobre negro
COLOR_CURSOR = (150, 150, 150)      # Gris para el borde del cursor
COLOR_BLACK_HOLE = (25, 25, 25)     # Negro casi puro
COLOR_XP_BAR_BG = (230, 230, 230)   # Fondo barra XP
COLOR_XP_BAR_FILL = (100, 200, 200) # Relleno barra XP (Cyan pastel)
COLOR_DAMAGE_TEXT = (255, 100, 100) # Rojo pastel para daño
COLOR_MONEY_TEXT = (100, 200, 100)  # Verde pastel para dinero
COLOR_TIME_TEXT = (100, 200, 255)   # Azul pastel para tiempo extra
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
GAME_DURATION = 30      # Duración de la run en segundos
BASE_DAMAGE = 5         # Daño base por tick del jugador (Aumentado de 1 a 5)
DAMAGE_TICK_RATE = 30   # Cada cuántos frames se aplica daño (60 FPS / 30 = 2 veces por seg)

# --- Configuración del Jugador ---
CURSOR_RADIUS = 35      # Radio del área de efecto (Reducido de 80 para permitir mejoras)

# --- Configuración del Agujero Negro ---
BLACK_HOLE_RADIUS_BASE = 50
BLACK_HOLE_GROWTH_FACTOR = 5 # Cuánto crece por nivel
XP_BASE_REQUIREMENT = 500    # XP necesaria para nivel 1->2
XP_SCALING_FACTOR = 1.5      # Multiplicador de XP por nivel

# --- Configuración de Spawns ---
# Distancia desde el centro donde aparecen los cuerpos
SPAWN_DISTANCE_MIN = 150
SPAWN_DISTANCE_MAX = 400

# --- Sistema de Mejoras (Tienda) ---
UPGRADES = {
    "damage": {
        "name": "Fuerza de Marea",
        "category": "asteroid",
        "parent": None,
        "tree_pos": (0, 0),
        "base_cost": 10,
        "cost_multiplier": 1.5,
        "description": "Aumenta el daño por tick",
        "base_value": BASE_DAMAGE,
        "increment": 2.0 # +2 daño
    },
    "radius": {
        "name": "Horizonte",
        "category": "blackhole",
        "parent": None,
        "tree_pos": (0, 0),
        "base_cost": 10,
        "cost_multiplier": 1.6,
        "description": "Aumenta el radio de acción",
        "base_value": CURSOR_RADIUS,
        "increment": 5 # +5 pixels
    },
    "duration": {
        "name": "Dilatación Temporal",
        "category": "blackhole",
        "parent": "radius",
        "tree_pos": (1, 0),
        "base_cost": 200,
        "cost_multiplier": 1.4,
        "description": "Probabilidad de +1s al destruir",
        "base_value": 0.0, # 0% probabilidad base
        "increment": 0.05 # +5% probabilidad por nivel
    },
    "spawn_rate": {
        "name": "Atracción",
        "category": "asteroid",
        "parent": "damage",
        "tree_pos": (1, 0.8), # Un poco hacia abajo
        "base_cost": 10,
        "cost_multiplier": 1.8,
        "description": "Más cuerpos celestes",
        "base_value": 10, # Valor inicial de bodies_per_level
        "increment": 1 # +1 cuerpo maximo
    },
    "mass": {
        "name": "Nucleosíntesis",
        "category": "asteroid",
        "parent": "damage",
        "tree_pos": (1, -0.8), # Un poco hacia arriba
        "base_cost": 10,
        "cost_multiplier": 1.5,
        "description": "Aumenta el nivel de los cuerpos",
        "base_value": 0,
        "increment": 1 # +1 nivel
    },
    "resonance": {
        "name": "Resonancia",
        "category": "unique",
        "parent": None,
        "tree_pos": (0, 0),
        "base_cost": 500, # Coste alto por ser única
        "cost_multiplier": 1.0, # No escala
        "description": "Recupera oleada al subir nivel",
        "base_value": 0.0,
        "increment": 1.0, # 100% refill (booleano en la práctica)
        "max_level": 1 # Solo se puede comprar una vez
    },
    "fission": {
        "name": "Fisión",
        "category": "asteroid",
        "parent": "spawn_rate",
        "tree_pos": (2, 0.8), # Sigue la línea de spawn_rate
        "base_cost": 10,
        "cost_multiplier": 1.6,
        "description": "Probabilidad de dividir al destruir",
        "base_value": 0.0,
        "increment": 0.1 # +10% probabilidad
    }
}

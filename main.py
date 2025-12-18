import pygame
import sys
from config import *
from game_state import GameManager, GameState

def main():
    # Inicialización de Pygame
    pygame.init()
    
    # Flags de pantalla: Doble Buffer y VSync para evitar flickering/tearing
    flags = pygame.DOUBLEBUF
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags, vsync=1)
    
    # --- Configuración de Icono ---
    # Generar icono proceduralmente (Agujero negro sobre fondo beige)
    icon_size = 32
    icon_surface = pygame.Surface((icon_size, icon_size))
    icon_surface.fill(COLOR_BACKGROUND)
    # Dibujar agujero negro
    pygame.draw.circle(icon_surface, COLOR_BLACK_HOLE, (icon_size//2, icon_size//2), icon_size//2 - 2)
    # Dibujar borde suave (opcional, para que destaque)
    pygame.draw.circle(icon_surface, (50, 50, 50), (icon_size//2, icon_size//2), icon_size//2 - 2, 1)
    pygame.display.set_icon(icon_surface)

    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()
    
    # Ocultar el cursor del sistema operativo porque usamos uno custom
    pygame.mouse.set_visible(False)

    # Instancia del Gestor de Juego
    game = GameManager()

    running = True
    while running:
        # 1. Gestión de Eventos
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.KEYDOWN:
                # Debug Inputs
                if DEBUG_MODE:
                    game.handle_debug_input(event.key)

                if event.key == pygame.K_ESCAPE:
                    # Toggle Pausa
                    if game.state == GameState.PLAYING:
                        game.state = GameState.PAUSED
                    elif game.state == GameState.PAUSED:
                        game.state = GameState.PLAYING
                
                if event.key == pygame.K_q:
                    if game.state == GameState.PAUSED:
                        game.end_run_from_pause()
                
                if event.key == pygame.K_r:
                    if game.state == GameState.SUMMARY:
                        game.reset_run()
                
                if event.key == pygame.K_m:
                    if game.state == GameState.SUMMARY:
                        game.state = GameState.TRANSITION_TO_SHOP

            # Pasar eventos de mouse al gestor (para la tienda)
            if event.type == pygame.MOUSEBUTTONDOWN:
                game.handle_input(event)

        # 2. Actualización Lógica
        game.update()

        # 3. Renderizado
        game.draw(screen)

        # 4. Control de FPS
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()

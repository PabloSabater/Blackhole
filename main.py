import pygame
import sys
from config import *
from game_state import GameManager, GameState

def main():
    # Inicialización de Pygame
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
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

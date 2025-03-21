import logging

from app import create_app

logger = logging.getLogger(__name__)

try:
    app = create_app()
    logger.info('Flask alkalmazás sikeresen elindult.')
except Exception as e:
    logger.critical(f'Kritikus hiba, nem sikerült elindítani az alkalmazást: {e}', exc_info=True)
    raise SystemExit('A program leállt, mert az alkalmazás nem tudott elindulni.')

if __name__ == '__main__':
    try:
        logger.info('Az alkalmazás fut...')
        app.run(host="0.0.0.0", port=5000, debug=True)
    except Exception as e:
        logger.critical(f'Kritikus hiba az alkalmazás futtatása közben: {e}', exc_info=True)
        raise SystemExit('A program leállt egy kritikus hiba miatt.')

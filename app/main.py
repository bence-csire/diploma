import logging

from app import create_app

# TODO Kapcsolódó eszköz jelzése a teszt oldalon (honlap)
# TODO disconnect gomb hozáádása
# TODO THREDING sleep helyett!!!
# TODO honlapon eredményeknél választani lehessen

logger = logging.getLogger(__name__)

try:
    app = create_app()
    logger.info("Flask alkalmazás sikeresen elindult.")
except Exception as e:
    logger.critical(f"Nem sikerült elindítani az alkalmazást: {e}", exc_info=True)
    raise SystemExit("A program leállt, mert az alkalmazás nem tudott elindulni.")

if __name__ == '__main__':
    try:
        logger.info("Az alkalmazás fut...")
        app.run(host="0.0.0.0", port=5000, debug=True)
    except Exception as e:
        logger.critical(f"Az alkalmazás futtatása közben hiba történt: {e}", exc_info=True)
        raise SystemExit("A program leállt egy kritikus hiba miatt.")

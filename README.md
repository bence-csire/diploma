# Projekt címe

Android tesztelés Flaskkel

## Leírás

A projekt egy Flask alapú webalkalmazás, melynek célja az Android eszközök tesztelésének automatizálása. Az alkalmazás ADB (Android Debug Bridge) segítségével csatlakozik az eszközökhöz, és különböző teszteket futtat:
- **Indítási idő mérése**: Az alkalmazás indítási idejét méri és rögzíti az adatbázisban.
- **CPU használat mérése**: Lekéri az alkalmazás CPU használatát.
- **Memória használat mérése**: Ellenőrzi az alkalmazás memóriahasználatát.

Az eredmények adatbázisban kerülnek tárolásra, és a felhasználó egy grafikon segítségével tekintheti meg az utolsó 10 mérés eredményét és azok átlagát.

## Kezdő lépések
A következő lépések segítenek a projekt helyi környezetben történő futtatásában.

### Függőségek
- **Python 3.8+**
  
- **Flask** – A webalkalmazás fejlesztéséhez.
- **Flask-WTF** – Formok kezeléséhez és validációhoz.
- **Flask-Bootstrap (Bootstrap5)** – Megjelenés és stílus biztosításához.
- **Flask-SQLAlchemy** – Adatbázis kezeléséhez és ORM használatához.
- **WTForms** – Űrlapok és validátorok megvalósításához.
- **ADB (Android Debug Bridge)** – Az Android eszközökkel való kommunikációhoz (győződj meg róla, hogy a rendszereden telepítve van).
- **Chart.js** – Az eredmények vizualizációjához (CDN-en keresztül töltődik be).

A pontos verziók megtalálhatóak a **requirements.txt** fileban

### Telepítés
1. **Repository klónozása**  
   Klónozd a repositoryt a következő paranccsal: <br />
   git clone https://github.com/bence-csire/diploma

2. Projekt mappába lépés <br />
   Navigálj a projekt könyvtárába

3. Virtuális környezet létrehozása <br />
   python3 -m venv venv

4. Virtuális környezet aktiválása <br />
   Windows: <br />
   venv\Scripts\activate

   Linux: <br />
   source venv/bin/activate

5. Függőségek telepítése <br />
   pip install -r requirements.txt

6. Környezeti változók beállítása <br />
   FLASK_SECRET_KEY – Az alkalmazás titkos kulcsa. <br />
   DATABASE_URI – Az adatbázis elérési útja (alapértelmezetten sqlite:///android.db) <br />
   (config.py file-ban van egy alapértelmezett, teszteléshez az is elég)
   
### Program futtatása
1. Android eszköz csatlakoztatása a számítógéphez, fejlesztői beállításokkal
   
2. Flask szerver indítása
   python main.py

3. Böngésző megnyitása
   http://localhost:5000

4. Tesztelés menete
   - Az első oldalon add meg a tesztelni kívánt Android eszköz IP címét.
   - Ha az IP cím érvényes, az alkalmazás ADB-n keresztül csatlakozik az eszközhöz.
   - Válaszd ki a futtatandó tesztet (indítási idő, CPU használat vagy memória használat).
   - A teszt végrehajtása után az eredmények az "Eredmények" oldalon grafikon formájában jelennek meg.

## Segítség
Hibaelhárítás:
  - Ellenőrizd, hogy az IP cím helyesen van-e megadva, és az eszköz engedélyezte-e az ADB kapcsolódást.
  - Nézd meg a app.log fájlt, ahol részletes naplózási információk találhatók a hibák okairól.
További információk:
  - A kódban található docstring-ek és kommentek (magyar nyelven) részletesen ismertetik a függvények működését.

## Szerző

Csire Bence

## Verziók


## Elismerés
* [html5up](https://html5up.net/alpha)

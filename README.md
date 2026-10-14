# Arbetsställen i Luleå kommun

Publik arbetsställeöversikt för **Luleå kommun (SCB kommunkod 2580)**.

## Status

Webbsidan `docs/index.html` är på plats. En autentiserad SCB-koppling är förberedd via GitHub Actions men **ingen aktuell arbetsställedata har ännu hämtats** och anslutningen är därför inte verifierad. Webbplatsen visar detta tydligt och hittar inte på antal eller adresser.

SCB:s allmänna företagsregister har ett avgiftsfritt API med personligt tilldelad API-nyckel: https://www.scb.se/vara-tjanster/bestall-data-och-statistik/foretagsregistret/avgiftsfria-uppgifter-i-foretagsregistret/ . Ansök via https://registreraafr.scb.se/ och läs **den aktuella OpenAPI-specifikationen** för sökning på arbetsställen och kommun.

## Koppla på API:et

Lägg till GitHub Actions *repository secrets* under **Settings → Secrets and variables → Actions**:

- `SCB_API_KEY`: personlig API-nyckel (lägg den aldrig i webbplatsens JavaScript, issues, datafiler eller chatt)
- `SCB_API_URL`: fullständig HTTPS-sökendpoint för arbetsställen från SCB:s dokumentation
- `SCB_API_QUERY_JSON`: JSON-anropskropp **enligt SCB:s faktiska OpenAPI-schema**, filtrerad på arbetsställets kommun **2580 (Luleå)**. Ett godtyckligt/ogranskat frågeformat fungerar inte.

Valfria repository variables: `SCB_API_METHOD` (standard POST) och `SCB_API_KEY_HEADER` (standard x-api-key); anpassa till SCB:s officiella dokumentation.

Starta **Actions → Hämta SCB arbetsställen Luleå → Run workflow**. Schemat är måndagar. Hämtningen stoppar publicering om ett kommunfält inte verifieras, om svarets form inte kan läsas, eller om en sida kan vara ofullständig (5 000 rader). Ett komplett kommunuttag kräver paginering om fler än 5 000 poster finns. Mappningen av SCB:s nya fältnamn behöver fortfarande jämföras mot ett riktigt API-svar innan kopplingen kan beskrivas som driftsatt.

**Viktigt före publicering:** kontrollera SCB:s användarvillkor, vidareutnyttjande av registeruppgifter och personuppgifter för enskilda näringsidkare. Den inbyggda utmatningen omfattar namn, besöksadress, SNI och anställdklass, och får inte betraktas som juridiskt godkänd enbart för att API:t ger en träff. Ingen koordinatgeokodning är implementerad ännu.

## Publicering

Publicera från `main` / `docs` under **Settings → Pages** om GitHub Pages inte redan är aktiverat.

Ingen API-nyckel exponeras i Pages-sidan. Efter genomförd och godkänd hämtning läses `docs/data/arbetsstallen_lulea.json` som sökbar lista.

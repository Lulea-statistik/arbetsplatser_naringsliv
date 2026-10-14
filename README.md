# Arbetsställen i Luleå kommun

Publik översikt för SCB:s allmänna företagsregister, arbetsställets kommunkod **2580**.

## Aktuell status
- Nya SCB-API:t på `https://apiafr.scb.se` är verifierat. Autentisering med GitHub-secret `SCB_API_KEY` i headern `X-API-Key`.
- Den 14 oktober 2026 hämtades **13 965 arbetsställen** och antalet stämde med SCB:s count.
- Webbplatsen visar offentliga aggregerade kategorifördelningar för anställdklass, arbetsställestatus, SNI-avdelning och reklamspärr.
- Enskilda företagsnamn, personnummer, organisationsnummer och adresser publiceras inte.
- En **månadsvis aggregerad historik med ändringslogg** är implementerad men behöver första verifierade månads-körningen.

## Webbplats och data
- Webb: https://lulea-statistik.github.io/arbetsplatser_naringsliv/
- Senaste sammanställning: `docs/data/scb_lulea_aggregate.json`
- Månadsbilder efter första månadskörning: `docs/data/history/YYYY-MM.json`
- Gles förändringslogg: `docs/data/scb_monthly_changes.json`

## Schemalagd hämtning
Använd GitHub Actions-flödet **Hämta aggregerad arbetsställestatistik Luleå**. Det körs den **5:e i månaden kl. 08:10 UTC** eller manuellt via `workflow_dispatch`. Varje körning har egen hård budget på **20 anrop** inklusive återförsök och en lägre takt än SCB:s avtalsgräns **5 anrop/sekund**. Detta är **inte** en central timkvot över flera flöden.

Läs [körningsstrategin](docs/KORNINGSSTRATEGI-SCB.md) för historikens semantik och skillnaden mellan aggregerade och individuella förändringar.

## Viktigt om GDPR
API-svaren kan innehålla personuppgifter för fysiska personer. Offentlig historik innehåller inga enskilda poster. Ett framtida företagsvis historik-/kartlager kräver separat integritetsbedömning och skyddad lagring; en hash eller ersatt `peOrgNr` ger inte automatisk anonymitet. Källan är **SCB, allmänna företagsregistret – egen bearbetning**.

Avtalsunderlag: [SCB:s användarvillkor](docs/SCB-API-ANVANDARVILLKOR.md).

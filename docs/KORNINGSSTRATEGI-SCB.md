# Körningsstrategi för SCB:s företagsregister

## Driftsatt första etapp: offentlig aggregerad historik

- Källa: SCB:s nya företagsregister-API, `GET /v1/arbetsstallen/kommun/2580`.
- Kommunkod 2580 avser **arbetsstället**, inte enbart huvudkontoret.
- En schemalagd hämtning den **5:e varje månad kl. 08:10 UTC** (svensk tid 09:10 vintertid, 10:10 sommartid). Manuell körning går via Actions.
- Varje körning använder först `count`, sedan `limit=2000` och `cursorId`. Historiskt har 13 965 poster inneburit 7 sidor och 8 API-anrop inklusive count.
- En **hård budget på högst 20 HTTP-anrop per körning inklusive återförsök**, med minst 0,5 sekunder mellan anrop. SCB:s avtal anger **max 5 anrop/sekund/nyckel**. Någon separat timkvot framgår **inte** av avtalet. 20/körning är vår egen säkerhetsregel, **inte** en ny SCB-gräns.
- Budgeten är **per körning, inte global per timme**. Andra workflow, manuella körningar eller andra användare av samma API-nyckel kan därför förbruka anrop parallellt. För en verklig central timbudget krävs en gemensam, transaktionssäker kvothanterare. Kör inte andra hämtningar parallellt.
- En fullständig kommunhämtning kräver lika många unika CFAR som SCB:s count och inget duplicerat cursorId. Avvikelse stoppar publicering.
- Den gamla, ännu inte integritetssäkrade veckohämtningen är borttagen från schemaläggning.

## Publicerade data

- `docs/data/scb_lulea_aggregate.json`: senaste verifierade månadsobservation och kategorifördelningar.
- `docs/data/history/YYYY-MM.json`: en aggregerad ögonblicksbild per faktiskt observerad månad. En omkörning samma månad ersätter samma månadsfil, den skapar inte extra månader.
- `docs/data/scb_monthly_changes.json`: en glest lagrad **förändringslogg på aggregerad nivå**. Första månaden är baslinje. Därefter skrivs bara förändrade antal/kategorier jämfört med föregående observerade månadsbild.

**Tolkning av utebliven händelse:** Om två **observerade** månader saknar förändringshändelse för en viss aggregerad kategori har kategorins antal inte ändrats. Det betyder **inte** att inget företag bytte status: lika många kan ha lämnat som tillkommit. Det säger inte heller något om en saknad månad. Inga äldre månader före första observationen rekonstrueras.

## Integritet och vidare utveckling

Offentliga GitHub-snapshots innehåller **inte** `peOrgNr`, `cfarNr`, namn, adress, koordinater eller enskilda statusförändringar. Registerposterna behandlas i körningens minne och lagras inte i repo eller Actions-artefakter.

Ett framtida företagsvis deltaformat, där oförändrade variabler ärvs från tidigare månad, kräver **skyddad lagring utanför det publika GitHub-repot**, en rättslig bedömning av personuppgiftsbehandlingen och en process för att särskilja fysiska personer från juridiska personer. Ett hashat eller slumpat företags-ID är inte automatiskt anonymt. Ett skyddat baseline- och händelselager skulle kunna innehålla:
- baslinje: skyddat internt arbetsställe-ID, startmånad, godkända variabelvärden
- ändringshändelse: skyddat ID, månad, variabel, nytt värde
- tillkomst/avregistrering och frånvaro ska särskiljas från utebliven förändring

**Inga individuella historikposter publiceras innan dessa skydd är godkända.**

## Kvalitet och förändring över tid

- SCB:s `aeStat`, `anstKl`, SNI-avdelning och reklamspärrsstatus aggregeras; celler under fem sammanförs före publicering. Reglerna är ett första försiktighetsmått, inte en garanti om anonymitet för framtida mer detaljerade korstabeller.
- Kontroller: antal, unika CFAR, paginering, totalsumma per variabel, månadens datum och publiceringsfel.
- Planerad utökning efter granskning: kodtexter från SCB, bransch och region på lämplig aggregeringsnivå, kontroll av uppdateringsdatum/källbryt, nyckelhantering och statistik över datakvalitet.
- Källhänvisning: **SCB, allmänna företagsregistret – egen bearbetning**.
- SCB:s avtalsvillkor finns i `docs/SCB-API-ANVANDARVILLKOR.md`.

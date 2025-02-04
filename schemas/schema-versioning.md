# Avro-skeemojen hallintamalli

Tämä dokumentti määrittelee, miten Avro-skeemoja ylläpidetään ja versioidaan hajautetussa tapahtumalähtöisessä signaalimittausjärjestelmässä. Skeemahallinnan tavoitteena on taata joustava, yhteensopiva ja hallittavissa oleva tietorakenne, joka mahdollistaa järjestelmän skaalautuvuuden ja pitkäikäisyyden.

## 1. Yleiset periaatteet

Avro-skeemat ovat järjestelmän datan ydinrakenne, ja niiden hallinta noudattaa seuraavia periaatteita:

- Jokainen skeema on versioitu erikseen. Kun skeemaan tehdään muutoksia, luodaan uusi versio, eikä vanhaa muokata.
- Skeemamuutokset ovat aina taaksepäin yhteensopivia. Uusia kenttiä voidaan lisätä, mutta vanhoja kenttiä ei poisteta tai muuteta.
- Skeemat ovat järjestetty hierarkkisesti tiedostorakenteessa, jossa jokainen versio tallennetaan omassa hakemistossaan.
- Kaikki kentät ovat oletuksena valinnaisia (`optional`), jotta vanhat datanlukijat voivat edelleen käsitellä uusia skeemaversioita ilman virheitä.
- Enum-tyyppejä ei käytetä, koska niiden muokkaaminen aiheuttaa yhteensopivuusongelmia.
- Skeemat tallennetaan Avro-muodossa, mutta ne voivat toimia JSON/Parquet-tiedostojen pohjana.

## 2. Skeemojen versionumeroitu tallennus

Skeemat tallennetaan versionumeroituina hakemistossa `/schemas/avro/` seuraavalla rakenteella:

```
/schemas/
  ├── avro/
  │   ├── 001/
  │   │   ├── measurement_schema.avsc
  │   │   ├── trigger_schema.avsc
  │   │   ├── metadata_schema.avsc
  │   ├── 002/
  │   │   ├── measurement_schema.avsc
  │   │   ├── trigger_schema.avsc
  │   │   ├── metadata_schema.avsc
  │   ├── 003/
  │       ├── measurement_schema.avsc
  │       ├── trigger_schema.avsc
  │       ├── metadata_schema.avsc
```

- Jokaisella skeemalla on oma numerointinsa (001, 002, 003, ...), eikä aiempia versioita koskaan muokata.
- Kun skeema päivittyy, uusi versio lisätään uuteen kansioon, eikä vanhaa skeemaa poisteta.
- Versionumerointi ei ole lineaarinen per skeema, vaan globaali kaikille skeemoille. Esimerkiksi jos `measurement_schema.avsc` päivittyy ja saa version 004, mutta `trigger_schema.avsc` ei muutu, `trigger_schema.avsc` pysyy vanhassa versiossa.

## 3. Yhteensopivuusstrategia

Jotta järjestelmän eri osat voivat toimia saumattomasti eri skeemaversioiden kanssa, noudatamme seuraavia sääntöjä:

| Muutos                     | Sallittu? | Perustelu                                           |
| -------------------------- | --------- | --------------------------------------------------- |
| Uuden kentän lisääminen | Kyllä    | Valinnaisuus (`optional`) estää virheet         |
| Kentän poistaminen        | Ei        | Vanhat sovellukset eivät osaisi käsitellä tätä |
| Kentän nimen muuttaminen  | Ei        | Rikkoo olemassa olevat tiedonlukijat                |
| Kentän tyypin muuttaminen | Ei        | Voi aiheuttaa vakavia yhteensopivuusongelmia        |
| Oletusarvon lisääminen   | Kyllä    | Auttaa yhteensopivuudessa                           |
| Enum-arvon lisääminen    | Ei        | Enum-muuttujien muuttaminen rikkoo serialisoinnin   |

## 4. Skeemajulkaisu ja käyttöönotto

Skeemajulkaisu tehdään seuraavalla prosessilla:

1. **Uuden skeeman luonnin yhteydessä**

   - Uusi skeema lisätään uuteen versiohakemistoon (`/schemas/avro/{versio}/`).
   - Skeeman `doc`-kenttään lisätään kuvaus muutoksista.
2. **Skeeman hyväksyntä ja testaus**

   - Skeema testataan yksikkötesteillä varmistaen, että se on yhteensopiva aiempien versioiden kanssa.
   - Validoidaan Avro-työkalujen avulla (`avro-tools`, `pyspark` jne.).
3. **Skeeman julkaisu ja versiointi**

   - Kun skeema on testattu, se lisätään versionhallintaan (GitHub/S3).
   - Kaikki uudet skeemaversiot kommunikoidaan kehittäjäyhteisölle.

## 5. Muutoksenhallinta ja dokumentaatio

Kaikki skeemat sisältävät `doc`-kentän, jossa kuvataan:

- Skeeman käyttötarkoitus
- Yksittäisten kenttien selitykset ja yksiköt
- Mahdolliset yhteensopivuusvaroitukset

Esimerkki skeeman dokumentaatiosta:

```json
{
  "name": "measurement_id",
  "type": "string",
  "doc": "Mittauksen yksilöllinen tunniste (UUID)"
},
{
  "name": "timestamp",
  "type": "long",
  "logicalType": "timestamp-millis",
  "doc": "Mittauksen aikaleima UTC-aikavyöhykkeessä"
}
```

## 6. Integraatio datan tallennuksen kanssa

- Avro toimii skeemadokumentaationa, mutta tallennus tehdään Parquet-muodossa.
- Partitiointi perustuu aikaleimaan, jotta tietokyselyt ovat nopeita ja skaalautuvia:

```
s3://measurement-data/
  ├── year=2025/
  │   ├── month=02/
  │   │   ├── day=01/
  │   │   │   ├── hour=00/
  │   │   │   │   ├── measurement-001.parquet
  │   │   │   │   ├── measurement-002.parquet
```

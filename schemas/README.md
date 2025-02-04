# RF-Mittausjärjestelmän Parquet-tiedostojen Tietorakenne

Tietorakenne kuvaa mittausjärjestelmän keräämää dataa, joka on optimoitu tapahtumalähtöiseen tallennukseen ja analyysiin. Skeema kuvataan Avro-formaatissa, mikä mahdollistaa versionhallinnan ja taaksepäin yhteensopivuuden.

## Keskeiset Ominaisuudet

- Reaaliaikainen ja tapahtumalähtöinen analyysi
- Trigger-pohjainen tallennus merkittävien tapahtumien eristämiseksi
- Parquet-muotoinen tallennus tehokasta analytiikkaa varten
- HyperLogLog-algoritmi korkean kardinaliteetin arviointiin
- Skaalautuva analyysi Apache Sparkilla ja Jupyter Notebookilla

## Tietokenttien Kuvaus

| Kenttä                 | Kuvaus                                 | Tyyppi      | Esimerkki                      |
| ----------------------- | -------------------------------------- | ----------- | ------------------------------ |
| `measurement_id`      | Mittausistunnon yksilöllinen tunniste | String      | "abc123-xyz789"                |
| `timestamp`           | Mittauksen aikaleima (UTC, ms)         | Long        | 1699876543123                  |
| `measurement_date`    | Mittauspäivämäärä (YYYYMMDD)      | Integer     | 20250203                       |
| `measurement_hour`    | Mittaustunti (0–23)                   | Integer     | 14                             |
| `duration_ms`         | Mittauksen tai tapahtuman kesto (ms)   | Long        | 5000                           |
| `center_frequency_hz` | Keskitaajuus (Hz)                      | Long        | 1420000000                     |
| `sample_rate_hz`      | Näytteenottotaajuus (Hz)              | Long        | 2400000                        |
| `antenna_info`        | Antennin tekniset tiedot               | Avro Record | Katso AntennaInfo-skeema       |
| `environmental`       | Mittausympäristön tiedot             | Avro Record | Katso EnvironmentalData-skeema |
| `trigger_info`        | Triggerin tiedot                       | Avro Record | Katso TriggerInfo-skeema       |
| `event_id`            | Tapahtuma-ID (nullable)                | String      | "evt-456def"                   |
| `raw_data`            | RF-näytteet (base64-koodattu)         | Bytes       | "A1B2C3D4..."                  |
| `fft_results`         | FFT-analyysin tulokset                 | Avro Record | Katso FFTResults-skeema        |
| `analysis_metrics`    | Analyysitiedot ja mittarit             | Avro Record | Katso AnalysisMetrics-skeema   |
| `system_info`         | Järjestelmän metatiedot              | Avro Record | Katso SystemInfo-skeema        |

## Antennin Tiedot (AntennaInfo)

| Kenttä              | Kuvaus                       | Tyyppi | Esimerkki     |
| -------------------- | ---------------------------- | ------ | ------------- |
| `antenna_type`     | Antennityyppi                | String | "Yagi"        |
| `lna_gain_db`      | LNA:n vahvistus (dB)         | Double | 20.0          |
| `calibration_date` | Kalibrointipäivä (UTC, ms) | Long   | 1690123456000 |

## Triggerin Tiedot (TriggerInfo)

| Kenttä                      | Kuvaus                                      | Tyyppi  | Esimerkki     |
| ---------------------------- | ------------------------------------------- | ------- | ------------- |
| `trigger_timestamp`        | Aikaleima, jolloin trigger aktivoitui (UTC) | Long    | 1699876549999 |
| `pre_trigger_duration_ms`  | Aikaväli ennen tapahtumaa (ms)             | Long    | 500           |
| `post_trigger_duration_ms` | Aikaväli tapahtuman jälkeen (ms)          | Long    | 1000          |
| `trigger_value`            | Signaalin arvo, joka ylitti kynnyksen       | Double  | -75.2         |
| `triggered`                | Indikaattori, havaittiinko tapahtuma        | Boolean | true          |

## FFT-analyysin Tulokset (FFTResults)

| Kenttä            | Kuvaus                            | Tyyppi          | Esimerkki                |
| ------------------ | --------------------------------- | --------------- | ------------------------ |
| `frequencies_hz` | FFT:n laskema taajuusvektori      | Array of Double | [1419990000, 1420000000] |
| `amplitudes`     | Normalisoidut amplitudit (dBFS)   | Array of Double | [-10.4, -9.8]            |
| `phases`         | Vaiheet radiaaneina (valinnainen) | Array of Double | [1.2, 0.8]               |

## Analytiikan Mittarit (AnalysisMetrics)

| Kenttä                   | Kuvaus                                  | Tyyppi              | Esimerkki                 |
| ------------------------- | --------------------------------------- | ------------------- | ------------------------- |
| `signal_to_noise_ratio` | Laskettu SNR (dB)                       | Double              | 32.5                      |
| `burst_detected`        | Havaittu merkittävä signaalipoikkeama | Boolean             | true                      |
| `additional_metrics`    | Lisämittarit                           | Map<String, Double> | {"peak_freq": 1420001000} |

## Järjestelmän Tiedot (SystemInfo)

| Kenttä              | Kuvaus                                 | Tyyppi | Esimerkki    |
| -------------------- | -------------------------------------- | ------ | ------------ |
| `software_version` | Käytetyn ohjelmiston versio           | String | "v1.2.3"     |
| `hardware_info`    | Mittausjärjestelmän laitteistotiedot | String | "RTL-SDR v3" |
| `firmware_version` | Käytetyn laiteohjelmiston versio      | String | "1.0.5"      |

## Optimointistrategiat

- Raw_data pakataan bytes-muotoon, mikä vähentää tallennustilaa.
- Kaikki aikaleimat ovat UTC, mikä selkeyttää analyysia.
- FFT-amplitudit normalisoidaan dBFS:ään, jotta signaaleja voidaan vertailla suoraan.
- trigger_offset_ms helpottaa triggerin ajoituksen ymmärtämistä.

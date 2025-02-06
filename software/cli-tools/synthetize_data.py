from pyspark.sql import SparkSession
from pyspark.sql.types import (StructType, StructField, StringType, LongType, IntegerType, DoubleType,
                               BooleanType, ArrayType, MapType, BinaryType)
from pyspark.sql.functions import to_date, hour, from_unixtime, col
import uuid
import random
import struct
import time
import numpy as np
import os

# Aseta satunnaisuuden siemen toistettavuuden varmistamiseksi
random.seed(42)
np.random.seed(42)

# Luo SparkSession
spark = SparkSession.builder \
    .appName("RFMeasurementSyntheticData_OneHour") \
    .getOrCreate()

# Määrittele skeema, joka vastaa Avro-skeemaa
schema = StructType([
    StructField("measurement_id", StringType(), False),
    StructField("timestamp", LongType(), False),  # timestamp-millis
    StructField("duration_ms", LongType(), False),
    StructField("center_frequency_hz", LongType(), False),
    StructField("sample_rate_hz", LongType(), False),
    StructField("antenna_info",
                StructType([
                    StructField("antenna_type", StringType(), False),
                    StructField("lna_gain_db", DoubleType(), False),
                    StructField("calibration_date", LongType(), False)
                ]), False),
    StructField("environmental",
                StructType([
                    StructField("temperature_c", DoubleType(), False),
                    StructField("humidity_percent", DoubleType(), False),
                    StructField("rfi_noise_level_dbm", DoubleType(), False)
                ]), False),
    StructField("trigger_info",
                StructType([
                    StructField("trigger_timestamp", LongType(), False),
                    StructField("pre_trigger_duration_ms", LongType(), False),
                    StructField("post_trigger_duration_ms", LongType(), False),
                    StructField("trigger_value", DoubleType(), False),
                    StructField("triggered", BooleanType(), False),
                    StructField("trigger_offset_ms", LongType(), False)
                ]), False),
    StructField("event_id", StringType(), True),
    StructField("raw_data", BinaryType(), False),
    StructField("fft_results",
                StructType([
                    StructField("frequencies_hz", ArrayType(DoubleType()), False),
                    StructField("amplitudes", ArrayType(DoubleType()), False),
                    StructField("phases", ArrayType(DoubleType()), True)
                ]), False),
    StructField("analysis_metrics",
                StructType([
                    StructField("signal_to_noise_ratio", DoubleType(), False),
                    StructField("burst_detected", BooleanType(), False),
                    StructField("additional_metrics", MapType(StringType(), DoubleType()), False)
                ]), False),
    StructField("system_info",
                StructType([
                    StructField("system_version", StringType(), False),
                    StructField("library_info", StringType(), False)
                ]), True)
])

# Funktio synteettisen raw datan ja FFT-tulosten generointiin:
def generate_raw_data_and_fft(sample_rate, center_freq):
    num_samples = 256
    # Generoidaan peruskohinataso (normaalijakauma)
    noise = np.random.normal(0, 0.1, num_samples * 2)

    # Simuloidaan signaali (esim. siniaalto, jonka taajuus on suhteessa keskitaajuuteen)
    signal_freq = center_freq * 0.0001  # Esim. signaali on 0.01% keskitaajuudesta
    t = np.linspace(0, num_samples / sample_rate, num_samples * 2, endpoint=False)
    signal = 0.5 * np.sin(2 * np.pi * signal_freq * t)

    # Yhdistetään kohina ja signaali
    data = noise + signal

    # Pakataan little-endian 32-bit float -muodossa
    binary_data = struct.pack('<' + 'f' * len(data), *data)

    # Lasketaan FFT
    fft_result = np.fft.fft(data)
    frequencies = np.fft.fftfreq(len(data)) * sample_rate  # Skaalataan taajuudet
    amplitudes = np.abs(fft_result) / num_samples  # Normalisoidaan amplitudit
    phases = np.angle(fft_result)

    return bytearray(binary_data), frequencies.tolist(), amplitudes.tolist(), phases.tolist()


# Määritä simulaation parametrit
num_events = 720  # Tapahtumia tunnissa (trigger joka 5. sekunti)
base_timestamp = int(time.time() * 1000)  # Mittauksen aloitusaika millisekunneissa (UTC)
event_interval_ms = 5000  # 5 sekuntia triggerien väli

# Vakioarvot laitteiston osalta
constant_measurement_id = str(uuid.uuid4())  # Sama mittausistunto koko tunnin ajan
constant_center_frequency = 1420000000  # 1.42 GHz
constant_sample_rate = 2400000  # 2.4 MS/s
constant_antenna_info = {
    "antenna_type": "Yagi",
    "lna_gain_db": 15.0,
    "calibration_date": base_timestamp - 86400000  # Kalibrointi 1 päivä sitten
}

# Ympäristöolosuhteet
constant_environmental = {
    "temperature_c": 20.0,
    "humidity_percent": 50.0,
    "rfi_noise_level_dbm": -80.0
}

# Järjestelmäinfo
constant_system_info = {
    "system_version": "1.0.1",
    "library_info": "pyrtlsdr-0.3.1, pyspark-3.4.1, numpy-1.24.3" #tarkennettu versioita
}

# Luo synteettinen data
synthetic_data = []
for i in range(num_events):
    event_timestamp = base_timestamp + i * event_interval_ms
    duration_ms = 2000
    trigger_ts = event_timestamp + random.randint(0, duration_ms)
    trigger_value = random.uniform(0.5, 2.0)
    trigger_offset_ms = trigger_ts - event_timestamp
    event_id = str(uuid.uuid4())

    # Käytä funktiota raakadatan ja FFT:n luomiseen
    raw_data_bytes, frequencies, amplitudes, phases = generate_raw_data_and_fft(constant_sample_rate, constant_center_frequency)

    #Laske SNR raakadatan perusteella:
    signal_power = np.mean(np.array(amplitudes)**2)
    noise_power = np.var(np.random.normal(0, 0.1, len(amplitudes)))
    snr = 10 * np.log10(signal_power/noise_power) if noise_power> 0 else 20.0

    record = {
        "measurement_id": constant_measurement_id,
        "timestamp": event_timestamp,
        "duration_ms": duration_ms,
        "center_frequency_hz": constant_center_frequency,
        "sample_rate_hz": constant_sample_rate,
        "antenna_info": constant_antenna_info,
        "environmental": constant_environmental,
        "trigger_info": {
            "trigger_timestamp": trigger_ts,
            "pre_trigger_duration_ms": 500,
            "post_trigger_duration_ms": 500,
            "trigger_value": trigger_value,
            "triggered": True,
            "trigger_offset_ms": trigger_offset_ms
        },
        "event_id": event_id,
        "raw_data": bytes(raw_data_bytes),
        "fft_results": {
            "frequencies_hz": frequencies,
            "amplitudes": amplitudes,
            "phases": phases  # phases on nyt aina mukana.  Jos sitä ei tarvita, jätä tyhjäksi listaksi: []
        },
        "analysis_metrics": {
            "signal_to_noise_ratio": snr,
            "burst_detected": True if max(amplitudes) > 0.2 else False,  # Burst-logiikka
            "additional_metrics": {"metric1": random.uniform(0, 1), "metric2": random.uniform(0, 1)}
        },
        "system_info": constant_system_info
    }
    synthetic_data.append(record)

# Luo DataFrame synteettisestä datasta
df = spark.createDataFrame(synthetic_data, schema=schema)

# Derivoi measurement_date ja measurement_hour
df = df.withColumn("measurement_date", to_date((col("timestamp") / 1000).cast("timestamp")))
df = df.withColumn("measurement_hour", hour((col("timestamp") / 1000).cast("timestamp")))

# Näytä esimerkkirivit
df.show(5, truncate=False)

# Tallenna DataFrame S3:lle partitioiden mukaan
s3_output_path = os.environ.get("S3_OUTPUT_PATH", "s3://logtopus/path/to/synthetic-data") 
try:
    df.write.partitionBy("measurement_date", "measurement_id") \
        .mode("overwrite") \
        .parquet(s3_output_path)
    print(f"Data saved to {s3_output_path}")
except Exception as e:
    print(f"Error writing to S3: {e}")

spark.stop()

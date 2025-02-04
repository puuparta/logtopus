from pyspark.sql import SparkSession
from pyspark.sql.types import (StructType, StructField, StringType, LongType, IntegerType, DoubleType, 
                               BooleanType, ArrayType, MapType, BinaryType)
from pyspark.sql.functions import to_date, hour, from_unixtime, col
import uuid
import random
import struct
import time

spark = SparkSession.builder \
    .appName("RFMeasurementSyntheticData_OneHour") \
    .getOrCreate()

schema = StructType([
    StructField("measurement_id", StringType(), False),
    StructField("timestamp", LongType(), False),  
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

def generate_raw_data():
    num_samples = 256
    # Generoidaan 2*num_samples satunnaista float-arvoa väliltä -1.0 ja 1.0
    floats = [random.uniform(-1.0, 1.0) for _ in range(num_samples * 2)]
    # Pakataan little-endian 32-bit float -muodossa
    binary_data = struct.pack('<' + 'f' * len(floats), *floats)
    return bytearray(binary_data)

num_events = 720
base_timestamp = int(time.time() * 1000)  # mittauksen aloitusaika millisekunneissa (UTC)

# Vakioarvot laitteiston osalta
constant_measurement_id = str(uuid.uuid4())  # sama mittausistunto koko tunnin ajan
constant_center_frequency = 1420000000        # 1.42 GHz
constant_sample_rate = 2400000                # 2.4 MS/s
constant_antenna_info = {
    "antenna_type": "Yagi",  # vakio
    "lna_gain_db": 15.0,     # esimerkkiarvo
    "calibration_date": base_timestamp - 86400000  # kalibrointi 1 päivä sitten
}

constant_environmental = {
    "temperature_c": 20.0,
    "humidity_percent": 50.0,
    "rfi_noise_level_dbm": -80.0
}
constant_system_info = {
    "system_version": "1.0.0",
    "library_info": "pyrtlsdr-0.1, pyspark-3.3.0"
}

synthetic_data = []
event_interval_ms = 5000  # 5 sekuntia triggerien väli

for i in range(num_events):
    event_timestamp = base_timestamp + i * event_interval_ms
    duration_ms = 2000
    trigger_ts = event_timestamp + random.randint(0, duration_ms)
    trigger_value = random.uniform(0.5, 2.0)
    trigger_offset_ms = trigger_ts - event_timestamp
    event_id = str(uuid.uuid4())
    
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
            "pre_trigger_duration_ms": 500,   # esim. 500 ms ennen triggeriä
            "post_trigger_duration_ms": 500,  # 500 ms triggerin jälkeen
            "trigger_value": trigger_value,
            "triggered": True,
            "trigger_offset_ms": trigger_offset_ms
        },
        "event_id": event_id,
        "raw_data": bytes(generate_raw_data()),
        "fft_results": {
            "frequencies_hz": [random.uniform(0, 1200) for _ in range(50)],
            "amplitudes": [random.uniform(-40, 0) for _ in range(50)],
            "phases": None  # Phases jätetään nulliksi, ellei tarvita
        },
        "analysis_metrics": {
            "signal_to_noise_ratio": random.uniform(5.0, 20.0),
            "burst_detected": random.choice([True, False]),
            "additional_metrics": {"metric1": random.uniform(0, 1), "metric2": random.uniform(0, 1)}
        },
        "system_info": constant_system_info
    }
    synthetic_data.append(record)

df = spark.createDataFrame(synthetic_data, schema=schema)

df = df.withColumn("measurement_date", to_date((col("timestamp")/1000).cast("timestamp")))
df = df.withColumn("measurement_hour", hour((col("timestamp")/1000).cast("timestamp")))

df.show(5, truncate=False)

s3_output_path = "s3://your-bucket/path/to/synthetic-data"
df.write.partitionBy("measurement_date", "measurement_id") \
    .mode("overwrite") \
    .parquet(s3_output_path)

spark.stop()

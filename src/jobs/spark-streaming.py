from time import sleep

import pyspark
from pyspark.sql import SparkSession
from pyspark.sql.types import StructField, StringType, StructType, FloatType
from pyspark.sql.functions import from_json, col, when, udf
from config.config import config


def start_streaming(spark):
    topic = 'customers_review'
    while True:
        try:

            stream_df = spark.readStream.format("socket").option("host", "0.0.0.0").option("port", 9999).load()

            schema = StructType([
                StructField("review_id", StringType()),
                StructField("user_id", StringType()),
                StructField("business_id", StringType()),
                StructField("stars", FloatType()),
                StructField("date", StringType()),
                StructField("text", StringType())
            ])

            stream_df = stream_df.select(from_json(col('value'), schema).alias("data")).select(("data.*"))

            kafka_df = stream_df.selectExpr("CAST(review_id AS STRING) AS key", "to_json(struct(*)) AS value")

            query = (kafka_df.writeStream
                     .format("kafka")
                     .option("kafka.bootstrap.servers", config['kafka']['bootstrap.servers'])
                     .option("kafka.security.protocol", config['kafka']['security.protocol'])
                     .option('kafka.sasl.mechanism', config['kafka']['sasl.mechanisms'])
                     .option('kafka.sasl.jaas.config',
                             'org.apache.kafka.common.security.plain.PlainLoginModule required username="{username}" '
                             'password="{password}";'.format(
                                 username=config['kafka']['sasl.username'],
                                 password=config['kafka']['sasl.password']
                             ))
                     .option('checkpointLocation', '/tmp/checkpoint')
                     .option('topic', topic)
                     .start()  # Inicia el stream
                     )

            query.awaitTermination()  # Espera a que termine el stream

        except Exception as e:
            print(f'Exception encountered: {e}. Retrying in 10 seconds')
            sleep(10)


if __name__ == "__main__":
    spark_conn = SparkSession.builder.appName("SocketStreamConsumer").getOrCreate()

    start_streaming(spark_conn)

from __future__ import annotations

from pyspark.sql import SparkSession


def main() -> int:
    spark = (
        SparkSession.builder.appName("shared_catalog_write_smoke")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )

    spark.sql("CREATE NAMESPACE IF NOT EXISTS local.test")

    # Make the smoke deterministic and rerunnable
    spark.sql("DROP TABLE IF EXISTS local.test.catalog_smoke")

    spark.sql(
        """
        CREATE TABLE local.test.catalog_smoke (
            id INT,
            name STRING
        )
        USING iceberg
        """
    )

    spark.sql(
        """
        INSERT INTO local.test.catalog_smoke VALUES
            (1, 'spark'),
            (2, 'iceberg')
        """
    )

    rows = spark.sql("SELECT * FROM local.test.catalog_smoke ORDER BY id").collect()
    for row in rows:
        print(f"{row['id']}\t{row['name']}")

    spark.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

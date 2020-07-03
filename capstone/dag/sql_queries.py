class SqlQueries:
    count_records_query = """
        SELECT
            COUNT(1) AS total_records
        FROM {table_name};
    """

    streams_copy_query = """
        COPY {table_name}
        FROM '{s3_path}'
        ACCESS_KEY_ID '{key}'
        SECRET_ACCESS_KEY '{secret}'
        REGION AS 'us-west-1'
        IGNOREHEADER 1
        CSV;
    """

    enrich_streams_query = """
        SELECT
            track_name,
            artist AS artist_name,
            url AS track_url
        FROM streams_staging
        WHERE date = '{date}'
    """

    streams_qa_qyery = """
        SELECT
            COUNT(1) AS total_rows
        FROM streams_staging
        WHERE date = '{date}'
    """

    s3_to_redshift_query = """
        CREATE TEMP TABLE {table_name}_temp (LIKE {table_name});

        COPY {table_name}_temp
        FROM '{s3_path}'
        ACCESS_KEY_ID '{key}'
        SECRET_ACCESS_KEY '{secret}'
        REGION AS 'us-west-1'
        DELIMITER ','
        CSV;

        DELETE FROM {table_name}
        USING {table_name}_temp
        WHERE {table_name}.track_url = {table_name}_temp.track_url;

        INSERT INTO {table_name}
        SELECT *
        FROM {table_name}_temp;
    """

    upsert_tracks_query = """
        CREATE TEMP TABLE tracks_temp (LIKE tracks);

        INSERT INTO tracks_temp (
            track_url,
            track_name,
            duration,
            popularity,
            explicit
            )
        SELECT DISTINCT
            t.track_url,
            t.track_name,
            t.duration,
            t.popularity,
            t.explicit
        FROM tracks_metadata t
        LEFT JOIN streams_staging s
            ON s.url = t.track_url
        WHERE s.date = '{date}';

        INSERT INTO tracks (
            track_url,
            track_name,
            duration,
            popularity,
            explicit
            )
        SELECT
            tt.track_url,
            tt.track_name,
            tt.duration,
            tt.popularity,
            tt.explicit
        FROM tracks_temp tt
        LEFT JOIN tracks t
            ON tt.track_url = t.track_url
        WHERE t.track_name IS NULL;
    """

    upsert_streams_query = """
        CREATE TEMP TABLE streams_temp (LIKE streams);

        INSERT INTO streams_temp
        SELECT DISTINCT
            ss.date AS event_stamp_date,
            ss.position AS position,
            t.track_id AS track_id,
            ss.artist AS artist_name,
            ss.region AS region_name,
            ss.streams stream_count
        FROM streams_staging ss
        LEFT JOIN tracks t
            ON ss.url = t.track_url
        WHERE ss.date = '{date}'
        ORDER BY ss.position;


        DELETE FROM streams
        USING streams_temp
        WHERE streams.event_stamp_date = streams_temp.event_stamp_date
            AND streams.position = streams_temp.position;

        INSERT INTO streams
        SELECT *
        FROM streams_temp;
    """
from datetime import datetime, timedelta
import pendulum
import os
from airflow.decorators import dag
from airflow.operators.dummy_operator import DummyOperator

from plugins.project_operators.stage_redshift import StageToRedshiftOperator
from plugins.project_operators.load_fact import LoadFactOperator
from plugins.project_operators.load_dimension import LoadDimensionOperator
from plugins.project_operators.data_quality import DataQualityOperator
from common.sql_statements import SqlQueries
from airflow.operators.postgres_operator import PostgresOperator

default_args = {
    'owner': 'udacity',
    'start_date': pendulum.now(),
    'depends_on_past': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=1),
}

@dag(
    default_args=default_args,
    description='Load and transform data in Redshift with Airflow',
    schedule_interval='0 * * * *',
    catchup=False,
    max_active_runs=1
)
def final_project():

    start_operator = DummyOperator(task_id='Begin_execution')
    
    create_staging_events_table = PostgresOperator(
        task_id="create_staging_events_table",
        postgres_conn_id="redshift",
        sql=SqlQueries.create_staging_events
    )

    create_staging_songs_table = PostgresOperator(
        task_id="create_staging_songs_table",
        postgres_conn_id="redshift",
        sql=SqlQueries.create_staging_songs
    )

    create_songplay_table = PostgresOperator(
        task_id="create_songplay_table",
        postgres_conn_id="redshift",
        sql=SqlQueries.create_songplay_table
    )

    create_user_table = PostgresOperator(
        task_id="create_user_table",
        postgres_conn_id="redshift",
        sql=SqlQueries.create_user_table
    )

    create_song_table = PostgresOperator(
        task_id="create_song_table",
        postgres_conn_id="redshift",
        sql=SqlQueries.create_song_table
    )

    create_artist_table = PostgresOperator(
        task_id="create_artist_table",
        postgres_conn_id="redshift",
        sql=SqlQueries.create_artist_table
    )

    create_time_table = PostgresOperator(
        task_id="create_time_table",
        postgres_conn_id="redshift",
        sql=SqlQueries.create_time_table
    )

    stage_events_to_redshift = StageToRedshiftOperator(
        task_id='Stage_Events',
        redshift_conn_id = 'redshift',
        aws_credentials_id="aws_credentials",
        table='staging_events_table',
        s3_bucket='udacity-ali-m4',
        s3_key='log-data'
    )
 
    stage_songs_to_redshift = StageToRedshiftOperator(
        task_id='Stage_Songs',
        redshift_conn_id = 'redshift',
        aws_credentials_id="aws_credentials",
        table='staging_songs_table',
        s3_bucket='udacity-ali-m4',
        s3_key='song-data/A/A/A'
    )

    load_songplays_table = LoadFactOperator(
        task_id='Load_songplays_fact_table',
        redshift_conn_id='redshift',
        table='songplay_table',
        sql=SqlQueries.songplay_table_insert
        
    )

    load_user_dimension_table = LoadDimensionOperator(
        task_id='Load_user_dim_table',
        redshift_conn_id='redshift',
        table='user_table',
        sql=SqlQueries.user_table_insert,
        truncate_insert=True
    )

    load_song_dimension_table = LoadDimensionOperator(
        task_id='Load_song_dim_table',
        redshift_conn_id='redshift',
        table='song_table',
        sql=SqlQueries.song_table_insert,
        truncate_insert=True
    )

    load_artist_dimension_table = LoadDimensionOperator(
        task_id='Load_artist_dim_table',
        redshift_conn_id='redshift',
        table='artist_table',
        sql=SqlQueries.artist_table_insert,
        truncate_insert=True
    )

    load_time_dimension_table = LoadDimensionOperator(
        task_id='Load_time_dim_table',
        redshift_conn_id='redshift',
        table='time_table',
        sql=SqlQueries.time_table_insert,
        truncate_insert=True
    )

    run_data_quality_checks = DataQualityOperator(
        task_id='Run_data_quality_checks',
        redshift_conn_id='redshift',
        dq_checks=SqlQueries.data_quality_checks,
    )

    end_operator = DummyOperator(task_id='End_execution')


    start_operator >> create_staging_events_table >> stage_events_to_redshift >> load_songplays_table
    start_operator >> create_staging_songs_table >> stage_songs_to_redshift >> load_songplays_table
    start_operator >> create_user_table >> create_songplay_table >> load_songplays_table  
    start_operator >> create_song_table >> create_songplay_table >> load_songplays_table  
    start_operator >> create_artist_table >> create_songplay_table >> load_songplays_table  
    start_operator >> create_time_table >> create_songplay_table >> load_songplays_table  
     
    load_songplays_table >> load_song_dimension_table
    load_songplays_table >> load_user_dimension_table
    load_songplays_table >> load_artist_dimension_table
    load_songplays_table >> load_time_dimension_table

    load_user_dimension_table >> run_data_quality_checks >> end_operator
    load_artist_dimension_table >> run_data_quality_checks >> end_operator
    load_song_dimension_table >> run_data_quality_checks >> end_operator
    load_time_dimension_table >> run_data_quality_checks >> end_operator


final_project_dag = final_project()
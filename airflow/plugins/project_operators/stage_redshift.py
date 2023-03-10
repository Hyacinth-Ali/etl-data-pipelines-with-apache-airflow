from airflow.hooks.postgres_hook import PostgresHook
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from airflow.secrets.metastore import MetastoreBackend


class StageToRedshiftOperator(BaseOperator):
    ui_color = '#358140'
    template_fields = ("s3_key",)
    copy_sql = """
        COPY {}
        FROM '{}'
        ACCESS_KEY_ID '{}'
        SECRET_ACCESS_KEY '{}'
        REGION '{}'
        json '{}'
        dateformat '{}';
    """

    @apply_defaults
    def __init__(self,
                 redshift_conn_id = '',
                 aws_credentials_id='',
                 table='',
                 s3_bucket='',
                 s3_key='',
                 region='us-east-1',
                 data_format='auto',
                 date_format='auto',
                 *args, **kwargs):

        super(StageToRedshiftOperator, self).__init__(*args, **kwargs)
        # Map params here
        # Example:
        self.redshift_conn_id = redshift_conn_id
        self.aws_credentials_id = aws_credentials_id
        self.table = table
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.region=region
        self.data_format = data_format
        self.date_format = date_format

    def execute(self, context):

        metastoreBackend = MetastoreBackend()
        # Initialize aws and redshift connection variables to allow airflow 
        # perform tasks in AWS as well as Redshift
        aws_connection = metastoreBackend.get_connection(self.aws_credentials_id)
        redshift = PostgresHook(postgres_conn_id=self.redshift_conn_id)

        self.log.info("Clearing existing data in destination Redshift table")
        redshift.run("DELETE FROM {}".format(self.table))

        self.log.info("Copying data from S3 to Redshift")
        rendered_key = self.s3_key.format(**context)
        s3_path = "s3://{}/{}".format(self.s3_bucket, rendered_key)
        formatted_sql = StageToRedshiftOperator.copy_sql.format(
            self.table,
            s3_path,
            aws_connection.login,
            aws_connection.password,
            self.region,
            self.data_format,
            self.date_format,
        )
        redshift.run(formatted_sql)





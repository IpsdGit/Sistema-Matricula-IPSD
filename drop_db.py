import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
database_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:Postgre202625@localhost:5434/sistema_unah')
conn = psycopg2.connect(database_url)
cur = conn.cursor()
cur.execute('DROP SCHEMA public CASCADE; CREATE SCHEMA public;')
conn.commit()
conn.close()
print('DB Wiped')

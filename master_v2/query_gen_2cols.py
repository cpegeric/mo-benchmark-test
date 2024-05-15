import csv

from sqlalchemy import create_engine, select, Column, String, func
from sqlalchemy.orm import sessionmaker, declarative_base  # Updated import here
import random
import string
import time

DATABASE_URI = "mysql+pymysql://root:111@127.0.0.1:6001/a"
engine = create_engine(DATABASE_URI, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()


class Tbl(Base):
    __tablename__ = 'tbl'
    locals().update({f'a{i}': Column(String(10)) for i in range(1, 100)})
    a100 = Column(String(10), primary_key=True)


def get_column_values(table, column_name):
    column = getattr(table, column_name, None)
    if column is not None:
        try:
            query = session.query(column).distinct()
            # query = query.order_by(func.random())
            query = query.limit(1)
            values = query.all()
            values_list = [value[0] for value in values]
            return values_list
        except Exception as e:
            print(f"An error occurred: {e}")
            return []
    else:
        print(f"Column {column_name} not found in table.")
        return []


def run_queries(n=5000):
    total_time = 0
    with open('query_results.csv', mode='w', newline='') as result_file, open('query_strings.csv', mode='w',
                                                                              newline='') as query_file:
        result_writer = csv.writer(result_file)
        query_writer = csv.writer(query_file)
        for _ in range(n):
            conditions = []
            random_column_number = random.randint(1, 100)
            column_values = get_column_values(Tbl, f'a{random_column_number}')
            random_column_number2 = random.randint(1, 100)
            column_values2 = get_column_values(Tbl, f'a{random_column_number2}')
            attr = getattr(Tbl, f'a{random_column_number}', None)
            attr2 = getattr(Tbl, f'a{random_column_number2}', None)
            if attr is not None:
                conditions = [attr == column_values[0], attr2 == column_values2[0]]

            start_time = time.time()
            query = select(Tbl.a100).where(*conditions)
            results = session.execute(query).all()
            total_time += time.time() - start_time

            if len(results) > 0:
                query_str = str(query.compile(compile_kwargs={"literal_binds": True})).replace('\n', ' ')
                query_writer.writerow([query_str])

                flattened_result = [item for sublist in results for item in sublist]
                result_writer.writerow(flattened_result)

                # print(query_str)
                print(f"Found {len(results)} rows.")

        qps = n / total_time
        return qps


qps = run_queries()
print(f"QPS: {qps}")

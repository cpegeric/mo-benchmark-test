"""
create database a;
use a;

-- create table is done by the insert.py script
-- insert 100_000 rows into 'tbl' with batch size 10_000

CREATE INDEX idx using master ON tbl(
    a1, a2, a3, a4, a5, a6, a7, a8, a9, a10,
    a11, a12, a13, a14, a15, a16, a17, a18, a19, a20,
    a21, a22, a23, a24, a25, a26, a27, a28, a29, a30,
    a31, a32, a33, a34, a35, a36, a37, a38, a39, a40,
    a41, a42, a43, a44, a45, a46, a47, a48, a49, a50,
    a51, a52, a53, a54, a55, a56, a57, a58, a59, a60,
    a61, a62, a63, a64, a65, a66, a67, a68, a69, a70,
    a71, a72, a73, a74, a75, a76, a77, a78, a79, a80,
    a81, a82, a83, a84, a85, a86, a87, a88, a89, a90,
    a91, a92, a93, a94, a95, a96, a97, a98, a99
);
Query OK, 0 rows affected (39.78 sec)


"""
import time

from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
import random
import string

DATABASE_URI = "mysql+pymysql://root:111@127.0.0.1:6001/a"

engine = create_engine(DATABASE_URI, echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()


class Tbl(Base):
    __tablename__ = 'tbl'
    locals().update({f'a{i}': Column(String(10)) for i in range(1, 100)})
    a100 = Column(String(10), primary_key=True)


Base.metadata.create_all(engine)
session = Session()


def generate_random_string(length=10):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


def insert_random_rows(n=100_000, batch_size=1_000):
    print(f"Inserting {n} rows into 'tbl' with batch size {batch_size}.")
    for batch_start in range(0, n, batch_size):
        batch_data = []
        for _ in range(batch_size):
            data_dict = {f'a{i}': generate_random_string() for i in range(1, 101)}
            data = Tbl(**data_dict)
            batch_data.append(data)

        session.bulk_save_objects(batch_data)
        session.commit()
        print(f"Inserted {batch_start + batch_size} rows into 'tbl'.")


start = time.time()
insert_random_rows()
end = time.time()
print(f"Time taken to insert rows: {end - start} seconds.")

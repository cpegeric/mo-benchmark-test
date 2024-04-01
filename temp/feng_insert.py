
import binascii
import time
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

table_name = "speedtest"
vec_len = 128
num_inserts = 1000_000
max_duration_seconds = 6 * 60


def to_db_binary(value):
    if value is None:
        return value

    value = np.asarray(value, dtype='<f4')
    if value.ndim != 1:
        raise ValueError('expected ndim to be 1')

    return binascii.b2a_hex(value.tobytes()).decode('utf-8')


def run():
    engine = create_engine("mysql+mysqldb://root:111@127.0.0.1:6001/")
    Session = sessionmaker(bind=engine)
    session = Session()

    session.execute(text("DROP DATABASE IF EXISTS vecdb;"))
    session.commit()

    session.execute(text("CREATE DATABASE vecdb;"))
    session.execute(text("USE vecdb;"))
    session.execute(text("DROP TABLE IF EXISTS " + table_name + ";"))
    session.execute(text("CREATE TABLE " + table_name + "(id INT, one_k_vector VECF32(128));"))
    session.commit()

    start_time = time.time()
    sql_insert = text("INSERT INTO " + table_name + " (id, one_k_vector) VALUES (:id, decode(:data,'hex'));")
    for i in range(num_inserts):
        current_time = time.time()
        if current_time - start_time > max_duration_seconds:
            raise RuntimeError("Execution time exceeded 3 minutes. Panic and abort!")

        arr = np.random.rand(vec_len)
        arr = np.asarray(arr, dtype='<f')
        session.execute(sql_insert, {"id": i, "data": to_db_binary(arr)})

        if i % 1000 == 0:
            print(f"inserted {i} rows")
    session.commit()

    duration = time.time() - start_time
    print(f"Result: vector dim={vec_len} vectors "
          f"inserted={num_inserts} "
          f"insert/second={num_inserts / duration} "
          f"duration={duration}")


def main():
    try:
        run()
    except RuntimeError as e:
        print(e)


if __name__ == "__main__":
    main()
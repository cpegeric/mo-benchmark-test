"""
create database a;
use a;
create table t3(a int, b vecf32(128));
create index idx3 using ivfflat on t3(b) lists=500 op_type "vector_l2_ops";
"""
import binascii
import time

import sys
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def to_db_str(value):
    if value is None:
        return value

    value = np.asarray(value, dtype='<f4')
    if value.ndim != 1:
        raise ValueError('expected ndim to be 1')

    s = '[' + ','.join(str(x) for x in value) + ']'
    return s

def to_db_binary(value):
    if value is None:
        return value

    value = np.asarray(value, dtype='<f4')
    if value.ndim != 1:
        raise ValueError('expected ndim to be 1')

    return binascii.b2a_hex(value.tobytes()).decode('utf-8')


def fvecs_read(filename, c_contiguous=True):
    fv = np.fromfile(filename, dtype=np.float32)
    if fv.size == 0:
        return np.zeros((0, 0))
    dim = fv.view(np.int32)[0]
    assert dim > 0
    fv = fv.reshape(-1, 1 + dim)
    fv = fv[:, 1:]
    if c_contiguous:
        fv = np.ascontiguousarray(fv)
    return fv


def run():
    # use pymysql
    engine = create_engine("mysql+pymysql://root:111@127.0.0.1:6001/a")
    Session = sessionmaker(bind=engine)
    session = Session()

    sql_insert = text("INSERT INTO t3 (a, b) VALUES (:id, :data);")

    start = time.time()
    vecList = fvecs_read("/Users/eric/github/mo-benchmark-test/dataset/sift/sift_base.fvecs")
    binVecList = []
    for i in range(0, len(vecList)):
        binVecList.append(to_db_str(vecList[i]))
    print(f"binary duration={time.time() - start}")

    rows = []
    for i in range(0, len(binVecList)):

        # sql_with_values = f"INSERT INTO t3 (a, b) VALUES ({i}, cast(unhex('{binVecList[i]}') as blob));"
        # print(sql_with_values)
        # return

        rows.append({"id": i, "data": binVecList[i]})
        if i % 1000 == 0:
            session.execute(sql_insert, rows)
            rows = []
            print(f"inserted {i}")

    if len(rows) > 0:
        session.execute(sql_insert, rows)
    # commit last
    session.commit()


def main():
    start = time.time()
    run()
    duration = time.time() - start
    print(f"duration={duration}")


if __name__ == "__main__":
    main()

import binascii
import struct
import time

import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

table_name = "speedtest"
sift_128_path = "/Users/arjunsunilkumar/Downloads/benchmark/1million128/sift/"

probe = "5"
topK = 100

expectedInsertDuration = 6 * 60
expectedRecall = 0.70
expectedQps = 35



# --------------------------------------------------------------------------------
def read_fvecs_file(filename, c_contiguous=True):
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


def read_ivecs_file(filename):
    with open(filename, 'rb') as f:
        vectors = []
        while True:
            bytes = f.read(4)
            if not bytes:
                break
            dim = struct.unpack('i', bytes)[0]
            vector = np.fromfile(f, dtype=np.int32, count=dim)
            vectors.append(vector)
    return vectors


def to_db_binary(value):
    if value is None:
        return value

    value = np.asarray(value, dtype='<f4')
    if value.ndim != 1:
        raise ValueError('expected ndim to be 1')

    return binascii.b2a_hex(value.tobytes()).decode('utf-8')


def calc_recall(count: int, ground_truth: list[np.ndarray], got: list[int]) -> float:
    ground_truth_set = set(np.concatenate(ground_truth))

    match = np.zeros(count)
    for idx, result in enumerate(got[:count]):
        if result in ground_truth_set:
            match[idx] = 1

    return np.mean(match)


# --------------------------------------------------------------------------------

def createTbl():
    engine = create_engine("mysql+mysqldb://root:111@127.0.0.1:6001/")
    Session = sessionmaker(bind=engine)
    session = Session()
    session.execute(text("DROP DATABASE IF EXISTS vecdb;"))
    session.commit()
    session.execute(text("CREATE DATABASE vecdb;"))
    session.execute(text("USE vecdb;"))
    session.execute(text("DROP TABLE IF EXISTS " + table_name + ";"))
    session.execute(text("CREATE TABLE " + table_name + "(id INT, vec VECF32(128));"))
    session.execute(text("SET GLOBAL experimental_ivf_index = 1;"))
    session.commit()
    return session


def runInserts(session):
    sql_insert = text("INSERT INTO " + table_name + " (id, vec) VALUES (:id, cast(unhex(:data) as blob) );")
    vecList = read_fvecs_file(sift_128_path + "sift_base.fvecs")

    # convert vectors to binary
    binVecList = []
    for i in range(0, len(vecList)):
        binVecList.append(to_db_binary(vecList[i]))

    # insert vectors
    start_time = time.time()
    for i in range(0, len(binVecList)):
        session.execute(sql_insert, {"id": i, "data": binVecList[i]})
        if i % 1000 == 0:
            if time.time() - start_time > expectedInsertDuration:
                raise RuntimeError("Execution time exceeded "+str(expectedInsertDuration)+". Panic and abort!")
            print(f"inserted {i} rows")
    session.commit()

    duration = time.time() - start_time
    print(f"Result: vector dim={128} vectors "
          f"inserted={len(binVecList)} "
          f"insert/second={len(binVecList) / duration} "
          f"duration={duration}")


def runCreateIndex(session):
    begin = time.time()
    session.execute(
        text("CREATE INDEX idx1 using ivfflat ON " + table_name + "(vec) lists=500 op_type \"vector_l2_ops\";"))
    session.commit()
    print(f"Index creation took {time.time() - begin:.4f}s")


def runQueries(session):
    query_vectors = read_fvecs_file(sift_128_path + 'sift_query.fvecs')
    expected_results = read_ivecs_file(sift_128_path + 'sift_groundtruth.ivecs')
    latencies, recalls = [], []
    session.execute(text("SET @probe_limit=" + probe + ";"))
    count = 0

    for i, vec in enumerate(query_vectors):
        # build query
        count += 1
        input_vector_str = '[' + ','.join(map(str, vec)) + ']'
        select_query = text("SELECT id FROM " + table_name + " ORDER BY l2_distance(vec, '" + input_vector_str + "') LIMIT 100;")

        # execute query
        start_time = time.perf_counter()
        result = session.execute(select_query)
        actual_result = [id for id, in result.fetchall()]
        expected_result = [expected_results[i].astype(np.float32)]
        duration = time.perf_counter() - start_time

        # metrics update
        latencies.append(duration)
        recall = calc_recall(topK, expected_result, actual_result)

        print(f"Query {i + 1} completed in {duration:.4f}s" + f" with recall: {recall:.4f}")
        recalls.append(recall)

    avg_latency = round(np.mean(latencies), 4)
    avg_recall = round(np.mean(recalls), 4)
    total_duration = round(np.sum(latencies), 4)
    qps = round(count / total_duration, 4)
    print(
        f"Recall: {avg_recall:.4f}, Total Duration: {total_duration:.4f}s, Avg Latency: {avg_latency:.4f}, QPS: {qps:.4f}")

    if avg_recall < expectedRecall:
        raise RuntimeError("Recall is less than "+str(expectedRecall)+". Panic and abort!")

    if qps < expectedQps:
        raise RuntimeError("QPS is less than "+str(expectedQps)+". Panic and abort!")


def main():
    try:
        session = createTbl()
        runInserts(session)
        runCreateIndex(session)
        runQueries(session)
    except RuntimeError as e:
        print(e)


if __name__ == "__main__":
    main()

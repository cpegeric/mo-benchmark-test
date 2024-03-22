import time

from sqlalchemy import create_engine, text
import numpy as np
import struct

def read_fvecs_file(filename, start=1, end=-1):
    vectors = []
    with open(filename, 'rb') as f:
        current_index = 1
        while True:
            bytes_read = f.read(4)
            if not bytes_read:
                break
            d, = struct.unpack('i', bytes_read)

            if start <= current_index <= end or (current_index >= start and end == -1):
                vec = np.fromfile(f, dtype=np.float32, count=d)
                vectors.append(vec)
            else:
                f.seek(d * 4, 1)

            if end != -1 and current_index >= end:
                break

            current_index += 1

    return vectors


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


def execute_knn_query(select_query, conn):
    result = conn.execute(text(select_query))
    return [id for id, in result.fetchall()]


def build_knn_query_template_with_ivfflat(input_vector_val, options):
    org_tbl_name = options['OrgTblName']
    org_tbl_id_name = options['OrgTblIdName']
    org_tbl_sk_name = options['OrgTblSkName']
    k = options['K']
    input_vector_str = '[' + ','.join(map(str, input_vector_val)) + ']'
    if options['DBType'] == 'mysql':
        sel_qry = f"SELECT {org_tbl_id_name} FROM {org_tbl_name} ORDER BY l2_distance({org_tbl_sk_name},'{input_vector_str}') ASC LIMIT {k};"
    else:
        sel_qry = f"SELECT {org_tbl_id_name}-1 FROM {org_tbl_name} ORDER BY {org_tbl_sk_name}<->'{input_vector_str}' ASC LIMIT {k};"
    return sel_qry


def exec_set_params(conn):
    probe_val = options['ProbeVal']
    if options['DBType'] == 'mysql':
        set_qry = f"SET @probe_limit={probe_val};"
    else:
        set_qry = f"SET ivfflat.probes={probe_val};"
    conn.execute(text(set_qry))


def calc_recall(count: int, ground_truth: list[np.ndarray], got: list[int]) -> float:
    ground_truth_set = set(np.concatenate(ground_truth))

    match = np.zeros(count)
    for idx, result in enumerate(got[:count]):
        if result in ground_truth_set:
            match[idx] = 1

    return np.mean(match)


if __name__ == "__main__":
    query_vectors = read_fvecs_file('/Users/arjunsunilkumar/Downloads/benchmark/1million128/sift/sift_query.fvecs')
    expected_results = read_ivecs_file(
        '/Users/arjunsunilkumar/Downloads/benchmark/1million128/sift/sift_groundtruth.ivecs')
    actual_results = []

    options = {
        # "DBType": "postgres",
        # "DbName": "postgres",
        "DBType": "mysql",
        "DbName": "a",
        "OrgTblName": "t3",
        "OrgTblIdName": "a",
        "OrgTblSkName": "b",
        "ProbeVal": 5,
        "K": 100,
    }

    if options["DBType"] == "mysql":
        engine = create_engine("mysql+mysqldb://root:111@127.0.0.1:6001/" + options["DbName"])
    else:
        engine = create_engine("postgresql+psycopg2://postgres:111@127.0.0.1:5432/" + options["DbName"])

    latencies, recalls = [], []
    count = 0
    with engine.connect() as conn:
        exec_set_params(conn)
        for i, vec in enumerate(query_vectors):
            count += 1
            select_query = build_knn_query_template_with_ivfflat(vec, options)
            start_time = time.perf_counter()
            # print(select_query)
            # break
            actual_result = execute_knn_query(select_query, conn)
            duration = time.perf_counter() - start_time

            latencies.append(duration)
            actual_results.append(actual_result)
            recall = calc_recall(options["K"], [expected_results[i].astype(np.float32)], actual_result)

            print(f"Query {i + 1} completed in {duration:.4f}s" +
                  f" with recall: {recall:.4f}")
            # print(f"Actual Result: {actual_result}")
            # print(f"Expected Result: {expected_results[i].tolist()}")
            # break
            recalls.append(recall)
            if i == 1000:
                break

        avg_latency = round(np.mean(latencies), 4)
        avg_recall = round(np.mean(recalls), 4)
        total_duration = round(np.sum(latencies), 4)
        qps = round(count / total_duration, 4)
        print(
            f"Recall: {avg_recall:.4f}, Total Duration: {total_duration:.4f}s, Avg Latency: {avg_latency:.4f}, QPS: {qps:.4f}")

import time
from sqlalchemy import create_engine, text
import numpy as np
import struct
import concurrent.futures

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


def exec_set_params(conn, options):
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


def execute_query_batch(start_index, end_index, db_url, query_vectors, expected_results, options):
    latencies = []
    recalls = []
    count = 0

    engine = create_engine(db_url)
    with engine.connect() as conn:
        exec_set_params(conn, options)

        for i in range(start_index, end_index):
            count += 1
            select_query = build_knn_query_template_with_ivfflat(query_vectors[i], options)

            start_time = time.perf_counter()
            actual_result = execute_knn_query(select_query, conn)
            duration = time.perf_counter() - start_time

            latencies.append(duration)

            recall = calc_recall(options["K"], [expected_results[i].astype(np.float32)], actual_result)
            recalls.append(recall)

            if i % 100 == 0:
                print(f"Processed {i} queries in range {start_index}-{end_index}")

    total_duration = sum(latencies)
    return latencies, recalls, count, total_duration


def main():
    query_vectors = read_fvecs_file('/Users/arjunsunilkumar/Downloads/benchmark/1million/gist/gist_query.fvecs')
    expected_results = read_ivecs_file(
        '/Users/arjunsunilkumar/Downloads/benchmark/1million/gist/gist_groundtruth.ivecs')

    options = {
        # "DBType": "postgres",
        # "DbName": "postgres",
        "DBType": "mysql",
        "DbName": "a",
        "OrgTblName": "t5",
        "OrgTblIdName": "a",
        "OrgTblSkName": "b",
        "ProbeVal": 10,
        "K": 100,
        "parallelism": 4,
    }

    if options["DBType"] == "mysql":
        db_url = "mysql+mysqldb://root:111@127.0.0.1:6001/" + options["DbName"]
    else:
        db_url = "postgresql+psycopg2://postgres:111@127.0.0.1:5432/" + options["DbName"]

    num_queries = len(query_vectors)
    batch_size = num_queries // options["parallelism"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=options["parallelism"]) as executor:
        futures = []
        for i in range(options["parallelism"]):
            start_index = i * batch_size
            end_index = min(start_index + batch_size, num_queries)
            futures.append(
                executor.submit(execute_query_batch, start_index, end_index, db_url, query_vectors, expected_results,
                                options))

        results = [f.result() for f in futures]

    all_latencies = [lat for res in results for lat in res[0]]
    all_recalls = [rec for res in results for rec in res[1]]
    total_queries = sum(res[2] for res in results)
    max_duration_of_all_threads = max(res[3] for res in results)

    avg_latency = round(np.mean(all_latencies), 4)
    avg_recall = round(np.mean(all_recalls), 4)
    qps = round(total_queries / max_duration_of_all_threads, 4)

    print(
        f"Recall: {avg_recall:.4f}, Max Duration among all threads: {max_duration_of_all_threads:.4f}s, Avg Latency: {avg_latency:.4f}, QPS: {qps:.4f}")


if __name__ == "__main__":
    main()

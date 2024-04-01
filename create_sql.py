from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def run():
    db_name = "a"
    org_tbl_name = "t3"
    org_tbl_sk_name = "b"
    org_tbl_pk_name = "a"
    original_tbl_vec_idx_name = "idx3"
    input_vector_val = "[-0.00038528442, -0.01965332, 0.00013542175, -0.030883789, 0.014160156, -0.02355957, -0.037841797, 0.026611328, -0.0016784668, -0.0032958984, 0.015075684, -0.0047912598, 0.012390137, -0.021240234, 0.017456055, 0.020385742, 0.007537842, -0.01159668, 0.020385742, -0.0146484375, 0.0048217773, 0.021118164, 0.03515625, 0.018554688, -0.010192871, 0.018798828, 0.023071289, -0.02734375, 0.020629883, 0.0038757324, -0.009765625, 0.017578125, 0.002319336, 0.0065307617, -0.011169434, 0.020507812, -0.018066406, -0.016601562, -0.007507324, -0.0068969727, -0.029174805, 0.004486084, 0.0017929077, -0.008361816, 0.025390625, -0.01574707, 0.00049972534, 0.024780273, -0.008300781, -0.005493164, 0.025634766, 0.003479004, 0.0075683594, 0.028808594, 0.029296875, 0.018188477, 0.0020141602, 0.01574707, -0.0019454956, 0.016601562, -0.014953613, 0.005859375, 0.002822876, -0.0019836426, -0.004699707, 0.014221191, -0.0004749298, -0.003616333, -0.020629883, -0.015136719, 0.0134887695, 0.017333984, -0.028808594, 0.0006713867, 0.029785156, -0.0034332275, 0.0035247803, -0.004180908, -0.012207031, -0.008911133, 0.0016326904, -0.021484375, 0.0051879883, -0.014160156, -0.008239746, -0.007232666, -0.019897461, -0.001953125, 0.001335144, 0.01373291, -0.0017852783, -0.0044555664, -0.013305664, 0.0062561035, -0.05444336, -0.027832031, 0.014709473, 0.018554688, 0.005340576, 0.004058838, 0.007659912, 0.011108398, 0.0040283203, -0.0020141602, 0.015319824, -0.0065612793, 0.009765625, 0.005859375, -0.028686523, 0.024658203, 0.006225586, 0.0038452148, 0.02722168, 0.0026245117, 0.011169434, 0.007446289, -0.0078125, 0.020141602, 0.021484375, -0.03491211, 0.0023498535, 0.00012779236, -0.022460938, 0.0053710938, -0.013549805, 0.007080078, 0.006958008, -0.029663086]"
    probe_val = 1
    number_of_outputs = 1

    engine = create_engine("mysql+pymysql://root:111@127.0.0.1:6001/" + db_name)
    Session = sessionmaker(bind=engine)
    session = Session()

    get_meta_tables = text("select algo_table_type,index_table_name from mo_catalog.mo_indexes where name=:idx_name"
                           + " and column_name=:org_tbl_sk_name;")
    result = session.execute(get_meta_tables, {"idx_name": original_tbl_vec_idx_name,
                                               "org_tbl_sk_name": org_tbl_sk_name})
    meta_tables = result.fetchall()

    idx_metadata_tbl_name = ""
    idx_centroids_tbl_name = ""
    idx_entries_tbl_name = ""

    for row in meta_tables:
        algo_table_type, index_table_name = row
        if algo_table_type == 'metadata':
            idx_metadata_tbl_name = index_table_name
        elif algo_table_type == 'centroids':
            idx_centroids_tbl_name = index_table_name
        elif algo_table_type == 'entries':
            idx_entries_tbl_name = index_table_name

    # get the current centroid version
    get_centroid_version_query = f"select cast(__mo_index_val as BIGINT) from `{idx_metadata_tbl_name}` where __mo_index_key = 'version';"
    get_centroid_version = text(get_centroid_version_query)
    result = session.execute(get_centroid_version)
    centroid_version = result.fetchone()[0]  # Assuming there's only one row
    # print("centroid version", centroid_version)

    # get the centroids nearest to the input vector
    get_centroids = text("select `__mo_index_centroid_id` from `" + idx_centroids_tbl_name + "` "
                         + " where `__mo_index_centroid_version`=" + str(centroid_version) + " "
                         + " order by l2_distance(`__mo_index_centroid`, normalize_l2(\"" + input_vector_val + "\")) asc "
                         + " limit " + str(probe_val) + "")

    # get the nearest vectors in the centroid
    get_entries_pk = text("select distinct(`__mo_index_pri_col`) from `" + idx_entries_tbl_name + "` "
                          + " where `__mo_index_centroid_fk_version`=" + str(centroid_version) + " and "
                          + " `__mo_index_centroid_fk_id` in ( " + get_centroids.text + ") ")

    # print(get_entries_pk.text)

    # get the nearest vector from the original table
    get_original_tbl_vector = text("select * from `" + org_tbl_name + "` "
                                   + " where `" + org_tbl_pk_name + "` in ( " + get_entries_pk.text + ") "
                                   + " order by l2_distance(`" + org_tbl_sk_name + "`, \"" + input_vector_val + "\") "
                                   + "asc  limit " + str(number_of_outputs) + "")

    print(get_original_tbl_vector.text)
    # result = session.execute(get_original_tbl_vector)
    # rows = result.fetchall()
    # for row in rows:
    #     print(row)


run()

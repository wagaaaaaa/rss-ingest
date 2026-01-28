from feishu_client import create_bitable_record_with_id


def test_create_bitable_record_with_id_signature():
    assert callable(create_bitable_record_with_id)

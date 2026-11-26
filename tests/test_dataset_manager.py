from finsight.workspace_ui import dataset_summary


def test_no_dataset():
    assert dataset_summary({}) == {'name': 'No dataset loaded', 'validated': False, 'records': None}


def test_pending_dataset():
    assert dataset_summary({'financial_data': [1, 2], 'file_name': 'upload.csv'}) == {'name': 'upload.csv', 'validated': False, 'records': 2}


def test_validated_count_preferred():
    assert dataset_summary({'financial_data': [1, 2], 'validated_data': [1], 'file_name': 'sample'}) == {'name': 'sample', 'validated': True, 'records': 1}


def test_empty_validated_dataset():
    assert dataset_summary({'validated_data': []})['records'] == 0

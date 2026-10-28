"""Small offline unit tests for semantic validation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from validate_semantics import validate


def fixtures():
    catalog = {'schema': 'public', 'tables': [
        {'name': 'orders', 'columns': [{'name': 'order_id'}, {'name': 'order_status'}]},
        {'name': 'order_items', 'columns': [{'name': 'order_id'}, {'name': 'price'}]},
    ]}
    semantics = {'schema': 'public', 'tables': {
        'orders': {'description': 'Orders', 'grain': 'one per order'},
        'order_items': {'description': 'Items', 'grain': 'one per item'},
    }, 'metrics': {'revenue': {'description': 'Revenue', 'base_table': 'order_items',
                              'expression': 'SUM(order_items.price)',
                              'status_filter': "orders.order_status = 'delivered'"}},
                 'logical_relationships': [{'left': 'orders.order_id', 'right': 'order_items.order_id'}]}
    return catalog, semantics


def test_valid_semantics():
    catalog, semantics = fixtures()
    assert validate(catalog, semantics) == []


def test_unknown_column_detected():
    catalog, semantics = fixtures()
    semantics['metrics']['revenue']['expression'] = 'SUM(order_items.nonexistent)'
    assert any('unknown column order_items.nonexistent' in e for e in validate(catalog, semantics))


def test_missing_table_description_detected():
    catalog, semantics = fixtures()
    del semantics['tables']['orders']
    assert any('Missing table description: orders' in e for e in validate(catalog, semantics))

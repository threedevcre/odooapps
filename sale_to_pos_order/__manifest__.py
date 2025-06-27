{
    'name': 'Sale to POS Order',
    'version': '1.0',
    'depends': ['sale', 'point_of_sale'],
    'category': 'Sales',
    'description': 'Create POS Order from Sale Order',
    'data': [
        'views/sale_order_view.xml',
    ],
    'installable': True,
    'application': False,
}
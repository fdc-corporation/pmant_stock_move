{
    'name': 'Movimientos y Recepcion de equipos',
    'version': '1.0',
    'category': 'sale',
    'author': 'Kauza Digital',
    'website': 'https://kauzadigital.pe/',
    'license': 'LGPL-3',
    'description': 'Extension de PMANT para las recepciones de equipos de los clientes con relacion de movimiento y tareas',
    'depends': [
        'base', 'stock', 'pmant', 'maintenance', 'sale'
    ],
    'data': [
        "security/ir.model.access.csv",
        "view/inhrit_form_tarea_mantenimiento.xml",
        "view/view_conf_ubicaciones.xml",
        "view/inherit_categorias_productos.xml",
        "view/inherit_stock_picking.xml",
        "view/wizard_repuestos_consumidos.xml",
    ],
    'support': 'soporte@kauzadigital.pe',
    'application': False,
    'installable': True,
    'auto_install': False,
}

from odoo import models, fields, api, _
from odoo.exceptions import UserError




class RequerimientosStock(models.Model):
    _name = "requerimientos.stock"

    tarea_id = fields.Many2one("tarea.mantenimiento", string="Tarea de mantenimiento")
    product_id = fields.Many2one(
        "product.product",
        string="Producto",
        domain=[("type", "in", ["consu", "combo"])],
    )
    cantidad = fields.Integer(string="Cantidad")
    nota = fields.Text(string="Nota")
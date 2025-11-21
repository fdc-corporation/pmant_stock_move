from odoo import models, fields, api, _
from odoo.exceptions import UserError




class RequerimientosStock(models.Model):
    _inherit = "stock.move"

    tarea_id = fields.Many2one("tarea.mantenimiento", string="Tarea de mantenimiento")
    product_id = fields.Many2one(
        "product.template",
        string="Producto",
        domain=[("type", "in", ["consu", "combo"])],
        ondelete="set null",
    )
    cantidad = fields.Integer(string="Cantidad")
    unidad_medida = fields.Many2one(
        "uom.uom",
        string="Unidad de medida",
        ondelete="set null",
    )
    nota = fields.Text(string="Nota")